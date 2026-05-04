#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import request

REPORT_JSON = "railway_step91c_log_evidence_report.json"
REPORT_MD = "railway_step91c_log_evidence_report.md"
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"

WARNING_PATTERNS = (
    "SUPABASE_KEY is deprecated",
    "transitional fallback",
    "SUPABASE_KEY fallback",
)
SECRET_LIKE_PATTERN = re.compile(
    r"(sb_secret_|service_role|bot token|webhook secret|initData|telegram\s*initData|\d{8,10}:[A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _read_only_graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = request.Request(
        RAILWAY_API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    if isinstance(payload, dict) and payload.get("errors"):
        raise RuntimeError("graphql_errors")
    return payload


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _scan_entries(entries: list[dict[str, Any]], since_dt: datetime) -> tuple[int, list[str]]:
    matches = 0
    snippets: list[str] = []
    for entry in entries:
        message = str(entry.get("message", ""))
        ts = _parse_iso(str(entry.get("timestamp", "")))
        if ts is not None and ts < since_dt:
            continue
        if any(pattern in message for pattern in WARNING_PATTERNS):
            if SECRET_LIKE_PATTERN.search(message):
                continue
            matches += 1
            snippets.append(message[:180])
    return matches, snippets[:8]


def _collect_service_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    edges = (
        payload.get("data", {})
        .get("project", {})
        .get("service", {})
        .get("deployments", {})
        .get("edges", [])
    )
    if not edges:
        return []
    log_edges = edges[0].get("node", {}).get("logs", {}).get("edges", [])
    entries: list[dict[str, Any]] = []
    for edge in log_edges:
        node = edge.get("node", {}) if isinstance(edge, dict) else {}
        if isinstance(node, dict):
            entries.append({"message": node.get("message", ""), "timestamp": node.get("timestamp")})
    return entries


def _render_md(report: dict[str, Any]) -> str:
    lines = ["# Railway Step 91C Log Evidence Report", ""]
    for key in (
        "overall_status",
        "railway_token_configured",
        "project_id_configured",
        "environment_id_configured",
        "checked_services",
        "log_window_minutes",
        "fallback_warning_check",
        "fallback_warning_matches_count",
        "staged_changes_check",
        "staged_changes_summary",
        "secrets_redacted",
        "raw_logs_included",
        "limitation",
    ):
        lines.append(f"- {key}: {report.get(key)}")
    if report.get("safe_snippets"):
        lines.extend(["", "## Safe snippets"])
        lines.extend([f"- {snippet}" for snippet in report["safe_snippets"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--log-window-minutes", type=int, default=120)
    p.add_argument("--service-names", default=os.getenv("RAILWAY_LOG_SERVICE_NAMES", "paper-daily-runner,telegram-webhook"))
    args = p.parse_args()

    token = os.getenv("RAILWAY_TOKEN", "").strip()
    project_id = os.getenv("RAILWAY_PROJECT_ID", "").strip()
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    services = _split_csv(args.service_names)
    since_dt = datetime.now(timezone.utc) - timedelta(minutes=max(1, args.log_window_minutes))

    report: dict[str, Any] = {
        "generated_at": _now(),
        "overall_status": "NOT_CONFIGURED",
        "railway_token_configured": bool(token),
        "project_id_configured": bool(project_id),
        "environment_id_configured": bool(environment_id),
        "checked_services": services,
        "log_window_minutes": args.log_window_minutes,
        "fallback_warning_check": "NOT_CONFIGURED",
        "fallback_warning_matches_count": 0,
        "staged_changes_check": "NOT_CONFIGURED",
        "staged_changes_summary": "redacted/count-only",
        "safe_snippets": [],
        "secrets_redacted": True,
        "raw_logs_included": False,
        "limitation": "Railway evidence unavailable or partial.",
    }

    configured = bool(token and project_id and environment_id and services)
    if configured:
        try:
            total_matches = 0
            safe_snippets: list[str] = []
            logs_query = (
                "query($projectId:String!,$environmentId:String!,$serviceName:String!){"
                "project(id:$projectId){service(name:$serviceName){deployments(first:1,environmentId:$environmentId){edges{node{logs(first:300){edges{node{message timestamp}}}}}}}}}"
            )
            for service_name in services:
                payload = _read_only_graphql(
                    token,
                    logs_query,
                    {"projectId": project_id, "environmentId": environment_id, "serviceName": service_name},
                )
                entries = _collect_service_entries(payload)
                match_count, snippets = _scan_entries(entries, since_dt)
                total_matches += match_count
                safe_snippets.extend(snippets)

            report["fallback_warning_matches_count"] = total_matches
            report["safe_snippets"] = safe_snippets[:8]
            report["fallback_warning_check"] = "FAIL" if total_matches > 0 else "PASS"
            report["overall_status"] = report["fallback_warning_check"]
            report["staged_changes_check"] = "NOT_CONFIGURED"
            report["staged_changes_summary"] = "count-only; staged changes read endpoint not configured"
            report["limitation"] = "Staged changes check remains NOT_CONFIGURED in this step."
        except Exception as exc:  # noqa: BLE001
            report["overall_status"] = "NOT_CONFIGURED"
            report["fallback_warning_check"] = "NOT_CONFIGURED"
            report["limitation"] = f"Railway API read failed: {exc.__class__.__name__}"

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(REPORT_MD).write_text(_render_md(report), encoding="utf-8")
    print(f"[railway_step91c_log_evidence] overall_status={report['overall_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
