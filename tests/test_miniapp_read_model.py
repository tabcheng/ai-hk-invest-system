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
    }
    section = build_runtime_status_section(env)
    assert section["status"] == "ok"
    assert section["git_commit_sha_short"] == "abcdef123456"


def test_review_shell_response_guardrails_and_stock_dossier_section():
    now = datetime(2026, 5, 2, 12, 0, tzinfo=timezone.utc)
    payload = build_miniapp_review_shell_response(operator={"telegram_user_id": 42}, now=now)
    assert payload["guardrails"]["read_only"] is True
    assert payload["guardrails"]["paper_trade_only"] is True
    assert payload["sections"]["stock_dossier_review"]["source"] == "stock_dossier_v1_read_model"


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
    assert "資料足夠" in item["data_sufficiency"]


def test_stock_dossier_neutral_medium_risk():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0005.HK", "signal": "neutral"}]},
        {"status": "ok", "risk_level": "medium"},
        {"status": "ok", "tickers": [{"ticker": "0005.HK", "risk": {"risk_level": "medium"}}]},
        {"status": "ok", "rows": []},
    )
    item = section["items"][0]
    assert "繼續觀察" in item["simulated_direction"]
    assert "風險中等" in item["risk_brief"]


def test_stock_dossier_negative_high_risk():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0011.HK", "signal": "negative"}]},
        {"status": "ok", "risk_level": "high"},
        {"status": "ok", "tickers": [{"ticker": "0011.HK", "risk": {"risk_level": "high"}}]},
        {"status": "ok", "rows": []},
    )
    item = section["items"][0]
    assert "偏審慎觀察" in item["simulated_direction"]
    assert "風險較高" in item["risk_brief"]


def test_stock_dossier_missing_ticker_context_and_unknown_data():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "", "signal": "positive"}]},
        {"status": "unavailable"},
        {"status": "ok", "tickers": [{"ticker": "0388.HK", "risk": {"risk_level": "unknown"}}]},
        {"status": "ok", "rows": [{"ticker": "0388.HK", "quantity": 0, "total_pnl": 0}]},
    )
    assert len(section["items"]) == 1
    item = section["items"][0]
    assert item["ticker"] == "0388.HK"
    assert "資料不足" in item["data_sufficiency"]


def test_stock_dossier_has_no_execution_wording():
    section = build_stock_dossiers_v1_section(
        {"status": "ok", "top_items": [{"ticker": "0700.HK", "signal": "positive"}]},
        {"status": "ok", "risk_level": "low"},
        {"status": "ok", "tickers": []},
        {"status": "ok", "rows": []},
    )
    serialized = str(section)
    for forbidden in ["Buy now", "Sell now", "Execute", "Order", "Trade action"]:
        assert forbidden not in serialized
