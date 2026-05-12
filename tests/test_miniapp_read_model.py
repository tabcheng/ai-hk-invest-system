from datetime import datetime, timezone

from src.miniapp_read_model import (
    build_miniapp_review_shell_response,
    build_runtime_status_section,
    build_stock_dossiers_v1_section,
)


def test_runtime_status_allowlisted_safe_fields_only():
    env = {
        "RAILWAY_SERVICE_NAME": "telegram-webhook",
        "RAILWAY_ENVIRONMENT_NAME": "production",
        "RAILWAY_GIT_BRANCH": "main",
        "RAILWAY_GIT_COMMIT_SHA": "abcdef1234567890abcdef",
        "RAILWAY_DEPLOYMENT_ID": "dep-123",
        "SUPABASE_SERVICE_ROLE_KEY": "must_not_appear",
        "TELEGRAM_BOT_TOKEN": "must_not_appear",
    }
    section = build_runtime_status_section(env)

    assert set(section.keys()) == {
        "status",
        "source",
        "service_name",
        "environment",
        "git_branch",
        "git_commit_sha_short",
        "deployment_id_present",
        "generated_at_hkt",
    }
    assert section["status"] == "ok"
    assert section["source"] == "railway_runtime_env"
    assert section["git_commit_sha_short"] == "abcdef123456"
    assert section["deployment_id_present"] is True


def test_runtime_status_missing_values_are_bounded_unknown():
    now = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)
    section = build_runtime_status_section({}, now=now)
    assert section["status"] == "unknown"
    assert section["service_name"] is None
    assert section["git_commit_sha_short"] is None
    assert section["deployment_id_present"] is False
    assert section["generated_at_hkt"] == "2026-05-02T20:00:00+08:00"


def test_runtime_status_commit_sha_is_safely_bounded():
    section = build_runtime_status_section({"RAILWAY_GIT_COMMIT_SHA": " a!b@c#1234567890xyz "})
    assert section["git_commit_sha_short"] == "abc123456789"


def test_default_latest_system_run_is_unavailable_contract():
    payload = build_miniapp_review_shell_response(operator={"telegram_user_id": 42})

    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run == {
        "status": "unavailable",
        "source": "not_configured",
        "run_id": None,
        "run_status": None,
        "started_at_hkt": None,
        "completed_at_hkt": None,
        "data_timestamp_hkt": None,
        "summary": None,
        "limitations": ["No production data source configured in Step 86."],
    }
    daily_review_summary = payload["sections"]["daily_review_summary"]
    assert daily_review_summary["status"] == "unavailable"
    assert daily_review_summary["source"] == "daily_review_read_model"
    assert payload["sections"]["decision_context_summary"]["status"] == "unavailable"


def test_review_shell_response_guardrails_and_mock_sections():
    now = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)
    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"RAILWAY_SERVICE_NAME": "svc"},
        now=now,
    )

    assert payload["guardrails"]["read_only"] is True
    assert payload["guardrails"]["paper_trade_only"] is True
    assert payload["guardrails"]["decision_support_only"] is True
    assert payload["sections"]["daily_review"]["status"] == "mock"
    assert payload["sections"]["pnl_snapshot"]["status"] == "mock"
    assert payload["sections"]["outcome_review"]["status"] == "mock"
    assert "latest_system_run" in payload["sections"]


def test_review_shell_response_does_not_dump_arbitrary_env_or_secrets():
    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={
            "RAILWAY_SERVICE_NAME": "telegram-webhook",
            "SUPABASE_SERVICE_ROLE_KEY": "super-secret",
            "TELEGRAM_BOT_TOKEN": "never-expose",
        },
    )
    serialized = str(payload)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in serialized
    assert "super-secret" not in serialized
    assert "TELEGRAM_BOT_TOKEN" not in serialized


