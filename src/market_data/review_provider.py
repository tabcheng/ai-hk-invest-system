from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
import re

_HKT = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class MarketTickerSnapshot:
    ticker: str
    status: str
    reference_price: float | None
    previous_close: float | None
    change: float | None
    change_pct: float | None
    volume: float | None
    turnover: float | None
    currency: str
    market: str
    data_source: str | None
    data_timestamp_hkt: str | None
    freshness_status: str
    delay_minutes: int | None
    adjustment_policy: str | None
    confidence: str
    limitations: list[str]


class ReviewShellMarketDataProvider(Protocol):
    def get_ticker_market_snapshot(self, ticker: str, business_date: str | None = None) -> MarketTickerSnapshot:
        ...


def to_vendor_symbol(ticker: str) -> str | None:
    normalized = str(ticker or "").strip().upper()
    m = re.fullmatch(r"(\d{4})\.HK", normalized)
    if not m:
        return None
    return f"{m.group(1)}.HK"


def from_vendor_symbol(symbol: str) -> str | None:
    normalized = str(symbol or "").strip().upper()
    return to_vendor_symbol(normalized)


def unavailable_snapshot(ticker: str, reason: str, source: str | None = None) -> MarketTickerSnapshot:
    return MarketTickerSnapshot(
        ticker=str(ticker or "").strip().upper(), status="unavailable", reference_price=None, previous_close=None,
        change=None, change_pct=None, volume=None, turnover=None, currency="HKD", market="HKEX",
        data_source=source, data_timestamp_hkt=None, freshness_status="unknown", delay_minutes=None,
        adjustment_policy=None, confidence="unknown", limitations=[reason],
    )


class NullMarketDataProvider:
    def get_ticker_market_snapshot(self, ticker: str, business_date: str | None = None) -> MarketTickerSnapshot:
        return unavailable_snapshot(ticker, "Market data provider disabled.", "null")


class ExistingSourceMarketDataProvider:
    """Step-123 bounded provider: keep existing-source-only behavior."""

    def get_ticker_market_snapshot(self, ticker: str, business_date: str | None = None) -> MarketTickerSnapshot:
        return unavailable_snapshot(
            ticker,
            "Existing-source market snapshot unavailable in current bounded read-model.",
            "existing",
        )


class EodhdMarketDataProvider:
    def __init__(self, token: str | None, timeout_seconds: float = 3.0, http_get: Any | None = None):
        self._token = (token or "").strip()
        self._timeout = timeout_seconds
        self._http_get = http_get

    def get_ticker_market_snapshot(self, ticker: str, business_date: str | None = None) -> MarketTickerSnapshot:
        symbol = to_vendor_symbol(ticker)
        if not symbol:
            return unavailable_snapshot(ticker, "Invalid HK ticker format.", "eodhd")
        if not self._token:
            return unavailable_snapshot(ticker, "EODHD API token not configured.", "eodhd")
        if self._http_get is None:
            return unavailable_snapshot(ticker, "EODHD runtime HTTP disabled in this environment.", "eodhd")
        try:
            payload = self._http_get(symbol=symbol, timeout_seconds=self._timeout, api_token=self._token)
            if not isinstance(payload, dict):
                return unavailable_snapshot(ticker, "Malformed vendor response.", "eodhd")
            close = payload.get("close")
            prev = payload.get("previousClose")
            volume = payload.get("volume")
            ts = payload.get("timestamp")
            dt_hkt = None
            if isinstance(ts, str):
                dt_hkt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(_HKT).isoformat()
            close_f = float(close) if close is not None else None
            prev_f = float(prev) if prev is not None else None
            ch = (close_f - prev_f) if close_f is not None and prev_f is not None else None
            ch_pct = ((ch / prev_f) * 100.0) if ch is not None and prev_f not in (None, 0) else None
            return MarketTickerSnapshot(
                ticker=str(ticker).upper(), status="ok" if close_f is not None else "partial",
                reference_price=close_f, previous_close=prev_f, change=ch, change_pct=ch_pct,
                volume=float(volume) if volume is not None else None, turnover=None,
                currency="HKD", market="HKEX", data_source="eodhd", data_timestamp_hkt=dt_hkt,
                freshness_status="unknown", delay_minutes=None, adjustment_policy="vendor_default",
                confidence="unknown", limitations=[],
            )
        except Exception:
            return unavailable_snapshot(ticker, "Vendor request failed.", "eodhd")


def build_review_shell_market_data_provider(env: dict[str, str] | None = None, http_get: Any | None = None) -> ReviewShellMarketDataProvider:
    env = env or {}
    name = str(env.get("MARKET_DATA_PROVIDER", "null") or "null").strip().lower()
    if name == "existing":
        return ExistingSourceMarketDataProvider()
    if name == "eodhd":
        try:
            timeout = float(str(env.get("MARKET_DATA_TIMEOUT_SECONDS", "3") or "3"))
        except ValueError:
            timeout = 3.0
        return EodhdMarketDataProvider(token=env.get("EODHD_API_TOKEN"), timeout_seconds=timeout, http_get=http_get)
    return NullMarketDataProvider()


def snapshot_to_dict(snapshot: MarketTickerSnapshot) -> dict[str, Any]:
    return asdict(snapshot)
