from src.ai_team_operating_model import build_ai_team_operating_model_v1


def test_operating_model_has_bounded_status_and_guardrails():
    model = build_ai_team_operating_model_v1()
    assert model["status"] == "ok"
    assert model["read_only"] is True
    assert model["paper_trade_only"] is True
    assert model["no_broker_execution"] is True
    assert model["no_live_execution"] is True
    assert model["no_real_money_execution"] is True
    allowed = {"working", "working_basic", "partial", "deferred"}
    assert model["desks"]
    for desk in model["desks"]:
        assert desk["status"] in allowed


def test_operating_model_contains_no_sensitive_terms():
    model = build_ai_team_operating_model_v1()
    text = str(model).lower()
    assert "supabase_service_role_key" not in text
    assert "supabase_secret_key" not in text
    assert "telegram bot token" not in text
    assert "initdata" not in text
    assert "allowlist" not in text
