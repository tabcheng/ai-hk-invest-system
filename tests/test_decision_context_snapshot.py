from src.human_decision_journal import build_human_decision_context_snapshot


def test_snapshot_builder_includes_required_fields():
    snapshot = build_human_decision_context_snapshot(
        business_date_hkt="2026-05-11",
        latest_run_id="run-1",
        ticker="0700.HK",
        human_paper_decision={"decision_type": "watch"},
        decision_context_summary={
            "tickers": [
                {
                    "ticker": "0700.HK",
                    "signal": {"direction": "neutral"},
                    "market_data": {"market_data_acceptance_status": "caution_last_available_close"},
                    "risk": {"risk_level": "medium"},
                    "missing_context": ["valuation"],
                }
            ]
        },
        ticker_level_paper_portfolio_review={"rows": [{"ticker": "0700.HK", "realized_pnl": 1}]},
    )
    assert snapshot["ticker"] == "0700.HK"
    assert snapshot["signal_snapshot"]["direction"] == "neutral"
    assert snapshot["market_data_acceptance_status"] == "caution_last_available_close"
    assert snapshot["paper_position_snapshot"]["ticker"] == "0700.HK"
    assert snapshot["risk_snapshot"]["risk_level"] == "medium"
    assert snapshot["paper_trade_only"] is True
