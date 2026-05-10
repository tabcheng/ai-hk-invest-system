from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
import re
import requests

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
    def __init__(self, token: str | None, timeout_seconds: float = 3.0, http_get: Any | None = None, delay_policy: str = "unknown"):
        self._token = (token or "").strip()
        self._timeout = timeout_seconds
        self._http_get = http_get
        self._delay_policy = str(delay_policy or "unknown").strip().lower()

    @staticmethod
    def _to_float(value: Any) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_hkt_iso(ts: Any) -> str | None:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone(_HKT).isoformat()
        if isinstance(ts, str) and ts.strip():
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(_HKT).isoformat()
            except ValueError:
                return None
        return None

    def _runtime_http_get(self, symbol: str, timeout_seconds: float, api_token: str) -> Any:
        resp = requests.get(
            "https://eodhd.com/api/real-time/",
            params={"api_token": api_token, "fmt": "json", "s": symbol},
            timeout=timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json()

    def _parse_vendor_payload(self, payload: dict[str, Any], ticker: str) -> MarketTickerSnapshot:
        close = payload.get("close")
        prev = payload.get("previousClose")
        volume = payload.get("volume")
        turnover = payload.get("turnover")
        dt_hkt = self._to_hkt_iso(payload.get("timestamp"))
        close_f = self._to_float(close)
        prev_f = self._to_float(prev)
        volume_f = self._to_float(volume)
        turnover_f = self._to_float(turnover)
        ch = (close_f - prev_f) if close_f is not None and prev_f is not None else None
        ch_pct = ((ch / prev_f) * 100.0) if ch is not None and prev_f not in (None, 0) else None
        usable = [close_f, prev_f, volume_f, turnover_f]
        status = "ok" if close_f is not None else ("partial" if any(x is not None for x in usable) else "unavailable")
        limitations = []
        if status == "partial":
            limitations.append("Bounded vendor fields partially available.")
        if status == "unavailable":
            return unavailable_snapshot(ticker, "No usable market fields in vendor response.", "eodhd")
        return MarketTickerSnapshot(
            ticker=str(ticker).upper(), status=status,
            reference_price=close_f, previous_close=prev_f, change=ch, change_pct=ch_pct,
            volume=volume_f, turnover=turnover_f,
            currency=str(payload.get("currency") or "HKD").upper(),
            market="HKEX", data_source="eodhd", data_timestamp_hkt=dt_hkt,
            freshness_status="delayed" if self._delay_policy == "delayed" else "unknown",
            delay_minutes=15 if self._delay_policy == "delayed" else None,
            adjustment_policy="vendor_default",
            confidence="unknown", limitations=limitations,
        )

    def get_ticker_market_snapshot(self, ticker: str, business_date: str | None = None) -> MarketTickerSnapshot:
        symbol = to_vendor_symbol(ticker)
        if not symbol:
            return unavailable_snapshot(ticker, "Invalid HK ticker format.", "eodhd")
        if not self._token:
            return unavailable_snapshot(ticker, "EODHD API credential not configured.", "eodhd")
        http_get = self._http_get or self._runtime_http_get
        try:
            payload = http_get(symbol=symbol, timeout_seconds=self._timeout, api_token=self._token)
            if not isinstance(payload, dict):
                return unavailable_snapshot(ticker, "Malformed vendor response.", "eodhd")
            return self._parse_vendor_payload(payload, ticker)
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
        return EodhdMarketDataProvider(
            token=env.get("EODHD_API_TOKEN"),
            timeout_seconds=timeout,
            http_get=http_get,
            delay_policy=str(env.get("MARKET_DATA_DELAY_POLICY", "unknown") or "unknown"),
        )
    return NullMarketDataProvider()


def snapshot_to_dict(snapshot: MarketTickerSnapshot) -> dict[str, Any]:
    return asdict(snapshot)
