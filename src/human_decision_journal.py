from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

ALLOWED_HUMAN_ACTIONS = {"observe", "watchlist", "reject_signal", "accept_for_paper", "defer"}
ALLOWED_SOURCE_COMMANDS = {"/daily_review", "/runner_status", "/runs", "/risk_review", "/pnl_review", "/outcome_review"}
ALLOWED_MINIAPP_DECISION_TYPES = {"watch", "paper_buy", "paper_sell", "paper_hold", "skip"}
ALLOWED_MINIAPP_CONFIDENCE = {"low", "medium", "high", "unknown"}


def build_human_decision_context_snapshot(
    *,
    business_date_hkt: str,
    latest_run_id: str,
    ticker: str,
    human_paper_decision: dict[str, Any],
    decision_context_summary: dict[str, Any] | None,
    ticker_level_paper_portfolio_review: dict[str, Any] | None,
) -> dict[str, Any]:
    tickers = (decision_context_summary or {}).get("tickers") or []
    matched = next((row for row in tickers if str(row.get("ticker") or "").upper() == ticker.upper()), {})
    market = matched.get("market_data") if isinstance(matched, dict) else {}
    signal = matched.get("signal") if isinstance(matched, dict) else {}
    risk = matched.get("risk") if isinstance(matched, dict) else {}
    missing_context = matched.get("missing_context") if isinstance(matched, dict) else []
    portfolio_rows = (ticker_level_paper_portfolio_review or {}).get("rows") or []
    portfolio = next((row for row in portfolio_rows if str(row.get("ticker") or "").upper() == ticker.upper()), {})
    created_at_hkt = datetime.now(timezone.utc).astimezone(timezone.utc).isoformat()
    return {
        "snapshot_schema_version": 1,
        "created_at_hkt": created_at_hkt,
        "business_date_hkt": business_date_hkt,
        "latest_run_id": latest_run_id,
        "ticker": ticker,
        "human_paper_decision": human_paper_decision,
        "signal_snapshot": signal if isinstance(signal, dict) else {},
        "market_data_snapshot": market if isinstance(market, dict) else {},
        "market_data_acceptance_status": (market or {}).get("market_data_acceptance_status", "unknown"),
        "market_data_acceptance_warning": (market or {}).get("market_data_acceptance_warning"),
        "paper_position_snapshot": portfolio,
        "paper_pnl_snapshot": {
            "realized_pnl": portfolio.get("realized_pnl"),
            "unrealized_pnl": portfolio.get("unrealized_pnl"),
            "total_pnl": portfolio.get("total_pnl"),
        } if isinstance(portfolio, dict) else {},
        "risk_snapshot": risk if isinstance(risk, dict) else {},
        "missing_context": missing_context if isinstance(missing_context, list) else [],
        "data_sources": {"decision_context": "review_shell_decision_context", "portfolio": "paper_pnl_read_model"},
        "data_timestamps": {"created_at_hkt": created_at_hkt, "market_data_timestamp_hkt": (market or {}).get("timestamp_hkt")},
        "paper_trade_only": True,
        "decision_support_only": True,
        "no_broker_execution": True,
        "no_real_money_execution": True,
    }


def persist_decision_context_snapshot(client: Any, *, snapshot: dict[str, Any]) -> dict[str, Any]:
    market = snapshot.get("market_data_snapshot") or {}
    payload = {
        "ticker": snapshot.get("ticker"),
        "latest_run_id": snapshot.get("latest_run_id"),
        "business_date_hkt": snapshot.get("business_date_hkt"),
        "snapshot_json": snapshot,
        "reference_price": market.get("price"),
        "previous_close": market.get("previous_close"),
        "change": market.get("change"),
        "change_pct": market.get("change_pct"),
        "volume": market.get("volume"),
        "turnover": market.get("turnover"),
        "currency": market.get("currency"),
        "market": market.get("market"),
        "data_source": market.get("source"),
        "data_timestamp_hkt": market.get("timestamp_hkt"),
        "freshness_status": market.get("freshness_status"),
        "freshness_label": market.get("freshness_label"),
        "market_data_acceptance_status": snapshot.get("market_data_acceptance_status", "unknown"),
        "market_data_acceptance_warning": snapshot.get("market_data_acceptance_warning"),
        "limitations": market.get("limitations") if isinstance(market.get("limitations"), list) else [],
        "paper_trade_only": True,
        "decision_support_only": True,
        "no_broker_execution": True,
        "no_real_money_execution": True,
    }
    result = client.table("decision_context_snapshots").insert(payload).execute()
    row = (result.data or [{}])[0]
    return {"id": row.get("id"), "status": "saved"}


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