def test_provider_injection_can_override_runtime_status_and_latest_system_run():
    class _StubProvider:
        def get_runtime_status_summary(self):
            return {"status": "ok", "source": "stub_runtime"}

        def get_latest_system_run_summary(self):
            return {
                "status": "ok",
                "source": "stub_system_run",
                "run_id": 86,
                "run_status": "success",
                "started_at_hkt": "2026-05-02T08:00:00+08:00",
                "completed_at_hkt": "2026-05-02T08:05:00+08:00",
                "data_timestamp_hkt": "2026-05-02T08:05:00+08:00",
                "summary": "stub",
                "limitations": [],
            }
        def get_daily_review_summary(self):
            return {"status": "ok", "source": "stub_daily_review", "paper_trade_only": True}
        def get_signals_summary(self):
            return {"status": "unavailable", "source": "stub_signals"}
        def get_paper_pnl_summary(self):
            return {"status": "unavailable", "source": "stub_pnl"}
        def get_risk_summary(self):
            return {"status": "unavailable", "source": "stub_risk"}
        def get_decision_context_summary(self):
            return {"status": "partial", "source": "stub_decision_context"}
        def get_ticker_level_paper_portfolio_review(self):
            return {"status": "ok", "source": "stub_ticker_portfolio", "paper_trade_only": True, "rows": []}

    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        provider=_StubProvider(),
    )

    assert payload["sections"]["runner_status"] == {"status": "ok", "source": "stub_runtime"}
    assert payload["sections"]["latest_system_run"]["source"] == "stub_system_run"
    assert payload["sections"]["latest_system_run"]["run_id"] == 86
    assert payload["sections"]["daily_review_summary"]["source"] == "stub_daily_review"
    assert payload["sections"]["signals_summary"]["source"] == "stub_signals"
    assert payload["sections"]["paper_pnl_summary"]["source"] == "stub_pnl"
    assert payload["sections"]["risk_summary"]["source"] == "stub_risk"
    assert payload["sections"]["decision_context_summary"]["source"] == "stub_decision_context"
    assert payload["sections"]["ticker_level_paper_portfolio_review"]["source"] == "stub_ticker_portfolio"
    assert payload["sections"]["ticker_level_paper_portfolio_review"]["paper_trade_only"] is True


def test_local_artifact_provider_reads_latest_system_run_summary(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text(
        """
{
  "run_id": 87,
  "run_status": "success",
  "started_at_hkt": "2026-05-02T20:00:00+08:00",
  "completed_at_hkt": "2026-05-02T20:05:00+08:00",
  "data_timestamp_hkt": "2026-05-02T20:05:00+08:00",
  "summary": "Bounded local artifact summary."
}
""".strip(),
        encoding="utf-8",
    )

    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )

    assert payload["sections"]["latest_system_run"] == {
        "status": "ok",
        "source": "local_artifact",
        "run_id": "87",
        "run_status": "success",
        "started_at_hkt": "2026-05-02T20:00:00+08:00",
        "completed_at_hkt": "2026-05-02T20:05:00+08:00",
        "data_timestamp_hkt": "2026-05-02T20:05:00+08:00",
        "summary": "Bounded local artifact summary.",
        "limitations": [],
    }


