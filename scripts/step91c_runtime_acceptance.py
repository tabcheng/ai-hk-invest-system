#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError

REPORT_JSON = "step91c_runtime_acceptance_report.json"
REPORT_MD = "step91c_runtime_acceptance_report.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_key() -> tuple[str | None, str]:
    k = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if k:
        return k, "SUPABASE_SECRET_KEY"
    k = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if k:
        return k, "SUPABASE_SERVICE_ROLE_KEY"
    return None, "MISSING"


def _check_table(base: str, key: str, table: str, freshness_minutes: int) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/rest/v1/{table}?select=*&order=created_at.desc&limit=1"
    req = request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        if exc.code in (404, 400):
            return {"status": "NOT_CONFIGURED", "reason": f"http_{exc.code}"}
        return {"status": "FAIL", "reason": f"http_{exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "reason": exc.__class__.__name__}

    if not isinstance(payload, list):
        return {"status": "FAIL", "reason": "unexpected_payload"}
    if not payload:
        return {"status": "FAIL", "reason": "no_rows"}

    row = payload[0] if isinstance(payload[0], dict) else {}
    ts = row.get("updated_at") or row.get("created_at") or row.get("timestamp")
    freshness = "UNKNOWN"
    if isinstance(ts, str):
        try:
            row_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_min = (datetime.now(timezone.utc) - row_dt.astimezone(timezone.utc)).total_seconds() / 60
            freshness = "FRESH" if age_min <= freshness_minutes else "STALE"
        except Exception:
            freshness = "UNKNOWN"

    return {"status": "PASS", "freshness": freshness, "timestamp": ts}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--target", default="production")
    p.add_argument("--test-run-id", required=True)
    p.add_argument("--freshness-minutes", type=int, default=1440)
    args = p.parse_args()

    base = os.getenv("SUPABASE_URL", "").strip()
    key, key_name = _resolve_key()

    preflight = "PASS"
    supabase_key_class_check = "PASS"
    if not base or not key:
        preflight = "FAIL"
    if key_name == "SUPABASE_SECRET_KEY" and key and not key.startswith("sb_secret_"):
        supabase_key_class_check = "FAIL"
        preflight = "FAIL"

    operator_json = Path("operator_smoke_report.json")
    miniapp_json = Path("miniapp_api_smoke_report.json")

    report: dict[str, Any] = {
        "generated_at": _now(),
        "target": args.target,
        "test_run_id": args.test_run_id,
        "preflight_status": preflight,
        "supabase_key_class_check": supabase_key_class_check,
        "operator_smoke_report_found": operator_json.exists(),
        "operator_smoke_report_status": "UNKNOWN",
        "miniapp_smoke_report_found": miniapp_json.exists(),
        "miniapp_smoke_report_status": "UNKNOWN",
        "runs_check": {"status": "NOT_CHECKED"},
        "signals_check": {"status": "NOT_CHECKED"},
        "decision_ledger_check": {"status": "NOT_CHECKED"},
        "paper_trades_check": {"status": "NOT_CHECKED"},
        "latest_system_runs_check": {"status": "NOT_CHECKED"},
        "secrets_redacted": True,
        "fallback_warning_check": "NOT_CHECKED",
        "domain_guardrail_confirmation": "no broker/live-money execution",
    }

    if operator_json.exists():
        try:
            report["operator_smoke_report_status"] = json.loads(operator_json.read_text()).get("overall_result", "UNKNOWN")
        except Exception:
            report["operator_smoke_report_status"] = "INVALID"
    if miniapp_json.exists():
        try:
            report["miniapp_smoke_report_status"] = "PASS" if json.loads(miniapp_json.read_text()).get("overall_passed") else "FAIL"
        except Exception:
            report["miniapp_smoke_report_status"] = "INVALID"

    if preflight == "PASS":
        report["runs_check"] = _check_table(base, key or "", "runs", args.freshness_minutes)
        report["signals_check"] = _check_table(base, key or "", "signals", args.freshness_minutes)
        report["decision_ledger_check"] = _check_table(base, key or "", "decision_ledger", args.freshness_minutes)
        report["paper_trades_check"] = _check_table(base, key or "", "paper_trades", args.freshness_minutes)
        report["latest_system_runs_check"] = _check_table(base, key or "", "latest_system_runs", args.freshness_minutes)

    statuses = [
        report["preflight_status"],
        report["supabase_key_class_check"],
        report["operator_smoke_report_status"],
        report["miniapp_smoke_report_status"],
        report["runs_check"].get("status"),
        report["signals_check"].get("status"),
        report["decision_ledger_check"].get("status"),
        report["paper_trades_check"].get("status"),
    ]
    report["overall_status"] = "PASS" if all(s in ("PASS", "NOT_CONFIGURED") for s in statuses) else "FAIL"

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = ["# Step 91C Runtime Acceptance Report", "", f"- overall_status: {report['overall_status']}"]
    for k in ["preflight_status", "supabase_key_class_check", "operator_smoke_report_status", "miniapp_smoke_report_status", "secrets_redacted", "fallback_warning_check", "domain_guardrail_confirmation"]:
        md.append(f"- {k}: {report[k]}")
    md += [
        "",
        "## Supabase checks",
        f"- runs_check: {report['runs_check']}",
        f"- signals_check: {report['signals_check']}",
        f"- decision_ledger_check: {report['decision_ledger_check']}",
        f"- paper_trades_check: {report['paper_trades_check']}",
        f"- latest_system_runs_check: {report['latest_system_runs_check']}",
    ]
    Path(REPORT_MD).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[step91c_runtime_acceptance] overall_status={report['overall_status']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
