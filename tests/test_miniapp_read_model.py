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


def test_stock_dossier_horizon_policy_short_term_observation_only():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "unknown"}]},
        {"status": "ok", "risk_level": "unknown"},
        {"status": "unavailable", "tickers": []},
        {"status": "ok", "rows": []},
    )
    item = section["items"][0]
    assert item["strategy_horizon_policy"]["short_term_policy"].startswith("短線：只供觀察")
    assert item["strategy_horizon_policy"]["paper_decision_scope"] == "observation_only"
    assert "短線只供觀察" in item["simulated_direction"]


def test_stock_dossier_horizon_policy_medium_sufficient_recommend_medium():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
    )
    policy = section["items"][0]["strategy_horizon_policy"]
    assert policy["recommended_review_horizon"] == "medium"
    assert policy["medium_term_data_state"] == "sufficient"


def test_stock_dossier_horizon_policy_not_sufficient_when_global_ok_but_ticker_context_missing():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0005.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 2, "total_pnl": 10}]},
    )
    policy = section["items"][0]["strategy_horizon_policy"]
    assert policy["recommended_review_horizon"] != "medium"
    assert policy["medium_term_data_state"] != "sufficient"
    assert "缺少個股層級脈絡資料" in policy["horizon_data_gaps"]


def test_stock_dossier_horizon_policy_sufficient_when_matching_ticker_context_exists():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0388.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "medium"},
        {"status": "partial", "tickers": [{"ticker": "0388.HK", "context_readiness": "basic"}]},
        {"status": "ok", "rows": [{"ticker": "0388.HK", "quantity": 1, "total_pnl": 0}]},
    )
    policy = section["items"][0]["strategy_horizon_policy"]
    assert policy["recommended_review_horizon"] == "medium"
    assert policy["medium_term_data_state"] == "sufficient"


def test_stock_dossier_horizon_policy_long_term_gap_visible():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "medium"},
        {"status": "partial", "tickers": []},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 2, "total_pnl": 11}]},
    )
    policy = section["items"][0]["strategy_horizon_policy"]
    assert policy["long_term_data_state"] == "insufficient"
    assert "缺少基本面資料" in policy["horizon_data_gaps"]


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
    assert item["simulated_direction"] == "偏正面觀察"
    assert "AI 模擬方向：" not in item["simulated_direction"]
    assert item["portfolio_context"] == "持倉=100，總盈虧=12.3。"


def test_stock_dossier_neutral_medium_risk():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0005.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "medium"},
        {"status": "ok", "tickers": [{"ticker": "0005.HK", "risk": {"risk_level": "medium"}}]},
        {"status": "ok", "rows": []},
    )
    assert section["items"][0]["simulated_direction"] == "繼續觀察"


def test_stock_dossier_negative_high_risk_and_unknown_source_fallback():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0011.HK", "signal": "negative"}]},
        {"status": "ok", "risk_level": "high"},
        {"status": "ok", "tickers": [{"ticker": "0011.HK", "risk": {"risk_level": "high"}}]},
        {"status": "ok", "rows": []},
    )
    item = section["items"][0]
    assert item["simulated_direction"] == "偏審慎觀察"
    assert "風險較高" in item["risk_brief"]
    assert item["portfolio_context"] == "未有持倉資料。"


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
        "立即落盤", "真實買入", "真實賣出", "下單指令", "請建立訂單", "立即建立訂單", "建立訂單：",
    ]:
        assert forbidden not in serialized
    assert "不建立訂單" in serialized


def test_stock_dossier_exposes_backend_data_gap_action_contract():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "unknown"}]},
        {"status": "ok", "risk_level": "unknown"},
        {"status": "unavailable", "tickers": []},
        {"status": "ok", "rows": []},
        latest_system_run={"market_data_status": "stale"},
    )
    item = section["items"][0]
    assert item["data_gap_action_source"] == "backend_read_model"
    assert isinstance(item["data_gap_actions"], list) and item["data_gap_actions"]
    assert item["data_gap_interpretation_summary"].startswith("解讀限制：")
    assert all(action["review_only"] is True for action in item["data_gap_actions"])
    assert all("target_surface" in action for action in item["data_gap_actions"])
    assert all("target_surface_label" in action for action in item["data_gap_actions"])
    assert all("action_type" in action for action in item["data_gap_actions"])
    assert all("confidence_effect" in action for action in item["data_gap_actions"])
    assert all("priority" in action for action in item["data_gap_actions"])
    assert all("operator_hint" in action for action in item["data_gap_actions"])
    categories = {action["category"] for action in item["data_gap_actions"]}
    assert "ticker_decision_context" in categories
    assert "market_freshness" in categories


