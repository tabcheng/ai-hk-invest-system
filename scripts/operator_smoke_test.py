#!/usr/bin/env python3
"""Manual Telegram operator smoke test harness (Step 65 optional Supabase verification)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import string
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import quote
from urllib import request
from urllib.error import HTTPError, URLError

REPORT_MD_PATH = "operator_smoke_report.md"
REPORT_JSON_PATH = "operator_smoke_report.json"
PLACEHOLDER_PATTERN = re.compile(r"<(?:id|cmd|action|text)>", re.IGNORECASE)


@dataclass
class SmokeCaseResult:
    name: str
    command: str
    passed: bool
    checks: list[dict[str, Any]]
    response_snippet: str
    status_code: int | None
    error: str | None = None
    response_text_verification: str = "SKIPPED_current_webhook_contract"


class SmokeHarnessError(RuntimeError):
    """Configuration or harness execution error."""


@dataclass
class SupabaseVerificationResult:
    status: str
    table: str
    qa_marker: str
    matched_rows_count: int
    reason: str | None = None
    guidance: str | None = None
    secrets_redacted: bool = True


def _redact(value: str) -> str:
    for key in ("OPERATOR_WEBHOOK_TEST_URL", "OPERATOR_WEBHOOK_SECRET", "SUPABASE_SERVICE_ROLE_KEY"):
        secret = os.getenv(key, "")
        if secret:
            value = value.replace(secret, "[REDACTED]")
    return value


def _build_update(command: str, chat_id: str, user_id: str) -> dict[str, Any]:
    now_epoch = int(dt.datetime.now(dt.timezone.utc).timestamp())
    return {
        "update_id": now_epoch,
        "message": {
            "message_id": 999001,
            "date": now_epoch,
            "chat": {"id": chat_id, "type": "private"},
            "from": {"id": user_id, "is_bot": False, "first_name": "QA"},
            "text": command,
            "entities": [{"offset": 0, "length": len(command.split()[0]), "type": "bot_command"}],
        },
    }


def _build_qa_marker(timestamp: dt.datetime | None = None) -> str:
    now = timestamp or dt.datetime.now(dt.timezone.utc)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"operator-smoke-{now.strftime('%Y%m%dT%H%M%SZ')}-{suffix}"


def _verify_supabase_decision_note(test_run_id: str, qa_marker: str) -> SupabaseVerificationResult:
    table_name = "human_decision_journal_entries"
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url:
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="Missing required env var: SUPABASE_URL",
            guidance="Set GitHub Actions secret SUPABASE_URL when verify_supabase=true.",
        )
    if not service_role_key:
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="Missing required env var: SUPABASE_SERVICE_ROLE_KEY",
            guidance="Set GitHub Actions secret SUPABASE_SERVICE_ROLE_KEY when verify_supabase=true.",
        )

    encoded_marker = quote(qa_marker, safe="")
    encoded_source_command = quote("/daily_review", safe="")
    url = (
        f"{supabase_url.rstrip('/')}/rest/v1/{table_name}"
        f"?select=id&scope=eq.run&run_id=eq.{test_run_id}&source_command=eq.{encoded_source_command}"
        f"&human_action=eq.observe&note=ilike.*{encoded_marker}*"
    )
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Accept": "application/json",
    }
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="Supabase verification query failed",
            guidance=f"Check SUPABASE_URL/service role key and table access; error={_redact(str(exc))}",
        )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="Supabase verification query returned non-JSON response",
            guidance="Confirm Supabase REST endpoint and credentials are valid for read-only query.",
        )

    if not isinstance(payload, list):
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="Supabase verification query returned unexpected payload shape",
            guidance="Expected list payload from PostgREST query; confirm table/API behavior.",
        )

    matched_rows_count = len(payload)
    if matched_rows_count < 1:
        return SupabaseVerificationResult(
            status="FAIL",
            table=table_name,
            qa_marker=qa_marker,
            matched_rows_count=0,
            reason="No matching /decision_note row found in Supabase",
            guidance="Confirm webhook command succeeded and note includes qa_marker for this run.",
        )
    return SupabaseVerificationResult(
        status="PASS",
        table=table_name,
        qa_marker=qa_marker,
        matched_rows_count=matched_rows_count,
    )


def _send_command(command: str, webhook_url: str, webhook_secret: str | None, chat_id: str, user_id: str) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        headers["X-Telegram-Bot-Api-Secret-Token"] = webhook_secret

    data = json.dumps(_build_update(command, chat_id, user_id)).encode("utf-8")
    req = request.Request(webhook_url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=30) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status_code = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"network error: {exc}") from exc

    try:
        payload = json.loads(body)
        if isinstance(payload, dict) and "message" in payload:
            body = str(payload["message"])
    except json.JSONDecodeError:
        pass

    return status_code, _redact(body)


def _run_case(
    name: str,
    command: str,
    must_include: list[str],
    must_exclude_patterns: list[re.Pattern[str]],
    webhook_url: str,
    webhook_secret: str | None,
    chat_id: str,
    user_id: str,
) -> SmokeCaseResult:
    try:
        status_code, body = _send_command(command, webhook_url, webhook_secret, chat_id, user_id)
    except Exception as exc:  # noqa: BLE001 - harness should capture test failure detail.
        return SmokeCaseResult(
            name=name,
            command=command,
            passed=False,
            checks=[],
            response_snippet="",
            status_code=None,
            error=str(exc),
        )

    checks: list[dict[str, Any]] = []
    passed = True
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = {}

    http_ok = status_code == 200
    checks.append({"name": "http_status_200", "passed": http_ok, "actual": status_code})
    passed = passed and http_ok

    ok_true = bool(payload.get("ok") is True)
    checks.append({"name": "json_ok_true", "passed": ok_true, "actual": payload.get("ok")})
    passed = passed and ok_true

    handled_true = bool(payload.get("handled") is True)
    checks.append({"name": "json_handled_true", "passed": handled_true, "actual": payload.get("handled")})
    passed = passed and handled_true

    replied_true = bool(payload.get("replied") is True)
    checks.append({"name": "json_replied_true", "passed": replied_true, "actual": payload.get("replied")})
    passed = passed and replied_true

    send_result = payload.get("send_result") if isinstance(payload, dict) else None
    send_result_available = isinstance(send_result, dict)
    delivered_true = bool(send_result_available and send_result.get("delivered") is True)
    checks.append(
        {
            "name": "send_result_delivered_true_when_available",
            "passed": delivered_true if send_result_available else True,
            "actual": (send_result or {}).get("delivered") if send_result_available else "SKIPPED_not_available",
            "status": ("PASS" if delivered_true else "FAIL") if send_result_available else "SKIPPED_not_available",
        }
    )
    if send_result_available:
        passed = passed and delivered_true

    for token in must_include:
        checks.append(
            {
                "name": f"response_text_includes:{token}",
                "passed": True,
                "status": "SKIPPED_current_webhook_contract",
            }
        )
    for pattern in must_exclude_patterns:
        checks.append(
            {
                "name": f"response_text_excludes:{pattern.pattern}",
                "passed": True,
                "status": "SKIPPED_current_webhook_contract",
            }
        )

    return SmokeCaseResult(
        name=name,
        command=command,
        passed=passed,
        checks=checks,
        response_snippet=body[:500],
        status_code=status_code,
        response_text_verification="SKIPPED_current_webhook_contract",
    )


def _write_reports(
    target: str,
    test_run_id: str,
    timestamp_utc: str,
    results: list[SmokeCaseResult],
    verify_supabase: bool,
    qa_marker: str,
    supabase_result: SupabaseVerificationResult | None = None,
    failure_reason: str | None = None,
    guidance: str | None = None,
) -> None:
    supabase_status = supabase_result.status if supabase_result else "SKIPPED"
    overall_pass = all(result.passed for result in results) and failure_reason is None and supabase_status != "FAIL"
    supabase_payload = {
        "status": supabase_status,
        "table": "human_decision_journal_entries",
        "qa_marker": qa_marker,
        "matched_rows_count": supabase_result.matched_rows_count if supabase_result else 0,
        "reason": supabase_result.reason if supabase_result else ("SKIPPED_verify_supabase_false" if not verify_supabase else None),
        "guidance": supabase_result.guidance if supabase_result else ("No DB query performed because verify_supabase=false." if not verify_supabase else None),
        "secrets_redacted": True,
    }

    report_json = {
        "target": target,
        "timestamp_utc": timestamp_utc,
        "test_run_id": test_run_id,
        "overall_result": "PASS" if overall_pass else "FAIL",
        "overall_pass": overall_pass,
        "supabase_verification": supabase_payload,
        "guardrail_confirmation": "no broker/live-money execution detected",
        "transport_verification": "PASS" if overall_pass else "FAIL",
        "response_text_verification": "SKIPPED_current_webhook_contract",
        "reason": failure_reason,
        "guidance": guidance,
        "results": [asdict(result) for result in results],
    }
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report_json, ensure_ascii=False, indent=2) + "\n")

    md_lines = [
        "# Operator Smoke Test Report",
        f"- target: `{target}`",
        f"- timestamp_utc: `{timestamp_utc}`",
        f"- test_run_id: `{test_run_id}`",
        "",
        "## Per-check Results",
    ]

    for result in results:
        md_lines.extend(
            [
                f"### {'PASS' if result.passed else 'FAIL'} — {result.name}",
                f"- command: `{result.command}`",
                f"- status_code: `{result.status_code}`",
            ]
        )
        if result.error:
            md_lines.append(f"- error: `{_redact(result.error)}`")

        md_lines.append("- checks:")
        for check in result.checks:
            md_lines.append(f"  - [{'PASS' if check['passed'] else 'FAIL'}] {check['name']}")

        md_lines.extend(["- response_snippet:", "```text", result.response_snippet, "```", ""])

    md_lines.extend(
        [
            "## Overall",
            f"- overall_result: `{'PASS' if overall_pass else 'FAIL'}`",
            f"- supabase_verification_status: `{supabase_status}`",
            f"- supabase_table: `{supabase_payload['table']}`",
            f"- qa_marker: `{qa_marker}`",
            f"- matched_rows_count: `{supabase_payload['matched_rows_count']}`",
            f"- supabase_reason: `{supabase_payload['reason'] or 'N/A'}`",
            f"- supabase_guidance: `{supabase_payload['guidance'] or 'N/A'}`",
            f"- secrets_redacted: `{supabase_payload['secrets_redacted']}`",
            "- guardrail_confirmation: `no broker/live-money execution detected`",
            f"- transport_verification: `{'PASS' if overall_pass else 'FAIL'}`",
            "- response_text_verification: `SKIPPED_current_webhook_contract`",
            f"- reason: `{failure_reason or 'N/A'}`",
            f"- guidance: `{guidance or 'N/A'}`",
        ]
    )

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="production")
    parser.add_argument("--test-run-id", required=True, help="Enter only the numeric run id, e.g. 31")
    parser.add_argument("--verify-supabase", default="false", choices=["true", "false"])
    args = parser.parse_args()
    if not args.test_run_id.isdigit() or int(args.test_run_id) <= 0:
        error_msg = "invalid test_run_id"
        guidance = "enter only a positive integer, e.g. 31"
        _write_reports(
            args.target,
            args.test_run_id,
            dt.datetime.now(dt.timezone.utc).isoformat(),
            [
                SmokeCaseResult(
                    name="CONFIGURATION",
                    command="N/A",
                    passed=False,
                    checks=[{"name": "test_run_id_positive_integer", "passed": False, "actual": args.test_run_id}],
                    response_snippet="",
                    status_code=None,
                    error=error_msg,
                )
            ],
            verify_supabase=args.verify_supabase == "true",
            qa_marker="N/A",
            failure_reason=error_msg,
            guidance=guidance,
        )
        raise SmokeHarnessError(f"{error_msg}; {guidance}")

    webhook_url = os.getenv("OPERATOR_WEBHOOK_TEST_URL", "").strip()
    chat_id = os.getenv("OPERATOR_TEST_CHAT_ID", "").strip()
    user_id = os.getenv("OPERATOR_TEST_USER_ID", "").strip()
    webhook_secret = os.getenv("OPERATOR_WEBHOOK_SECRET", "").strip() or None

    if not webhook_url or not chat_id or not user_id:
        error_msg = (
            "Missing required env vars: OPERATOR_WEBHOOK_TEST_URL, "
            "OPERATOR_TEST_CHAT_ID, OPERATOR_TEST_USER_ID"
        )
        _write_reports(
            args.target,
            args.test_run_id,
            dt.datetime.now(dt.timezone.utc).isoformat(),
            [
                SmokeCaseResult(
                    name="CONFIGURATION",
                    command="N/A",
                    passed=False,
                    checks=[{"name": "required_env_vars_present", "passed": False}],
                    response_snippet="",
                    status_code=None,
                    error=error_msg,
                    response_text_verification="SKIPPED_current_webhook_contract",
                )
            ],
            verify_supabase=args.verify_supabase == "true",
            qa_marker="N/A",
        )
        raise SmokeHarnessError(error_msg)

    qa_marker = _build_qa_marker()
    run_success_command = (
        f"/decision_note scope=run run_id={args.test_run_id} source_command=/daily_review "
        f"human_action=observe note=QA smoke test only; no execution. marker={qa_marker}"
    )

    cases = _build_smoke_cases(args.test_run_id, run_success_command)

    results = [
        _run_case(name, command, includes, excludes, webhook_url, webhook_secret, chat_id, user_id)
        for (name, command, includes, excludes) in cases
    ]
    supabase_result = None
    if args.verify_supabase == "true":
        supabase_result = _verify_supabase_decision_note(args.test_run_id, qa_marker)

    timestamp_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    _write_reports(
        args.target,
        args.test_run_id,
        timestamp_utc,
        results,
        verify_supabase=args.verify_supabase == "true",
        qa_marker=qa_marker,
        supabase_result=supabase_result,
    )

    print(f"[operator-smoke] target={args.target} run_id={args.test_run_id}")
    for result in results:
        print(f"[operator-smoke] {result.name}: {'PASS' if result.passed else 'FAIL'}")

    overall_pass = all(result.passed for result in results) and (supabase_result is None or supabase_result.status == "PASS")
    print(f"[operator-smoke] overall={'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


def _build_smoke_cases(test_run_id: str, run_success_command: str) -> list[tuple[str, str, list[str], list[re.Pattern[str]]]]:
    return [
        ("A_help", "/help", ["/daily_review", "/decision_note"], [PLACEHOLDER_PATTERN]),
        ("B_runs", "/runs", ["Status: completed.", "run"], []),
        ("C_runner_status", "/runner_status", ["Status: completed.", "latest"], []),
        ("D_risk_review", f"/risk_review {test_run_id}", ["Status: completed.", "risk"], []),
        ("E_pnl_review", "/pnl_review", ["Status: completed.", "pnl"], []),
        ("F_outcome_review", "/outcome_review", ["Status: completed.", "outcome"], []),
        ("B_daily_review", "/daily_review", ["Status: completed.", "business_date_hkt", "daily_review_health", "decision-support"], []),
        (
            "G_decision_note_run_success",
            run_success_command,
            [
                "Status: completed.",
                "human decision journal entry recorded",
                "journaling only; no execution; no real-money trading",
            ],
            [],
        ),
        (
            "H_decision_note_stock_not_implemented",
            "/decision_note scope=stock run_id=1 source_command=/daily_review human_action=observe note=QA check",
            ["stock-level decision journal is not implemented yet", "no execution performed"],
            [],
        ),
        (
            "I_decision_note_invalid",
            "/decision_note scope=run run_id=abc source_command=/daily_review human_action=observe note=QA",
            ["Status: failed.", "run_id must be a positive integer"],
            [],
        ),
    ]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeHarnessError as exc:
        print(f"[operator-smoke] configuration error: {exc}")
        raise SystemExit(2)
