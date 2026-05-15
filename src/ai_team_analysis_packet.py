from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

RUN_TYPE_TO_SCHEDULE = {
    "post_close_daily_review": "HKT around 20:00 daily (Railway cron UTC: 0 12 * * *)",
    "midday_market_monitor": "HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)",
    "stale_risk_refresh": "HKT around 15:30 weekday (Railway cron UTC: 30 7 * * 1-5)",
}

SAFE_DIRECTIONS = {"watch_only", "insufficient_data", "mixed_watch"}


def _status_and_confidence(has_market: bool, has_signal: bool, has_risk: bool) -> tuple[str, str]:
    score = sum([has_market, has_signal, has_risk])
    if score == 3:
        return "ready", "medium"
    if score == 2:
        return "partial", "low"
    if score == 1:
        return "blocked", "low"
    return "not_available", "very_low"


def _build_slot(name: str, status: str, confidence: str, gaps: List[str], inputs_used: List[str]) -> Dict[str, Any]:
    return {
        "status": status,
        "headline": f"{name} deterministic review packet",
        "inputs_used": inputs_used,
        "gaps": gaps,
        "confidence": confidence,
        "limitations": ["paper-only deterministic context", "no llm summary", "no external vendor call in this builder"],
    }


def _derive_simulated_direction(status: str, market_context: Dict[str, Any], risk_context: Dict[str, Any]) -> str:
    if status in {"blocked", "not_available"}:
        return "insufficient_data"

    has_market_baseline = market_context.get("price") is not None or bool(market_context.get("signal_direction"))
    if not has_market_baseline:
        return "insufficient_data"

    risk_flags = risk_context.get("risk_flags") or []
    signal_direction = str(market_context.get("signal_direction", "")).lower()

    if risk_flags and signal_direction in {"down", "mixed", "not_available", ""}:
        return "mixed_watch"
    return "watch_only"


def build_ai_team_analysis_packet(
    ticker: str,
    as_of: str,
    run_context: Dict[str, Any],
    market_context: Dict[str, Any] | None = None,
    paper_signal_context: Dict[str, Any] | None = None,
    risk_context: Dict[str, Any] | None = None,
    journal_context: Dict[str, Any] | None = None,
    outcome_context: Dict[str, Any] | None = None,
    ruleset_version: str = "deterministic.v1",
    source_refs: List[str] | None = None,
) -> Dict[str, Any]:
    market_context = market_context or {}
    paper_signal_context = paper_signal_context or {}
    risk_context = risk_context or {}

    has_market = bool(market_context.get("price") is not None or market_context.get("signal_direction"))
    has_signal = bool(paper_signal_context.get("latest_signal"))
    has_risk = bool(risk_context)

    run_type = run_context.get("run_type", "unknown")
    run_schedule = run_context.get("schedule_basis") or RUN_TYPE_TO_SCHEDULE.get(run_type, "not_available")
    run_manual = bool(run_context.get("manual_evidence_only", run_type in {"midday_market_monitor", "stale_risk_refresh"}))

    status, confidence = _status_and_confidence(has_market, has_signal, has_risk)
    decision = _derive_simulated_direction(status, market_context, risk_context)
    if decision not in SAFE_DIRECTIONS:
        decision = "insufficient_data"

    gaps: List[str] = []
    if not has_market:
        gaps.append("market_context_missing")
    if not has_signal:
        gaps.append("paper_signal_missing")
    if not has_risk:
        gaps.append("risk_context_missing")

    journal_payload = journal_context or {"status": "not_available", "reason": "journal repository accessor not provided"}
    outcome_payload = outcome_context or {"status": "not_available", "reason": "outcome repository accessor not provided"}

    packet = {
        "schema_version": "ai_team_analysis_packet.v1",
        "ticker": ticker,
        "as_of": as_of,
        "run_context": {
            "run_id": run_context.get("run_id", "not_available"),
            "run_type": run_type,
            "schedule_basis": run_schedule,
            "data_timestamp": run_context.get("data_timestamp", "not_available"),
            "source": run_context.get("source", "paper_daily_runner"),
            "manual_evidence_only": run_manual,
        },
        "market_context": {
            "signal_direction": market_context.get("signal_direction", "not_available"),
            "price": market_context.get("price", "not_available"),
            "data_timestamp": market_context.get("data_timestamp", "not_available"),
            "freshness": market_context.get("freshness", "unknown"),
            "limitations": market_context.get("limitations", ["market context incomplete"]) if market_context else ["market context not provided"],
        },
        "paper_signal_context": {
            "latest_signal": paper_signal_context.get("latest_signal", "not_available"),
            "reason": paper_signal_context.get("reason", "not_available"),
            "duplicate_protection_state": paper_signal_context.get("duplicate_protection_state", "unknown"),
            "label": "ai_simulated_or_paper_signal_only",
        },
        "risk_context": {
            "risk_flags": risk_context.get("risk_flags", ["unknown"]),
            "liquidity_flag": risk_context.get("liquidity_flag", "not_available"),
            "freshness_flag": risk_context.get("freshness_flag", "not_available"),
            "data_gap_flag": risk_context.get("data_gap_flag", "not_available"),
        },
        "journal_context": journal_payload,
        "outcome_context": outcome_payload,
    }

    packet["ai_team_slots"] = {
        "market_data_analyst": _build_slot("market_data_analyst", status, confidence, gaps, ["run_context", "market_context"]),
        "risk_manager": _build_slot("risk_manager", status, confidence, gaps, ["run_context", "risk_context"]),
        "strategy_researcher": _build_slot("strategy_researcher", status, confidence, gaps, ["run_context", "paper_signal_context", "market_context"]),
        "paper_portfolio_manager": _build_slot("paper_portfolio_manager", "partial" if journal_payload.get("status") == "not_available" else status, confidence, gaps, ["run_context", "journal_context", "outcome_context"]),
        "decision_advisor": _build_slot("decision_advisor", status, confidence, gaps, ["run_context", "market_context", "paper_signal_context", "risk_context"]),
        "model_auditor": _build_slot("model_auditor", "ready", "medium", [], ["audit", "guardrails", "run_context"]),
    }

    packet["decision_support"] = {
        "simulated_direction": decision,
        "human_action_required": True,
        "operator_next_steps": [
            "review risk context",
            "open paper journal",
            "wait for updated data",
            "compare with latest outcome",
        ],
    }
    packet["guardrails"] = {
        "paper_only": True,
        "decision_support_only": True,
        "broker_connection": False,
        "creates_orders": False,
        "live_execution": False,
        "real_money_execution": False,
        "llm_generated": False,
        "vendor_call_performed": False,
    }
    packet["audit"] = {
        "ruleset_version": ruleset_version,
        "packet_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_refs": source_refs or ["daily_runner", "signals", "risk"],
        "limitations": ["deterministic-only synthesis", "missing upstream contexts remain explicit"],
    }
    return packet
