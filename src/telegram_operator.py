from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from typing import Any

from src.daily_runner import ENTRYPOINT, SCHEDULE_BASIS
from src.runs import get_latest_run_execution_summary, get_run_by_id, list_recent_runs

_RUNS_COMMAND_PATTERN = re.compile(r"^/runs(?:\s+(\d+)d)?\s*$", re.IGNORECASE)
_RISK_REVIEW_COMMAND_PATTERN = re.compile(r"^/risk_review(?:\s+(\S+))?\s*$", re.IGNORECASE)
_RUNNER_STATUS_COMMAND_PATTERN = re.compile(r"^/runner_status\s*$", re.IGNORECASE)
_HELP_COMMAND_PATTERN = re.compile(r"^/(?:help|h)\s*$", re.IGNORECASE)
_DEFAULT_DAYS = 5
_MAX_DAYS = 30
_DEFAULT_LIMIT = 50


def _parse_allowed_user_ids(raw_value: str | None) -> set[str]:
    if not raw_value:
        return set()
    return {token.strip() for token in raw_value.split(",") if token.strip()}


def get_operator_auth_decision(update: dict[str, Any]) -> dict[str, Any]:
    """
    Guardrail: only the configured operator chat/allowed user can use commands.

    We enforce existing chat-level control via TELEGRAM_CHAT_ID and optionally add
    stricter user-id allowlisting via TELEGRAM_OPERATOR_ALLOWED_USER_IDS.
    """
    configured_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    message = update.get("message") or {}
    chat_id = str((message.get("chat") or {}).get("id", "")).strip()
    from_user_id = str((message.get("from") or {}).get("id", "")).strip()
    if not configured_chat_id:
        return {
            "authorized": False,
            "reason": "missing_configured_chat_id",
            "chat_id": chat_id,
            "user_id": from_user_id,
        }
    if chat_id != configured_chat_id:
        return {
            "authorized": False,
            "reason": "chat_not_allowed",
            "chat_id": chat_id,
            "user_id": from_user_id,
        }

    allowed_user_ids = _parse_allowed_user_ids(os.getenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS"))
    if not allowed_user_ids:
        return {
            "authorized": True,
            "reason": "chat_allowed_user_open",
            "chat_id": chat_id,
            "user_id": from_user_id,
        }
    is_allowed = from_user_id in allowed_user_ids
    return {
        "authorized": is_allowed,
        "reason": "user_allowed" if is_allowed else "user_not_allowed",
        "chat_id": chat_id,
        "user_id": from_user_id,
    }


def _parse_runs_days(command_text: str) -> int:
    match = _RUNS_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError("Unsupported command. Use /runs or /runs [days]d, e.g. /runs 5d.")

    days_group = match.group(1)
    if not days_group:
        return _DEFAULT_DAYS

    days = int(days_group)
    if days <= 0 or days > _MAX_DAYS:
        raise ValueError(f"Days must be between 1 and {_MAX_DAYS}. Example: /runs 5d.")
    return days


def _parse_risk_review_run_id(command_text: str) -> int:
    """
    Parse `/risk_review [run_id]` with strict integer validation.

    Guardrail: run_id must be a positive integer so malformed user input does not
    reach DB queries/execution paths as ambiguous tokens.
    """
    match = _RISK_REVIEW_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError("Unsupported command. Use /risk_review [run_id], e.g. /risk_review 12345.")

    run_id_token = (match.group(1) or "").strip()
    if not run_id_token:
        raise ValueError("Usage: /risk_review [run_id], e.g. /risk_review 12345.")

    if not run_id_token.isdigit():
        raise ValueError("Invalid run_id format. Use a positive integer, e.g. /risk_review 12345.")

    run_id = int(run_id_token)
    if run_id <= 0:
        raise ValueError("Invalid run_id format. Use a positive integer, e.g. /risk_review 12345.")
    return run_id


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


def _parse_iso_datetime(value: Any, *, field_name: str) -> datetime:
    """
    Parse ISO timestamps from persistent run metadata for operator rendering.

    Guardrail: strict parsing keeps operator output deterministic and allows
    safe failure fallback when data shape is malformed/unexpected.
    """
    if not value:
        raise ValueError(f"missing {field_name}")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            # Guardrail: persisted timestamps should be timezone-aware; when a
            # naive value appears unexpectedly, normalize as UTC to keep
            # operator output deterministic across host timezones.
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}") from exc


