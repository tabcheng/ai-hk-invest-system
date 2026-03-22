import re

from src.telegram_operator import (
    _build_operator_message,
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

    assert "Command: /runs" in response
    assert "Status: completed." in response
    assert "- window_days: 5" in response
    assert "run_id=12" in response
    assert "status=SUCCESS" in response


def test_handle_runs_command_rejects_unauthorized_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-allowed")
    response = handle_telegram_operator_command(object(), _build_update("/runs", chat_id="chat-other"))
    assert "Command: /runs" in response
    assert "Status: unauthorized." in response


def test_handle_runs_command_unauthorized_malformed_label_is_html_escaped(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-allowed")
    response = handle_telegram_operator_command(object(), _build_update("/runs<bad>", chat_id="chat-other"))
    assert "Command: /runs&lt;bad&gt;" in response
    assert "Command: /runs<bad>" not in response


def test_handle_runs_command_internal_failure_malformed_label_is_html_escaped(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr("src.telegram_operator._parse_runs_days", lambda _text: (_ for _ in ()).throw(RuntimeError("boom")))
    response = handle_telegram_operator_command(object(), _build_update("/runs<bad>"))
    assert "Command: /runs&lt;bad&gt;" in response
    assert "Status: failed." in response
    assert "internal command processing error" in response
    assert "Command: /runs<bad>" not in response


def test_operator_message_header_fields_are_html_escaped():
    response = _build_operator_message(
        command_label="/cmd<bad>",
        status="failed<&>",
        result="done > now",
        reason="check <this> & retry",
        fields=[("sample", "ok")],
    )
    assert "Command: /cmd&lt;bad&gt;" in response
    assert "Status: failed&lt;&amp;&gt;." in response
    assert "Result: done &gt; now" in response
    assert "Reason: check &lt;this&gt; &amp; retry" in response
    assert "Command: /cmd<bad>" not in response


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
    assert "Command: /runs" in response
    assert "Status: no data." in response
    assert "Reason: no runs found in the last 7 day(s)" in response


def test_handle_runs_command_enforces_allowed_users_when_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1,u-2")
    monkeypatch.setattr("src.telegram_operator.list_recent_runs", lambda *_args, **_kwargs: [])

    allowed = handle_telegram_operator_command(object(), _build_update("/runs", user_id="u-2"))
    denied = handle_telegram_operator_command(object(), _build_update("/runs", user_id="u-9"))

    assert "Status: no data." in allowed
    assert "Status: unauthorized." in denied


def test_build_runs_command_message_handles_empty_rows():
    message = build_runs_command_message([], days=5)
    assert "Command: /runs" in message
    assert "Status: no data." in message
    assert "Reason: no runs found in the last 5 day(s)" in message


def test_handle_runs_command_returns_usage_on_invalid_parameter(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    response = handle_telegram_operator_command(object(), _build_update("/runs 99d"))
    assert "Command: /runs" in response
    assert "Status: failed." in response
    assert "Days must be between 1 and 30" in response


def test_handle_runs_command_returns_usage_on_malformed_tokens(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    response_text = handle_telegram_operator_command(object(), _build_update("/runs foo"))
    response_numeric_without_suffix = handle_telegram_operator_command(object(), _build_update("/runs 7"))
    assert "Command: /runs" in response_text
    assert "Status: failed." in response_text
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
    assert "/runner_status" in message
    assert "/risk_review [run_id]" in message
    assert "/help" in message
    assert "/h" in message


def test_help_message_avoids_telegram_html_placeholder_tags():
    message = build_help_command_message()
    assert re.search(r"<[a-zA-Z][^>]*>", message) is None


def test_handle_runs_command_invalid_parameter_message_is_html_safe(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    response_text = handle_telegram_operator_command(object(), _build_update("/runs foo"))
    assert "/runs [days]d" in response_text
    assert re.search(r"<[a-zA-Z][^>]*>", response_text) is None


def test_handle_help_command_rejects_unauthorized_chat(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-allowed")
    response = handle_telegram_operator_command(object(), _build_update("/help", chat_id="chat-other"))
    assert "Command: /help" in response
    assert "Status: unauthorized." in response


def test_handle_risk_review_command_allowlisted_user_and_valid_run_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_run_by_id",
        lambda _client, run_id: {"id": run_id, "status": "SUCCESS", "created_at": "2026-03-21T00:00:00+00:00"},
    )
    monkeypatch.setattr(
        "src.telegram_operator._get_paper_risk_review",
        lambda _client, run_id: {
            "run_id": run_id,
            "total_executed_buys": 2,
            "total_blocked_buys": 1,
            "total_warning_buys": 1,
            "per_ticker": {"0005.HK": [], "0700.HK": []},
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/risk_review 12345", user_id="u-1"))

    assert "Command: /risk_review" in response
    assert "Status: completed." in response
    assert "- run_id: 12345" in response
    assert "- executed_buys: 2" in response
    assert "- blocked_buys: 1" in response
    assert "- warning_buys: 1" in response
    assert "- tickers: 2" in response


def test_handle_risk_review_command_rejects_non_allowlisted_user(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1")

    response = handle_telegram_operator_command(object(), _build_update("/risk_review 12345", user_id="u-9"))

    assert "Status: unauthorized." in response


def test_handle_risk_review_command_returns_usage_when_run_id_missing(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")

    response = handle_telegram_operator_command(object(), _build_update("/risk_review"))

    assert "Command: /risk_review" in response
    assert "Status: failed." in response
    assert "Usage: /risk_review [run_id]" in response


def test_handle_risk_review_command_rejects_invalid_run_id_format(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")

    response = handle_telegram_operator_command(object(), _build_update("/risk_review abc"))

    assert "Command: /risk_review" in response
    assert "Status: failed." in response
    assert "Invalid run_id format" in response


def test_handle_risk_review_command_rejects_nonexistent_run(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr("src.telegram_operator.get_run_by_id", lambda _client, run_id: None)

    response = handle_telegram_operator_command(object(), _build_update("/risk_review 99999"))

    assert "Command: /risk_review" in response
    assert "Status: no data." in response
    assert "Reason: run_id not found. Use /runs to list recent runs" in response
    assert "- run_id: 99999" in response


def test_handle_risk_review_command_handles_execution_failure_without_stack_trace(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_run_by_id",
        lambda _client, run_id: {"id": run_id, "status": "SUCCESS", "created_at": "2026-03-21T00:00:00+00:00"},
    )

    def _raise_failure(_client, run_id):
        raise RuntimeError(f"simulated failure for run_id={run_id}")

    monkeypatch.setattr("src.telegram_operator._get_paper_risk_review", _raise_failure)

    response = handle_telegram_operator_command(object(), _build_update("/risk_review 1001"))

    assert "Command: /risk_review" in response
    assert "Status: failed." in response
    assert "internal review execution error" in response
    assert "simulated failure" not in response


def test_handle_risk_review_command_handles_run_lookup_failure_without_stack_trace(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")

    def _raise_lookup_failure(_client, run_id):
        raise RuntimeError(f"lookup failed for run_id={run_id}")

    monkeypatch.setattr("src.telegram_operator.get_run_by_id", _raise_lookup_failure)

    response = handle_telegram_operator_command(object(), _build_update("/risk_review 1002"))

    assert "Command: /risk_review" in response
    assert "Status: failed." in response
    assert "internal review execution error" in response
    assert "lookup failed" not in response


def test_handle_runner_status_command_allowlisted_user_success(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: {
            "id": 2001,
            "status": "SUCCESS",
            "created_at": "2026-03-21T12:00:00+00:00",
            "finished_at": "2026-03-21T12:00:05+00:00",
            "error_summary": None,
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/runner_status", user_id="u-1"))

    assert "Command: /runner_status" in response
    assert "Status: completed." in response
    assert "- runner_status: SUCCESS" in response
    assert "- run_id: 2001" in response
    assert "- started_at: 2026-03-21T12:00:00+00:00" in response
    assert "- finished_at: 2026-03-21T12:00:05+00:00" in response
    assert "- duration_seconds: 5.0" in response
    assert "- entrypoint: python -m src.daily_runner" in response
    assert "HKT 20:00" in response
    assert "- error_summary: None" in response


def test_handle_runner_status_command_rejects_unauthorized_caller(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setenv("TELEGRAM_OPERATOR_ALLOWED_USER_IDS", "u-1")

    response = handle_telegram_operator_command(object(), _build_update("/runner_status", user_id="u-9"))

    assert "Status: unauthorized." in response


def test_handle_runner_status_command_no_latest_summary(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr("src.telegram_operator.get_latest_run_execution_summary", lambda _client: None)

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "Command: /runner_status" in response
    assert "Status: no data." in response
    assert "no persisted daily runner summary available yet" in response


def test_handle_runner_status_command_failed_latest_summary_formatting(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: {
            "id": 3001,
            "status": "SUCCESS",
            "created_at": "not-a-time",
            "finished_at": "2026-03-21T12:00:05+00:00",
            "error_summary": None,
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "Command: /runner_status" in response
    assert "Status: failed." in response
    assert "latest summary formatting error" in response
    assert "not-a-time" not in response


def test_handle_runner_status_command_lookup_failure_path(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")

    def _raise_lookup_failure(_client):
        raise RuntimeError("db timeout")

    monkeypatch.setattr("src.telegram_operator.get_latest_run_execution_summary", _raise_lookup_failure)

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "Command: /runner_status" in response
    assert "Status: failed." in response
    assert "internal status lookup error" in response
    assert "db timeout" not in response


def test_handle_runner_status_command_normalizes_naive_timestamps_as_utc(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: {
            "id": 3002,
            "status": "SUCCESS",
            "created_at": "2026-03-21T12:00:00",
            "finished_at": "2026-03-21T12:00:07",
            "error_summary": None,
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "- started_at: 2026-03-21T12:00:00+00:00" in response
    assert "- finished_at: 2026-03-21T12:00:07+00:00" in response
    assert "- duration_seconds: 7.0" in response


def test_handle_runner_status_command_escapes_error_summary_for_html_safety(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: {
            "id": 3003,
            "status": "FAILED",
            "created_at": "2026-03-21T12:00:00+00:00",
            "finished_at": "2026-03-21T12:00:02+00:00",
            "error_summary": "ValueError: bad <tag> & broken > parser",
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "- error_summary: ValueError: bad &lt;tag&gt; &amp; broken &gt; parser" in response
    assert "<tag>" not in response
    assert " & broken > " not in response


def test_handle_runner_status_command_escapes_other_dynamic_fields_for_html_safety(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: {
            "id": "run<&>01",
            "status": "FAILED<&>",
            "created_at": "2026-03-21T12:00:00+00:00",
            "finished_at": "2026-03-21T12:00:03+00:00",
            "error_summary": None,
        },
    )

    response = handle_telegram_operator_command(object(), _build_update("/runner_status"))

    assert "- run_id: run&lt;&amp;&gt;01" in response
    assert "- runner_status: FAILED&lt;&amp;&gt;" in response
    assert "- run_id: run<&>01" not in response
    assert "- runner_status: FAILED<&>" not in response


def test_operator_command_responses_share_consistent_shape(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr("src.telegram_operator.list_recent_runs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("src.telegram_operator.get_latest_run_execution_summary", lambda _client: None)
    monkeypatch.setattr("src.telegram_operator.get_run_by_id", lambda _client, run_id: None)

    responses = [
        handle_telegram_operator_command(object(), _build_update("/runs")),
        handle_telegram_operator_command(object(), _build_update("/runner_status")),
        handle_telegram_operator_command(object(), _build_update("/risk_review 1001")),
    ]

    for response in responses:
        assert "Command: /" in response
        assert "Status:" in response
