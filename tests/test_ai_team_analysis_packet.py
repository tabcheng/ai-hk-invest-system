from src.ai_team_analysis_packet import build_ai_team_analysis_packet


def _base_run(run_type="post_close_daily_review", include_schedule_basis=True):
    payload = {
        "run_id": "56",
        "run_type": run_type,
        "data_timestamp": "2026-05-15T09:38:50Z",
        "source": "paper_daily_runner",
    }
    if include_schedule_basis:
        payload["schedule_basis"] = "custom"
    return payload


def test_full_packet_sample_contexts():
    packet = build_ai_team_analysis_packet(
        ticker="0700.HK",
        as_of="2026-05-15",
        run_context=_base_run(),
        market_context={"signal_direction": "up", "price": 500.0, "data_timestamp": "2026-05-15T09:30:00Z", "freshness": "delayed"},
        paper_signal_context={"latest_signal": "HOLD", "reason": "mixed trend", "duplicate_protection_state": "triggered"},
        risk_context={"risk_flags": ["volatility"], "liquidity_flag": "ok", "freshness_flag": "delayed", "data_gap_flag": "none"},
    )
    assert packet["schema_version"] == "ai_team_analysis_packet.v1"
    assert packet["decision_support"]["simulated_direction"] in {"watch_only", "mixed_watch", "insufficient_data"}
    assert packet["guardrails"]["paper_only"] is True


def test_missing_market_data_produces_insufficient_or_partial_state():
    packet = build_ai_team_analysis_packet(
        ticker="0700.HK",
        as_of="2026-05-15",
        run_context=_base_run(),
        market_context=None,
        paper_signal_context={"latest_signal": "HOLD"},
        risk_context={"risk_flags": ["unknown"]},
    )
    assert packet["market_context"]["price"] == "not_available"
    assert packet["decision_support"]["simulated_direction"] in {"watch_only", "insufficient_data"}
    assert "market_context_missing" in packet["ai_team_slots"]["market_data_analyst"]["gaps"]


def test_missing_journal_outcome_is_explicit():
    packet = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run())
    assert packet["journal_context"]["status"] == "not_available"
    assert packet["outcome_context"]["status"] == "not_available"


def test_guardrails_and_flags_hardcoded_safe():
    packet = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run())
    assert packet["guardrails"]["broker_connection"] is False
    assert packet["guardrails"]["live_execution"] is False
    assert packet["guardrails"]["real_money_execution"] is False
    assert packet["guardrails"]["llm_generated"] is False
    assert packet["guardrails"]["vendor_call_performed"] is False


def test_no_execution_wording_in_user_facing_fields():
    packet = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run())
    text_fields = [packet["decision_support"]["simulated_direction"], *packet["decision_support"]["operator_next_steps"]]
    banned = ["buy now", "sell now", "execute", "place order", "live trade"]
    lowered = " ".join(text_fields).lower()
    for token in banned:
        assert token not in lowered


def test_run_type_schedule_mappings_supported():
    midday = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run("midday_market_monitor"))
    stale = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run("stale_risk_refresh"))
    post = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run("post_close_daily_review"))
    assert midday["run_context"]["run_type"] == "midday_market_monitor"
    assert stale["run_context"]["run_type"] == "stale_risk_refresh"
    assert post["run_context"]["run_type"] == "post_close_daily_review"


def test_pre_market_and_event_context_schedule_basis_uses_canonical_runtime_mapping():
    pre_market = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run("pre_market_readiness_check", include_schedule_basis=False))
    event_context = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run("event_context_refresh", include_schedule_basis=False))

    assert pre_market["run_context"]["schedule_basis"] == "HKT around 08:45 weekday (Railway cron UTC: 45 0 * * 1-5)"
    assert event_context["run_context"]["schedule_basis"] == "Event-driven context refresh (Railway cron UTC: planned later)"


def test_confidence_downgrades_when_context_missing():
    packet = build_ai_team_analysis_packet("0700.HK", "2026-05-15", _base_run(), market_context=None, paper_signal_context=None, risk_context=None)
    assert packet["ai_team_slots"]["decision_advisor"]["status"] in {"blocked", "not_available"}
    assert packet["ai_team_slots"]["decision_advisor"]["confidence"] in {"low", "very_low"}
    assert packet["audit"]["packet_version"] == "v1"
    assert isinstance(packet["audit"]["source_refs"], list)


def test_mixed_watch_when_risk_and_non_bullish_market_signal():
    packet = build_ai_team_analysis_packet(
        "0700.HK",
        "2026-05-15",
        _base_run(),
        market_context={"signal_direction": "down", "price": 500.0},
        paper_signal_context={"latest_signal": "HOLD"},
        risk_context={"risk_flags": ["volatility", "freshness_gap"]},
    )
    assert packet["decision_support"]["simulated_direction"] == "mixed_watch"


def test_placeholder_values_are_treated_as_missing_context():
    packet = build_ai_team_analysis_packet(
        "0700.HK",
        "2026-05-15",
        _base_run(),
        market_context={"signal_direction": "not_available", "price": "unknown"},
        paper_signal_context={"latest_signal": "unknown", "reason": "n/a"},
        risk_context={"risk_flags": ["unknown"], "liquidity_flag": "n/a", "freshness_flag": "not_available", "data_gap_flag": "missing"},
    )
    assert packet["decision_support"]["simulated_direction"] == "insufficient_data"
    assert "market_context_missing" in packet["ai_team_slots"]["decision_advisor"]["gaps"]
    assert "paper_signal_missing" in packet["ai_team_slots"]["decision_advisor"]["gaps"]
    assert "risk_context_missing" in packet["ai_team_slots"]["decision_advisor"]["gaps"]
    assert packet["ai_team_slots"]["decision_advisor"]["status"] in {"blocked", "not_available"}


def test_risk_flags_unknown_only_does_not_count_as_valid_risk_context():
    packet = build_ai_team_analysis_packet(
        "0700.HK",
        "2026-05-15",
        _base_run(),
        market_context={"signal_direction": "down", "price": 500.0},
        paper_signal_context={"latest_signal": "HOLD"},
        risk_context={"risk_flags": ["unknown"]},
    )
    assert packet["decision_support"]["simulated_direction"] == "watch_only"
