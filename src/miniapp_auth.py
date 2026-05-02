from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


@dataclass(frozen=True)
class MiniAppAuthValidationError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


def _build_data_check_string(pairs: list[tuple[str, str]]) -> str:
    filtered = [(k, v) for k, v in pairs if k != "hash"]
    filtered.sort(key=lambda item: item[0])
    return "\n".join(f"{key}={value}" for key, value in filtered)


def validate_telegram_init_data(
    init_data: str,
    *,
    bot_token: str,
    max_age_seconds: int = 300,
    now_ts: int | None = None,
) -> dict[str, Any]:
    """Validate Telegram Mini App initData query string server-side only."""
    if not bot_token:
        raise MiniAppAuthValidationError("empty_bot_token")

    pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)
    fields = dict(pairs)

    received_hash = fields.get("hash")
    if not received_hash:
        raise MiniAppAuthValidationError("missing_hash")

    raw_auth_date = fields.get("auth_date")
    if raw_auth_date is None:
        raise MiniAppAuthValidationError("missing_auth_date")

    try:
        auth_date = int(raw_auth_date)
    except (TypeError, ValueError):
        raise MiniAppAuthValidationError("invalid_auth_date") from None

    current_ts = int(now_ts if now_ts is not None else time.time())
    if auth_date > current_ts:
        raise MiniAppAuthValidationError("invalid_auth_date")

    if current_ts - auth_date > max_age_seconds:
        raise MiniAppAuthValidationError("expired_auth_date")

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_check_string = _build_data_check_string(pairs)
    expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise MiniAppAuthValidationError("hash_mismatch")

    user = None
    if "user" in fields:
        try:
            user = json.loads(fields["user"])
        except json.JSONDecodeError:
            raise MiniAppAuthValidationError("malformed_user_json") from None

    context: dict[str, Any] = {"auth_date": auth_date}
    if user is not None:
        context["user"] = user
    if "query_id" in fields:
        context["query_id"] = fields["query_id"]
    return context
