import hashlib
import hmac
import io
import json
from urllib.parse import urlencode

from src.telegram_webhook_server import MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES, create_wsgi_app

FAKE_BOT_TOKEN = "123456:TEST_FAKE_BOT_TOKEN"
NOW_TS = 1_700_000_000


def _build_signed_init_data(fields: dict[str, str], *, bot_token: str) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items(), key=lambda item: item[0]))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": data_hash})


def _call(path: str, method: str, body: bytes, *, content_type: str | None = "application/json", origin: str | None = None):
    app = create_wsgi_app()
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    if content_type is not None:
        environ["CONTENT_TYPE"] = content_type
    if origin is not None:
        environ["HTTP_ORIGIN"] = origin
    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    raw_body = b"".join(response)
    if raw_body == b"":
        return captured["status"], dict(captured["headers"]), raw_body
    return captured["status"], dict(captured["headers"]), json.loads(raw_body.decode("utf-8"))


def _authorized_request(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42,99")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)
    init_data = _build_signed_init_data(
        {
            "auth_date": str(NOW_TS - 100),
            "query_id": "AAEAAAE",
            "user": '{"id":42,"username":"hk_operator"}',
        },
        bot_token=FAKE_BOT_TOKEN,
    )
    return json.dumps({"init_data": init_data}).encode()


def test_miniapp_review_shell_success_accepts_json_content_type(monkeypatch):
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    assert payload["status"] == "ok"


def test_miniapp_review_shell_success_accepts_json_charset_content_type(monkeypatch):
    status, _headers, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        _authorized_request(monkeypatch),
        content_type="application/json; charset=utf-8",
    )
    assert status.startswith("200")
    assert payload["status"] == "ok"


def test_miniapp_review_shell_success_runner_status_bounded_runtime_source(monkeypatch):
    monkeypatch.setenv("RAILWAY_SERVICE_NAME", "telegram-webhook")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_GIT_BRANCH", "main")
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abcdef1234567890")
    monkeypatch.setenv("RAILWAY_DEPLOYMENT_ID", "dep-1")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-do-not-expose")
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))

    assert status.startswith("200")
    runner_status = payload["sections"]["runner_status"]
    assert runner_status["source"] == "railway_runtime_env"
    assert runner_status["status"] in {"ok", "unknown"}
    assert runner_status["git_commit_sha_short"] == "abcdef123456"
    assert "SUPABASE_SERVICE_ROLE_KEY" not in json.dumps(payload)
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] in {"unavailable", "ok", "unknown"}
    if latest_system_run["status"] == "unavailable":
        assert latest_system_run["source"] in {"not_configured", "latest_system_runs"}



def test_miniapp_review_shell_rejects_missing_content_type():
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", b"{}", content_type=None)
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_non_json_content_type():
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", b"{}", content_type="text/plain")
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_unsupported_json_content_type_params(monkeypatch):
    body = _authorized_request(monkeypatch)
    status, _headers, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        body,
        content_type="application/json; charset=latin-1",
    )
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"

    status, _headers, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        body,
        content_type="application/json; version=1",
    )
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_oversized_payload():
    oversized = b"x" * (MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES + 1)
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", oversized)
    assert status.startswith("413")
    assert payload["error"] == "payload_too_large"


def test_miniapp_review_shell_failures(monkeypatch):
    status, _headers, payload = _call("/miniapp/api/review-shell", "GET", b"")
    assert status.startswith("405") and payload["error"] == "method_not_allowed"

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", b"{")
    assert status.startswith("400") and payload["error"] == "invalid_json"

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({}).encode())
    assert status.startswith("400") and payload["error"] == "missing_init_data"

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "x"}).encode())
    assert status.startswith("503") and payload["error"] == "miniapp_auth_config_unavailable"

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "true")
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "x"}).encode())
    assert status.startswith("503") and payload["error"] == "miniapp_operator_allowlist_unavailable"


def test_miniapp_review_shell_validation_and_authorization_failures(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "bad=payload"}).encode())
    assert status.startswith("401") and payload["error"] == "invalid_init_data"

    init_data = _build_signed_init_data(
        {"auth_date": str(NOW_TS - 50), "user": '{"id":99,"username":"other"}'},
        bot_token=FAKE_BOT_TOKEN,
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": init_data}).encode())
    assert status.startswith("403") and payload["error"] == "operator_not_authorized"


def test_miniapp_route_does_not_require_supabase_client(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: (_ for _ in ()).throw(RuntimeError("should_not_call")))
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)
    init_data = _build_signed_init_data(
        {"auth_date": str(NOW_TS - 1), "user": '{"id":42}'},
        bot_token=FAKE_BOT_TOKEN,
    )

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": init_data}).encode())
    assert status.startswith("200")
    assert payload["status"] == "ok"


