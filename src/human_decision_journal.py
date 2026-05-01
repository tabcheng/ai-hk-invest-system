from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ALLOWED_HUMAN_ACTIONS = {"observe", "watchlist", "reject_signal", "accept_for_paper", "defer"}
ALLOWED_SOURCE_COMMANDS = {"/daily_review", "/runner_status", "/runs", "/risk_review", "/pnl_review", "/outcome_review"}


def record_run_level_decision_note(
    client: Any,
    *,
    run_id: int,
    source_command: str,
    human_action: str,
    note: str,
    operator_user_id_hash_or_label: str | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one run-level Human Decision Journal entry (Step 62 MVP)."""
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "run",
        "run_id": run_id,
        "human_action": human_action,
        "note": note,
        "source_command": source_command,
        "operator_user_id_hash_or_label": operator_user_id_hash_or_label or None,
        "metadata": metadata or None,
    }
    result = client.table("human_decision_journal_entries").insert(payload).execute()
    data = (result.data or [{}])[0]
    return {**payload, "id": data.get("id")}


def record_stock_level_decision_note(
    client: Any,
    *,
    run_id: int,
    stock_id: str,
    source_command: str,
    human_action: str,
    note: str,
    operator_user_id_hash_or_label: str | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one stock-level Human Decision Journal entry (Step 68 MVP)."""
    merged_metadata = dict(metadata or {})
    merged_metadata["stock_id"] = stock_id
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "stock",
        "run_id": run_id,
        "human_action": human_action,
        "note": note,
        "source_command": source_command,
        "operator_user_id_hash_or_label": operator_user_id_hash_or_label or None,
        "metadata": merged_metadata,
    }
    result = client.table("human_decision_journal_entries").insert(payload).execute()
    data = (result.data or [{}])[0]
    return {**payload, "id": data.get("id")}
