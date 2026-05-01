from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from src.daily_runner import ENTRYPOINT, SCHEDULE_BASIS
from src.human_decision_journal import (
    ALLOWED_HUMAN_ACTIONS,
    ALLOWED_SOURCE_COMMANDS,
    record_run_level_decision_note,
    record_stock_level_decision_note,
)
from src.runs import get_latest_run_execution_summary, get_run_by_id, list_recent_runs

_RUNS_COMMAND_PATTERN = re.compile(r"^/runs(?:\s+(\d+)d)?\s*$", re.IGNORECASE)
_RISK_REVIEW_COMMAND_PATTERN = re.compile(r"^/risk_review(?:\s+(\S+))?\s*$", re.IGNORECASE)
_RUNNER_STATUS_COMMAND_PATTERN = re.compile(r"^/runner_status\s*$", re.IGNORECASE)
_PNL_REVIEW_COMMAND_PATTERN = re.compile(r"^/pnl_review\s*$", re.IGNORECASE)
_OUTCOME_REVIEW_COMMAND_PATTERN = re.compile(r"^/outcome_review(?:\s+(\S+))?\s*$", re.IGNORECASE)
_DAILY_REVIEW_COMMAND_PATTERN = re.compile(r"^/daily_review\s*$", re.IGNORECASE)
_DECISION_NOTE_COMMAND_PATTERN = re.compile(r"^/decision_note(?:\s+(.*))?$", re.IGNORECASE)
_HELP_COMMAND_PATTERN = re.compile(r"^/(?:help|h)\s*$", re.IGNORECASE)
_DEFAULT_DAYS = 5
_MAX_DAYS = 30
_DEFAULT_LIMIT = 50
_OUTCOME_REVIEW_MIN_DAYS = 1
_OUTCOME_REVIEW_MAX_DAYS = 365
_DECISION_NOTE_STOCK_ID_MAX_LENGTH = 32
_DECISION_NOTE_NOTE_MAX_LENGTH = 500
_DECISION_NOTE_STOCK_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_DECISION_NOTE_EXECUTION_WORDING_PATTERN = re.compile(r"\b(?:broker|execute|execution|real[-_\s]?money|live[-_\s]?money|live\s+trade)\b", re.IGNORECASE)
_HKT_TZ = ZoneInfo("Asia/Hong_Kong")


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
        raise ValueError("Usage: /runs or /runs [days]d (e.g. /runs 5d).")

    days_group = match.group(1)
    if not days_group:
        return _DEFAULT_DAYS

    days = int(days_group)
    if days <= 0 or days > _MAX_DAYS:
        raise ValueError(f"Invalid input: days must be between 1 and {_MAX_DAYS}. Usage: /runs [days]d (e.g. /runs 5d).")
    return days


def _parse_risk_review_run_id(command_text: str) -> int:
    """
    Parse `/risk_review [run_id]` with strict integer validation.

    Guardrail: run_id must be a positive integer so malformed user input does not
    reach DB queries/execution paths as ambiguous tokens.
    """
    match = _RISK_REVIEW_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError("Usage: /risk_review [run_id] (e.g. /risk_review 12345).")

    run_id_token = (match.group(1) or "").strip()
    if not run_id_token:
        raise ValueError("Usage: /risk_review [run_id] (e.g. /risk_review 12345).")

    if not run_id_token.isdigit():
        raise ValueError("Invalid input: run_id must be a positive integer. Usage: /risk_review [run_id] (e.g. /risk_review 12345).")

    run_id = int(run_id_token)
    if run_id <= 0:
        raise ValueError("Invalid input: run_id must be a positive integer. Usage: /risk_review [run_id] (e.g. /risk_review 12345).")
    return run_id


def _parse_pnl_review_command(command_text: str) -> None:
    """
    Validate `/pnl_review` with no extra tokens.

    Guardrail: malformed variants (for example `/pnl_review now`) should return
    explicit usage guidance rather than being silently ignored.
    """
    if not _PNL_REVIEW_COMMAND_PATTERN.match(command_text or ""):
        raise ValueError("Usage: /pnl_review")


