#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError

REPORT_JSON = "step92a_post_merge_smoke_report.json"
REPORT_MD = "step92a_post_merge_smoke_report.md"
SAFE_STATUSES = {"success", "failed", "partial", "unknown"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_key() -> tuple[str | None, str]:
    for name in ("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"):
        value = os.getenv(name, "").strip()
        if value:
            return value, name
    return None, "MISSING"


def _get(base: str, key: str, query: str) -> Any:
    url = f"{base.rstrip('/')}/rest/v1/{query}"
    req = request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _contract_evidence_check(base: str, key: str) -> tuple[dict[str, str], str | None]:
    fail_result = {
        "table_exists": "FAIL",
        "rls_enabled": "FAIL",
        "source_unique_index_exists": "FAIL",
        "latest_read_index_exists": "FAIL",
    }
    try:
        payload = _get(base, key, "rpc/step92a_latest_system_runs_contract_evidence")
    except HTTPError as exc:
        return fail_result, f"contract_evidence_rpc_not_configured_http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        return fail_result, f"contract_evidence_rpc_not_configured_{exc.__class__.__name__}"

    if not isinstance(payload, dict):
        return fail_result, "contract_evidence_rpc_unexpected_payload"

    mapped: dict[str, str] = {}
    for key_name in ("table_exists", "rls_enabled", "source_unique_index_exists", "latest_read_index_exists"):
        mapped[key_name] = "PASS" if payload.get(key_name) is True else "FAIL"
    return mapped, "ok"


def _safe_latest_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    summary_json = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
    return {
        "run_id": row.get("run_id"),
        "business_date": row.get("business_date"),
        "status": row.get("status"),
        "source": row.get("source"),
        "data_timestamp": row.get("data_timestamp"),
        "paper_trade_only": summary_json.get("paper_trade_only"),
        "processed_tickers": summary_json.get("processed_tickers"),
        "successful_tickers": summary_json.get("successful_tickers"),
        "failed_tickers": summary_json.get("failed_tickers"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _run_paper_daily_runner() -> dict[str, Any]:
    try:
        cp = subprocess.run(["python", "-m", "src.daily_runner"], capture_output=True, text=True, timeout=900, check=False)
        return {
            "mode": "github_runner_execution",
            "status": "PASS" if cp.returncode == 0 else "FAIL",
            "exit_code": cp.returncode,
            "stdout_lines": len(cp.stdout.splitlines()),
            "stderr_lines": len(cp.stderr.splitlines()),
            "limitation": "Verifies repository runner code path + injected env on GitHub runner; not identical to deployed Railway container runtime.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"mode": "github_runner_execution", "status": "FAIL", "error_kind": exc.__class__.__name__}


def _compute_overall_status(report: dict[str, Any]) -> str:
    gates = [
        report["preflight"],
        report["table_exists"],
        report["rls_enabled"],
        report["source_unique_index_exists"],
        report["latest_read_index_exists"],
        report["paper_daily_runner_row_count_lte_1"],
    ]
    if report["latest_row_readable"] == "PASS":
        gates += [report["paper_trade_only_true_if_row_exists"], report["status_allowed_if_row_exists"]]
    if report["run_paper_daily_runner"]:
        gates.append(report["runner_execution"].get("status", "FAIL"))
    return "PASS" if all(x == "PASS" for x in gates) else "FAIL"


def _railway_probe() -> dict[str, Any]:
    token = os.getenv("RAILWAY_TOKEN", "").strip()
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    service_ids = [x.strip() for x in os.getenv("RAILWAY_LOG_SERVICE_IDS", "").split(",") if x.strip()]
    api_url = os.getenv("RAILWAY_API_URL", "https://backboard.railway.app/graphql/v2").strip()
    host = parse.urlparse(api_url).netloc or "unknown"
    result: dict[str, Any] = {"configured": bool(token and environment_id and service_ids), "railway_api_host_only": host, "status": "NOT_CONFIGURED"}
    if not result["configured"]:
        return result
    body = json.dumps({"query": "query($environmentId:String!, $filter:String, $beforeLimit:Int){environmentLogs(environmentId:$environmentId, filter:$filter, beforeLimit:$beforeLimit){timestamp}}", "variables": {"environmentId": environment_id, "filter": " OR ".join([f"@service:{sid}" for sid in service_ids]), "beforeLimit": 10}}).encode("utf-8")
    req = request.Request(api_url, data=body, headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "ai-hk-invest-system-step92a/1.2 (+github-actions; read-only)", "Authorization": f"Bearer {token}"}, method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        logs = payload.get("data", {}).get("environmentLogs") or []
        result["status"] = "PASS"
        result["log_entries_returned"] = len(logs) if isinstance(logs, list) else 0
    except HTTPError as exc:
        result["status"] = "FAIL"
        result["http_status"] = exc.code
    except Exception as exc:  # noqa: BLE001
        result["status"] = "FAIL"
        result["error_kind"] = exc.__class__.__name__
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-paper-daily-runner", choices=("true", "false"), default="false")
    ns = parser.parse_args()

    base = os.getenv("SUPABASE_URL", "").strip()
    key, key_name = _resolve_key()
    report: dict[str, Any] = {
        "generated_at": _now(),
        "preflight": "PASS" if base and key else "FAIL",
        "supabase_key_source": key_name,
        "run_paper_daily_runner": ns.run_paper_daily_runner == "true",
        "runner_execution": {"status": "SKIPPED"},
        "table_exists": "NOT_CHECKED",
        "rls_enabled": "NOT_CHECKED",
        "rls_check_reason": None,
        "source_unique_index_exists": "NOT_CHECKED",
        "source_unique_index_reason": None,
        "latest_read_index_exists": "NOT_CHECKED",
        "latest_read_index_reason": None,
        "paper_daily_runner_row_count_lte_1": "NOT_CHECKED",
        "latest_row_readable": "NOT_CHECKED",
        "paper_trade_only_true_if_row_exists": "NOT_CHECKED",
        "status_allowed_if_row_exists": "NOT_CHECKED",
        "safe_latest_row": None,
        "railway_evidence": _railway_probe(),
        "secrets_redacted": True,
    }

    if report["run_paper_daily_runner"]:
        report["runner_execution"] = _run_paper_daily_runner()

    if report["preflight"] == "PASS":
        try:
            contract_evidence, contract_reason = _contract_evidence_check(base, key or "")
            report["table_exists"] = contract_evidence["table_exists"]
            report["rls_enabled"] = contract_evidence["rls_enabled"]
            report["source_unique_index_exists"] = contract_evidence["source_unique_index_exists"]
            report["latest_read_index_exists"] = contract_evidence["latest_read_index_exists"]
            report["rls_check_reason"] = contract_reason
            report["source_unique_index_reason"] = contract_reason
            report["latest_read_index_reason"] = contract_reason

            rows = _get(base, key or "", "latest_system_runs?select=run_id,business_date,status,source,data_timestamp,summary_json,created_at,updated_at&source=eq.paper_daily_runner&order=updated_at.desc,created_at.desc&limit=10")
            report["paper_daily_runner_row_count_lte_1"] = "PASS" if isinstance(rows, list) and len(rows) <= 1 else "FAIL"
            latest = rows[0] if isinstance(rows, list) and rows else None
            report["latest_row_readable"] = "PASS" if latest else "NOT_CONFIGURED"
            if latest:
                report["safe_latest_row"] = _safe_latest_row(latest)
                report["paper_trade_only_true_if_row_exists"] = "PASS" if report["safe_latest_row"].get("paper_trade_only") is True else "FAIL"
                report["status_allowed_if_row_exists"] = "PASS" if str(latest.get("status", "")) in SAFE_STATUSES else "FAIL"
            else:
                report["paper_trade_only_true_if_row_exists"] = "NOT_CONFIGURED"
                report["status_allowed_if_row_exists"] = "NOT_CONFIGURED"
        except Exception as exc:  # noqa: BLE001
            report["error_kind"] = exc.__class__.__name__

    report["overall_status"] = _compute_overall_status(report)

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(REPORT_MD).write_text("# Step 92A Post-merge Smoke Report\n\n" + "\n".join([f"- {k}: {report[k]}" for k in ["overall_status", "preflight", "run_paper_daily_runner", "table_exists", "rls_enabled", "source_unique_index_exists", "latest_read_index_exists", "paper_daily_runner_row_count_lte_1", "latest_row_readable"]]), encoding="utf-8")
    print(f"[step92a_post_merge_smoke] overall_status={report['overall_status']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
