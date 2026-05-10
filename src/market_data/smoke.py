from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.market_data.review_provider import build_review_shell_market_data_provider, snapshot_to_dict

_ALLOWED_TICKERS = {"0700.HK", "0388.HK", "1299.HK"}
_HKT = timezone(timedelta(hours=8))


def normalize_smoke_ticker(raw: str) -> str:
    return str(raw or "").strip().upper()


def is_supported_smoke_ticker(raw: str) -> bool:
    return normalize_smoke_ticker(raw) in _ALLOWED_TICKERS


def _parse_hkt_timestamp(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_HKT)
        return parsed.astimezone(_HKT)
    except ValueError:
        return None


def classify_market_data_freshness(
    *,
    data_timestamp_hkt: Any,
    now_hkt: datetime | None = None,
    provider_freshness_status: str | None = None,
    delay_minutes: int | None = None,
) -> dict[str, Any]:
    now = (now_hkt or datetime.now(_HKT)).astimezone(_HKT)
    parsed = _parse_hkt_timestamp(data_timestamp_hkt)
    provider_status = str(provider_freshness_status or "unknown").strip().lower()
    if parsed is None:
        return {
            "freshness_status_display": "unknown",
            "freshness_label_zh": "未知",
            "freshness_label_en": "unknown",
            "freshness_warning": "資料時間未能解析或未提供，請勿視為即時資料。",
            "data_age_minutes": None,
            "data_age_hours": None,
            "is_stale": False,
        }
    age_minutes = max(0, int((now - parsed).total_seconds() // 60))
    age_hours = round(age_minutes / 60.0, 1)
    threshold = (delay_minutes if isinstance(delay_minutes, int) and delay_minutes >= 0 else 15) + 20
    if age_minutes > 72 * 60:
        status = "stale"
    elif parsed.date() < now.date():
        status = "last_available_close"
    elif age_minutes <= threshold and provider_status == "fresh":
        status = "fresh"
    elif age_minutes <= threshold + 120:
        status = "delayed"
    else:
        status = "stale"
    labels = {
        "fresh": ("即日可用 / fresh", "Data within expected delay window."),
        "delayed": ("延遲資料 / delayed", "資料可能延遲，請勿視為即時交易資料。"),
        "last_available_close": ("上一交易日 / last available close", "此資料可能不是即日即時資料，只供 paper review。"),
        "stale": ("過舊資料 / stale", "資料已過舊，只可作參考，請勿用作即時判斷。"),
        "unknown": ("未知 / unknown", "資料時間未能解析或未提供，請勿視為即時資料。"),
    }
    zh_en, warning = labels.get(status, labels["unknown"])
    zh, en = [x.strip() for x in zh_en.split("/", 1)]
    return {
        "freshness_status_display": status,
        "freshness_label_zh": zh,
        "freshness_label_en": en,
        "freshness_warning": warning,
        "data_age_minutes": age_minutes,
        "data_age_hours": age_hours,
        "is_stale": status == "stale",
    }




def build_market_data_acceptance_summary(*, freshness_status_display: Any) -> dict[str, Any]:
    status = str(freshness_status_display or "unknown").strip().lower()
    mapping = {
        "fresh": {
            "market_data_acceptance_status": "acceptable_for_paper_review",
            "market_data_acceptance_label_zh": "可用於每日檢視",
            "market_data_acceptance_label_en": "acceptable for paper review",
            "market_data_acceptance_warning": "資料在可接受延遲範圍內，仍非即時報價。",
            "accepted_for_daily_review": True,
            "market_data_acceptance_reason": "fresh within expected delay window; paper review only",
        },
        "delayed": {
            "market_data_acceptance_status": "acceptable_for_paper_review",
            "market_data_acceptance_label_zh": "可用於每日檢視（延遲）",
            "market_data_acceptance_label_en": "acceptable for paper review (delayed)",
            "market_data_acceptance_warning": "資料有延遲，只供 paper review，不可當作即時資料。",
            "accepted_for_daily_review": True,
            "market_data_acceptance_reason": "delayed but still within bounded paper-review tolerance",
        },
        "last_available_close": {
            "market_data_acceptance_status": "caution_last_available_close",
            "market_data_acceptance_label_zh": "可用於每日檢視（上一交易日）",
            "market_data_acceptance_label_en": "caution: last available close",
            "market_data_acceptance_warning": "僅為上一交易日收市資料，不是即時報價。",
            "accepted_for_daily_review": True,
            "market_data_acceptance_reason": "last available close is acceptable for daily review with caution",
        },
        "stale": {
            "market_data_acceptance_status": "stale_do_not_use_for_intraday",
            "market_data_acceptance_label_zh": "過舊，不可用於盤中判斷",
            "market_data_acceptance_label_en": "stale; do not use for intraday",
            "market_data_acceptance_warning": "資料過舊，請勿用作盤中判斷。",
            "accepted_for_daily_review": False,
            "market_data_acceptance_reason": "stale snapshot exceeds daily-review acceptance threshold",
        },
        "unknown": {
            "market_data_acceptance_status": "unknown",
            "market_data_acceptance_label_zh": "未知，不可驗證",
            "market_data_acceptance_label_en": "unknown; cannot verify freshness",
            "market_data_acceptance_warning": "未能驗證 timestamp/freshness，請勿用於判斷。",
            "accepted_for_daily_review": False,
            "market_data_acceptance_reason": "timestamp/freshness cannot be verified",
        },
    }
    return dict(mapping.get(status, mapping["unknown"]))


def build_market_acceptance_by_ticker(
    tickers: list[str] | tuple[str, ...],
    *,
    env: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Build bounded market acceptance metadata per ticker with per-ticker fallback."""
    acceptance_by_ticker: dict[str, dict[str, Any]] = {}
    for raw_ticker in tickers:
        ticker = normalize_smoke_ticker(str(raw_ticker or ""))
        if not ticker:
            continue
        try:
            smoke = build_market_smoke_summary(ticker, env)
            freshness_meta = classify_market_data_freshness(
                data_timestamp_hkt=smoke.get("data_timestamp_hkt"),
                provider_freshness_status=smoke.get("freshness_status"),
                delay_minutes=smoke.get("delay_minutes"),
            )
            acceptance_by_ticker[ticker] = build_market_data_acceptance_summary(
                freshness_status_display=freshness_meta.get("freshness_status_display")
            )
        except Exception:
            acceptance_by_ticker[ticker] = build_market_data_acceptance_summary(freshness_status_display="unknown")
    return acceptance_by_ticker


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
            **classify_market_data_freshness(data_timestamp_hkt=None, provider_freshness_status="unknown", delay_minutes=None),
        }
    try:
        provider = build_review_shell_market_data_provider(env=dict(env or {}))
        snap = provider.get_ticker_market_snapshot(normalized)
        payload = snapshot_to_dict(snap)
        result = {k: payload.get(k) for k in (
            "ticker","status","reference_price","previous_close","change","change_pct","volume","turnover",
            "currency","market","data_source","data_timestamp_hkt","freshness_status","delay_minutes","limitations",
        )}
        result.update(
            classify_market_data_freshness(
                data_timestamp_hkt=result.get("data_timestamp_hkt"),
                provider_freshness_status=result.get("freshness_status"),
                delay_minutes=result.get("delay_minutes"),
            )
        )
        return result
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
            **classify_market_data_freshness(data_timestamp_hkt=None, provider_freshness_status="unknown", delay_minutes=None),
        }