def _parse_outcome_review_command(command_text: str) -> int | None:
    """
    Parse `/outcome_review` with optional bounded integer days window.

    Grammar:
    - /outcome_review
    - /outcome_review <days>
    """
    match = _OUTCOME_REVIEW_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError("Usage: /outcome_review [days] (e.g. /outcome_review 30).")
    days_token = (match.group(1) or "").strip()
    if not days_token:
        return None
    if not days_token.isdigit():
        raise ValueError("Invalid input: days must be an integer. Usage: /outcome_review [days] (e.g. /outcome_review 30).")
    days = int(days_token)
    if days < _OUTCOME_REVIEW_MIN_DAYS or days > _OUTCOME_REVIEW_MAX_DAYS:
        raise ValueError(
            f"Invalid input: days must be between {_OUTCOME_REVIEW_MIN_DAYS} and {_OUTCOME_REVIEW_MAX_DAYS}. "
            "Usage: /outcome_review [days] (e.g. /outcome_review 30)."
        )
    return days




def _parse_decision_note_command(command_text: str) -> dict[str, Any]:
    match = _DECISION_NOTE_COMMAND_PATTERN.match(command_text or "")
    if not match:
        raise ValueError(
            "Usage: /decision_note scope=run run_id=123 source_command=/daily_review human_action=observe note=Daily review checked."
        )
    args_text = (match.group(1) or "").strip()
    if not args_text:
        raise ValueError(
            "Invalid input: missing scope. Usage: /decision_note scope=run run_id=123 source_command=/daily_review human_action=observe note=Daily review checked."
        )

    parsed: dict[str, str] = {}
    note_match = re.search(r"\bnote=(.*)$", args_text)
    leading = args_text
    if note_match:
        parsed["note"] = note_match.group(1).strip()
        leading = args_text[: note_match.start()].strip()
    for token in leading.split():
        if "=" not in token:
            raise ValueError(
                "Malformed command: expected key=value tokens. Usage: /decision_note scope=run run_id=123 source_command=/daily_review human_action=observe note=Daily review checked."
            )
        key, value = token.split("=", 1)
        parsed[key.strip().lower()] = value.strip()

    scope = parsed.get("scope", "").strip().lower()
    if not scope:
        raise ValueError("Invalid input: missing scope.")
    if scope not in {"run", "stock"}:
        raise ValueError("Invalid input: unsupported scope. scope must be run or stock.")

    run_id_token = parsed.get("run_id", "").strip()
    if not run_id_token:
        raise ValueError("Invalid input: missing run_id.")
    if not run_id_token.isdigit() or int(run_id_token) <= 0:
        raise ValueError("Invalid input: run_id must be a positive integer.")
    run_id = int(run_id_token)

    source_command = parsed.get("source_command", "").strip()
    if not source_command:
        raise ValueError("Invalid input: missing source_command.")
    if source_command not in ALLOWED_SOURCE_COMMANDS:
        raise ValueError("Invalid input: unsupported source_command.")

    human_action = parsed.get("human_action", "").strip()
    if not human_action:
        raise ValueError("Invalid input: missing human_action.")
    if human_action not in ALLOWED_HUMAN_ACTIONS:
        raise ValueError("Invalid input: unsupported human_action.")

    note = parsed.get("note", "").strip()
    if not note:
        raise ValueError("Invalid input: note must not be empty.")
    if len(note) > _DECISION_NOTE_NOTE_MAX_LENGTH:
        raise ValueError(f"Invalid input: note exceeds max length {_DECISION_NOTE_NOTE_MAX_LENGTH}.")
    if _DECISION_NOTE_EXECUTION_WORDING_PATTERN.search(note):
        raise ValueError("Invalid input: note must remain journaling-only and must not imply broker/live execution.")

    stock_id = parsed.get("stock_id", "").strip()
    if scope == "stock":
        if not stock_id:
            raise ValueError("Invalid input: stock_id is required when scope=stock.")
        if len(stock_id) > _DECISION_NOTE_STOCK_ID_MAX_LENGTH:
            raise ValueError(f"Invalid input: stock_id exceeds max length {_DECISION_NOTE_STOCK_ID_MAX_LENGTH}.")
        if not _DECISION_NOTE_STOCK_ID_PATTERN.match(stock_id):
            raise ValueError("Invalid input: stock_id contains unsupported characters.")

    return {
        "scope": scope,
        "run_id": run_id,
        "stock_id": stock_id if scope == "stock" else None,
        "source_command": source_command,
        "human_action": human_action,
        "note": note,
    }
