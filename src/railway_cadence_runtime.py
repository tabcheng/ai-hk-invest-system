from __future__ import annotations

from typing import Any

from src.backend_data_cadence import (
    DEFAULT_RUN_TYPE,
    RUN_TYPE_EVENT_CONTEXT,
    RUN_TYPE_MIDDAY,
    RUN_TYPE_POST_CLOSE,
    RUN_TYPE_PRE_MARKET,
    RUN_TYPE_STALE_RISK,
)

_CADENCE_BY_RUN_TYPE: dict[str, dict[str, str]] = {
    RUN_TYPE_POST_CLOSE: {
        "intended_hkt_window": "20:00 HKT",
        "railway_cron_utc": "0 12 * * *",
        "schedule_basis": "HKT 20:00 (Railway cron UTC: 0 12 * * *)",
    },
    RUN_TYPE_MIDDAY: {
        "intended_hkt_window": "around 12:30 HKT weekday",
        "railway_cron_utc": "30 4 * * 1-5",
        "schedule_basis": "HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)",
    },
    RUN_TYPE_STALE_RISK: {
        "intended_hkt_window": "around 15:30 HKT weekday",
        "railway_cron_utc": "30 7 * * 1-5",
        "schedule_basis": "HKT around 15:30 weekday (Railway cron UTC: 30 7 * * 1-5)",
    },
    RUN_TYPE_PRE_MARKET: {
        "intended_hkt_window": "around 08:45 HKT weekday",
        "railway_cron_utc": "45 0 * * 1-5",
        "schedule_basis": "HKT around 08:45 weekday (Railway cron UTC: 45 0 * * 1-5)",
    },
    RUN_TYPE_EVENT_CONTEXT: {
        "intended_hkt_window": "event-driven, not scheduled now",
        "railway_cron_utc": "TBD",
        "schedule_basis": "Event-driven context refresh (Railway cron UTC: planned later)",
    },
}


def _normalize_run_type(run_type: str | None) -> str:
    candidate = str(run_type or "").strip().lower()
    return candidate if candidate in _CADENCE_BY_RUN_TYPE else DEFAULT_RUN_TYPE


def get_expected_railway_cron_utc(run_type: str | None) -> str | None:
    normalized = _normalize_run_type(run_type)
    cron = _CADENCE_BY_RUN_TYPE[normalized]["railway_cron_utc"]
    return cron if cron != "TBD" else None


def get_intended_hkt_window(run_type: str | None) -> str:
    return _CADENCE_BY_RUN_TYPE[_normalize_run_type(run_type)]["intended_hkt_window"]


def get_runtime_schedule_basis(run_type: str | None) -> str:
    return _CADENCE_BY_RUN_TYPE[_normalize_run_type(run_type)]["schedule_basis"]


def build_runtime_cadence_metadata(run_type: str | None) -> dict[str, Any]:
    normalized = _normalize_run_type(run_type)
    return {
        "run_type": normalized,
        "intended_hkt_window": get_intended_hkt_window(normalized),
        "railway_cron_utc": get_expected_railway_cron_utc(normalized),
        "schedule_basis": get_runtime_schedule_basis(normalized),
    }
