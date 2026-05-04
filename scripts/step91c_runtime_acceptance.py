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

REQUIRED_TABLES = ("runs", "signals")
OPTIONAL_TABLES = ("decision_ledger", "paper_trades", "latest_system_runs")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_key() -> tuple[str | None, str]:
    key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if key:
        return key, "SUPABASE_SECRET_KEY"
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if key:
        return key, "SUPABASE_SERVICE_ROLE_KEY"
    return None, "MISSING"


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _check_table(base: str, key: str, table: str, freshness_minutes: int, required: bool) -> dict[str, Any]:
    url = f"{base.rstrip('/')}/rest/v1/{table}?select=*&order=created_at.desc&limit=1"
    req = request.Request(url, headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as exc:
        if (not required) and exc.code in (400, 404):
            return {"status": "NOT_CONFIGURED", "reason": f"http_{exc.code}"}
        return {"status": "FAIL", "reason": f"http_{exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "FAIL", "reason": exc.__class__.__name__}

    if not isinstance(payload, list):
        return {"status": "FAIL", "reason": "unexpected_payload"}
    if not payload:
        return {"status": "FAIL", "reason": "no_rows"} if required else {"status": "NOT_CONFIGURED", "reason": "no_rows"}

    row = payload[0] if isinstance(payload[0], dict) else {}
    ts = row.get("updated_at") or row.get("created_at") or row.get("timestamp")
    if not isinstance(ts, str):
        return {"status": "FAIL", "reason": "missing_timestamp"} if required else {"status": "PASS", "freshness": "UNKNOWN"}

    row_dt = _parse_iso(ts)
    if row_dt is None:
        return {"status": "FAIL", "reason": "invalid_timestamp", "timestamp": ts} if required else {"status": "PASS", "freshness": "UNKNOWN", "timestamp": ts}

    age_minutes = round((datetime.now(timezone.utc) - row_dt).total_seconds() / 60, 2)
    fresh = age_minutes <= freshness_minutes
    if required and not fresh:
        return {"status": "FAIL", "freshness": "STALE", "age_minutes": age_minutes, "timestamp": ts}
    return {"status": "PASS", "freshness": "FRESH" if fresh else "STALE", "age_minutes": age_minutes, "timestamp": ts}


def _read_operator_status(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("overall_result", "UNKNOWN")
    except Exception:
        return "INVALID"


def _read_miniapp_status(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    try:
        return "PASS" if json.loads(path.read_text(encoding="utf-8")).get("overall_passed") else "FAIL"
    except Exception:
        return "INVALID"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="production")
    parser.add_argument("--test-run-id", required=True)
    parser.add_argument("--freshness-minutes", type=int, default=1440)
    args = parser.parse_args()

    base = os.getenv("SUPABASE_URL", "").strip()
    key, key_name = _resolve_key()

    preflight = "PASS"
    key_class = "PASS"
    if not base or not key:
        preflight = "FAIL"
    if key_name == "SUPABASE_SECRET_KEY" and key and not key.startswith("sb_secret_"):
        key_class = "FAIL"
        preflight = "FAIL"

    report: dict[str, Any] = {
        "generated_at": _now(),
        "target": args.target,
        "test_run_id": args.test_run_id,
        "preflight_status": preflight,
        "supabase_key_class_check": key_class,
        "operator_smoke_report_found": Path("operator_smoke_report.json").exists(),
        "operator_smoke_report_status": _read_operator_status(Path("operator_smoke_report.json")),
        "miniapp_smoke_report_found": Path("miniapp_api_smoke_report.json").exists(),
        "miniapp_smoke_report_status": _read_miniapp_status(Path("miniapp_api_smoke_report.json")),
        "runs_check": {"status": "NOT_CHECKED"},
        "signals_check": {"status": "NOT_CHECKED"},
        "decision_ledger_check": {"status": "NOT_CHECKED", "classification": "optional"},
        "paper_trades_check": {"status": "NOT_CHECKED", "classification": "optional"},
        "latest_system_runs_check": {"status": "NOT_CHECKED", "classification": "optional"},
        "secrets_redacted": True,
        "fallback_warning_check": "NOT_CHECKED",
        "domain_guardrail_confirmation": "no broker/live-money execution",
    }

    if preflight == "PASS":
        report["runs_check"] = _check_table(base, key or "", "runs", args.freshness_minutes, required=True)
        report["signals_check"] = _check_table(base, key or "", "signals", args.freshness_minutes, required=True)
        report["decision_ledger_check"] = {
            **_check_table(base, key or "", "decision_ledger", args.freshness_minutes, required=False),
            "classification": "optional",
        }
        report["paper_trades_check"] = {
            **_check_table(base, key or "", "paper_trades", args.freshness_minutes, required=False),
            "classification": "optional",
        }
        report["latest_system_runs_check"] = {
            **_check_table(base, key or "", "latest_system_runs", args.freshness_minutes, required=False),
            "classification": "optional",
        }

    required_gate_statuses = [
        report["preflight_status"],
        report["supabase_key_class_check"],
        report["operator_smoke_report_status"],
        report["miniapp_smoke_report_status"],
        report["runs_check"].get("status"),
        report["signals_check"].get("status"),
    ]
    report["overall_status"] = "PASS" if all(status == "PASS" for status in required_gate_statuses) else "FAIL"

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Step 91C Runtime Acceptance Report", "", f"- overall_status: {report['overall_status']}"]
    for key_name in (
        "preflight_status",
        "supabase_key_class_check",
        "operator_smoke_report_status",
        "miniapp_smoke_report_status",
        "secrets_redacted",
        "fallback_warning_check",
        "domain_guardrail_confirmation",
    ):
        lines.append(f"- {key_name}: {report[key_name]}")
    lines.extend(
        [
            "",
            "## Required Supabase checks",
            f"- runs_check: {report['runs_check']}",
            f"- signals_check: {report['signals_check']}",
            "",
            "## Optional Supabase checks",
            f"- decision_ledger_check: {report['decision_ledger_check']}",
            f"- paper_trades_check: {report['paper_trades_check']}",
            f"- latest_system_runs_check: {report['latest_system_runs_check']}",
        ]
    )
    Path(REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[step91c_runtime_acceptance] overall_status={report['overall_status']}")
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