def _parse_daily_review_command(command_text: str) -> None:
    """Validate `/daily_review` with no extra tokens."""
    if not _DAILY_REVIEW_COMMAND_PATTERN.match(command_text or ""):
        raise ValueError("Usage: /daily_review")


def _normalize_run_time(row: dict[str, Any]) -> str:
    # Human-facing display policy:
    # - Operator-facing time text is always rendered in HKT for consistency.
    # - Storage/log semantics stay unchanged (persisted UTC/ISO is parsed only
    #   at display boundary and never mutated by this formatter).
    #
    # Guardrail: `runs` operator output relies on stable schema fields only.
    # We intentionally use `created_at` (existing column) and avoid fallbacks to
    # non-guaranteed fields so malformed schema assumptions do not break `/runs`.
    raw = row.get("created_at")
    return _format_display_timestamp_hkt(raw, field_name="created_at")


def _format_display_timestamp_hkt(raw_value: Any, *, field_name: str) -> str:
    """
    Render operator-facing timestamps in `Asia/Hong_Kong` at display boundary.

    Timestamp boundary contract:
    - Parse persisted/raw values defensively for read surfaces only.
    - Keep storage semantics untouched (no write-back/no normalization side effects).
    - Show explicit `HKT` suffix so operators know timezone context quickly.
    """
    if not raw_value:
        return "N/A"
    if isinstance(raw_value, datetime):
        parsed = raw_value if raw_value.tzinfo else raw_value.replace(tzinfo=timezone.utc)
        return f"{parsed.astimezone(_HKT_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"

    raw_text = str(raw_value).strip()
    # Date-only value should be treated as a business-date label, not as UTC
    # midnight instant, to avoid surprising +08:00 clock shifts in operator view.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_text):
        return f"{raw_text} 00:00:00 HKT (date-based)"
    try:
        parsed = _parse_iso_datetime(raw_value, field_name=field_name)
        return f"{parsed.astimezone(_HKT_TZ).strftime('%Y-%m-%d %H:%M:%S')} HKT"
    except ValueError:
        return raw_text


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


def _escape_dynamic(value: Any) -> str:
    """Escape dynamic Telegram message fields for HTML parse-mode safety."""
    return html.escape(str(value), quote=False)


def _build_operator_message(
    *,
    command_label: str,
    status: str,
    reason: str | None = None,
    result: str | None = None,
    fields: list[tuple[str, Any]] | None = None,
) -> str:
    """
    Build operator-facing responses using one small shared contract.

    Step 40 contract goals:
    - keep command/status/result wording consistent across commands;
    - keep key fields in deterministic `- key: value` lines for scanability;
    - enforce centralized HTML-safe escaping for dynamic field rendering.
    """
    escaped_command_label = _escape_dynamic(command_label)
    escaped_status = _escape_dynamic(status)
    lines = [f"Command: {escaped_command_label}", f"Status: {escaped_status}."]
    if result:
        lines.append(f"Result: {_escape_dynamic(result)}")
    if reason:
        lines.append(f"Reason: {_escape_dynamic(reason)}")
    for key, value in fields or []:
        lines.append(f"- {key}: {_escape_dynamic(value)}")
    return "\n".join(lines)


def _build_usage_error_message(*, command_label: str, error_text: str) -> str:
    """
    Keep validation/usage failures in the same operator-facing response contract.

    Guardrail: parsing/validation errors are expected operator input paths and
    should stay easy to scan with the same `Command` + `Status` + `Reason` shape.
    """
    return _build_operator_message(
        command_label=command_label,
        status="failed",
        reason=error_text.rstrip("."),
    )


