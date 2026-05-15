from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _ensure_repo_root_on_path() -> None:
    repo_root = str(_REPO_ROOT)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_path()

from src.railway_cadence_runtime import get_runtime_schedule_basis

ALLOWED_RUN_TYPES = {"post_close_daily_review", "midday_market_monitor", "stale_risk_refresh"}
DEFAULT_ENTRYPOINT = "python -m src.daily_runner"
SECRET_PATTERNS = [
    re.compile(r"sb_secret_[a-z0-9_\-]+", re.IGNORECASE),
    re.compile(r"service_role", re.IGNORECASE),
    re.compile(r"\bsk-[a-z0-9]{8,}\b", re.IGNORECASE),
    re.compile(r"\bbot\d{8,}:[A-Za-z0-9_\-]{20,}\b"),
    re.compile(r"\btoken\s*[=:]\s*[^\s]+", re.IGNORECASE),
]
REDACTED = "[REDACTED_SECRET_LIKE_VALUE]"
UNSAFE_EXECUTION_PHRASES = ["order created", "place order", "broker execution", "live execution", "real-money execution"]
SAFE_NEGATIVE_EXECUTION_PHRASES = {
    "no broker connection",
    "no live execution",
    "no real-money execution",
    "no real-money execution observed",
    "no broker/live/order/real-money execution observed",
    "no order execution observed",
}


