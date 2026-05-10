from __future__ import annotations

from typing import Any, Mapping

from src.market_data.review_provider import build_review_shell_market_data_provider, snapshot_to_dict

_ALLOWED_TICKERS = {"0700.HK", "0388.HK", "1299.HK"}


def normalize_smoke_ticker(raw: str) -> str:
    return str(raw or "").strip().upper()


def is_supported_smoke_ticker(raw: str) -> bool:
    return normalize_smoke_ticker(raw) in _ALLOWED_TICKERS


def build_market_smoke_summary(ticker: str, env: Mapping[str, str]) -> dict[str, Any]:
    normalized = normalize_smoke_ticker(ticker)
    if not is_supported_smoke_ticker(normalized):
        return {
            "ticker": normalized,
            "status": "unavailable",
            "reference_price": None,
            "previous_close": None,
            "change": None,
            "change_pct": None,
            "volume": None,
            "turnover": None,
            "currency": "HKD",
            "market": "HKEX",
            "data_source": None,
            "data_timestamp_hkt": None,
            "freshness_status": "unknown",
            "delay_minutes": None,
            "limitations": ["Ticker not in monitored smoke list."],
        }
    try:
        provider = build_review_shell_market_data_provider(env=dict(env or {}))
        snap = provider.get_ticker_market_snapshot(normalized)
        payload = snapshot_to_dict(snap)
        return {k: payload.get(k) for k in (
            "ticker","status","reference_price","previous_close","change","change_pct","volume","turnover",
            "currency","market","data_source","data_timestamp_hkt","freshness_status","delay_minutes","limitations",
        )}
    except Exception:
        return {
            "ticker": normalized,
            "status": "unavailable",
            "reference_price": None,
            "previous_close": None,
            "change": None,
            "change_pct": None,
            "volume": None,
            "turnover": None,
            "currency": "HKD",
            "market": "HKEX",
            "data_source": None,
            "data_timestamp_hkt": None,
            "freshness_status": "unknown",
            "delay_minutes": None,
            "limitations": ["Market smoke summary unavailable."],
        }