def _format_stock_display(*, stock_id: Any, stock_name: Any) -> str:
    """
    Operator stock-display policy:
    - Prefer `stock_name + stock_id` when both are available.
    - Fallback explicitly when name is unavailable (do not imply a name exists).
    """
    normalized_id = str(stock_id).strip() if stock_id is not None else ""
    normalized_name = str(stock_name).strip() if stock_name is not None else ""
    stock_id_text = normalized_id or "unknown"
    if normalized_name:
        return f"stock_name={normalized_name} | stock_id={stock_id_text}"
    return f"stock_id={stock_id_text} | name_unavailable"


def _format_runner_status_message(latest_summary_row: dict[str, Any]) -> str:
    """Build operator-facing response for `/runner_status` from latest persisted run."""
    started_at = _parse_iso_datetime(latest_summary_row.get("created_at"), field_name="created_at")
    finished_raw = latest_summary_row.get("finished_at")
    finished_at: datetime | None = None
    if finished_raw:
        finished_at = _parse_iso_datetime(finished_raw, field_name="finished_at")

    duration_seconds: str | float = "N/A"
    if finished_at is not None:
        duration_value = max((finished_at - started_at).total_seconds(), 0.0)
        duration_seconds = round(duration_value, 6)

    error_summary = (latest_summary_row.get("error_summary") or "").strip()

    return _build_operator_message(
        command_label="/runner_status",
        status="completed",
        result="latest daily runner summary (display timezone: HKT)",
        fields=[
            ("run_id", latest_summary_row.get("id", "N/A")),
            ("runner_status", latest_summary_row.get("status") or "UNKNOWN"),
            ("started_at_hkt", _format_display_timestamp_hkt(started_at, field_name="created_at")),
            (
                "finished_at_hkt",
                _format_display_timestamp_hkt(finished_at, field_name="finished_at")
                if finished_at
                else "N/A",
            ),
            ("duration_seconds", duration_seconds),
            ("entrypoint", ENTRYPOINT),
            ("schedule_basis", SCHEDULE_BASIS),
            # `error_summary` can come from persistence and may include reserved
            # HTML symbols. Rendering via `_build_operator_message` applies
            # centralized escaping so all commands stay parse-safe by default.
            ("error_summary", error_summary if error_summary else "None"),
        ],
    )


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
            "- /pnl_review : Show paper position/PnL review snapshot (查看持倉與盈虧摘要).",
            "- /outcome_review [days] : Show closed-trade outcome summary (查看平倉結果摘要，可選天數視窗).",
            "- /daily_review : Show daily operator review packet MVP (每日操作員快速檢視封包).",
            "- /decision_note scope=run run_id=123 source_command=/daily_review human_action=observe note=Daily review checked. : "
            "Record run-level human decision journal entry (journaling only; no execution).",
            "- /decision_note scope=stock run_id=123 stock_id=0700.HK source_command=/daily_review human_action=observe note=Reviewed signal; no action. : "
            "Record stock-level human decision journal entry (journaling only; no execution).",
            "- /help : Show this operator usage guide (顯示操作說明).",
            "- /h : Alias of /help (與 /help 相同).",
        ]
    )


def build_runs_command_message(rows: list[dict[str, Any]], *, days: int) -> str:
    if not rows:
        return _build_operator_message(
            command_label="/runs",
            status="no data",
            reason=f"no matching records in the last {days} day(s)",
            fields=[("window_days", days)],
        )

    fields: list[tuple[str, Any]] = [("window_days", days), ("row_count", len(rows))]
    for idx, row in enumerate(rows, start=1):
        run_id = row.get("id", "N/A")
        run_status = row.get("status") or "UNKNOWN"
        run_time = _normalize_run_time(row)
        fields.append((f"run_{idx}", f"run_id={run_id} | time={run_time} | status={run_status}"))

    return _build_operator_message(
        command_label="/runs",
        status="completed",
        result="recent runs listed (newest first)",
        fields=fields,
    )