def _safe_load_json(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON input: {exc}") from exc


def _collect_messages(input_json: Any) -> list[str]:
    if isinstance(input_json, list):
        items = input_json
    elif isinstance(input_json, dict):
        items = input_json.get("logs") if isinstance(input_json.get("logs"), list) else [input_json]
    else:
        return []

    messages: list[str] = []
    for row in items:
        if isinstance(row, str):
            messages.append(row)
            continue
        if not isinstance(row, dict):
            continue
        for k in ("message", "log", "text", "line"):
            v = row.get(k)
            if isinstance(v, str):
                messages.append(v)
                break
    return messages


def _collect_rows(input_json: Any) -> list[dict[str, Any]]:
    if isinstance(input_json, list):
        return [x for x in input_json if isinstance(x, dict)]
    if isinstance(input_json, dict):
        logs = input_json.get("logs")
        if isinstance(logs, list):
            return [x for x in logs if isinstance(x, dict)]
        return [input_json]
    return []


def _parse_ts(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def _has_secret_like(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    return any(p.search(v) for p in SECRET_PATTERNS)


def _sanitize_text(v: Any) -> Any:
    if isinstance(v, str) and _has_secret_like(v):
        return REDACTED
    return v


def _is_safe_negative_guardrail_line(normalized_line: str) -> bool:
    if normalized_line in SAFE_NEGATIVE_EXECUTION_PHRASES:
        return True
    parts = [p.strip() for p in re.split(r"[;,]", normalized_line) if p.strip()]
    return bool(parts) and all(p in SAFE_NEGATIVE_EXECUTION_PHRASES for p in parts)




def _derive_expected_schedule_basis_fragment(expected_run_type: str) -> str:
    schedule_basis = get_runtime_schedule_basis(expected_run_type)
    marker = "Railway cron UTC:"
    if marker in schedule_basis:
        cron_fragment = schedule_basis.split(marker, 1)[1].rstrip(")").strip()
        return f"{marker} {cron_fragment}"
    return schedule_basis

def validate_evidence(args: argparse.Namespace) -> dict[str, Any]:
    if args.expected_run_type not in ALLOWED_RUN_TYPES:
        raise ValueError("unsupported expected run type")

    messages: list[str] = []
    rows: list[dict[str, Any]] = []
    input_json: Any = None
    if args.input_json:
        input_json = _safe_load_json(Path(args.input_json))
        messages.extend(_collect_messages(input_json))
        rows.extend(_collect_rows(input_json))
    if args.input_text:
        messages.extend(Path(args.input_text).read_text(encoding="utf-8").splitlines())

    full_text = "\n".join(messages)

    deployment_id = None
    run_record_id = None
    execution_summary: dict[str, Any] | None = None
    started_at = None
    finished_at = None
    paper_trades = None
    paper_events = None
    telegram_sent = False
    telegram_chat_id_redacted = False

    dep_match = re.search(r"\bdeployment id\s*[:=]\s*([0-9a-f\-]{36})", full_text, re.IGNORECASE)
    if dep_match:
        deployment_id = dep_match.group(1)
    if deployment_id is None:
        for row in rows:
            tags = row.get("tags")
            if isinstance(tags, dict) and isinstance(tags.get("deploymentId"), str):
                deployment_id = tags["deploymentId"]
                break

    run_match = re.search(r"\brun record\s*[:=]\s*id\s*[:=]\s*(\d+)|\bid=(\d+)\b", full_text, re.IGNORECASE)
    if run_match:
        run_record_id = int(run_match.group(1) or run_match.group(2))

    ex_match = re.search(r"execution_summary\s*=\s*(\{.*?\})", full_text, re.DOTALL)
    if ex_match:
        try:
            execution_summary = json.loads(ex_match.group(1))
        except json.JSONDecodeError:
            execution_summary = None

    st_match = re.search(r"started_at\s*[:=]\s*([0-9T:\-\.\+Z]+)", full_text)
    fn_match = re.search(r"finished_at\s*[:=]\s*([0-9T:\-\.\+Z]+)", full_text)
    started_at = st_match.group(1) if st_match else None
    finished_at = fn_match.group(1) if fn_match else None

    pe_match = re.search(r"trades\s*=\s*(\d+)\s*,\s*events\s*=\s*(\d+)", full_text, re.IGNORECASE)
    if pe_match:
        paper_trades = int(pe_match.group(1))
        paper_events = int(pe_match.group(2))

    tg_match = re.search(r"telegram message sent to chat_id\s*=\s*([^\s,]+)", full_text, re.IGNORECASE)
    if tg_match:
        telegram_sent = True
        telegram_chat_id_redacted = True

    observed_run_type = execution_summary.get("run_type") if execution_summary else None
    execution_status = execution_summary.get("status") if execution_summary else None
    entrypoint = execution_summary.get("entrypoint") if execution_summary else None
    schedule_basis = execution_summary.get("schedule_basis") if execution_summary else None

    secrets_observed = any(p.search(full_text) for p in SECRET_PATTERNS)
    if _has_secret_like(entrypoint):
        secrets_observed = True
        entrypoint = REDACTED
    if _has_secret_like(schedule_basis):
        secrets_observed = True
        schedule_basis = REDACTED
    if _has_secret_like(deployment_id):
        secrets_observed = True
        deployment_id = REDACTED

    broker_live_order_execution_observed = False
    for line in messages:
        normalized = " ".join(line.lower().split())
        if _is_safe_negative_guardrail_line(normalized):
            continue
        if any(x in normalized for x in UNSAFE_EXECUTION_PHRASES):
            broker_live_order_execution_observed = True
            break

    notes: list[str] = []
    status = "pass"

    if execution_summary is None:
        status = "fail"
        notes.append("missing execution_summary")
    if observed_run_type != args.expected_run_type:
        status = "fail"
        notes.append("run_type mismatch")
    if execution_status != "success":
        status = "fail"
        notes.append("execution status is not success")
    if entrypoint != args.expected_entrypoint:
        status = "fail"
        notes.append("entrypoint mismatch")
    expected_schedule_basis_contains = args.expected_schedule_basis_contains or _derive_expected_schedule_basis_fragment(args.expected_run_type)
    if expected_schedule_basis_contains and (not schedule_basis or expected_schedule_basis_contains not in str(schedule_basis)):
        status = "fail"
        notes.append("schedule basis mismatch")
    if "completed" not in full_text.lower():
        status = "fail"
        notes.append("completed message missing")
    if secrets_observed:
        status = "fail"
        notes.append("secret-like pattern observed")
    if broker_live_order_execution_observed:
        status = "fail"
        notes.append("broker/live/order execution wording observed")

    duration_seconds = None
    st_dt, fn_dt = _parse_ts(started_at), _parse_ts(finished_at)
    if st_dt and fn_dt:
        duration_seconds = round((fn_dt - st_dt).total_seconds(), 6)

    notes = [_sanitize_text(n) for n in notes]
    result = {
        "status": status,
        "expected_run_type": args.expected_run_type,
        "observed_run_type": observed_run_type,
        "execution_status": execution_status,
        "entrypoint": _sanitize_text(entrypoint),
        "schedule_basis": _sanitize_text(schedule_basis),
        "run_record_id": run_record_id,
        "deployment_id": _sanitize_text(deployment_id),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "paper_trades": paper_trades,
        "paper_events": paper_events,
        "telegram_sent": telegram_sent,
        "telegram_chat_id_redacted": telegram_chat_id_redacted,
        "secrets_observed": secrets_observed,
        "broker_live_order_execution_observed": broker_live_order_execution_observed,
        "manual_evidence_only": True,
        "natural_cron_evidence": False,
        "notes": notes,
    }
    return result


def to_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Railway Cadence Evidence Validation Report",
        "",
        f"- status: `{result['status']}`",
        f"- expected_run_type: `{result['expected_run_type']}`",
        f"- observed_run_type: `{result['observed_run_type']}`",
        f"- execution_status: `{result['execution_status']}`",
        f"- entrypoint: `{result['entrypoint']}`",
        f"- schedule_basis: `{result['schedule_basis']}`",
        f"- run_record_id: `{result['run_record_id']}`",
        f"- deployment_id: `{result['deployment_id']}`",
        f"- started_at: `{result['started_at']}`",
        f"- finished_at: `{result['finished_at']}`",
        f"- duration_seconds: `{result['duration_seconds']}`",
        f"- paper_trades: `{result['paper_trades']}`",
        f"- paper_events: `{result['paper_events']}`",
        f"- telegram_sent: `{result['telegram_sent']}`",
        f"- telegram_chat_id_redacted: `{result['telegram_chat_id_redacted']}`",
        f"- secrets_observed: `{result['secrets_observed']}`",
        f"- broker_live_order_execution_observed: `{result['broker_live_order_execution_observed']}`",
        "- only for paper-only simulated decision support review.",
        "- no broker connection, no live execution, no real-money execution.",
        "",
        "## Notes",
    ]
    for n in result["notes"]:
        lines.append(f"- {n}")
    if not result["notes"]:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input-json")
    p.add_argument("--input-text")
    p.add_argument("--expected-run-type", required=True)
    p.add_argument("--expected-entrypoint", default=DEFAULT_ENTRYPOINT)
    p.add_argument("--expected-schedule-basis-contains")
    p.add_argument("--output-json")
    p.add_argument("--output-md")
    args = p.parse_args()
    result = validate_evidence(args)
    print(to_markdown(result))
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(to_markdown(result), encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
