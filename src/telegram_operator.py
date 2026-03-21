from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from src.runs import list_recent_runs

_RUNS_COMMAND_PATTERN = re.compile(r"^/runs(?:\s+(\d+)d)?\s*$", re.IGNORECASE)
_DEFAULT_DAYS = 5
_MAX_DAYS = 30
_DEFAULT_LIMIT = 50


def _parse_allowed_user_ids(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {token.strip() for token in raw_value.split(",") if token.strip()}


def _is_operator_authorized(update: dict[str, Any]) -> bool:
    """
    Guardrail: only the configured operator chat/allowed user can use commands.

    We enforce existing chat-level control via TELEGRAM_CHAT_ID and optionally add
    stricter user-id allowlisting via TELEGRAM_OPERATOR_ALLOWED_USER_IDS.
    """
    configured_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    message = update.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", "")).strip()
    from_user_id = str((message.get("from") or {}).get("id", "")).strip()
    if not configured_chat_id or chat_id != configured_chat_id:
        return False

    allowed_user_ids = _parse_allowed_user_ids(os.getenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS"))
    if not allowed_user_ids:
        return True
    return from_user_id in allowed_user_ids


def _parse_runs_days(command_text: str) -> int:
    match = _RUNS_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError("Unsupported command. Use /runs or /runs <days>d, e.g. /runs 5d.")

    days_group = match.group(1)
    if not days_group:
        return _DEFAULT_DAYS

    days = int(days_group)
    if days <= 0 or days > _MAX_DAYS:
        raise ValueError(f"Days must be between 1 and {_MAX_DAYS}. Example: /runs 5d.")
    return days


def _normalize_run_time(row: dict[str, Any]) -> str:
    # Guardrail: `runs` operator output relies on stable schema fields only.
    # We intentionally use `created_at` (existing column) and avoid fallbacks to
    # non-guaranteed fields so malformed schema assumptions do not break `/runs`.
    raw = row.get("created_at")
    if not raw:
        return "N/A"
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(raw)


def build_runs_command_message(rows: list[dict[str, Any]], *, days: int) -> str:
    if not rows:
        return f"No runs found in the last {days} day(s)."

    header = f"Recent runs (last {days} day(s), newest first):"
    lines = [header]
    for row in rows:
        run_id = row.get("id", "N/A")
        run_status = row.get("status") or "UNKNOWN"
        run_time = _normalize_run_time(row)
        lines.append(f"- run_id={run_id} | time={run_time} | status={run_status}")
    return "\n".join(lines)


def handle_telegram_operator_command(client: Any, update: dict[str, Any]) -> str | None:
    """
    Parse and handle Telegram operator commands.

    Returns:
    - Response text for recognized commands.
    - None when update is not an operator command (so existing notification flow
      can ignore it with no behavior change).
    """
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    if not text.startswith("/"):
        return None

    if not text.lower().startswith("/runs"):
        return None

    if not _is_operator_authorized(update):
        return "Unauthorized: this command is restricted to the configured operator chat/user."

    try:
        days = _parse_runs_days(text)
    except ValueError as exc:
        return str(exc)
    runs = list_recent_runs(client, days=days, limit=_DEFAULT_LIMIT)
    return build_runs_command_message(runs, days=days)
