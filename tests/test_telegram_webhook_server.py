import io
import json

from src.telegram_webhook_server import create_wsgi_app, handle_telegram_webhook_update


def _build_update(text: str = "/help", *, chat_id: str = "chat-1", user_id: str = "u-1") -> dict:
    return {
        "update_id": 1001,
        "message": {
            "message_id": 99,
            "chat": {"id": chat_id},
            "from": {"id": user_id},
            "text": text,
        },
    }


def test_handle_webhook_update_noop_for_non_command(monkeypatch):
    called = {"send": False}
    code, payload = handle_telegram_webhook_update(
        client=object(),
        update=_build_update("hello"),
        command_handler=lambda *_args, **_kwargs: None,
        auth_decision_reader=lambda *_args, **_kwargs: {"authorized": True, "reason": "test"},
        reply_sender=lambda *_args, **_kwargs: called.__setitem__("send", True),
    )

    assert code == 200
    assert payload["handled"] is False
    assert called["send"] is False


def test_handle_webhook_update_replies_with_handler_text(monkeypatch):
    sent = {}

    def _fake_send(chat_id: str, text: str):
        sent["chat_id"] = chat_id
        sent["text"] = text
        return {
            "delivered": True,
            "channel": "telegram",
            "telegram_message_id": 77,
            "failure_reason": None,
        }

    code, payload = handle_telegram_webhook_update(
        client=object(),
        update=_build_update("/help"),
        command_handler=lambda *_args, **_kwargs: "operator reply",
        auth_decision_reader=lambda *_args, **_kwargs: {"authorized": True, "reason": "test"},
        reply_sender=_fake_send,
    )

    assert code == 200
    assert payload["handled"] is True
    assert payload["replied"] is True
    assert sent["chat_id"] == "chat-1"
    assert sent["text"] == "operator reply"


def test_handle_webhook_update_sanitizes_command_handler_exception(monkeypatch):
    sent = {}

    def _fake_send(chat_id: str, text: str):
        sent["chat_id"] = chat_id
        sent["text"] = text
        return {
            "delivered": True,
            "channel": "telegram",
            "telegram_message_id": 88,
            "failure_reason": None,
        }

    def _raise_handler(*_args, **_kwargs):
        raise RuntimeError("simulated operator handler crash")

    code, payload = handle_telegram_webhook_update(
        client=object(),
        update=_build_update("/risk_review 123"),
        command_handler=_raise_handler,
        auth_decision_reader=lambda *_args, **_kwargs: {"authorized": True, "reason": "test"},
        reply_sender=_fake_send,
    )

    assert code == 200
    assert payload["handled"] is True
    assert payload["replied"] is True
    assert sent["chat_id"] == "chat-1"
    assert "internal command processing error" in sent["text"]
    assert "simulated operator handler crash" not in sent["text"]


def test_handle_webhook_update_runner_status_lookup_failure_does_not_crash(monkeypatch):
    sent = {}

    def _fake_send(chat_id: str, text: str):
        sent["chat_id"] = chat_id
        sent["text"] = text
        return {
            "delivered": True,
            "channel": "telegram",
            "telegram_message_id": 89,
            "failure_reason": None,
        }

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")
    monkeypatch.setattr(
        "src.telegram_operator.get_latest_run_execution_summary",
        lambda _client: (_ for _ in ()).throw(RuntimeError("query down")),
    )

    code, payload = handle_telegram_webhook_update(
        client=object(),
        update=_build_update("/runner_status"),
        reply_sender=_fake_send,
    )

    assert code == 200
    assert payload["handled"] is True
    assert payload["replied"] is True
    assert sent["chat_id"] == "chat-1"
    assert "Status: failed." in sent["text"]
    assert "internal status lookup error" in sent["text"]
    assert "query down" not in sent["text"]


def test_wsgi_route_dispatches_post_telegram_webhook(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    monkeypatch.setattr(
        "src.telegram_webhook_server.handle_telegram_webhook_update",
        lambda **_kwargs: (200, {"ok": True, "handled": True}),
    )
    app = create_wsgi_app()
    body = json.dumps(_build_update("/runs")).encode("utf-8")
    environ = {
        "PATH_INFO": "/telegram/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }

    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    payload = json.loads(response[0].decode("utf-8"))

    assert captured["status"].startswith("200")
    assert payload["ok"] is True
    assert payload["handled"] is True


def test_wsgi_route_rejects_invalid_webhook_secret(monkeypatch):
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET_TOKEN", "expected-secret")
    app = create_wsgi_app()
    body = json.dumps(_build_update("/help")).encode("utf-8")
    environ = {
        "PATH_INFO": "/telegram/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
        "HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": "wrong-secret",
    }

    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    payload = json.loads(response[0].decode("utf-8"))

    assert captured["status"].startswith("401")
    assert payload["error"] == "unauthorized"


def test_wsgi_route_returns_503_when_supabase_client_unavailable(monkeypatch):
    monkeypatch.setattr(
        "src.telegram_webhook_server._load_supabase_client",
        lambda: (_ for _ in ()).throw(RuntimeError("db down")),
    )
    app = create_wsgi_app()
    body = json.dumps(_build_update("/help")).encode("utf-8")
    environ = {
        "PATH_INFO": "/telegram/webhook",
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }

    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    payload = json.loads(response[0].decode("utf-8"))

    assert captured["status"].startswith("503")
    assert payload["error"] == "supabase_client_unavailable"


def test_wsgi_route_rejects_non_post():
    app = create_wsgi_app()
    environ = {
        "PATH_INFO": "/telegram/webhook",
        "REQUEST_METHOD": "GET",
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(b""),
    }

    captured = {}

    def _start_response(status, headers):
        captured["status"] = status
        captured["headers"] = headers

    response = app(environ, _start_response)
    payload = json.loads(response[0].decode("utf-8"))

    assert captured["status"].startswith("405")
    assert payload["error"] == "method_not_allowed"
