from src.market_data.review_provider import (
    EodhdMarketDataProvider,
    ExistingSourceMarketDataProvider,
    NullMarketDataProvider,
    build_review_shell_market_data_provider,
    from_vendor_symbol,
    snapshot_to_dict,
    to_vendor_symbol,
)


def test_null_provider_unavailable():
    snap = NullMarketDataProvider().get_ticker_market_snapshot("0700.HK")
    assert snap.status == "unavailable"


def test_to_vendor_symbol_hk():
    assert to_vendor_symbol("0700.HK") == "0700.HK"
    assert to_vendor_symbol("0388.HK") == "0388.HK"
    assert to_vendor_symbol("1299.HK") == "1299.HK"
    assert to_vendor_symbol("AAPL") is None
    assert from_vendor_symbol("0700.HK") == "0700.HK"


def test_eodhd_absent_token_unavailable():
    provider = EodhdMarketDataProvider(token="", http_get=lambda **kwargs: {})
    snap = provider.get_ticker_market_snapshot("0700.HK")
    assert snap.status == "unavailable"


def test_eodhd_maps_fake_ok_response():
    def fake_get(**kwargs):
        assert "api_token" in kwargs
        return {"close": 320.5, "previousClose": 318.0, "volume": 1000, "timestamp": "2026-05-10T08:00:00Z"}

    provider = EodhdMarketDataProvider(token="secret", http_get=fake_get)
    snap = provider.get_ticker_market_snapshot("0700.HK")
    assert snap.status == "ok"
    assert snap.reference_price == 320.5
    assert snap.previous_close == 318.0
    assert snap.data_source == "eodhd"


def test_eodhd_malformed_response_unavailable():
    provider = EodhdMarketDataProvider(token="secret", http_get=lambda **kwargs: [])
    snap = provider.get_ticker_market_snapshot("0700.HK")
    assert snap.status == "unavailable"


def test_builder_default_null():
    snap = build_review_shell_market_data_provider(env={}).get_ticker_market_snapshot("0700.HK")
    assert snap.status == "unavailable"


def test_builder_existing_provider():
    provider = build_review_shell_market_data_provider(env={"MARKET_DATA_PROVIDER": "existing"})
    assert isinstance(provider, ExistingSourceMarketDataProvider)
    assert provider.get_ticker_market_snapshot("0700.HK").status == "unavailable"


def test_snapshot_to_dict_no_token():
    snap = NullMarketDataProvider().get_ticker_market_snapshot("0700.HK")
    payload = snapshot_to_dict(snap)
    assert "token" not in str(payload).lower()
