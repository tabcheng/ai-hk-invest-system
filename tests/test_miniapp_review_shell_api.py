import hashlib
import hmac
import io
import json
from urllib.parse import urlencode

from src.telegram_webhook_server import create_wsgi_app

FAKE_BOT_TOKEN = "123456:TEST_FAKE_BOT_TOKEN"
NOW_TS = 1_700_000_000


def _build_signed_init_data(fields: dict[str, str], *, bot_token: str) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items(), key=lambda item: item[0]))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": data_hash})


def _call(path: str, method: str, body: bytes):
    app = create_wsgi_app()
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    return captured["status"], json.loads(response[0].decode("utf-8"))


def test_miniapp_review_shell_authorized_returns_mock_response(monkeypatch):
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

    status, payload = _call("/miniapp/api/review-shell", "POST", json.dumps({"init_data": init_data}).encode())

    assert status.startswith("200")
    assert payload["status"] == "ok"
    assert payload["guardrails"]["read_only"] is True
    assert payload["guardrails"]["paper_trade_only"] is True
    assert payload["guardrails"]["no_broker_execution"] is True
    assert "order" not in json.dumps(payload).lower()
    assert payload["sections"]["runner_status"]["status"] == "mock"


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