def _build_risk_review_command_message(
    *,
    run_id: int,
    risk_review: dict[str, Any],
    run_created_at: Any,
) -> str:
    """Return a compact operator-facing summary for synchronous risk review output."""
    return _build_operator_message(
        command_label="/risk_review",
        status="completed",
        result="paper risk review generated (read-only)",
        fields=[
            ("run_id", run_id),
            (
                "run_started_at_hkt",
                _format_display_timestamp_hkt(run_created_at, field_name="created_at"),
            ),
            ("executed_buys", int(risk_review.get("total_executed_buys") or 0)),
            ("blocked_buys", int(risk_review.get("total_blocked_buys") or 0)),
            ("warning_buys", int(risk_review.get("total_warning_buys") or 0)),
            ("tickers", len(risk_review.get("per_ticker") or {})),
        ],
    )


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


def _get_paper_position_pnl_review_snapshot(client: Any) -> dict[str, Any]:
    """
    Lazy-load read-only position/PnL review dependency for command isolation.

    Guardrail: this command path must remain review-only and cannot mutate any
    simulated orders/positions/decisions.
    """
    from src.paper_trading import get_paper_position_pnl_review_snapshot

    return get_paper_position_pnl_review_snapshot(client)


def _build_pnl_review_command_message(snapshot: dict[str, Any]) -> str:
    """
    Build compact Telegram output for paper position/PnL review snapshot.

    To keep operator replies bounded, only the first 10 per-symbol rows are
    rendered in detail while preserving total symbol count in a separate field.
    """
    per_symbol = snapshot.get("per_symbol") or []
    fields: list[tuple[str, Any]] = [
        ("open_positions_count", int(snapshot.get("open_positions_count") or 0)),
        ("closed_positions_count", int(snapshot.get("closed_positions_count") or 0)),
        ("total_realized_pnl_hkd", round(float(snapshot.get("total_realized_pnl") or 0.0), 2)),
        ("total_unrealized_pnl_hkd", round(float(snapshot.get("total_unrealized_pnl") or 0.0), 2)),
        (
            "valuation_timestamp_hkt",
            _format_display_timestamp_hkt(snapshot.get("valuation_timestamp"), field_name="valuation_timestamp"),
        ),
        ("per_symbol_count", len(per_symbol)),
        ("review_scope", "paper-trading decision support only; no real-money execution"),
    ]
    for idx, row in enumerate(per_symbol[:10], start=1):
        stock_display = _format_stock_display(stock_id=row.get("stock"), stock_name=row.get("stock_name"))
        fields.append(
            (
                f"symbol_{idx}",
                (
                    f"{stock_display} "
                    f"| status={row.get('position_status')} | qty={row.get('quantity')} "
                    f"| avg_cost={float(row.get('avg_cost') or 0.0):.4f} "
                    f"| last_price={float(row.get('last_price') or 0.0):.4f} "
                    f"| realized={float(row.get('realized_pnl') or 0.0):.2f} "
                    f"| unrealized={float(row.get('unrealized_pnl') or 0.0):.2f}"
                ),
            )
        )
    if not per_symbol:
        fields.append(("note", "no matching records in current snapshot"))
    if len(per_symbol) > 10:
        fields.append(("note", "showing first 10 symbols only"))

    return _build_operator_message(
        command_label="/pnl_review",
        status="completed",
        result="paper trading position/pnl review snapshot generated",
        fields=fields,
    )


def _get_paper_trade_outcome_summary(client: Any, *, recent_days: int | None = None) -> dict[str, Any]:
    """Lazy-load closed-trade outcome summary dependency for command isolation."""
    from src.paper_trading import get_paper_trade_outcome_summary

    return get_paper_trade_outcome_summary(client, recent_days=recent_days)