def _format_runner_status_message(latest_summary_row: dict[str, Any]) -> str:
    """
    Build operator-facing response for `/runner_status` from latest persisted run.

    Traceability notes:
    - `created_at` is treated as runner `started_at` because run records are
      created when the daily workflow starts.
    - Entry point + schedule basis are fixed constants from `src.daily_runner`,
      so responses remain consistent with deployed runner contract.
    """
    started_at = _parse_iso_datetime(latest_summary_row.get("created_at"), field_name="created_at")
    finished_raw = latest_summary_row.get("finished_at")
    finished_at: datetime | None = None
    if finished_raw:
        finished_at = _parse_iso_datetime(finished_raw, field_name="finished_at")

    duration_seconds = "N/A"
    if finished_at is not None:
        duration_value = max((finished_at - started_at).total_seconds(), 0.0)
        duration_seconds = f"{round(duration_value, 6)}"

    status = html.escape(str(latest_summary_row.get("status") or "UNKNOWN"))
    run_id = html.escape(str(latest_summary_row.get("id", "N/A")))
    error_summary = (latest_summary_row.get("error_summary") or "").strip()
    # Telegram replies use parse_mode="HTML"; escape dynamic failure text so
    # persisted `<`, `>`, `&` in error_summary cannot break message parsing.
    error_line = html.escape(error_summary) if error_summary else "None"

    lines = [
        f"Latest daily runner status (run_id={run_id}):",
        f"- status: {status}",
        f"- started_at: {started_at.isoformat()}",
        f"- finished_at: {finished_at.isoformat() if finished_at else 'N/A'}",
        f"- duration_seconds: {duration_seconds}",
        f"- entrypoint: {ENTRYPOINT}",
        f"- schedule_basis: {SCHEDULE_BASIS}",
        f"- error_summary: {error_line}",
    ]
    return "\n".join(lines)


def build_help_command_message() -> str:
    """
    Return a compact bilingual operator help message for Telegram command discoverability.

    Guardrail: this copy is informational only (analysis/suggestion/review support)
    and must never imply or enable autonomous real-money execution.
    """
    return "\n".join(
        [
            "AI HK Investment System — Operator Help",
            "用途: AI decision support + paper trading simulation (投資決策輔助 + 模擬盤).",
            "Guardrail: analysis/suggestion/review support only; human makes final decision.",
            "風險界線: no real-money auto execution (不會自動進行真錢交易).",
            "",
            "Commands:",
            "- /runs : List recent run IDs from the last 5 days (最近 5 日 run 記錄).",
            "- /runs [days]d : Query a custom window, e.g. /runs 7d (自訂查詢日數).",
            "- /runner_status : Show latest daily runner execution summary (最新 runner 狀態摘要).",
            "- /risk_review [run_id] : Run paper-trading risk review for one run (查看單次 run 風險回顧).",
            "- /help : Show this operator usage guide (顯示操作說明).",
            "- /h : Alias of /help (與 /help 相同).",
        ]
    )


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


def _build_risk_review_command_message(*, run_id: int, risk_review: dict[str, Any]) -> str:
    """Return a compact operator-facing summary for synchronous risk review output."""
    lines = [
        f"Accepted: /risk_review run_id={run_id}.",
        "Status: completed.",
        (
            "Result summary: "
            f"executed_buys={int(risk_review.get('total_executed_buys') or 0)}, "
            f"blocked_buys={int(risk_review.get('total_blocked_buys') or 0)}, "
            f"warning_buys={int(risk_review.get('total_warning_buys') or 0)}, "
            f"tickers={len(risk_review.get('per_ticker') or {})}."
        ),
    ]
    return "\n".join(lines)


def _get_caller_context(update: dict[str, Any]) -> tuple[str, str, str]:
    message = update.get("message") or {}
    text = (message.get("text") or "").strip()
    chat_id = str((message.get("chat") or {}).get("id", "")).strip() or "<unknown>"
    user_id = str((message.get("from") or {}).get("id", "")).strip() or "<unknown>"
    return text, chat_id, user_id


def _get_paper_risk_review(client: Any, *, run_id: int) -> dict[str, Any]:
    """
    Lazy-load paper-trading review dependency so command parsing/auth tests can run
    without importing optional runtime DB client packages at module import time.
    """
    from src.paper_trading import get_paper_risk_review_for_run

    return get_paper_risk_review_for_run(client, run_id=run_id)


