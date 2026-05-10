from src.market_data.smoke import build_market_smoke_summary


def test_smoke_summary_null_provider_unavailable():
    out = build_market_smoke_summary("0700.HK", {"MARKET_DATA_PROVIDER": "null"})
    assert out["status"] == "unavailable"


def test_smoke_summary_fake_eodhd_ok_and_bounded_fields(monkeypatch):
    from src.market_data.review_provider import MarketTickerSnapshot

    class _FakeProvider:
        def get_ticker_market_snapshot(self, ticker: str, business_date=None):
            return MarketTickerSnapshot(
                ticker=ticker, status="ok", reference_price=320.5, previous_close=318.0, change=2.5, change_pct=0.79,
                volume=100, turnover=1000, currency="HKD", market="HKEX", data_source="eodhd",
                data_timestamp_hkt="2026-05-10T10:00:00+08:00", freshness_status="delayed", delay_minutes=15,
                adjustment_policy="vendor_default", confidence="unknown", limitations=["bounded"],
            )

    monkeypatch.setattr("src.market_data.smoke.build_review_shell_market_data_provider", lambda env: _FakeProvider())
    out = build_market_smoke_summary("0700.HK", {"MARKET_DATA_PROVIDER": "eodhd", "EODHD_API_TOKEN": "secret"})
    assert out["status"] == "ok"
    assert set(out.keys()) == {
        "ticker", "status", "reference_price", "previous_close", "change", "change_pct", "volume", "turnover",
        "currency", "market", "data_source", "data_timestamp_hkt", "freshness_status", "delay_minutes", "limitations",
    }


def test_smoke_summary_invalid_ticker_safe():
    out = build_market_smoke_summary("AAPL", {})
    assert out["status"] == "unavailable"


def test_smoke_summary_provider_exception_fallback(monkeypatch):
    monkeypatch.setattr(
        "src.market_data.smoke.build_review_shell_market_data_provider",
        lambda env: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    out = build_market_smoke_summary("0700.HK", {"MARKET_DATA_PROVIDER": "eodhd", "EODHD_API_TOKEN": "secret"})
    assert out["status"] == "unavailable"
    assert "boom" not in str(out)


def test_smoke_summary_no_token_leak_in_stringified_output():
    out = build_market_smoke_summary("0700.HK", {"MARKET_DATA_PROVIDER": "eodhd", "EODHD_API_TOKEN": "super-secret-token"})
    assert "super-secret-token" not in str(out)
