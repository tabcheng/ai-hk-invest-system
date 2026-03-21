from __future__ import annotations

import json
import os
from typing import Any
from wsgiref.simple_server import make_server


def _load_supabase_client() -> Any:
    from src.config import get_supabase_client

    return get_supabase_client()


def handle_telegram_webhook_update(
    *,
    client: Any,
    update: dict[str, Any],
    command_handler: Any | None = None,
    auth_decision_reader: Any | None = None,
    reply_sender: Any | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    Handle one Telegram update payload in a webhook-safe, guardrail-preserving path.

    Guardrails:
    - Ingress only bridges existing operator command handlers (`/help`, `/h`, `/runs`, `/risk_review [run_id]`).
    - No strategy/paper-trading/real-money execution behavior is introduced here.
    - Unknown/non-command updates return 200 no-op to avoid Telegram retries.
    """
    message = update.get("message") or {}
    text = str(message.get("text") or "").strip()
    chat_id = str((message.get("chat") or {}).get("id") or "").strip()

    print("Telegram webhook request received.")
    print(f"Telegram webhook command text: {text or '<empty>'}")

    if auth_decision_reader is None or command_handler is None:
        from src.telegram_operator import get_operator_auth_decision, handle_telegram_operator_command

        auth_decision_reader = auth_decision_reader or get_operator_auth_decision
        command_handler = command_handler or handle_telegram_operator_command
    if reply_sender is None:
        from src.notifications import send_telegram_chat_message_with_result

        reply_sender = send_telegram_chat_message_with_result

    auth = auth_decision_reader(update)
    print(
        "Telegram operator auth decision: "
        f"authorized={auth.get('authorized')} reason={auth.get('reason')} "
        f"chat_id={auth.get('chat_id')} user_id={auth.get('user_id')}"
    )

    try:
        response_text = command_handler(client, update)
    except Exception as exc:
        # Webhook isolation guardrail: one handler failure must not crash ingress.
        # Keep Telegram reply sanitized while retaining internal details in logs.
        print(f"Telegram webhook command handler failed: {exc!r}")
        response_text = (
            "Failed: internal command processing error. "
            "Please check service logs and retry."
        )
    if response_text is None:
        return 200, {"ok": True, "handled": False}

    if not chat_id:
        print("Telegram webhook reply skipped: missing chat id in update payload.")
        return 200, {"ok": True, "handled": True, "replied": False, "reason": "missing_chat_id"}

    send_result = reply_sender(chat_id, response_text)
    if send_result.get("delivered"):
        print(
            "Telegram sendMessage success: "
            f"chat_id={chat_id} message_id={send_result.get('telegram_message_id')}"
        )
    else:
        print(
            "Telegram sendMessage failure: "
            f"chat_id={chat_id} reason={send_result.get('failure_reason')}"
        )

    return 200, {
        "ok": True,
        "handled": True,
        "replied": bool(send_result.get("delivered")),
        "send_result": send_result,
    }


def create_wsgi_app() -> Any:
    """Create a minimal WSGI app exposing `POST /telegram/webhook` for Telegram ingress."""

    def _is_webhook_request_authorized(environ: dict[str, Any]) -> bool:
        """
        Validate optional Telegram webhook secret token.

        Guardrail: this check only protects ingress transport; it must not alter
        operator command semantics or strategy/runtime decision logic.
        """
        configured_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET_TOKEN", "").strip()
        if not configured_secret:
            print("Telegram webhook transport auth: open (no secret configured).")
            return True

        provided_secret = str(
            environ.get("HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN", "") or ""
        ).strip()
        is_authorized = provided_secret == configured_secret
        print(
            "Telegram webhook transport auth decision: "
            f"authorized={is_authorized} has_provided_secret={bool(provided_secret)}"
        )
        return is_authorized

    def _app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "")

        if path != "/telegram/webhook":
            status = "404 Not Found"
            payload = {"ok": False, "error": "not_found"}
        elif method != "POST":
            status = "405 Method Not Allowed"
            payload = {"ok": False, "error": "method_not_allowed"}
        elif not _is_webhook_request_authorized(environ):
            status = "401 Unauthorized"
            payload = {"ok": False, "error": "unauthorized"}
        else:
            try:
                body_size = int(environ.get("CONTENT_LENGTH") or 0)
            except (TypeError, ValueError):
                body_size = 0
            raw_body = environ["wsgi.input"].read(body_size)
            try:
                update = json.loads(raw_body.decode("utf-8") or "{}")
            except Exception:
                status = "400 Bad Request"
                payload = {"ok": False, "error": "invalid_json"}
            else:
                try:
                    client = _load_supabase_client()
                except Exception as exc:
                    # Keep webhook response explicit so operators can detect
                    # infrastructure dependency issues from ingress logs.
                    print(f"Telegram webhook failed to init Supabase client: {exc}")
                    status = "503 Service Unavailable"
                    payload = {"ok": False, "error": "supabase_client_unavailable"}
                else:
                    code, payload = handle_telegram_webhook_update(client=client, update=update)
                    status = f"{code} OK"

        response_body = json.dumps(payload).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ],
        )
        return [response_body]

    return _app


def main() -> None:
    """
    Start Telegram webhook ingress HTTP server.

    Use this process as a dedicated ingress service. Keep the existing batch runtime
    (`python main.py`) unchanged.
    """
    host = os.getenv("TELEGRAM_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("TELEGRAM_WEBHOOK_PORT", "8080")))
    app = create_wsgi_app()
    print(f"Starting Telegram webhook server on {host}:{port} route=/telegram/webhook")
    with make_server(host, port, app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