def _build_outcome_review_command_message(summary: dict[str, Any]) -> str:
    """Build compact Telegram output for closed-trade outcome review summary."""
    top_winners = summary.get("top_realized_winners") or []
    top_losers = summary.get("top_realized_losers") or []
    closed_trade_count = int(summary.get("closed_trade_count") or 0)
    win_rate = summary.get("win_rate")
    win_rate_text = "N/A (closed_trade_count=0)" if win_rate is None else f"{round(float(win_rate) * 100, 2)}%"

    fields: list[tuple[str, Any]] = [
        ("window_days", summary.get("window_days") or "all"),
        (
            "window_basis",
            str(
                summary.get("window_basis")
                or "exit trade_date of paired closed trades; window anchored to latest available trade_date in snapshot"
            ),
        ),
        ("closed_trade_count", closed_trade_count),
        ("win_count", int(summary.get("win_count") or 0)),
        ("loss_count", int(summary.get("loss_count") or 0)),
        ("flat_count", int(summary.get("flat_count") or 0)),
        ("win_rate", win_rate_text),
        ("win_rate_formula", str(summary.get("win_rate_denominator") or "win_count / closed_trade_count")),
        ("median_holding_days", summary.get("median_holding_days") if closed_trade_count > 0 else "N/A"),
        ("p75_holding_days", summary.get("p75_holding_days") if closed_trade_count > 0 else "N/A"),
        ("max_holding_days", summary.get("max_holding_days") if closed_trade_count > 0 else "N/A"),
        ("review_scope", "closed paper trades only"),
        ("review_boundary", str(summary.get("review_boundary_note") or "review/diagnostic only")),
    ]
    if closed_trade_count == 0:
        fields.append(
            (
                "note",
                str(summary.get("empty_window_message") or "no closed paper trades in review window"),
            )
        )

    for idx, row in enumerate(top_winners[:5], start=1):
        fields.append(
            (
                f"winner_{idx}",
                (
                    f"{_format_stock_display(stock_id=row.get('stock'), stock_name=row.get('stock_name'))} "
                    f"| realized_pnl={float(row.get('realized_pnl') or 0.0):.2f}"
                ),
            )
        )
    for idx, row in enumerate(top_losers[:5], start=1):
        fields.append(
            (
                f"loser_{idx}",
                (
                    f"{_format_stock_display(stock_id=row.get('stock'), stock_name=row.get('stock_name'))} "
                    f"| realized_pnl={float(row.get('realized_pnl') or 0.0):.2f}"
                ),
            )
        )

    return _build_operator_message(
        command_label="/outcome_review",
        status="completed",
        result="closed-trade outcome summary generated",
        fields=fields,
    )


