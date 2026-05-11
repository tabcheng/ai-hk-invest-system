from __future__ import annotations

import json
import os
import re
import hashlib
from typing import Any
from wsgiref.simple_server import make_server

from src.miniapp_auth import (
    MiniAppAuthValidationError,
    authorize_telegram_operator,
    validate_telegram_init_data,
)

from src.miniapp_read_model import build_miniapp_review_shell_response
from src.miniapp_data_provider import SupabaseLatestSystemRunMiniAppReadDataProvider
from src.human_decision_journal import (
    ALLOWED_MINIAPP_CONFIDENCE,
    ALLOWED_MINIAPP_DECISION_TYPES,
    build_human_decision_context_snapshot,
    persist_decision_context_snapshot,
    record_miniapp_human_paper_decision_journal,
)

def _parse_miniapp_allowed_telegram_user_ids(raw_value: str | None) -> list[int]:
    if raw_value is None:
        raise MiniAppAuthValidationError("missing_operator_allowlist_config")

    tokens = [part.strip() for part in raw_value.split(",")]
    if not tokens or any(token == "" for token in tokens):
        raise MiniAppAuthValidationError("invalid_operator_allowlist_config")

    disallowed_literals = {"true", "false", "null", "none"}
    parsed: list[int] = []
    for token in tokens:
        if token.lower() in disallowed_literals or not token.isdigit():
            raise MiniAppAuthValidationError("invalid_operator_allowlist_config")
        parsed.append(int(token))
    return parsed


def _load_miniapp_bot_token_from_env() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise MiniAppAuthValidationError("missing_miniapp_bot_token_config")
    return token


def _load_miniapp_allowed_telegram_user_ids_from_env() -> list[int]:
    return _parse_miniapp_allowed_telegram_user_ids(os.getenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS"))


MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES = 8192
MINIAPP_HUMAN_DECISION_MAX_BODY_BYTES = 8192
MINIAPP_DECISION_MAX_RATIONALE = 500
_MINIAPP_TICKER_PATTERN = re.compile(r"^[0-9A-Z.\-]{1,16}$")


def _build_operator_label_from_telegram_user_id(user_id: Any) -> str:
    raw = str(user_id or "").strip()
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16] if raw else "unknown"
    return f"tg_user_hash:{digest}"


def _is_supported_json_content_type(content_type: str) -> bool:
    normalized = content_type.strip().lower()
    if not normalized:
        return False

    parts = [part.strip() for part in normalized.split(";") if part.strip()]
    if not parts or parts[0] != "application/json":
        return False
    if len(parts) == 1:
        return True

    allowed_params = {"charset=utf-8"}
    return all(part in allowed_params for part in parts[1:])


def _safe_parse_content_length(raw_value: Any) -> int | None:
    if raw_value is None:
        return None
    try:
        parsed = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _handle_miniapp_review_shell_request(raw_body: bytes) -> tuple[str, dict[str, Any]]:
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        return "400 Bad Request", {"ok": False, "error": "invalid_json"}

    if not isinstance(payload, dict):
        return "400 Bad Request", {"ok": False, "error": "invalid_json"}
    init_data = payload.get("init_data")
    if not isinstance(init_data, str) or not init_data.strip():
        return "400 Bad Request", {"ok": False, "error": "missing_init_data"}

    try:
        bot_token = _load_miniapp_bot_token_from_env()
    except MiniAppAuthValidationError:
        return "503 Service Unavailable", {"ok": False, "error": "miniapp_auth_config_unavailable"}
    try:
        allowed_user_ids = _load_miniapp_allowed_telegram_user_ids_from_env()
    except MiniAppAuthValidationError:
        return "503 Service Unavailable", {"ok": False, "error": "miniapp_operator_allowlist_unavailable"}

    try:
        validated_context = validate_telegram_init_data(init_data, bot_token=bot_token)
    except MiniAppAuthValidationError:
        return "401 Unauthorized", {"ok": False, "error": "invalid_init_data"}
    try:
        operator = authorize_telegram_operator(
            validated_context, allowed_telegram_user_ids=allowed_user_ids
        )
    except MiniAppAuthValidationError:
        return "403 Forbidden", {"ok": False, "error": "operator_not_authorized"}
    supabase_client = None
    try:
        supabase_client = _load_supabase_client()
    except Exception:
        supabase_client = None
    provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=supabase_client, env=os.environ)
    return "200 OK", build_miniapp_review_shell_response(operator=operator, env=os.environ, provider=provider)


