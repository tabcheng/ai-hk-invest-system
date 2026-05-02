from datetime import datetime, timezone

from src.miniapp_read_model import (
    build_miniapp_review_shell_response,
    build_runtime_status_section,
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


def test_review_shell_response_does_not_dump_arbitrary_env():
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
