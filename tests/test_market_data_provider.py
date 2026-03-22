from datetime import date

import pandas as pd
import pytest

from src import data
from src.signals import get_signal_for_ticker
from src.market_data.providers import (
    MockMarketDataProvider,
    YFinanceMarketDataProvider,
    build_market_data_provider,
    normalize_symbol,
)


def test_normalize_symbol_defaults_to_hk_suffix():
    assert normalize_symbol("0700") == "0700.HK"
    assert normalize_symbol("0700.hk") == "0700.HK"
    assert normalize_symbol("AAPL.US") == "AAPL.US"


def test_mock_provider_returns_daily_ohlcv():
    provider = MockMarketDataProvider()

    frame = provider.get_daily_ohlcv("0700", date(2026, 1, 1), date(2026, 1, 3))

    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 3
    assert float(frame["Close"].iloc[0]) > 0


def test_build_market_data_provider_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unsupported MARKET_DATA_PROVIDER"):
        build_market_data_provider("unknown")


def test_build_market_data_provider_rejects_blank_provider():
    with pytest.raises(ValueError, match="Unsupported MARKET_DATA_PROVIDER"):
        build_market_data_provider("   ")


def test_fetch_market_data_uses_env_selected_provider(monkeypatch):
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "mock")

    frame = data.fetch_market_data("0700.HK")

    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    assert "Close" in frame.columns


def test_yfinance_latest_price_extends_end_date_by_one_day(monkeypatch):
    captured: dict[str, str] = {}
    expected_close = 123.45

    def fake_download(symbol, start, end, interval, auto_adjust, progress):
        captured["symbol"] = symbol
        captured["start"] = start
        captured["end"] = end
        return pd.DataFrame(
            [{"Date": "2026-03-22", "Open": 120.0, "High": 125.0, "Low": 119.0, "Close": expected_close, "Volume": 1_000_000}]
        ).set_index("Date")

    monkeypatch.setattr("src.market_data.providers.yf.download", fake_download)
    monkeypatch.setattr("src.market_data.providers.date", type("FakeDate", (), {"today": staticmethod(lambda: date(2026, 3, 22))}))

    provider = YFinanceMarketDataProvider()
    latest = provider.get_latest_price("0700.HK")

    assert latest == expected_close
    assert captured["symbol"] == "0700.HK"
    assert captured["start"] == "2026-03-01"
    assert captured["end"] == "2026-03-23"


def test_fetch_market_data_with_yfinance_includes_end_date_bar(monkeypatch):
    captured: dict[str, str] = {}

    def fake_download(symbol, start, end, interval, auto_adjust, progress):
        captured["symbol"] = symbol
        captured["start"] = start
        captured["end"] = end
        return pd.DataFrame(
            [
                {
                    "Date": "2026-03-22",
                    "Open": 100.0,
                    "High": 101.0,
                    "Low": 99.0,
                    "Close": 100.5,
                    "Volume": 1_000_000,
                }
            ]
        ).set_index("Date")

    monkeypatch.setattr("src.market_data.providers.yf.download", fake_download)
    monkeypatch.setattr(
        "src.data.date",
        type("FakeDate", (), {"today": staticmethod(lambda: date(2026, 3, 22))}),
    )

    provider = YFinanceMarketDataProvider()
    frame = data.fetch_market_data("0700.HK", provider=provider, lookback_days=1)

    assert not frame.empty
    assert float(frame["Close"].iloc[-1]) == 100.5
    assert captured["start"] == "2026-03-21"
    # Inclusive provider contract => yfinance request uses end_date + 1 day.
    assert captured["end"] == "2026-03-23"


def test_signal_path_not_one_day_late_with_yfinance_exclusive_end(monkeypatch):
    def fake_download(symbol, start, end, interval, auto_adjust, progress):
        if end == "2026-03-23":
            closes = [100.0] * 199 + [300.0]
        else:
            closes = [100.0] * 200

        rows = [
            {
                "Date": f"2026-03-{i + 1:02d}",
                "Open": close,
                "High": close,
                "Low": close,
                "Close": close,
                "Volume": 1_000_000,
            }
            for i, close in enumerate(closes)
        ]
        return pd.DataFrame(rows).set_index("Date")

    monkeypatch.setattr("src.market_data.providers.yf.download", fake_download)
    monkeypatch.setattr(
        "src.data.date",
        type("FakeDate", (), {"today": staticmethod(lambda: date(2026, 3, 22))}),
    )

    signal = get_signal_for_ticker("0700.HK", provider=YFinanceMarketDataProvider())

    # If the last bar were dropped by exclusive-end handling, this would be HOLD.
    assert signal["signal"] == "BUY"
