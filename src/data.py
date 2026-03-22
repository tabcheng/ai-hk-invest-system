from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.config import get_market_data_provider_name
from src.market_data.provider import MarketDataProvider, SymbolMetadata
from src.market_data.providers import build_market_data_provider


def get_market_data_provider() -> MarketDataProvider:
    """Resolve active market-data provider from runtime config.

    Failure handling guardrail:
    - Invalid provider configuration should fail fast early in the run.
    - Per-ticker data failures are still handled by callers as existing
      best-effort processing errors so one symbol does not crash all symbols.
    """

    return build_market_data_provider(get_market_data_provider_name())


def fetch_market_data(
    ticker: str,
    provider: MarketDataProvider | None = None,
    lookback_days: int = 365,
) -> pd.DataFrame:
    """Fetch daily OHLCV data through provider boundary.

    Data flow (v1):
    orchestrator -> signal module -> this function -> provider adapter -> source.
    """

    active_provider = provider or get_market_data_provider()
    end_date = date.today()
    start_date = end_date - timedelta(days=lookback_days)
    return active_provider.get_daily_ohlcv(ticker, start_date=start_date, end_date=end_date)


def fetch_latest_price(ticker: str, provider: MarketDataProvider | None = None) -> float | None:
    active_provider = provider or get_market_data_provider()
    return active_provider.get_latest_price(ticker)


def fetch_symbol_metadata(
    ticker: str,
    provider: MarketDataProvider | None = None,
) -> SymbolMetadata:
    active_provider = provider or get_market_data_provider()
    return active_provider.get_symbol_metadata(ticker)
