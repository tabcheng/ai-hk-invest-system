#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

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
SECRET_VALUE_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9._-]+|sb_secret_[A-Za-z0-9._-]+|"
    r"\d{8,10}:[A-Za-z0-9_-]{20,}|"
    r"(SUPABASE_(?:SECRET_KEY|SERVICE_ROLE_KEY|KEY)|TELEGRAM_BOT_TOKEN|"
    r"TELEGRAM_WEBHOOK_SECRET_TOKEN|RAILWAY_TOKEN|initData|allowlist(?:_ids)?)\s*[:=]\s*[^,\s\"']+)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _redact_text(raw: str, *, limit: int = 300) -> str:
    trimmed = re.sub(r"\s+", " ", str(raw)).strip()[:limit]
    return SECRET_VALUE_PATTERN.sub("[REDACTED]", trimmed)


def _read_only_graphql(token: str, query: str, variables: dict[str, Any], api_url: str) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = request.Request(
        api_url,
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


def _scan_entries(entries: list[dict[str, Any]], since_dt: datetime) -> tuple[int, int, int, int, list[str]]:
    matches = 0
    redacted_matches = 0
    in_window_count = 0
    unknown_ts_count = 0
    snippets: list[str] = []

    for entry in entries:
        message = str(entry.get("message", ""))
        ts = _parse_iso(str(entry.get("timestamp", "")))
        if ts is None:
            unknown_ts_count += 1
            continue
        if ts < since_dt:
            continue

        in_window_count += 1
        if any(pattern in message for pattern in WARNING_PATTERNS):
            matches += 1
            if SECRET_LIKE_PATTERN.search(message):
                redacted_matches += 1
                continue
            snippets.append(message[:180])

    return matches, redacted_matches, in_window_count, unknown_ts_count, snippets[:8]


def _collect_environment_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("data", {}).get("environmentLogs")
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        edges = raw.get("edges", [])
        return [edge.get("node", {}) for edge in edges if isinstance(edge, dict) and isinstance(edge.get("node"), dict)]
    return []


def _render_md(report: dict[str, Any]) -> str:
    keys = [
        "overall_status",
        "railway_token_configured",
        "project_id_configured",
        "environment_id_configured",
        "checked_services",
        "checked_service_ids",
        "railway_log_query_mode",
        "railway_query_stage",
        "log_window_minutes",
        "fallback_warning_check",
        "fallback_warning_matches_count",
        "redacted_warning_matches_count",
        "logs_read_count",
        "logs_recent_count",
        "logs_returned_count",
        "logs_unknown_timestamp_count",
        "railway_api_url_host_only",
        "connectivity_check",
        "connectivity_http_status",
        "connectivity_reason",
        "railway_api_http_status",
        "railway_api_error_kind",
        "railway_api_error_excerpt_redacted",
        "staged_changes_check",
        "staged_changes_summary",
        "secrets_redacted",
        "raw_logs_included",
        "limitation",
    ]
    lines = ["# Railway Step 91C Log Evidence Report", ""] + [f"- {k}: {report.get(k)}" for k in keys]
    if report.get("safe_snippets"):
        lines.extend(["", "## Safe snippets"] + [f"- {x}" for x in report["safe_snippets"]])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-window-minutes", type=int, default=120)
    parser.add_argument(
        "--service-names",
        default=os.getenv("RAILWAY_LOG_SERVICE_NAMES", "paper-daily-runner,telegram-webhook"),
    )
    args = parser.parse_args()

    token = os.getenv("RAILWAY_TOKEN", "").strip()
    project_id = os.getenv("RAILWAY_PROJECT_ID", "").strip()
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    api_url = os.getenv("RAILWAY_API_URL", RAILWAY_API_URL).strip() or RAILWAY_API_URL

    query_mode = (os.getenv("RAILWAY_LOG_QUERY_MODE", "environment").strip().lower() or "environment")
    if query_mode not in {"environment", "cli"}:
        query_mode = "environment"

    services = _split_csv(args.service_names)
    service_ids = _split_csv(os.getenv("RAILWAY_LOG_SERVICE_IDS", ""))
    api_host = parse.urlparse(api_url).netloc or "unknown"
    since_dt = datetime.now(timezone.utc) - timedelta(minutes=max(1, args.log_window_minutes))

    report: dict[str, Any] = {
        "generated_at": _now(),
        "overall_status": "NOT_CONFIGURED",
        "railway_token_configured": bool(token),
        "project_id_configured": bool(project_id),
        "environment_id_configured": bool(environment_id),
        "checked_services": services,
        "checked_service_ids": service_ids,
        "railway_log_query_mode": query_mode,
        "railway_query_stage": None,
        "log_window_minutes": args.log_window_minutes,
        "fallback_warning_check": "NOT_CONFIGURED",
        "fallback_warning_matches_count": 0,
        "redacted_warning_matches_count": 0,
        "logs_read_count": 0,
        "logs_recent_count": 0,
        "logs_returned_count": 0,
        "logs_unknown_timestamp_count": 0,
        "staged_changes_check": "NOT_CONFIGURED",
        "staged_changes_summary": "redacted/count-only",
        "safe_snippets": [],
        "secrets_redacted": True,
        "raw_logs_included": False,
        "railway_api_url_host_only": api_host,
        "railway_api_endpoint_label": f"https://{api_host}",
        "connectivity_check": "NOT_RUN",
        "connectivity_http_status": None,
        "connectivity_reason": "workspace_probe_not_configured",
        "railway_api_http_status": None,
        "railway_api_error_kind": None,
        "railway_api_error_excerpt_redacted": None,
        "limitation": "Railway evidence unavailable or partial.",
    }

    if token and project_id and environment_id:
        try:
            if query_mode == "cli":
                report.update(
                    {
                        "overall_status": "FAIL",
                        "fallback_warning_check": "FAIL",
                        "railway_query_stage": "cli_logs",
                        "limitation": "RAILWAY_LOG_QUERY_MODE=cli is not implemented in this step.",
                    }
                )
            else:
                report["railway_query_stage"] = "environment_logs"
                if not service_ids:
                    report.update(
                        {
                            "overall_status": "FAIL",
                            "fallback_warning_check": "FAIL",
                            "limitation": "RAILWAY_LOG_SERVICE_IDS is required for scoped environmentLogs evidence.",
                        }
                    )
                    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    Path(REPORT_MD).write_text(_render_md(report), encoding="utf-8")
                    print(
                        "[railway_step91c_log_evidence] "
                        f"overall_status={report['overall_status']} "
                        f"fallback_warning_check={report['fallback_warning_check']} "
                        f"logs_read_count={report['logs_read_count']} "
                        f"railway_log_query_mode={report['railway_log_query_mode']} "
                        f"railway_query_stage={report['railway_query_stage']} "
                        f"railway_api_http_status={report['railway_api_http_status']} "
                        f"railway_api_error_kind={report['railway_api_error_kind']} "
                        f"limitation={report['limitation']}"
                    )
                    return 0
                filter_expr = " OR ".join([f"@service:{sid}" for sid in service_ids]) if service_ids else None
                payload = _read_only_graphql(
                    token,
                    "query($environmentId:String!, $filter:String, $beforeLimit:Int){environmentLogs(environmentId:$environmentId, filter:$filter, beforeLimit:$beforeLimit){message severity timestamp}}",
                    {"environmentId": environment_id, "filter": filter_expr, "beforeLimit": 300},
                    api_url,
                )

                entries = _collect_environment_entries(payload)
                matches, redacted, logs_recent, unknown_ts, snippets = _scan_entries(entries, since_dt)

                report["logs_returned_count"] = len(entries)
                report["logs_recent_count"] = logs_recent
                report["logs_unknown_timestamp_count"] = unknown_ts
                report["logs_read_count"] = logs_recent
                report["fallback_warning_matches_count"] = matches
                report["redacted_warning_matches_count"] = redacted
                report["safe_snippets"] = snippets
                report["staged_changes_summary"] = "count-only; staged changes read endpoint not configured"

                if logs_recent == 0:
                    report.update(
                        {
                            "overall_status": "FAIL",
                            "fallback_warning_check": "FAIL",
                            "limitation": "Configured Railway evidence returned no readable logs inside the configured log window.",
                        }
                    )
                else:
                    check = "FAIL" if matches > 0 else "PASS"
                    report.update(
                        {
                            "overall_status": check,
                            "fallback_warning_check": check,
                            "limitation": "Staged changes check remains NOT_CONFIGURED in this step.",
                        }
                    )
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            report.update(
                {
                    "overall_status": "FAIL",
                    "fallback_warning_check": "FAIL",
                    "railway_api_http_status": exc.code,
                    "railway_api_error_kind": "HTTPError",
                    "railway_api_error_excerpt_redacted": _redact_text(body),
                    "limitation": "Configured Railway evidence read failed: HTTPError",
                }
            )
        except Exception as exc:  # noqa: BLE001
            report.update(
                {
                    "overall_status": "FAIL",
                    "fallback_warning_check": "FAIL",
                    "railway_api_error_kind": exc.__class__.__name__,
                    "limitation": f"Configured Railway evidence read failed: {exc.__class__.__name__}",
                }
            )

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(REPORT_MD).write_text(_render_md(report), encoding="utf-8")

    print(
        "[railway_step91c_log_evidence] "
        f"overall_status={report['overall_status']} "
        f"fallback_warning_check={report['fallback_warning_check']} "
        f"logs_read_count={report['logs_read_count']} "
        f"railway_log_query_mode={report['railway_log_query_mode']} "
        f"railway_query_stage={report['railway_query_stage']} "
        f"railway_api_http_status={report['railway_api_http_status']} "
        f"railway_api_error_kind={report['railway_api_error_kind']} "
        f"limitation={report['limitation']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