def test_stock_dossier_market_freshness_gap_uses_market_fields_only():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
        latest_system_run={"market_data_status": "ok", "freshness_status": "ok", "market_data_acceptance_status": "ok"},
    )
    categories = {action["category"] for action in section["items"][0]["data_gap_actions"]}
    assert "market_freshness" not in categories


def test_stock_dossier_market_freshness_gap_acceptance_status_stale_variant():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
        latest_system_run={"market_data_acceptance_status": "stale_do_not_use_for_intraday"},
    )
    categories = {action["category"] for action in section["items"][0]["data_gap_actions"]}
    assert "market_freshness" in categories


def test_stock_dossier_market_freshness_gap_acceptance_status_caution_last_close():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
        latest_system_run={"market_data_acceptance_status": "caution_last_available_close"},
    )
    categories = {action["category"] for action in section["items"][0]["data_gap_actions"]}
    assert "market_freshness" in categories


def test_stock_dossier_market_freshness_gap_acceptance_status_acceptable_for_paper_review_not_stale():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
        latest_system_run={"market_data_acceptance_status": "acceptable_for_paper_review"},
    )
    categories = {action["category"] for action in section["items"][0]["data_gap_actions"]}
    assert "market_freshness" not in categories


def test_stock_dossier_market_freshness_gap_when_acceptable_for_paper_review_but_freshness_stale():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "ready"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
        latest_system_run={
            "market_data_acceptance_status": "acceptable_for_paper_review",
            "freshness_status": "stale",
        },
    )
    categories = {action["category"] for action in section["items"][0]["data_gap_actions"]}
    assert "market_freshness" in categories


def test_stock_dossier_data_gap_actions_no_execution_wording():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "unknown"}]},
        {"status": "ok", "risk_level": "unknown"},
        {"status": "unavailable", "tickers": []},
        {"status": "ok", "rows": []},
        latest_system_run={"market_data_status": "delayed"},
    )
    payload = str(section["items"][0]["data_gap_actions"])
    for forbidden in ["立即買入", "立即賣出", "馬上落盤", "立即執行", "Buy now", "Sell now", "Execute now", "Place order", "Trade action"]:
        assert forbidden not in payload


def test_stock_dossier_ticker_context_insufficient_maps_to_ticker_decision_context():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": [{"ticker": "0700.HK", "context_readiness": "insufficient"}]},
        {"status": "ok", "rows": [{"ticker": "0700.HK", "quantity": 1, "total_pnl": 0}]},
    )
    category_to_label = {row["category"]: row["label"] for row in section["items"][0]["data_gap_actions"]}
    assert category_to_label["ticker_decision_context"] == "先補看：最近模擬決策日誌、決策脈絡或結果"


def test_stock_dossier_data_gap_routing_mapping_fields():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "unknown"}]},
        {"status": "ok", "risk_level": "unknown"},
        {"status": "unavailable", "tickers": []},
        {"status": "ok", "rows": []},
        latest_system_run={"market_data_status": "stale"},
    )
    mapping = {row["category"]: row for row in section["items"][0]["data_gap_actions"]}
    assert mapping["market_freshness"]["target_surface"] == "system_market_data"
    assert mapping["market_freshness"]["confidence_effect"] == "blocks_short_term"
    assert mapping["fundamentals"]["target_surface"] == "external_authorized_research"
    assert mapping["fundamentals"]["confidence_effect"] == "caps_long_term"
    assert mapping["valuation"]["target_surface"] == "external_authorized_research"
    assert mapping["cashflow_earnings_balance_sheet"]["target_surface"] == "external_authorized_research"
    assert mapping["source_confidence"]["target_surface"] == "operator_review"
    assert mapping["source_confidence"]["confidence_effect"] == "watch_only"
