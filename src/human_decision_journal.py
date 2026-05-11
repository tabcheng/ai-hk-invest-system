from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

ALLOWED_HUMAN_ACTIONS = {"observe", "watchlist", "reject_signal", "accept_for_paper", "defer"}
ALLOWED_SOURCE_COMMANDS = {"/daily_review", "/runner_status", "/runs", "/risk_review", "/pnl_review", "/outcome_review"}
ALLOWED_MINIAPP_DECISION_TYPES = {"watch", "paper_buy", "paper_sell", "paper_hold", "skip"}
ALLOWED_MINIAPP_CONFIDENCE = {"low", "medium", "high", "unknown"}
_SENSITIVE_KEYS = {
    "raw_payload",
    "eodhd_api_token",
    "supabase_service_role_key",
    "telegram_bot_token",
    "init_data",
    "raw_init_data",
}


def _sanitize_snapshot_value(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for k, v in value.items():
            if str(k).strip().lower() in _SENSITIVE_KEYS:
                continue
            safe[k] = _sanitize_snapshot_value(v)
        return safe
    if isinstance(value, list):
        return [_sanitize_snapshot_value(item) for item in value]
    return value


def build_human_decision_context_snapshot(
    *,
    business_date_hkt: str,
    latest_run_id: str,
    ticker: str,
    human_decision_journal_entry_id: str | int,
    human_paper_decision: dict[str, Any],
    decision_context_summary: dict[str, Any] | None,
    ticker_level_paper_portfolio_review: dict[str, Any] | None,
) -> dict[str, Any]:
    tickers = (decision_context_summary or {}).get("tickers") or []
    matched = next((row for row in tickers if str(row.get("ticker") or "").upper() == ticker.upper()), {})
    market_raw = matched.get("market_data") if isinstance(matched, dict) else {}
    signal = matched.get("signal") if isinstance(matched, dict) else {}
    risk = matched.get("risk") if isinstance(matched, dict) else {}
    missing_context = matched.get("missing_context") if isinstance(matched, dict) else []
    portfolio_rows = (ticker_level_paper_portfolio_review or {}).get("rows") or []
    portfolio = next((row for row in portfolio_rows if str(row.get("ticker") or "").upper() == ticker.upper()), {})
    now_utc = datetime.now(timezone.utc)
    now_hkt = now_utc.astimezone(timezone(timedelta(hours=8)))
    market_data_snapshot = {
        "ticker": ticker,
        "reference_price": (market_raw or {}).get("reference_price") or (market_raw or {}).get("price"),
        "previous_close": (market_raw or {}).get("previous_close"),
        "change": (market_raw or {}).get("change"),
        "change_pct": (market_raw or {}).get("change_pct"),
        "volume": (market_raw or {}).get("volume"),
        "turnover": (market_raw or {}).get("turnover"),
        "currency": (market_raw or {}).get("currency"),
        "market": (market_raw or {}).get("market"),
        "data_source": (market_raw or {}).get("data_source") or (market_raw or {}).get("source"),
        "data_timestamp_hkt": (market_raw or {}).get("data_timestamp_hkt") or (market_raw or {}).get("timestamp_hkt"),
        "freshness_status": (market_raw or {}).get("freshness_status") or (market_raw or {}).get("freshness_status_display"),
        "freshness_label": (market_raw or {}).get("freshness_label"),
        "market_data_acceptance_status": (market_raw or {}).get("market_data_acceptance_status", "unknown"),
        "market_data_acceptance_warning": (market_raw or {}).get("market_data_acceptance_warning"),
        "delay_minutes": (market_raw or {}).get("delay_minutes"),
        "limitations": (market_raw or {}).get("limitations") if isinstance((market_raw or {}).get("limitations"), list) else [],
    }
    return {
        "snapshot_schema_version": 1,
        "created_at_utc": now_utc.isoformat(),
        "created_at_hkt": now_hkt.isoformat(),
        "human_decision_journal_entry_id": human_decision_journal_entry_id,
        "business_date_hkt": business_date_hkt,
        "latest_run_id": latest_run_id,
        "ticker": ticker,
        "human_paper_decision": _sanitize_snapshot_value(human_paper_decision),
        "signal_snapshot": _sanitize_snapshot_value(signal if isinstance(signal, dict) else {}),
        "market_data_snapshot": market_data_snapshot,
        "market_data_acceptance_status": market_data_snapshot.get("market_data_acceptance_status", "unknown"),
        "market_data_acceptance_warning": market_data_snapshot.get("market_data_acceptance_warning"),
        "paper_position_snapshot": _sanitize_snapshot_value(portfolio),
        "paper_pnl_snapshot": {
            "realized_pnl": portfolio.get("realized_pnl"),
            "unrealized_pnl": portfolio.get("unrealized_pnl"),
            "total_pnl": portfolio.get("total_pnl"),
        } if isinstance(portfolio, dict) else {},
        "risk_snapshot": _sanitize_snapshot_value(risk if isinstance(risk, dict) else {}),
        "missing_context": missing_context if isinstance(missing_context, list) else [],
        "data_sources": {"decision_context": "review_shell_decision_context", "portfolio": "paper_pnl_read_model"},
        "data_timestamps": {"created_at_hkt": now_hkt.isoformat(), "created_at_utc": now_utc.isoformat(), "market_data_timestamp_hkt": market_data_snapshot.get("data_timestamp_hkt")},
        "paper_trade_only": True,
        "decision_support_only": True,
        "no_broker_execution": True,
        "no_real_money_execution": True,
    }


def persist_decision_context_snapshot(client: Any, *, snapshot: dict[str, Any]) -> dict[str, Any]:
    market = snapshot.get("market_data_snapshot") or {}
    payload = {
        "human_decision_journal_entry_id": snapshot.get("human_decision_journal_entry_id"),
        "ticker": snapshot.get("ticker"),
        "latest_run_id": snapshot.get("latest_run_id"),
        "business_date_hkt": snapshot.get("business_date_hkt"),
        "decision_type": (snapshot.get("human_paper_decision") or {}).get("decision_type"),
        "confidence_label": (snapshot.get("human_paper_decision") or {}).get("confidence_label"),
        "snapshot_schema_version": snapshot.get("snapshot_schema_version"),
        "created_at_hkt": snapshot.get("created_at_hkt"),
        "delay_minutes": market.get("delay_minutes"),
        "snapshot_json": snapshot,
        "reference_price": market.get("reference_price") or market.get("price"),
        "previous_close": market.get("previous_close"),
        "change": market.get("change"),
        "change_pct": market.get("change_pct"),
        "volume": market.get("volume"),
        "turnover": market.get("turnover"),
        "currency": market.get("currency"),
        "market": market.get("market"),
        "data_source": market.get("data_source") or market.get("source"),
        "data_timestamp_hkt": market.get("data_timestamp_hkt") or market.get("timestamp_hkt"),
        "freshness_status": market.get("freshness_status") or market.get("freshness_status_display"),
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
