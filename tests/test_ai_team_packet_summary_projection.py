from src.ai_team_analysis_packet import (
    build_ai_team_analysis_packet,
    build_ai_team_packet_summary,
    build_latest_system_run_ai_team_packet_section,
)
from src.miniapp_data_provider import SupabaseLatestSystemRunMiniAppReadDataProvider


def test_build_ai_team_packet_summary_guardrails_and_bounded_fields():
    packet = build_ai_team_analysis_packet(
        ticker="0700.HK",
        as_of="2026-05-15",
        run_context={"run_id": "123", "run_type": "paper_daily_runner", "schedule_basis": "cron"},
        market_context={"signal_direction": "unknown", "price": "not_available"},
        paper_signal_context={"latest_signal": ""},
        risk_context={"risk_flags": ["unknown"]},
    )
    summary = build_ai_team_packet_summary(packet)
    assert summary["schema_version"] == "ai_team_analysis_packet_summary.v1"
    assert summary["paper_trade_only"] is True
    assert summary["decision_support_only"] is True
    assert summary["broker_connection"] is False
    assert summary["live_execution"] is False
    assert summary["real_money_execution"] is False
    assert summary["creates_orders"] is False
    assert summary["llm_generated"] is False
    assert summary["vendor_call_performed"] is False
    assert set(summary["slot_status_counts"].keys()) == {"ok", "partial", "missing", "unknown"}


def test_miniapp_provider_ai_team_packet_summary_unavailable_on_malformed_payload(monkeypatch):
    class _Client:
        pass

    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "summary_json": {"paper_trade_only": True, "ai_team_packet": "bad"}
        },
    )
    provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=_Client())
    result = provider.get_ai_team_packet_summary()
    assert result["status"] == "unavailable"
    assert result["paper_trade_only"] is True


def test_latest_system_run_ai_team_packet_section_uses_processed_ticker_counts():
    summary = build_latest_system_run_ai_team_packet_section(
        run_id=123,
        business_date="2026-05-15",
        run_type="paper_daily_runner",
        schedule_basis="daily_close",
        processed_tickers=5,
        successful_tickers=4,
        failed_tickers=1,
    )
    assert summary["covered_tickers"] == 5
    assert summary["status"] == "partial"
    assert summary["paper_trade_only"] is True
    assert summary["decision_support_only"] is True