def test_local_artifact_provider_returns_unavailable_when_artifact_invalid(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text("{invalid", encoding="utf-8")

    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "unavailable"
    assert latest_system_run["source"] == "local_artifact"


def test_local_artifact_provider_returns_unavailable_when_root_not_object(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text('["not-an-object"]', encoding="utf-8")

    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "unavailable"
    assert latest_system_run["source"] == "local_artifact"


def test_local_artifact_provider_returns_unavailable_when_run_id_invalid_type(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text('{"run_id":true,"run_status":"success"}', encoding="utf-8")

    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "unavailable"
    assert latest_system_run["source"] == "local_artifact"


def test_local_artifact_provider_returns_unavailable_when_oversized(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text("x" * (16 * 1024 + 1), encoding="utf-8")
    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "unavailable"
    assert latest_system_run["source"] == "local_artifact"


def test_local_artifact_provider_returns_unavailable_when_run_status_invalid(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text('{"run_id":87,"run_status":"completed"}', encoding="utf-8")
    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "unavailable"
    assert latest_system_run["source"] == "local_artifact"


def test_local_artifact_provider_bounds_long_fields_and_ignores_extra_fields(tmp_path):
    artifact = tmp_path / "latest_system_run.json"
    artifact.write_text(
        (
            "{"
            '"run_id":"%s",'
            '"run_status":"success",'
            '"started_at_hkt":"%s",'
            '"completed_at_hkt":"%s",'
            '"data_timestamp_hkt":"%s",'
            '"summary":"%s",'
            '"limitations":["%s","%s","%s","%s","%s","%s"],'
            '"SUPABASE_SERVICE_ROLE_KEY":"secret-a",'
            '"TELEGRAM_BOT_TOKEN":"secret-b",'
            '"broker_api_key":"secret-c"'
            "}"
        )
        % (
            "r" * 200,
            "t" * 90,
            "u" * 90,
            "v" * 90,
            "s" * 900,
            "l1" * 100,
            "l2" * 100,
            "l3" * 100,
            "l4" * 100,
            "l5" * 100,
            "l6" * 100,
        ),
        encoding="utf-8",
    )
    payload = build_miniapp_review_shell_response(
        operator={"telegram_user_id": 42},
        env={"MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH": str(artifact)},
    )
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] == "ok"
    assert len(latest_system_run["run_id"]) == 80
    assert len(latest_system_run["started_at_hkt"]) == 40
    assert len(latest_system_run["completed_at_hkt"]) == 40
    assert len(latest_system_run["data_timestamp_hkt"]) == 40
    assert len(latest_system_run["summary"]) == 500
    assert len(latest_system_run["limitations"]) == 5
    assert all(len(item) <= 160 for item in latest_system_run["limitations"])
    serialized = str(latest_system_run)
    assert "SUPABASE_SERVICE_ROLE_KEY" not in serialized
    assert "TELEGRAM_BOT_TOKEN" not in serialized
    assert "broker_api_key" not in serialized


def test_review_shell_includes_ticker_level_portfolio_section_and_read_only_guardrails():
    payload = build_miniapp_review_shell_response(operator={"telegram_user_id": 42})
    section = payload["sections"]["ticker_level_paper_portfolio_review"]
    assert section["status"] in {"ok", "unavailable"}
    assert "rows" in section
    assert payload["guardrails"]["read_only"] is True
    assert payload["guardrails"]["paper_trade_only"] is True
    assert payload["guardrails"]["no_real_money_execution"] is True
    serialized = str(payload)
    assert "EODHD_API_TOKEN" not in serialized
    assert "raw_payload" not in serialized.lower()

def test_stock_dossier_positive_low_risk():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "risk": {"risk_level": "low"}}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 100, "total_pnl": 12.3}]},
    )
    item = section["items"][0]
    assert item["ticker"] == "0700.HK"
    assert "偏正面觀察" in item["simulated_direction"]


def test_stock_dossier_neutral_medium_risk():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0005.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "medium"},
        {"status": "ok", "tickers": [{"ticker": "0005.HK", "risk": {"risk_level": "medium"}}]},
        {"status": "ok", "rows": []},
    )
    assert "繼續觀察" in section["items"][0]["simulated_direction"]


def test_stock_dossier_negative_high_risk_and_unknown_source_fallback():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0011.HK", "signal": "negative"}]},
        {"status": "ok", "risk_level": "high"},
        {"status": "ok", "tickers": [{"ticker": "0011.HK", "risk": {"risk_level": "high"}}]},
        {"status": "ok", "rows": []},
    )
    item = section["items"][0]
    assert "偏審慎觀察" in item["simulated_direction"]
    assert "風險較高" in item["risk_brief"]


def test_stock_dossier_includes_context_ticker_when_signal_ticker_missing():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "", "signal": "positive"}]},
        {"status": "unavailable"},
        {"status": "ok", "tickers": [{"ticker": "0388.HK", "risk": {"risk_level": "unknown"}}]},
        {"status": "ok", "rows": []},
    )
    assert section["items"][0]["ticker"] == "0388.HK"
    assert "資料不足" in section["items"][0]["data_sufficiency"]


def test_stock_dossier_has_no_execution_wording_in_english_or_chinese():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": []},
        {"status": "ok", "rows": []},
    )
    serialized = str(section)
    for forbidden in [
        "Buy now", "Sell now", "Execute", "Order", "Trade action",
        "立即落盤", "真實買入", "真實賣出", "建立訂單", "下單指令",
    ]:
        assert forbidden not in serialized
