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
    monkeypatch.setattr(
        "src.telegram_webhook_server.send_telegram_chat_message_with_result",
        lambda *_args, **_kwargs: called.__setitem__("send", True),
    )

    code, payload = handle_telegram_webhook_update(client=object(), update=_build_update("hello"))

    assert code == 200
    assert payload["handled"] is False
    assert called["send"] is False


def test_handle_webhook_update_replies_with_handler_text(monkeypatch):
    monkeypatch.setattr(
        "src.telegram_webhook_server.handle_telegram_operator_command",
        lambda *_args, **_kwargs: "operator reply",
    )
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

    monkeypatch.setattr("src.telegram_webhook_server.send_telegram_chat_message_with_result", _fake_send)

    code, payload = handle_telegram_webhook_update(client=object(), update=_build_update("/help"))

    assert code == 200
    assert payload["handled"] is True
    assert payload["replied"] is True
    assert sent["chat_id"] == "chat-1"
    assert sent["text"] == "operator reply"


def test_wsgi_route_dispatches_post_telegram_webhook(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server.get_supabase_client", lambda: object())
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