def _build_daily_review_command_message(client: Any) -> str:
    """Build short daily operator review packet (MVP, read-only aggregation)."""
    runner_status_result = "no data"
    latest_run_id = "N/A"
    latest_run_time_hkt = "N/A"
    pnl_snapshot = "internal error"
    outcome_summary = "internal error"
    business_date_hkt = datetime.now(timezone.utc).astimezone(_HKT_TZ).date().isoformat()

    try:
        latest_row = get_latest_run_execution_summary(client)
        if latest_row:
            latest_run_id = latest_row.get("id") or "N/A"
            runner_status_result = str(latest_row.get("status") or "unknown").lower()
            latest_run_time_hkt = _format_display_timestamp_hkt(latest_row.get("created_at"), field_name="created_at")
    except Exception:
        print("Telegram /daily_review runner status helper failed")
        runner_status_result = "internal error"

    try:
        snapshot = _get_paper_position_pnl_review_snapshot(client)
        has_pnl_rows = bool(snapshot.get("per_symbol"))
        has_pnl_totals = any(
            float(snapshot.get(key) or 0.0) != 0.0
            for key in ("total_realized_pnl", "total_unrealized_pnl")
        )
        pnl_snapshot = "available" if has_pnl_rows or has_pnl_totals else "no matching records"
    except Exception:
        print("Telegram /daily_review pnl snapshot helper failed")
        pnl_snapshot = "internal error"

    try:
        summary = _get_paper_trade_outcome_summary(client)
        outcome_summary = "available" if int(summary.get("closed_trade_count") or 0) > 0 else "no closed trades"
    except Exception:
        print("Telegram /daily_review outcome summary helper failed")
        outcome_summary = "internal error"

    section_values = [runner_status_result, pnl_snapshot, outcome_summary]
    has_internal_error = any(value == "internal error" for value in section_values)
    runner_attention_needed = runner_status_result in {"failed", "unknown"}
    has_no_data = any(value in {"no data", "no matching records", "no closed trades"} for value in section_values)
    if has_internal_error:
        daily_review_health = "internal_error"
        next_action_hint = "Check service logs and run detailed commands."
    elif runner_attention_needed:
        daily_review_health = "attention_needed"
        next_action_hint = "Check /runner_status, /runs, and service logs if needed."
    elif has_no_data:
        daily_review_health = "attention_needed"
        next_action_hint = "Check detailed command output and confirm whether no-data is expected."
    else:
        daily_review_health = "ok"
        next_action_hint = "Review detail commands before making any human decision."

    detail_commands = ["/runner_status", "/runs", "/pnl_review", "/outcome_review"]
    if str(latest_run_id) != "N/A":
        detail_commands.append(f"/risk_review {latest_run_id}")

    return _build_operator_message(
        command_label="/daily_review",
        status="completed",
        result="daily operator review packet generated",
        fields=[
            ("business_date_hkt", business_date_hkt),
            ("runner_status", runner_status_result),
            ("latest_run_id", latest_run_id),
            ("latest_run_time_hkt", latest_run_time_hkt),
            ("pnl_snapshot", pnl_snapshot),
            ("outcome_summary", outcome_summary),
            ("daily_review_health", daily_review_health),
            ("next_action_hint", next_action_hint),
            ("detail_commands", ", ".join(detail_commands)),
            ("boundary", "paper-trading decision support only; no real-money execution"),
        ],
    )


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
    is_pnl_review_command = text.lower().startswith("/pnl_review")
    is_outcome_review_command = text.lower().startswith("/outcome_review")
    is_daily_review_command = text.lower().startswith("/daily_review")
    is_decision_note_command = text.lower().startswith("/decision_note")
    if not (
        is_help_command
        or is_runs_command
        or is_runner_status_command
        or is_risk_review_command
        or is_pnl_review_command
        or is_outcome_review_command
        or is_daily_review_command
        or is_decision_note_command
    ):
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
        command_label = text.split()[0].lower() if text else "/unknown"
        return _build_operator_message(
            command_label=command_label,
            status="unauthorized",
            reason="this command is restricted to the configured operator chat/user",
        )

    try:
        if is_help_command:
            return build_help_command_message()

        if is_runs_command:
            try:
                days = _parse_runs_days(text)
            except ValueError as exc:
                return _build_usage_error_message(command_label="/runs", error_text=str(exc))
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
                return _build_operator_message(
                    command_label="/runner_status",
                    status="failed",
                    reason="internal status lookup error",
                )

            if not latest_row:
                return _build_operator_message(
                    command_label="/runner_status",
                    status="no data",
                    reason="no matching records: persisted daily runner summary is not available yet",
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
                return _build_operator_message(
                    command_label="/runner_status",
                    status="failed",
                    reason="latest summary formatting error",
                )

        if is_pnl_review_command:
            try:
                _parse_pnl_review_command(text)
            except ValueError as exc:
                return _build_usage_error_message(command_label="/pnl_review", error_text=str(exc))
            try:
                snapshot = _get_paper_position_pnl_review_snapshot(client)
            except Exception as exc:
                print(
                    "Telegram /pnl_review execution failed: "
                    f"chat_id={chat_id} user_id={user_id} error={exc!r}"
                )
                return _build_operator_message(
                    command_label="/pnl_review",
                    status="failed",
                    reason="internal review snapshot error",
                )
            return _build_pnl_review_command_message(snapshot)

        if is_outcome_review_command:
            try:
                outcome_review_days = _parse_outcome_review_command(text)
            except ValueError as exc:
                return _build_usage_error_message(command_label="/outcome_review", error_text=str(exc))
            try:
                summary = _get_paper_trade_outcome_summary(client, recent_days=outcome_review_days)
            except Exception as exc:
                print(
                    "Telegram /outcome_review execution failed: "
                    f"chat_id={chat_id} user_id={user_id} error={exc!r}"
                )
                return _build_operator_message(
                    command_label="/outcome_review",
                    status="failed",
                    reason="internal outcome summary error",
                )
            return _build_outcome_review_command_message(summary)

        if is_daily_review_command:
            try:
                _parse_daily_review_command(text)
            except ValueError as exc:
                return _build_usage_error_message(command_label="/daily_review", error_text=str(exc))
            return _build_daily_review_command_message(client)

        if is_decision_note_command:
            try:
                parsed = _parse_decision_note_command(text)
            except ValueError as exc:
                return _build_usage_error_message(command_label="/decision_note", error_text=str(exc))
            try:
                user_id_for_journal = auth_decision.get("user_id") or None
                if parsed["scope"] == "stock":
                    record_stock_level_decision_note(
                        client,
                        run_id=parsed["run_id"],
                        stock_id=parsed["stock_id"],
                        source_command=parsed["source_command"],
                        human_action=parsed["human_action"],
                        note=parsed["note"],
                        operator_user_id_hash_or_label=user_id_for_journal,
                    )
                else:
                    record_run_level_decision_note(
                        client,
                        run_id=parsed["run_id"],
                        source_command=parsed["source_command"],
                        human_action=parsed["human_action"],
                        note=parsed["note"],
                        operator_user_id_hash_or_label=user_id_for_journal,
                    )
            except Exception as exc:
                print(f"Telegram /decision_note persistence failed: chat_id={chat_id} user_id={user_id} error={exc!r}")
                return _build_operator_message(command_label="/decision_note", status="failed", reason="internal decision journal persistence error")
            return _build_operator_message(
                command_label="/decision_note",
                status="completed",
                result="human decision journal entry recorded",
                fields=[
                    ("run_id", parsed["run_id"]),
                    ("scope", parsed["scope"]),
                    ("stock_id", parsed["stock_id"] or "N/A"),
                    ("human_action", parsed["human_action"]),
                    ("source_command", parsed["source_command"]),
                    ("journal_boundary", "journaling only; no execution; no real-money trading"),
                ],
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
            return _build_usage_error_message(command_label="/risk_review", error_text=str(exc))

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
            return _build_operator_message(
                command_label="/risk_review",
                status="failed",
                reason="internal review execution error. Please check service logs and retry",
                fields=[("run_id", run_id)],
            )

        if not run_row:
            print(
                "Telegram /risk_review failed: "
                f"run_id={run_id} chat_id={chat_id} user_id={user_id} reason=run_not_found"
            )
            return _build_operator_message(
                command_label="/risk_review",
                status="no data",
                reason="no matching records: run_id not found. Use /runs to list recent runs",
                fields=[("run_id", run_id)],
            )

        try:
            risk_review = _get_paper_risk_review(client, run_id=run_id)
        except Exception as exc:  # defensive operator boundary
            print(
                "Telegram /risk_review internal failure: "
                f"run_id={run_id} chat_id={chat_id} user_id={user_id} error={exc!r}"
            )
            return _build_operator_message(
                command_label="/risk_review",
                status="failed",
                reason="internal review execution error. Please check service logs and retry",
                fields=[("run_id", run_id)],
            )

        print(
            "Telegram /risk_review completed: "
            f"run_id={run_id} chat_id={chat_id} user_id={user_id} "
            "status=completed"
        )
        return _build_risk_review_command_message(
            run_id=run_id,
            risk_review=risk_review,
            run_created_at=run_row.get("created_at"),
        )
    except Exception as exc:
        print(
            "Telegram operator command internal failure: "
            f"text={text!r} chat_id={chat_id} user_id={user_id} error={exc!r}"
        )
        return _build_operator_message(
            command_label=(text.split()[0].lower() if text else "/unknown"),
            status="failed",
            reason="internal command processing error. Please check service logs",
        )
