#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError

REPORT_JSON = "railway_api_probe_report.json"
REPORT_MD = "railway_api_probe_report.md"
DEFAULT_API_URL = "https://backboard.railway.app/graphql/v2"
SECRET_PATTERN = re.compile(r"(Bearer\s+[A-Za-z0-9._-]+|sb_secret_[A-Za-z0-9._-]+|RAILWAY_TOKEN\s*[:=]\s*[^,\s]+)", re.IGNORECASE)


def _split_csv(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _redact(text: str, *, limit: int = 260) -> str:
    compact = re.sub(r"\s+", " ", str(text)).strip()[:limit]
    return SECRET_PATTERN.sub("[REDACTED]", compact)


def _graphql(api_url: str, token: str, query: str, variables: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = request.Request(api_url, data=body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
    with request.urlopen(req, timeout=20) as resp:
        return int(getattr(resp, "status", 200)), json.loads(resp.read().decode("utf-8", errors="replace"))


def _safe_error(exc: Exception) -> tuple[str, int | None, str]:
    if isinstance(exc, HTTPError):
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw = str(exc)
        return "HTTPError", int(exc.code), _redact(raw or str(exc))
    return type(exc).__name__, None, _redact(str(exc))


def _write_and_print(report: dict[str, Any]) -> int:
    Path(REPORT_JSON).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(REPORT_MD).write_text(
        "\n".join(
            ["# Railway API Probe Report", ""]
            + [f"- {k}: {report.get(k)}" for k in [
                "overall_status", "token_present", "api_url_host_only", "account_probe_status", "account_probe_http_status", "project_metadata_status", "project_metadata_http_status", "project_services_environments_status", "configured_environment_id_found", "configured_service_ids_found", "missing_service_ids", "environment_logs_probe_status", "environment_logs_http_status", "environment_logs_returned_count", "environment_logs_first_timestamp", "railway_api_error_kind", "railway_api_error_excerpt_redacted", "limitation",
            ]]
        ) + "\n",
        encoding="utf-8",
    )
    print(f"[railway_api_probe] overall_status={report['overall_status']} project_metadata_status={report['project_metadata_status']} project_metadata_http_status={report['project_metadata_http_status']} configured_environment_id_found={report['configured_environment_id_found']} configured_service_ids_found_count={len(report['configured_service_ids_found'])} environment_logs_probe_status={report['environment_logs_probe_status']} environment_logs_http_status={report['environment_logs_http_status']} limitation={report['limitation']}")
    return 0


def main() -> int:
    token = os.getenv("RAILWAY_TOKEN", "").strip()
    project_id = os.getenv("RAILWAY_PROJECT_ID", "").strip()
    environment_id = os.getenv("RAILWAY_ENVIRONMENT_ID", "").strip()
    service_ids = _split_csv(os.getenv("RAILWAY_LOG_SERVICE_IDS", ""))
    connectivity = (os.getenv("RAILWAY_CONNECTIVITY_PROBE", "metadata").strip().lower() or "metadata")
    if connectivity not in {"metadata", "account", "workspace", "off"}:
        connectivity = "metadata"
    api_url = os.getenv("RAILWAY_API_URL", DEFAULT_API_URL).strip() or DEFAULT_API_URL

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "NOT_CONFIGURED",
        "token_present": bool(token),
        "api_url_host_only": parse.urlparse(api_url).netloc or "unknown",
        "account_probe_status": "NOT_RUN",
        "account_probe_http_status": None,
        "project_metadata_status": "NOT_RUN",
        "project_metadata_http_status": None,
        "project_services_environments_status": "NOT_RUN",
        "configured_environment_id_found": None,
        "configured_service_ids_found": [],
        "missing_service_ids": [],
        "environment_logs_probe_status": "NOT_RUN",
        "environment_logs_http_status": None,
        "environment_logs_returned_count": 0,
        "environment_logs_first_timestamp": None,
        "railway_api_error_kind": None,
        "railway_api_error_excerpt_redacted": None,
        "limitation": "Railway probe unavailable or partial.",
    }
    if not token:
        report["project_metadata_status"] = "NOT_CONFIGURED"
        report["environment_logs_probe_status"] = "NOT_CONFIGURED"
        return _write_and_print(report)
    current_stage = None
    try:
        if connectivity == "account":
            current_stage = "account_probe"
            http, payload = _graphql(api_url, token, "query { me { name email } }", {})
            report["account_probe_http_status"] = http
            report["account_probe_status"] = "PASS" if not payload.get("errors") else "FAIL"

        if not project_id:
            report["project_metadata_status"] = "NOT_CONFIGURED"
            report["environment_logs_probe_status"] = "NOT_RUN"
            report["overall_status"] = "PASS" if report["account_probe_status"] == "PASS" else "NOT_CONFIGURED"
            report["limitation"] = "RAILWAY_PROJECT_ID is not configured."
            return _write_and_print(report)

        current_stage = "project_metadata"
        http, payload = _graphql(api_url, token, "query($projectId:String!){project(id:$projectId){id name}}", {"projectId": project_id})
        report["project_metadata_http_status"] = http
        if payload.get("errors") or not payload.get("data", {}).get("project"):
            report["project_metadata_status"] = "FAIL"
            report["environment_logs_probe_status"] = "NOT_RUN"
            report["railway_api_error_kind"] = "GraphQLError"
            report["railway_api_error_excerpt_redacted"] = _redact(json.dumps(payload.get("errors", [])))
            report["overall_status"] = "FAIL"
            return _write_and_print(report)

        report["project_metadata_status"] = "PASS"
        current_stage = "project_services_environments"
        _, services_payload = _graphql(api_url, token, "query($projectId:String!){project(id:$projectId){id name environments{edges{node{id name}}} services{edges{node{id name}}}}}", {"projectId": project_id})
        if services_payload.get("errors"):
            report["project_services_environments_status"] = "FAIL"
            report["overall_status"] = "FAIL"
            report["railway_api_error_kind"] = "GraphQLError"
            report["railway_api_error_excerpt_redacted"] = _redact(json.dumps(services_payload.get("errors", [])))
            return _write_and_print(report)

        report["project_services_environments_status"] = "PASS"
        proj = services_payload.get("data", {}).get("project", {})
        env_ids = [e.get("node", {}).get("id") for e in proj.get("environments", {}).get("edges", []) if isinstance(e, dict)]
        svc_ids = [e.get("node", {}).get("id") for e in proj.get("services", {}).get("edges", []) if isinstance(e, dict)]
        report["configured_environment_id_found"] = environment_id in env_ids if environment_id else None
        report["configured_service_ids_found"] = [sid for sid in service_ids if sid in svc_ids]
        report["missing_service_ids"] = [sid for sid in service_ids if sid not in svc_ids]

        if not environment_id:
            report["environment_logs_probe_status"] = "NOT_CONFIGURED"
            report["overall_status"] = "FAIL"
            report["limitation"] = "RAILWAY_ENVIRONMENT_ID is not configured."
            return _write_and_print(report)

        current_stage = "environment_logs"
        filter_expr = " OR ".join([f"@service:{sid}" for sid in service_ids]) if service_ids else None
        log_http, log_payload = _graphql(api_url, token, "query($environmentId:String!,$filter:String,$beforeLimit:Int){environmentLogs(environmentId:$environmentId,filter:$filter,beforeLimit:$beforeLimit){message severity timestamp}}", {"environmentId": environment_id, "filter": filter_expr, "beforeLimit": 1})
        report["environment_logs_http_status"] = log_http
        if log_payload.get("errors"):
            report["environment_logs_probe_status"] = "FAIL"
            report["railway_api_error_kind"] = "GraphQLError"
            report["railway_api_error_excerpt_redacted"] = _redact(json.dumps(log_payload.get("errors", [])))
            report["overall_status"] = "FAIL"
        else:
            report["environment_logs_probe_status"] = "PASS"
            logs = log_payload.get("data", {}).get("environmentLogs") or []
            report["environment_logs_returned_count"] = len(logs) if isinstance(logs, list) else 0
            if isinstance(logs, list) and logs:
                report["environment_logs_first_timestamp"] = logs[0].get("timestamp")
            report["overall_status"] = "PASS"
            report["limitation"] = "Read-only probe completed."

        if report["configured_environment_id_found"] is False or report["missing_service_ids"]:
            report["overall_status"] = "FAIL"
            report["limitation"] = "Configured Railway IDs do not match project metadata."

    except Exception as exc:
        kind, status, excerpt = _safe_error(exc)
        report["railway_api_error_kind"] = kind
        report["railway_api_error_excerpt_redacted"] = excerpt
        report["overall_status"] = "FAIL"
        if current_stage == "account_probe":
            report["account_probe_status"] = "FAIL"
            report["account_probe_http_status"] = status
        elif current_stage == "project_metadata":
            report["project_metadata_status"] = "FAIL"
            report["project_metadata_http_status"] = status
            report["environment_logs_probe_status"] = "NOT_RUN"
        elif current_stage == "project_services_environments":
            report["project_services_environments_status"] = "FAIL"
            report["project_metadata_status"] = "PASS"
        elif current_stage == "environment_logs":
            report["environment_logs_probe_status"] = "FAIL"
            report["environment_logs_http_status"] = status

    return _write_and_print(report)


if __name__ == "__main__":
    raise SystemExit(main())
