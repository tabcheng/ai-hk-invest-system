from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class SymbolMetadata:
    """Provider-agnostic symbol metadata used by strategy and operator surfaces."""

    symbol: str
    display_name: str
    market: str = "HK"
    currency: str = "HKD"


class MarketDataProvider(Protocol):
    """Boundary for market data adapters.

    Data-flow guardrail:
    - Upstream orchestration/signal modules only call this protocol.
    - Concrete providers hide source-specific implementation details.
    - This keeps Step 42 scoped to paper-trading/decision support only;
      it does NOT authorize live broker connectivity or auto execution.
    """

    def get_daily_ohlcv(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Return daily OHLCV rows with Date index and Open/High/Low/Close/Volume columns."""

    def get_latest_price(self, symbol: str) -> float | None:
        """Return latest available close/mark price for symbol, or None when unavailable."""

    def get_symbol_metadata(self, symbol: str) -> SymbolMetadata:
        """Return normalized symbol metadata used for display and audit contexts."""
