from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from src.config import STOCK_METADATA
from src.market_data.provider import MarketDataProvider, SymbolMetadata


_REQUIRED_OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def normalize_symbol(raw_symbol: str) -> str:
    """Normalize tickers to uppercase and default HK suffix.

    Symbol normalization assumptions (v1):
    - Input may be `0700` or `0700.hk`; normalize to `0700.HK`.
    - If a non-HK explicit suffix is provided (e.g., `AAPL.US`), preserve it.
    - This is a lightweight guardrail for consistent provider-boundary behavior,
      not a full exchange-symbol canonicalization engine.
    """

    symbol = raw_symbol.strip().upper()
    if "." not in symbol:
        return f"{symbol}.HK"
    return symbol


class YFinanceMarketDataProvider:
    """Production-default provider using yfinance.

    Failure handling guardrail:
    - Provider methods raise ValueError for irrecoverable schema issues.
    - Callers keep existing behavior by translating failures into per-ticker
      runtime errors (no process crash across all symbols).
    """

    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        normalized_symbol = normalize_symbol(symbol)
        data = yf.download(
            normalized_symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval="1d",
            auto_adjust=False,
            progress=False,
        )

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Keep provider boundary strict: callers can assume consistent columns.
        missing_columns = [column for column in _REQUIRED_OHLCV_COLUMNS if column not in data.columns]
        if missing_columns and not data.empty:
            raise ValueError(
                "Market data provider returned unexpected schema; "
                f"missing columns: {', '.join(missing_columns)}"
            )

        if data.empty:
            return pd.DataFrame(columns=_REQUIRED_OHLCV_COLUMNS)

        return data[_REQUIRED_OHLCV_COLUMNS].copy()

    def get_latest_price(self, symbol: str) -> float | None:
        today = date.today()
        # yfinance `end` is exclusive, so include one extra day to avoid
        # dropping the most recent available daily bar in month-to-date lookups.
        history = self.get_daily_ohlcv(
            symbol,
            start_date=today.replace(day=1),
            end_date=today + timedelta(days=1),
        )
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])

    def get_symbol_metadata(self, symbol: str) -> SymbolMetadata:
        normalized_symbol = normalize_symbol(symbol)
        display_name = STOCK_METADATA.get(normalized_symbol, normalized_symbol)
        return SymbolMetadata(symbol=normalized_symbol, display_name=display_name)


class MockMarketDataProvider:
    """Deterministic stub provider for local development/tests.

    Paper-only guardrail:
    - Returns fixture-like synthetic rows.
    - Never calls external network APIs.
    - Enables predictable signal/paper-trading verification without affecting
      real-money trading paths (which are out of scope for this project phase).
    """

    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        normalized_symbol = normalize_symbol(symbol)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        if len(dates) == 0:
            return pd.DataFrame(columns=_REQUIRED_OHLCV_COLUMNS)

        base_price = 100.0 + (sum(ord(ch) for ch in normalized_symbol) % 50)
        rows = []
        for i, ts in enumerate(dates):
            close = base_price + i * 0.5
            rows.append(
                {
                    "Date": ts,
                    "Open": close - 0.3,
                    "High": close + 0.8,
                    "Low": close - 1.0,
                    "Close": close,
                    "Volume": 1_000_000 + i * 100,
                }
            )
        frame = pd.DataFrame(rows).set_index("Date")
        return frame[_REQUIRED_OHLCV_COLUMNS]

    def get_latest_price(self, symbol: str) -> float | None:
        today = date.today()
        history = self.get_daily_ohlcv(symbol, start_date=today, end_date=today)
        if history.empty:
            return None
        return float(history["Close"].iloc[-1])

    def get_symbol_metadata(self, symbol: str) -> SymbolMetadata:
        normalized_symbol = normalize_symbol(symbol)
        display_name = f"Mock {normalized_symbol}"
        return SymbolMetadata(symbol=normalized_symbol, display_name=display_name)


def build_market_data_provider(provider_name: str) -> MarketDataProvider:
    """Resolve provider implementation by config name.

    v1 deliberately supports only `yfinance` and `mock` to keep rollout scope
    small and avoid premature multi-provider orchestration complexity.
    """

    provider_name = provider_name.strip().lower()
    if not provider_name:
        raise ValueError(
            "Unsupported MARKET_DATA_PROVIDER ''. Supported values: mock, yfinance."
        )

    registry = {
        "yfinance": YFinanceMarketDataProvider,
        "mock": MockMarketDataProvider,
    }

    provider_cls = registry.get(provider_name)
    if provider_cls is None:
        supported = ", ".join(sorted(registry.keys()))
        raise ValueError(
            f"Unsupported MARKET_DATA_PROVIDER '{provider_name}'. Supported values: {supported}."
        )

    return provider_cls()
