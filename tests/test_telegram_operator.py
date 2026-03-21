from src.telegram_operator import (
    build_help_command_message,
    build_runs_command_message,
    handle_telegram_operator_command,
)


def _build_update(text: str, *, chat_id: str = "chat-1", user_id: str = "u-1") -> dict:
    return {"message": {"text": text, "chat": {"id": chat_id}, "from": {"id": user_id}}}


def test_handle_runs_command_defaults_to_5d(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.delenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", raising=False)
    monkeypatch.setattr(
        "src.telegram_operator.list_recent_runs",
        lambda _client, days, limit: [
            {"id": 12, "status": "SUCCESS", "created_at": "2026-03-20T01:02:03+00:00"}
        ],
    )

    response = handle_telegram_operator_command(object(), _build_update("/runs"))

    assert "last 5 day(s)" in response
    assert "run_id=12" in response
    assert "status=SUCCESS" in response


def test_handle_runs_command_rejects_unauthorized_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-allowed")
    response = handle_telegram_operator_command(object(), _build_update("/runs", chat_id="chat-other"))
    assert "Unauthorized" in response


def test_handle_runs_command_supports_days_parameter(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    seen = {}

    def _fake_list(_client, days, limit):
        seen["days"] = days
        seen["limit"] = limit
        return []

    monkeypatch.setattr("src.telegram_operator.list_recent_runs", _fake_list)
    response = handle_telegram_operator_command(object(), _build_update("/runs 7d"))

    assert seen["days"] == 7
    assert "No runs found in the last 7 day(s)." == response


def test_handle_runs_command_enforces_allowed_users_when_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1,u-2")
    monkeypatch.setattr("src.telegram_operator.list_recent_runs", lambda *_args, **_kwargs: [])

    allowed = handle_telegram_operator_command(object(), _build_update("/runs", user_id="u-2"))
    denied = handle_telegram_operator_command(object(), _build_update("/runs", user_id="u-9"))

    assert allowed == "No runs found in the last 5 day(s)."
    assert "Unauthorized" in denied


def test_build_runs_command_message_handles_empty_rows():
    assert build_runs_command_message([], days=5) == "No runs found in the last 5 day(s)."


def test_handle_runs_command_returns_usage_on_invalid_parameter(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    response = handle_telegram_operator_command(object(), _build_update("/runs 99d"))
    assert "Days must be between 1 and 30" in response


def test_handle_runs_command_returns_usage_on_malformed_tokens(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    response_text = handle_telegram_operator_command(object(), _build_update("/runs foo"))
    response_numeric_without_suffix = handle_telegram_operator_command(object(), _build_update("/runs 7"))
    assert "Unsupported command" in response_text
    assert "Unsupported command" in response_numeric_without_suffix


def test_handle_help_and_h_alias_return_same_message(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    help_response = handle_telegram_operator_command(object(), _build_update("/help"))
    alias_response = handle_telegram_operator_command(object(), _build_update("/h"))
    assert help_response == alias_response == build_help_command_message()


def test_help_message_contains_guardrails_and_command_list():
    message = build_help_command_message()
    assert "AI HK Investment System" in message
    assert "paper trading" in message
    assert "human makes final decision" in message
    assert "no real-money auto execution" in message
    assert "/runs" in message
    assert "/runs [days]d" in message
    assert "/help" in message
    assert "/h" in message


def test_help_message_avoids_telegram_html_placeholder_tags():
    message = build_help_command_message()
    assert "<days>" not in message
    assert "<run_id>" not in message


def test_handle_help_command_rejects_unauthorized_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-allowed")
    response = handle_telegram_operator_command(object(), _build_update("/help", chat_id="chat-other"))
    assert "Unauthorized" in response
