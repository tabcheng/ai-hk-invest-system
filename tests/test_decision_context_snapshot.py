from src.human_decision_journal import build_human_decision_context_snapshot, persist_decision_context_snapshot


def test_snapshot_builder_includes_required_fields():
    snapshot = build_human_decision_context_snapshot(
        business_date_hkt="2026-05-11",
        latest_run_id="run-1",
        ticker="0700.HK",
        human_decision_journal_entry_id=123,
        human_paper_decision={"decision_type": "watch", "init_data": "raw"},
        decision_context_summary={
            "tickers": [
                {
                    "ticker": "0700.HK",
                    "signal": {"direction": "neutral", "SUPABASE_SERVICE_ROLE_KEY": "x"},
                    "market": {
                        "reference_price": 420.5,
                        "previous_close": 418.0,
                        "change": 2.5,
                        "change_pct": 0.6,
                        "volume": 123456,
                        "data_source": "eodhd",
                        "data_timestamp_hkt": "2026-05-11 16:08 HKT",
                        "freshness_status": "last_available_close",
                        "market_data_acceptance_status": "caution_last_available_close",
                        "market_data_acceptance_warning": "last available close / paper review caution",
                        "raw_payload": {"x": 1},
                        "EODHD_API_TOKEN": "s",
                    },
                    "risk": {"risk_level": "medium", "TELEGRAM_BOT_TOKEN": "x"},
                    "missing_context": ["valuation"],
                }
            ]
        },
        ticker_level_paper_portfolio_review={"rows": [{"ticker": "0700.HK", "realized_pnl": 1}]},
    )
    assert snapshot["ticker"] == "0700.HK"
    assert snapshot["signal_snapshot"]["direction"] == "neutral"
    assert snapshot["market_data_acceptance_status"] == "caution_last_available_close"
    assert snapshot["human_decision_journal_entry_id"] == 123
    assert snapshot["market_data_snapshot"]["reference_price"] == 420.5
    assert "raw_payload" not in snapshot["market_data_snapshot"]
    assert "EODHD_API_TOKEN" not in snapshot["market_data_snapshot"]
    assert "SUPABASE_SERVICE_ROLE_KEY" not in snapshot["signal_snapshot"]
    assert "TELEGRAM_BOT_TOKEN" not in snapshot["risk_snapshot"]
    assert "init_data" not in snapshot["human_paper_decision"]
    assert snapshot["paper_position_snapshot"]["ticker"] == "0700.HK"
    assert snapshot["risk_snapshot"]["risk_level"] == "medium"
    assert snapshot["paper_trade_only"] is True


def test_persist_snapshot_uses_alias_safe_mapping_and_linkage():
    captured = {}
    class _T:
        def insert(self, payload):
            captured.update(payload)
            return self
        def execute(self):
            return type("R", (), {"data": [{"id": "s1"}]})()
    class _C:
        def table(self, name):
            assert name == "decision_context_snapshots"
            return _T()
    persist_decision_context_snapshot(_C(), snapshot={
        "human_decision_journal_entry_id": 88,
        "ticker": "0700.HK",
        "latest_run_id": "run-1",
        "business_date_hkt": "2026-05-11",
        "snapshot_schema_version": 1,
        "created_at_hkt": "2026-05-11T20:00:00+08:00",
        "human_paper_decision": {"decision_type": "watch", "confidence_label": "medium"},
        "market_data_acceptance_status": "caution_last_available_close",
        "market_data_snapshot": {"reference_price": 500.0, "data_source": "eodhd", "data_timestamp_hkt": "2026-05-11 16:00:00 HKT", "freshness_status": "last_available_close"},
    })
    assert captured["human_decision_journal_entry_id"] == 88
    assert captured["reference_price"] == 500.0
    assert captured["data_source"] == "eodhd"
    assert captured["market_data_acceptance_status"] == "caution_last_available_close"