def _handle_miniapp_human_paper_decision_request(raw_body: bytes) -> tuple[str, dict[str, Any]]:
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        return "400 Bad Request", {"ok": False, "error": "invalid_json"}
    if not isinstance(payload, dict):
        return "400 Bad Request", {"ok": False, "error": "invalid_json"}
    init_data = payload.get("init_data")
    if not isinstance(init_data, str) or not init_data.strip():
        return "400 Bad Request", {"ok": False, "error": "missing_init_data"}
    guardrail_ack = payload.get("guardrail_ack")
    if guardrail_ack is not True:
        return "400 Bad Request", {"ok": False, "error": "guardrail_ack_required"}
    decision_type = str(payload.get("decision_type") or "").strip().lower()
    if decision_type not in ALLOWED_MINIAPP_DECISION_TYPES:
        return "400 Bad Request", {"ok": False, "error": "invalid_decision_type"}
    ticker = str(payload.get("ticker") or "").strip().upper()
    if not _MINIAPP_TICKER_PATTERN.match(ticker):
        return "400 Bad Request", {"ok": False, "error": "invalid_ticker"}
    business_date = str(payload.get("business_date") or "").strip()
    run_id = str(payload.get("run_id") or "").strip()
    rationale_text = str(payload.get("rationale_text") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", business_date):
        return "400 Bad Request", {"ok": False, "error": "invalid_business_date"}
    if not run_id or len(run_id) > 80:
        return "400 Bad Request", {"ok": False, "error": "invalid_request_fields"}
    if not rationale_text or len(rationale_text) > MINIAPP_DECISION_MAX_RATIONALE:
        return "400 Bad Request", {"ok": False, "error": "invalid_rationale_text"}
    confidence_label = payload.get("confidence_label")
    if confidence_label is not None and str(confidence_label).strip().lower() not in ALLOWED_MINIAPP_CONFIDENCE:
        return "400 Bad Request", {"ok": False, "error": "invalid_confidence_label"}
    quantity_intent = payload.get("quantity_intent")
    if quantity_intent is not None and (
        isinstance(quantity_intent, bool)
        or not isinstance(quantity_intent, int)
        or quantity_intent < 0
        or quantity_intent > 1_000_000
    ):
        return "400 Bad Request", {"ok": False, "error": "invalid_quantity_intent"}
    notional_intent = payload.get("notional_intent")
    if notional_intent is not None and (
        isinstance(notional_intent, bool)
        or
        not isinstance(notional_intent, (int, float)) or notional_intent < 0 or notional_intent > 1_000_000_000
    ):
        return "400 Bad Request", {"ok": False, "error": "invalid_notional_intent"}
    try:
        bot_token = _load_miniapp_bot_token_from_env()
        allowed_user_ids = _load_miniapp_allowed_telegram_user_ids_from_env()
        validated_context = validate_telegram_init_data(init_data, bot_token=bot_token)
        operator = authorize_telegram_operator(validated_context, allowed_telegram_user_ids=allowed_user_ids)
        supabase_client = _load_supabase_client()
        recorded = record_miniapp_human_paper_decision_journal(
            supabase_client,
            business_date=business_date,
            run_id=run_id,
            ticker=ticker,
            decision_type=decision_type,
            rationale_text=rationale_text,
            operator_user_id_hash_or_label=_build_operator_label_from_telegram_user_id(operator.get("telegram_user_id")),
            confidence_label=(str(confidence_label).strip().lower() if confidence_label is not None else None),
            quantity_intent=quantity_intent,
            notional_intent=notional_intent,
            ui_build_version=str(payload.get("ui_build_version") or "").strip() or None,
            data_timestamp_hkt=str(payload.get("data_timestamp_hkt") or "").strip() or None,
        )
        provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=supabase_client, env=os.environ)
        context_snapshot = build_human_decision_context_snapshot(
            business_date_hkt=business_date,
            latest_run_id=run_id,
            ticker=ticker,
            human_paper_decision={
                "decision_type": decision_type,
                "rationale_text": rationale_text,
                "confidence_label": (str(confidence_label).strip().lower() if confidence_label is not None else "unknown"),
            },
            decision_context_summary=provider.get_decision_context_summary(),
            ticker_level_paper_portfolio_review=provider.get_ticker_level_paper_portfolio_review(),
        )
        snapshot_status = {"status": "failed", "id": None}
        try:
            snapshot_status = persist_decision_context_snapshot(supabase_client, snapshot=context_snapshot)
        except Exception:
            snapshot_status = {"status": "failed", "id": None}
    except MiniAppAuthValidationError as exc:
        reason = str(exc)
        if "allowlist" in reason:
            return "503 Service Unavailable", {"ok": False, "error": "miniapp_operator_allowlist_unavailable"}
        if "bot_token" in reason:
            return "503 Service Unavailable", {"ok": False, "error": "miniapp_auth_config_unavailable"}
        if reason == "unauthorized_user_id":
            return "403 Forbidden", {"ok": False, "error": "operator_not_authorized"}
        return "401 Unauthorized", {"ok": False, "error": "invalid_init_data"}
    except Exception:
        return "503 Service Unavailable", {"ok": False, "error": "journal_unavailable", "no_data_written": True}
    return "200 OK", {
        "ok": True,
        "status": "ok",
        "journal_id": recorded.get("id"),
        "journal_saved": True,
        "snapshot_saved": snapshot_status.get("status") == "saved",
        "snapshot_id": snapshot_status.get("id"),
        "no_order_created": True,
        "paper_trade_only": True,
        "operator_note": "human paper decision journal recorded",
    }


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
    allowed_miniapp_origin = str(os.getenv("MINIAPP_ALLOWED_ORIGIN", "") or "").strip()

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
        request_origin = str(environ.get("HTTP_ORIGIN", "") or "").strip()
        allow_cors_origin = (
            request_origin
            if path in {"/miniapp/api/review-shell", "/miniapp/api/human-paper-decision"}
            and request_origin
            and allowed_miniapp_origin
            and request_origin == allowed_miniapp_origin
            else None
        )
        response_headers: list[tuple[str, str]] = []

        if path in {"/miniapp/api/review-shell", "/miniapp/api/human-paper-decision"} and method == "OPTIONS":
            if allow_cors_origin:
                response_headers.extend(
                    [
                        ("Access-Control-Allow-Origin", allow_cors_origin),
                        ("Access-Control-Allow-Methods", "POST, OPTIONS"),
                        ("Access-Control-Allow-Headers", "Content-Type"),
                        ("Vary", "Origin"),
                    ]
                )
            start_response("204 No Content", response_headers)
            return [b""]
        elif path not in {"/telegram/webhook", "/miniapp/api/review-shell", "/miniapp/api/human-paper-decision"}:
            status = "404 Not Found"
            payload = {"ok": False, "error": "not_found"}
        elif method != "POST":
            status = "405 Method Not Allowed"
            payload = {"ok": False, "error": "method_not_allowed"}
        elif path in {"/miniapp/api/review-shell", "/miniapp/api/human-paper-decision"}:
            content_type = str(environ.get("CONTENT_TYPE") or "")
            if not _is_supported_json_content_type(content_type):
                status = "415 Unsupported Media Type"
                payload = {"ok": False, "error": "unsupported_media_type"}
            else:
                body_size = _safe_parse_content_length(environ.get("CONTENT_LENGTH"))
                max_bytes = MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES if path == "/miniapp/api/review-shell" else MINIAPP_HUMAN_DECISION_MAX_BODY_BYTES
                if body_size is not None and body_size > max_bytes:
                    status = "413 Payload Too Large"
                    payload = {"ok": False, "error": "payload_too_large"}
                else:
                    safe_read_size = max_bytes + 1
                    if body_size is not None:
                        safe_read_size = min(body_size, max_bytes + 1)
                    raw_body = environ["wsgi.input"].read(safe_read_size)
                    if len(raw_body) > max_bytes:
                        status = "413 Payload Too Large"
                        payload = {"ok": False, "error": "payload_too_large"}
                    else:
                        if path == "/miniapp/api/review-shell":
                            status, payload = _handle_miniapp_review_shell_request(raw_body)
                        else:
                            status, payload = _handle_miniapp_human_paper_decision_request(raw_body)
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

        if allow_cors_origin:
            if ("Access-Control-Allow-Origin", allow_cors_origin) not in response_headers:
                response_headers.append(("Access-Control-Allow-Origin", allow_cors_origin))
            if ("Vary", "Origin") not in response_headers:
                response_headers.append(("Vary", "Origin"))
        response_body = json.dumps(payload).encode("utf-8")
        response_headers.extend(
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(response_body))),
            ]
        )
        start_response(
            status,
            response_headers,
        )
        return [response_body]

    return _app


def main() -> None:
    """
    Start Telegram webhook ingress HTTP server.

    Use this process as a dedicated ingress service. Keep the existing batch runtime
    (`python -m src.daily_runner`) unchanged.
    """
    host = os.getenv("TELEGRAM_WEBHOOK_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("TELEGRAM_WEBHOOK_PORT", "8080")))
    app = create_wsgi_app()
    print(f"Starting Telegram webhook server on {host}:{port} route=/telegram/webhook")
    with make_server(host, port, app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
