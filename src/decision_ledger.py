from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from supabase import Client

from src.risk_manager import build_risk_evaluation_payload

# Keep validation enums intentionally small and explicit so records are easy to
# query consistently in analytics/review workflows.
_ALLOWED_SIGNAL_ACTIONS = {"BUY", "SELL", "HOLD", "NO_DATA", "INSUFFICIENT_DATA", "ERROR"}
_ALLOWED_HUMAN_DECISIONS = {"PENDING", "APPROVE", "REJECT", "DEFER"}
_ALLOWED_PAPER_TRADE_STATUSES = {"PENDING", "SIMULATED", "SKIPPED", "CANCELLED"}


@dataclass(frozen=True)
class DecisionRecord:
    run_id: int | None
    stock_id: str
    stock_name: str
    signal_action: str
    signal_score: float | None
    rationale_summary: str | None
    human_decision: str
    decision_note: str
    paper_trade_status: str
    risk_evaluation: dict | None = None


def build_decision_record_payload(record: DecisionRecord) -> dict:
    """Build a validated decision-ledger payload for persistence."""
    if not isinstance(record.stock_id, str) or not record.stock_id.strip():
        raise ValueError("stock_id is required")
    if not isinstance(record.stock_name, str) or not record.stock_name.strip():
        raise ValueError("stock_name is required")
    if record.signal_action not in _ALLOWED_SIGNAL_ACTIONS:
        raise ValueError(f"signal_action must be one of {sorted(_ALLOWED_SIGNAL_ACTIONS)}")
    if record.human_decision not in _ALLOWED_HUMAN_DECISIONS:
        raise ValueError(f"human_decision must be one of {sorted(_ALLOWED_HUMAN_DECISIONS)}")
    if not isinstance(record.decision_note, str) or not record.decision_note.strip():
        raise ValueError("decision_note is required")
    if record.paper_trade_status not in _ALLOWED_PAPER_TRADE_STATUSES:
        raise ValueError(
            f"paper_trade_status must be one of {sorted(_ALLOWED_PAPER_TRADE_STATUSES)}"
        )
    if record.signal_score is not None:
        if not isinstance(record.signal_score, (float, int)) or not isfinite(float(record.signal_score)):
            raise ValueError("signal_score must be a finite number when provided")

    payload = {
        "run_id": record.run_id,
        "stock_id": record.stock_id,
        "stock_name": record.stock_name,
        "signal_action": record.signal_action,
        "signal_score": record.signal_score,
        "rationale_summary": record.rationale_summary,
        "human_decision": record.human_decision,
        "decision_note": record.decision_note,
        "paper_trade_status": record.paper_trade_status,
    }

    risk_payload = build_risk_evaluation_payload(record.risk_evaluation)
    if risk_payload is not None:
        payload["risk_evaluation"] = risk_payload

    return payload


def save_paper_trade_decision_record(client: Client, record: DecisionRecord) -> None:
    payload = build_decision_record_payload(record)
    client.table("paper_trade_decisions").insert(payload).execute()


def create_decision_record_from_signal(
    *,
    run_id: int | None,
    stock_id: str,
    stock_name: str,
    signal_data: dict,
) -> DecisionRecord:
    """
    Map signal output into a review-first decision record.

    Guardrail: this is an audit ledger entry, not an execution command. The
    initial human_decision always starts as PENDING for explicit human review.
    """
    return DecisionRecord(
        run_id=run_id,
        stock_id=stock_id,
        stock_name=stock_name,
        signal_action=signal_data["signal"],
        signal_score=None,
        rationale_summary=signal_data.get("reason"),
        human_decision="PENDING",
        decision_note="Initial AI signal recorded; awaiting human review.",
        paper_trade_status="PENDING",
        risk_evaluation=signal_data.get("risk_evaluation"),
    )
