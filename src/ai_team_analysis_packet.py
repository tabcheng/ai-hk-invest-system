from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from src.railway_cadence_runtime import get_runtime_schedule_basis

SAFE_DIRECTIONS = {"watch_only", "insufficient_data", "mixed_watch"}

_MISSING_SENTINELS = {"", "unknown", "not_available", "n/a", "na", "missing", "null"}
_SUMMARY_MISSING_SENTINELS = _MISSING_SENTINELS | {"none"}


def _is_available_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _MISSING_SENTINELS
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _has_valid_risk_flags(risk_flags: Any) -> bool:
    if not isinstance(risk_flags, list) or not risk_flags:
        return False
    return any(_is_available_value(flag) for flag in risk_flags)


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

    has_market_baseline = _is_available_value(market_context.get("price")) or _is_available_value(market_context.get("signal_direction"))
    if not has_market_baseline:
        return "insufficient_data"

    risk_flags = risk_context.get("risk_flags") or []
    signal_direction = str(market_context.get("signal_direction", "")).lower()

    if _has_valid_risk_flags(risk_flags) and signal_direction in {"down", "mixed", "not_available", ""}:
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

    has_market = _is_available_value(market_context.get("price")) or _is_available_value(market_context.get("signal_direction"))
    has_signal = _is_available_value(paper_signal_context.get("latest_signal"))
    has_risk = (
        _has_valid_risk_flags(risk_context.get("risk_flags"))
        or _is_available_value(risk_context.get("liquidity_flag"))
        or _is_available_value(risk_context.get("freshness_flag"))
        or _is_available_value(risk_context.get("data_gap_flag"))
    )

    run_type = run_context.get("run_type", "unknown")
    run_schedule = run_context.get("schedule_basis") or get_runtime_schedule_basis(run_type)
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


def build_ai_team_packet_summary(packet: Dict[str, Any]) -> Dict[str, Any]:
    guardrails = packet.get("guardrails") if isinstance(packet.get("guardrails"), dict) else {}
    run_context = packet.get("run_context") if isinstance(packet.get("run_context"), dict) else {}
    slots = packet.get("ai_team_slots") if isinstance(packet.get("ai_team_slots"), dict) else {}
    decision_support = (
        packet.get("decision_support") if isinstance(packet.get("decision_support"), dict) else {}
    )

    slot_status_counts = {"ok": 0, "partial": 0, "missing": 0, "unknown": 0}
    for slot in slots.values():
        status = str((slot or {}).get("status") or "").strip().lower()
        if status in {"ready", "ok"}:
            slot_status_counts["ok"] += 1
        elif status == "partial":
            slot_status_counts["partial"] += 1
        elif status in {"not_available", "blocked"}:
            slot_status_counts["missing"] += 1
        else:
            slot_status_counts["unknown"] += 1

    direction = str(decision_support.get("simulated_direction") or "insufficient_data").strip().lower()
    if direction not in SAFE_DIRECTIONS:
        direction = "insufficient_data"
    simulated_direction_counts = {"insufficient_data": 0, "watch_only": 0, "mixed_watch": 0}
    simulated_direction_counts[direction] += 1

    top_gaps = []
    for slot in slots.values():
        for gap in list((slot or {}).get("gaps") or []):
            gap_text = str(gap or "").strip().lower()
            if not gap_text or gap_text in _SUMMARY_MISSING_SENTINELS:
                continue
            if gap_text in top_gaps:
                continue
            top_gaps.append(gap_text[:80])
            if len(top_gaps) >= 5:
                break
        if len(top_gaps) >= 5:
            break

    limitations = []
    for source in [packet.get("audit"), *slots.values()]:
        source_limitations = (source or {}).get("limitations")
        for item in list(source_limitations or []):
            text = str(item or "").strip()
            if not text:
                continue
            if text in limitations:
                continue
            limitations.append(text[:120])
            if len(limitations) >= 5:
                break
        if len(limitations) >= 5:
            break

    missing_context_count = sum(
        1
        for key in ("run_id", "run_type", "schedule_basis")
        if str(run_context.get(key, "")).strip().lower() in _SUMMARY_MISSING_SENTINELS
    )
    if missing_context_count >= 2:
        status = "insufficient_data"
    elif slot_status_counts["ok"] > 0:
        status = "ok" if slot_status_counts["partial"] == 0 and slot_status_counts["missing"] == 0 else "partial"
    else:
        status = "unavailable"

    return {
        "schema_version": "ai_team_analysis_packet_summary.v1",
        "packet_schema_version": str(packet.get("schema_version") or "ai_team_analysis_packet.v1")[:64],
        "status": status,
        "paper_trade_only": bool(guardrails.get("paper_only", True)),
        "decision_support_only": bool(guardrails.get("decision_support_only", True)),
        "llm_generated": bool(guardrails.get("llm_generated", False)),
        "vendor_call_performed": bool(guardrails.get("vendor_call_performed", False)),
        "broker_connection": bool(guardrails.get("broker_connection", False)),
        "live_execution": bool(guardrails.get("live_execution", False)),
        "real_money_execution": bool(guardrails.get("real_money_execution", False)),
        "creates_orders": bool(guardrails.get("creates_orders", False)),
        "run_id": str(run_context.get("run_id") or "not_available")[:80],
        "business_date": str(packet.get("as_of") or "not_available")[:40],
        "run_type": str(run_context.get("run_type") or "unknown")[:80],
        "schedule_basis": str(run_context.get("schedule_basis") or "unknown")[:80],
        "covered_tickers": 1,
        "slot_status_counts": slot_status_counts,
        "simulated_direction_counts": simulated_direction_counts,
        "top_gaps": top_gaps,
        "limitations": limitations,
        "source": "deterministic_backend_packet",
    }


