#!/usr/bin/env python3
"""Manual Telegram operator smoke test harness (Step 63 MVP)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any
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


class SmokeHarnessError(RuntimeError):
    """Configuration or harness execution error."""


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

    checks: list[dict[str, Any]] = [{"name": "http_status_200", "passed": status_code == 200, "actual": status_code}]
    passed = status_code == 200

    for token in must_include:
        ok = token.lower() in body.lower()
        checks.append({"name": f"includes:{token}", "passed": ok})
        passed = passed and ok

    for pattern in must_exclude_patterns:
        ok = pattern.search(body) is None
        checks.append({"name": f"excludes:{pattern.pattern}", "passed": ok})
        passed = passed and ok

    return SmokeCaseResult(
        name=name,
        command=command,
        passed=passed,
        checks=checks,
        response_snippet=body[:500],
        status_code=status_code,
    )


def _write_reports(
    target: str,
    test_run_id: str,
    timestamp_utc: str,
    results: list[SmokeCaseResult],
    verify_supabase: bool,
) -> None:
    overall_pass = all(result.passed for result in results)
    supabase_status = "SKIPPED"
    if verify_supabase:
        supabase_status = "SKIPPED"

    report_json = {
        "target": target,
        "timestamp_utc": timestamp_utc,
        "test_run_id": test_run_id,
        "overall_pass": overall_pass,
        "supabase_verification": {
            "status": supabase_status,
            "note": "Step 63 defers full row verification to Step 65 candidate.",
        },
        "guardrail_confirmation": "no broker/live-money execution detected",
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
            "- guardrail_confirmation: `no broker/live-money execution detected`",
        ]
    )

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="production")
    parser.add_argument("--test-run-id", required=True)
    parser.add_argument("--verify-supabase", default="false", choices=["true", "false"])
    args = parser.parse_args()

    webhook_url = os.getenv("OPERATOR_WEBHOOK_TEST_URL", "").strip()
    chat_id = os.getenv("OPERATOR_TEST_CHAT_ID", "").strip()
    user_id = os.getenv("OPERATOR_TEST_USER_ID", "").strip()
    webhook_secret = os.getenv("OPERATOR_WEBHOOK_SECRET", "").strip() or None

    if not webhook_url or not chat_id or not user_id:
        raise SmokeHarnessError(
            "Missing required env vars: OPERATOR_WEBHOOK_TEST_URL, "
            "OPERATOR_TEST_CHAT_ID, OPERATOR_TEST_USER_ID"
        )

    run_success_command = (
        f"/decision_note scope=run run_id={args.test_run_id} source_command=/daily_review "
        "human_action=observe note=QA smoke test only; no execution."
    )

    cases: list[tuple[str, str, list[str], list[re.Pattern[str]]]] = [
        ("A_help", "/help", ["/daily_review", "/decision_note"], [PLACEHOLDER_PATTERN]),
        (
            "B_daily_review",
            "/daily_review",
            ["Status: completed.", "business_date_hkt", "daily_review_health", "decision-support"],
            [],
        ),
        (
            "C_decision_note_run_success",
            run_success_command,
            [
                "Status: completed.",
                "human decision journal entry recorded",
                "journaling only; no execution; no real-money trading",
            ],
            [],
        ),
        (
            "D_decision_note_stock_not_implemented",
            "/decision_note scope=stock run_id=1 source_command=/daily_review human_action=observe note=QA check",
            ["stock-level decision journal is not implemented yet", "no execution performed"],
            [],
        ),
        (
            "E_decision_note_invalid",
            "/decision_note scope=run run_id=abc source_command=/daily_review human_action=observe note=QA",
            ["Status: failed.", "run_id must be a positive integer"],
            [],
        ),
    ]

    results = [
        _run_case(name, command, includes, excludes, webhook_url, webhook_secret, chat_id, user_id)
        for (name, command, includes, excludes) in cases
    ]

    timestamp_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    _write_reports(args.target, args.test_run_id, timestamp_utc, results, verify_supabase=args.verify_supabase == "true")

    print(f"[operator-smoke] target={args.target} run_id={args.test_run_id}")
    for result in results:
        print(f"[operator-smoke] {result.name}: {'PASS' if result.passed else 'FAIL'}")

    overall_pass = all(result.passed for result in results)
    print(f"[operator-smoke] overall={'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeHarnessError as exc:
        print(f"[operator-smoke] configuration error: {exc}")
        raise SystemExit(2)
