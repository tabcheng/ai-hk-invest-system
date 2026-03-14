"""Operator-facing read path for persisted paper-risk review output."""

from __future__ import annotations

import argparse
import json
from typing import Any

from src.config import get_supabase_client
from src.paper_trading import get_paper_risk_review_for_run


def _build_deterministic_operator_review(review: dict[str, Any]) -> dict[str, Any]:
    """Normalize risk review output for compact deterministic operator consumption."""
    per_ticker_rows = review.get("per_ticker")
    normalized_per_ticker: list[dict[str, Any]] = []

    if isinstance(per_ticker_rows, dict):
        for ticker in sorted(per_ticker_rows.keys()):
            rows = per_ticker_rows.get(ticker)
            if not isinstance(rows, list):
                continue
            normalized_rows: list[dict[str, str]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                normalized_rows.append(
                    {
                        "event_type": str(row.get("event_type") or ""),
                        "severity": str(row.get("severity") or "info"),
                        "summary_message": str(row.get("summary_message") or ""),
                        "compact_rule_summary": str(row.get("compact_rule_summary") or "rules=none"),
                    }
                )
            normalized_per_ticker.append({"ticker": ticker, "review_rows": normalized_rows})

    return {
        "run_id": int(review.get("run_id") or 0),
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
    operator_review = _build_deterministic_operator_review(review)
    print(json.dumps(operator_review, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