def handle_telegram_operator_command(client: Any, update: dict[str, Any]) -> str | None:
    """
    Parse and handle Telegram operator commands.

    Returns:
    - Response text for recognized commands.
    - None when update is not an operator command (so existing notification flow
      can ignore it with no behavior change).

    Traceability notes:
    - Logs include command + caller context for operator audits.
    - Internal errors are logged in detail but sanitized for Telegram replies.
    """
    text, chat_id, user_id = _get_caller_context(update)
    if not text.startswith("/"):
        return None

    is_help_command = bool(_HELP_COMMAND_PATTERN.match(text))
    is_runs_command = text.lower().startswith("/runs")
    is_runner_status_command = bool(_RUNNER_STATUS_COMMAND_PATTERN.match(text))
    is_risk_review_command = text.lower().startswith("/risk_review")
    if not (is_help_command or is_runs_command or is_runner_status_command or is_risk_review_command):
        return None

    print(
        "Telegram operator command received: "
        f"text={text!r} chat_id={chat_id} user_id={user_id}"
    )

    auth_decision = get_operator_auth_decision(update)
    print(
        "Telegram operator auth decision: "
        f"authorized={auth_decision.get('authorized')} reason={auth_decision.get('reason')} "
        f"chat_id={chat_id} user_id={user_id}"
    )
    if not auth_decision.get("authorized"):
        return "Unauthorized: this command is restricted to the configured operator chat/user."

    try:
        if is_help_command:
            return build_help_command_message()

        if is_runs_command:
            try:
                days = _parse_runs_days(text)
            except ValueError as exc:
                return str(exc)
            runs = list_recent_runs(client, days=days, limit=_DEFAULT_LIMIT)
            return build_runs_command_message(runs, days=days)

        if is_runner_status_command:
            # Authorization already completed above. Keep this lookup path narrow
            # and read-only so it remains a low-latency operator observability
            # query that does not affect webhook process stability.
            try:
                latest_row = get_latest_run_execution_summary(client)
            except Exception as exc:
                print(
                    "Telegram /runner_status lookup failed: "
                    f"chat_id={chat_id} user_id={user_id} error={exc}"
                )
                return (
                    "Accepted: /runner_status.\n"
                    "Status: failed.\n"
                    "Reason: internal status lookup error."
                )

            if not latest_row:
                return (
                    "Accepted: /runner_status.\n"
                    "Status: no data.\n"
                    "Reason: no persisted daily runner summary available yet."
                )

            try:
                return _format_runner_status_message(latest_row)
            except Exception as exc:
                # Safe operator response: never expose internal traceback/raw
                # exception detail in Telegram, while keeping details in logs.
                print(
                    "Telegram /runner_status formatting failed: "
                    f"chat_id={chat_id} user_id={user_id} error={exc}"
                )
                return (
                    "Accepted: /runner_status.\n"
                    "Status: failed.\n"
                    "Reason: latest summary formatting error."
                )

        # /risk_review execution guardrail:
        # - Parse and validate run_id early.
        # - Verify run exists before expensive review query.
        # - Keep failures isolated with explicit operator-safe responses.
        try:
            run_id = _parse_risk_review_run_id(text)
        except ValueError as exc:
            print(
                "Telegram /risk_review failed during parsing: "
                f"chat_id={chat_id} user_id={user_id} error={exc}"
            )
            return str(exc)

        print(
            "Telegram /risk_review requested: "
            f"run_id={run_id} chat_id={chat_id} user_id={user_id} status=accepted"
        )

        try:
            run_row = get_run_by_id(client, run_id=run_id)
        except Exception as exc:
            print(
                "Telegram /risk_review failed during run lookup: "
                f"run_id={run_id} chat_id={chat_id} user_id={user_id} error={exc!r}"
            )
            return (
                f"Accepted: /risk_review run_id={run_id}.\n"
                "Status: failed.\n"
                "Reason: internal review execution error. Please check service logs and retry."
            )

        if not run_row:
            print(
                "Telegram /risk_review failed: "
                f"run_id={run_id} chat_id={chat_id} user_id={user_id} reason=run_not_found"
            )
            return f"Failed: run_id={run_id} not found. Use /runs to list recent runs."

        try:
            risk_review = _get_paper_risk_review(client, run_id=run_id)
        except Exception as exc:  # defensive operator boundary
            print(
                "Telegram /risk_review internal failure: "
                f"run_id={run_id} chat_id={chat_id} user_id={user_id} error={exc!r}"
            )
            return (
                f"Accepted: /risk_review run_id={run_id}.\n"
                "Status: failed.\n"
                "Reason: internal review execution error. Please check service logs and retry."
            )

        print(
            "Telegram /risk_review completed: "
            f"run_id={run_id} chat_id={chat_id} user_id={user_id} "
            "status=completed"
        )
        return _build_risk_review_command_message(run_id=run_id, risk_review=risk_review)
    except Exception as exc:
        print(
            "Telegram operator command internal failure: "
            f"text={text!r} chat_id={chat_id} user_id={user_id} error={exc!r}"
        )
        return "Failed: internal command processing error. Please check service logs."
