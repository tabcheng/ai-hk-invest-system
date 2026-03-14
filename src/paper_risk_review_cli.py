"""Operator-facing read path for persisted paper-risk review output."""

from __future__ import annotations

import argparse
import json
from typing import Any

from src.config import get_supabase_client
from src.paper_trading import get_paper_risk_review_for_run


REVIEW_ROW_SORT_KEY = (
    "event_type",
    "severity",
    "summary_message",
    "compact_rule_summary",
)


def _normalize_review_row(row: dict[str, Any]) -> dict[str, str]:
    """Project one review row into a stable, compact operator schema."""
    return {
        "event_type": str(row.get("event_type") or ""),
        "severity": str(row.get("severity") or "info"),
        "summary_message": str(row.get("summary_message") or ""),
        "compact_rule_summary": str(row.get("compact_rule_summary") or "rules=none"),
    }


def _build_deterministic_operator_review(review: dict[str, Any], run_id: int) -> dict[str, Any]:
    """Normalize risk review output for compact deterministic operator consumption."""
    per_ticker_rows = review.get("per_ticker")
    normalized_per_ticker: dict[str, list[dict[str, str]]] = {}

    if isinstance(per_ticker_rows, dict):
        # Sort ticker keys and review rows explicitly so output remains stable even if
        # upstream query/order behavior evolves in future read surfaces.
        for ticker in sorted(per_ticker_rows.keys()):
            rows = per_ticker_rows.get(ticker)
            if not isinstance(rows, list):
                continue
            normalized_rows = [_normalize_review_row(row) for row in rows if isinstance(row, dict)]
            normalized_rows.sort(key=lambda row: tuple(row.get(field, "") for field in REVIEW_ROW_SORT_KEY))
            normalized_per_ticker[str(ticker)] = normalized_rows

    return {
        "run_id": run_id,
        "total_blocked_buys": int(review.get("total_blocked_buys") or 0),
        "total_warning_buys": int(review.get("total_warning_buys") or 0),
        "total_executed_buys": int(review.get("total_executed_buys") or 0),
        "per_ticker": normalized_per_ticker,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="paper-risk-review",
        description="Read one run's persisted paper-trading risk review.",
    )
    parser.add_argument("--run-id", type=int, required=True, help="Run identifier to review")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    client = get_supabase_client()
    review = get_paper_risk_review_for_run(client, run_id=args.run_id)
    operator_review = _build_deterministic_operator_review(review, run_id=args.run_id)
    print(json.dumps(operator_review, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