def test_miniapp_review_shell_latest_system_run_ok(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Client: pass

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": "42",
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"processed_tickers": 3, "successful_tickers": 3, "failed_tickers": 0, "paper_trade_only": True},
        },
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["latest_system_run"]
    assert section["status"] == "ok"
    assert section["paper_trade_only"] is True
    assert section["data_timestamp_hkt"].endswith("HKT")
    assert section["updated_at_hkt"].endswith("HKT")
    assert "data_timestamp" not in section
    assert "updated_at" not in section


def test_miniapp_review_shell_latest_system_run_unavailable_on_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Client: pass

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr("src.latest_system_runs_repository.get_latest_system_run", lambda client, source="paper_daily_runner": (_ for _ in ()).throw(RuntimeError("secret error")))

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["latest_system_run"]
    assert section["status"] == "unavailable"
    assert section["reason"] == "latest bounded row is not available yet"
    assert "secret error" not in json.dumps(payload)


def test_miniapp_review_shell_latest_system_run_bad_counters_are_bounded(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Client: pass

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": "42",
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"processed_tickers": "N/A", "successful_tickers": "bad-value", "failed_tickers": None, "paper_trade_only": True},
        },
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["latest_system_run"]
    assert section["status"] == "ok"
    assert section["processed_tickers"] == 0
    assert section["successful_tickers"] == 0
    assert section["failed_tickers"] == 0


def test_miniapp_review_shell_cors_options_allowed_origin(monkeypatch):
    monkeypatch.setenv("MINIAPP_ALLOWED_ORIGIN", "https://miniapp.example.com")
    status, headers, payload = _call(
        "/miniapp/api/review-shell",
        "OPTIONS",
        b"",
        content_type=None,
        origin="https://miniapp.example.com",
    )
    assert status.startswith("204")
    assert payload == b""
    assert headers["Access-Control-Allow-Origin"] == "https://miniapp.example.com"
    assert headers["Access-Control-Allow-Methods"] == "POST, OPTIONS"
    assert headers["Access-Control-Allow-Headers"] == "Content-Type"
    assert headers["Vary"] == "Origin"


def test_miniapp_review_shell_cors_options_disallowed_origin(monkeypatch):
    monkeypatch.setenv("MINIAPP_ALLOWED_ORIGIN", "https://miniapp.example.com")
    status, headers, payload = _call(
        "/miniapp/api/review-shell",
        "OPTIONS",
        b"",
        content_type=None,
        origin="https://other.example.com",
    )
    assert status.startswith("204")
    assert payload == b""
    assert "Access-Control-Allow-Origin" not in headers


def test_miniapp_review_shell_cors_post_allowed_origin_missing_init_data(monkeypatch):
    monkeypatch.setenv("MINIAPP_ALLOWED_ORIGIN", "https://miniapp.example.com")
    status, headers, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        json.dumps({}).encode(),
        origin="https://miniapp.example.com",
    )
    assert status.startswith("400")
    assert payload["error"] == "missing_init_data"
    assert headers["Access-Control-Allow-Origin"] == "https://miniapp.example.com"
    assert headers["Vary"] == "Origin"


def test_miniapp_review_shell_cors_disallowed_origin_no_allow_header(monkeypatch):
    monkeypatch.setenv("MINIAPP_ALLOWED_ORIGIN", "https://miniapp.example.com")
    status, headers, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        json.dumps({}).encode(),
        origin="https://other.example.com",
    )
    assert status.startswith("400")
    assert payload["error"] == "missing_init_data"
    assert "Access-Control-Allow-Origin" not in headers


def test_miniapp_review_shell_latest_system_run_requires_paper_trade_only_true(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Client: pass

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": "42",
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"processed_tickers": 3, "successful_tickers": 3, "failed_tickers": 0, "paper_trade_only": False},
        },
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["latest_system_run"]
    assert section["status"] == "unavailable"
    assert section["reason"] == "latest bounded row is not available yet"
    assert section.get("paper_trade_only") is not True


def test_miniapp_review_shell_latest_system_run_bool_counter_is_bounded(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Client: pass

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": "42",
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"processed_tickers": True, "successful_tickers": False, "failed_tickers": True, "paper_trade_only": True},
        },
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["latest_system_run"]
    assert section["processed_tickers"] == 0
    assert section["successful_tickers"] == 0
    assert section["failed_tickers"] == 0
