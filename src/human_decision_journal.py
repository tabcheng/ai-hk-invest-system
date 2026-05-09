from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ALLOWED_HUMAN_ACTIONS = {"observe", "watchlist", "reject_signal", "accept_for_paper", "defer"}
ALLOWED_SOURCE_COMMANDS = {"/daily_review", "/runner_status", "/runs", "/risk_review", "/pnl_review", "/outcome_review"}
ALLOWED_MINIAPP_DECISION_TYPES = {"watch", "paper_buy", "paper_sell", "paper_hold", "skip"}
ALLOWED_MINIAPP_CONFIDENCE = {"low", "medium", "high", "unknown"}


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


def record_miniapp_human_paper_decision_journal(
    client: Any,
    *,
    business_date: str,
    run_id: str,
    ticker: str,
    decision_type: str,
    rationale_text: str,
    operator_user_id_hash_or_label: str,
    confidence_label: str | None = None,
    quantity_intent: int | None = None,
    notional_intent: float | None = None,
    ui_build_version: str | None = None,
    data_timestamp_hkt: str | None = None,
) -> dict[str, Any]:
    """Persist one Mini App bounded human paper decision journal row."""
    metadata = {
        "business_date": business_date,
        "ticker": ticker,
        "decision_type": decision_type,
        "decision_scope": "human_paper_decision",
        "paper_trade_only": True,
        "real_trade_decision": False,
        "broker_execution": False,
        "quantity_intent": quantity_intent,
        "notional_intent": notional_intent,
        "rationale_text": rationale_text,
        "confidence_label": confidence_label or "unknown",
        "source": "miniapp_human_journal",
        "ui_build_version": ui_build_version,
        "data_timestamp_hkt": data_timestamp_hkt,
        "guardrail_ack": True,
        "no_order_created": True,
    }
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scope": "stock",
        "run_id": run_id,
        "human_action": "accept_for_paper",
        "note": "miniapp_human_paper_decision_journal",
        "source_command": "/miniapp_human_paper_decision",
        "operator_user_id_hash_or_label": operator_user_id_hash_or_label,
        "metadata": metadata,
    }
    result = client.table("human_decision_journal_entries").insert(payload).execute()
    data = (result.data or [{}])[0]
    return {"id": data.get("id"), "run_id": run_id}
