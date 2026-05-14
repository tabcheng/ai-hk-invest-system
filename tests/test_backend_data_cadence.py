from src.backend_data_cadence import (
    RUN_TYPE_MANUAL_FALLBACK,
    RUN_TYPE_STALE_RISK,
    build_backend_data_cadence_policy,
    get_effective_run_type,
    plan_backend_auto_refreshes,
)


def test_policy_contains_required_run_types_and_guardrails():
    policy = build_backend_data_cadence_policy()
    run_types = {row["run_type"] for row in policy}
    assert "pre_market_readiness_check" in run_types
    assert "midday_market_monitor" in run_types
    assert "post_close_daily_review" in run_types
    assert "stale_risk_refresh" in run_types
    assert "event_context_refresh" in run_types
    assert RUN_TYPE_MANUAL_FALLBACK in run_types
    assert all(row["paper_only"] is True and row["creates_orders"] is False and row["broker_connection"] is False for row in policy)
    manual = [row for row in policy if row["run_type"] == RUN_TYPE_MANUAL_FALLBACK][0]
    assert manual["manual_fallback_only"] is True


def test_default_run_type_safe_default():
    assert get_effective_run_type({}) == "post_close_daily_review"
    assert get_effective_run_type({"AIHK_RUN_TYPE": "invalid"}) == "post_close_daily_review"


def test_planner_stale_and_context_candidates_and_bounded_deduped():
    plan = plan_backend_auto_refreshes(
        latest_system_run={"market_data_acceptance_status": "stale_do_not_use_for_intraday", "market_data_status": "unknown"},
        risk_summary={"risk_level": "unknown", "warnings": ["context insufficient"]},
        stock_dossier_items=[{"ticker": "0700.HK", "data_gap_actions": [{"category": "ticker_decision_context"}, {"category": "fundamentals"}, {"category": "fundamentals"}]}],
        max_items=5,
    )
    assert plan["manual_refresh_primary"] is False
    assert plan["manual_refresh_fallback_only"] is True
    triggers = {x["trigger"] for x in plan["items"]}
    assert "market_data_stale" in triggers
    assert "risk_context_insufficient" in triggers
    assert "ticker_decision_context_missing" in triggers
    assert len(plan["items"]) <= 5
    keys = {(x["run_type"], x["scope"], x["trigger"]) for x in plan["items"]}
    assert len(keys) == len(plan["items"])


def test_acceptable_for_paper_review_does_not_force_stale_trigger():
    plan = plan_backend_auto_refreshes(
        latest_system_run={"market_data_acceptance_status": "acceptable_for_paper_review"},
        risk_summary={"risk_level": "low", "warnings": []},
        stock_dossier_items=[],
    )
    assert "market_data_stale" not in {x["trigger"] for x in plan["items"]}


def test_no_execution_wording_in_output():
    plan = plan_backend_auto_refreshes(
        latest_system_run={"market_data_status": "delayed"},
        risk_summary={"risk_level": "unknown"},
        stock_dossier_items=[],
    )
    user_facing_text = " ".join(
        part
        for item in plan["items"]
        for part in (
            str(item.get("reason") or ""),
            str(item.get("operator_hint") or ""),
            str(item.get("target_surface_label") or ""),
            str(item.get("freshness_requirement") or ""),
        )
    ).lower()
    assert "buy" not in user_facing_text
    assert "sell" not in user_facing_text
    assert "order" not in user_facing_text
    assert "execute" not in user_facing_text
    assert all(x["creates_orders"] is False for x in plan["items"])
    assert all(x["broker_connection"] is False for x in plan["items"])
    assert all(x["paper_only"] is True for x in plan["items"])
    assert any(x["run_type"] == RUN_TYPE_STALE_RISK for x in plan["items"])
