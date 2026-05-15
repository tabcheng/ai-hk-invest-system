from src.railway_cadence_runtime import (
    build_runtime_cadence_metadata,
    get_expected_railway_cron_utc,
    get_runtime_schedule_basis,
)


def test_runtime_schedule_mapping_core_run_types():
    assert get_expected_railway_cron_utc("post_close_daily_review") == "0 12 * * *"
    assert get_expected_railway_cron_utc("midday_market_monitor") == "30 4 * * 1-5"
    assert get_expected_railway_cron_utc("stale_risk_refresh") == "30 7 * * 1-5"


def test_runtime_schedule_mapping_fallback_default_run_type():
    assert get_expected_railway_cron_utc("") == "0 12 * * *"
    assert get_runtime_schedule_basis("invalid") == "HKT 20:00 (Railway cron UTC: 0 12 * * *)"


def test_build_runtime_cadence_metadata_uses_normalized_run_type():
    metadata = build_runtime_cadence_metadata("MIDDAY_MARKET_MONITOR")
    assert metadata["run_type"] == "midday_market_monitor"
    assert metadata["schedule_basis"] == "HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)"
