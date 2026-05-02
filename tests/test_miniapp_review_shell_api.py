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


def _call(path: str, method: str, body: bytes, *, content_type: str | None = "application/json"):
    app = create_wsgi_app()
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    if content_type is not None:
        environ["CONTENT_TYPE"] = content_type
    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    return captured["status"], json.loads(response[0].decode("utf-8"))


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
    status, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    assert payload["status"] == "ok"


def test_miniapp_review_shell_success_accepts_json_charset_content_type(monkeypatch):
    status, payload = _call(
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
    status, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))

    assert status.startswith("200")
    runner_status = payload["sections"]["runner_status"]
    assert runner_status["source"] == "railway_runtime_env"
    assert runner_status["status"] in {"ok", "unknown"}
    assert runner_status["git_commit_sha_short"] == "abcdef123456"
    assert "SUPABASE_SERVICE_ROLE_KEY" not in json.dumps(payload)
    latest_system_run = payload["sections"]["latest_system_run"]
    assert latest_system_run["status"] in {"unavailable", "ok", "unknown"}
    if latest_system_run["status"] == "unavailable":
        assert latest_system_run["source"] == "not_configured"



def test_miniapp_review_shell_rejects_missing_content_type():
    status, payload = _call("/miniapp/api/review-shell", "POST", b"{}", content_type=None)
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_non_json_content_type():
    status, payload = _call("/miniapp/api/review-shell", "POST", b"{}", content_type="text/plain")
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_unsupported_json_content_type_params(monkeypatch):
    body = _authorized_request(monkeypatch)
    status, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        body,
        content_type="application/json; charset=latin-1",
    )
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"

    status, payload = _call(
        "/miniapp/api/review-shell",
        "POST",
        body,
        content_type="application/json; version=1",
    )
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_miniapp_review_shell_rejects_oversized_payload():
    oversized = b"x" * (MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES + 1)
    status, payload = _call("/miniapp/api/review-shell", "POST", oversized)
    assert status.startswith("413")
    assert payload["error"] == "payload_too_large"


def test_miniapp_review_shell_failures(monkeypatch):
    status, payload = _call("/miniapp/api/review-shell", "GET", b"")
    assert status.startswith("405") and payload["error"] == "method_not_allowed"

    status, payload = _call("/miniapp/api/review-shell", "POST", b"{")
    assert status.startswith("400") and payload["error"] == "invalid_json"

    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({}).encode())
    assert status.startswith("400") and payload["error"] == "missing_init_data"

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "x"}).encode())
    assert status.startswith("503") and payload["error"] == "miniapp_auth_config_unavailable"

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "true")
    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "x"}).encode())
    assert status.startswith("503") and payload["error"] == "miniapp_operator_allowlist_unavailable"


def test_miniapp_review_shell_validation_and_authorization_failures(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": "bad=payload"}).encode())
    assert status.startswith("401") and payload["error"] == "invalid_init_data"

    init_data = _build_signed_init_data(
        {"auth_date": str(NOW_TS - 50), "user": '{"id":99,"username":"other"}'},
        bot_token=FAKE_BOT_TOKEN,
    )
    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": init_data}).encode())
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

    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": init_data}).encode())
    assert status.startswith("200")
    assert payload["status"] == "ok"