def build_latest_system_run_ai_team_packet_section(
    *,
    run_id: str | int | None,
    business_date: str,
    run_type: str,
    schedule_basis: str,
    processed_tickers: int,
    successful_tickers: int,
    failed_tickers: int,
) -> Dict[str, Any]:
    processed = max(0, int(processed_tickers))
    success = max(0, int(successful_tickers))
    failed = max(0, int(failed_tickers))
    unknown = max(0, processed - success - failed)
    if processed <= 0:
        status = "insufficient_data"
    elif success == processed:
        status = "ok"
    elif success > 0:
        status = "partial"
    else:
        status = "unavailable"

    return {
        "schema_version": "ai_team_analysis_packet_summary.v1",
        "packet_schema_version": "ai_team_analysis_packet.v1",
        "status": status,
        "paper_trade_only": True,
        "decision_support_only": True,
        "llm_generated": False,
        "vendor_call_performed": False,
        "broker_connection": False,
        "live_execution": False,
        "real_money_execution": False,
        "creates_orders": False,
        "run_id": str(run_id or "not_available")[:80],
        "business_date": str(business_date or "not_available")[:40],
        "run_type": str(run_type or "unknown")[:80],
        "schedule_basis": str(schedule_basis or "unknown")[:80],
        "covered_tickers": processed,
        "slot_status_counts": {
            "ok": success,
            "partial": 1 if success > 0 and failed > 0 else 0,
            "missing": failed,
            "unknown": unknown,
        },
        "simulated_direction_counts": {
            "insufficient_data": failed if failed > 0 else 0,
            "watch_only": success if success > 0 else 0,
            "mixed_watch": 1 if success > 0 and failed > 0 else 0,
        },
        "top_gaps": (["paper_signal_missing", "risk_context_missing"] if failed > 0 else []),
        "limitations": [
            "deterministic runner projection only",
            "paper-only decision support summary",
            "no llm summary or external vendor call",
        ],
        "source": "deterministic_backend_packet",
    }
