from pathlib import Path

from scripts.backend_cadence_smoke import run_smoke


def test_smoke_valid_run_types_pass_and_keep_guardrails():
    run_types = [
        "post_close_daily_review",
        "pre_market_readiness_check",
        "midday_market_monitor",
        "stale_risk_refresh",
        "event_context_refresh",
        "manual_operator_refresh_fallback",
    ]
    for run_type in run_types:
        report = run_smoke(run_type)
        assert report["status"] == "pass"
        assert report["requested_run_type"] == run_type
        assert report["effective_run_type"] == run_type
        assert report["guardrails"]["paper_only"] is True
        assert report["guardrails"]["creates_orders"] is False
        assert report["guardrails"]["broker_connection"] is False
        assert report["manual_refresh_fallback_only"] is True
        assert report["contains_execution_wording"] is False


def test_smoke_invalid_run_type_falls_back_safely():
    report = run_smoke("invalid")
    assert report["status"] == "pass"
    assert report["effective_run_type"] == "post_close_daily_review"
    assert report["contains_execution_wording"] is False


def test_workflow_is_manual_only():
    text = Path('.github/workflows/backend-cadence-smoke.yml').read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'schedule:' not in text
