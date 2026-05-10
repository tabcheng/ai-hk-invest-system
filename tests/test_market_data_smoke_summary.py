from datetime import datetime, timedelta, timezone

from src.market_data.smoke import build_market_smoke_summary, classify_market_data_freshness


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
        "freshness_status_display", "freshness_label_zh", "freshness_label_en", "freshness_warning",
        "data_age_minutes", "data_age_hours", "is_stale",
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


def test_freshness_unknown_when_timestamp_missing():
    out = classify_market_data_freshness(data_timestamp_hkt=None)
    assert out["freshness_status_display"] == "unknown"
    assert out["is_stale"] is False


def test_freshness_last_available_close_for_previous_day():
    now = datetime(2026, 5, 10, 11, 0, tzinfo=timezone(timedelta(hours=8)))
    out = classify_market_data_freshness(data_timestamp_hkt="2026-05-09T16:08:00+08:00", now_hkt=now)
    assert out["freshness_status_display"] == "last_available_close"


def test_freshness_stale_over_72_hours():
    now = datetime(2026, 5, 10, 11, 0, tzinfo=timezone(timedelta(hours=8)))
    out = classify_market_data_freshness(data_timestamp_hkt="2026-05-06T10:00:00+08:00", now_hkt=now)
    assert out["freshness_status_display"] == "stale"


def test_freshness_delayed_same_day_outside_delay_buffer():
    now = datetime(2026, 5, 10, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    out = classify_market_data_freshness(
        data_timestamp_hkt="2026-05-10T11:10:00+08:00", now_hkt=now, provider_freshness_status="delayed", delay_minutes=15
    )
    assert out["freshness_status_display"] == "delayed"


def test_freshness_invalid_timestamp_unknown():
    out = classify_market_data_freshness(data_timestamp_hkt="not-a-time")
    assert out["freshness_status_display"] == "unknown"
