import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from src.miniapp_auth import (
    MiniAppAuthValidationError,
    authorize_telegram_operator,
    validate_telegram_init_data,
)


FAKE_BOT_TOKEN = "123456:TEST_FAKE_BOT_TOKEN"
NOW_TS = 1_700_000_000


def _build_signed_init_data(fields: dict[str, str], *, bot_token: str) -> str:
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items(), key=lambda item: item[0]))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    data_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    payload = {**fields, "hash": data_hash}
    return urlencode(payload)


def test_validate_telegram_init_data_passes_for_valid_payload():
    user_payload = json.dumps({"id": 42, "username": "hk_operator"}, separators=(",", ":"))
    init_data = _build_signed_init_data(
        {"auth_date": str(NOW_TS - 100), "query_id": "AAEAAAE", "user": user_payload},
        bot_token=FAKE_BOT_TOKEN,
    )

    context = validate_telegram_init_data(init_data, bot_token=FAKE_BOT_TOKEN, max_age_seconds=300, now_ts=NOW_TS)
    assert context["auth_date"] == NOW_TS - 100
    assert context["query_id"] == "AAEAAAE"
    assert context["user"]["id"] == 42


def test_validate_telegram_init_data_fails_when_field_tampered():
    init_data = _build_signed_init_data({"auth_date": str(NOW_TS - 100), "query_id": "AAEAAAE"}, bot_token=FAKE_BOT_TOKEN)
    tampered = init_data.replace("query_id=AAEAAAE", "query_id=TAMPERED")

    with pytest.raises(MiniAppAuthValidationError, match="hash_mismatch"):
        validate_telegram_init_data(tampered, bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)


def test_validate_telegram_init_data_fails_when_hash_missing():
    with pytest.raises(MiniAppAuthValidationError, match="missing_hash"):
        validate_telegram_init_data("auth_date=1700000000", bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)


def test_validate_telegram_init_data_fails_when_auth_date_missing():
    init_data = _build_signed_init_data({"query_id": "AAEAAAE"}, bot_token=FAKE_BOT_TOKEN)

    with pytest.raises(MiniAppAuthValidationError, match="missing_auth_date"):
        validate_telegram_init_data(init_data, bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)


def test_validate_telegram_init_data_fails_when_auth_date_expired():
    init_data = _build_signed_init_data({"auth_date": str(NOW_TS - 301), "query_id": "AAEAAAE"}, bot_token=FAKE_BOT_TOKEN)

    with pytest.raises(MiniAppAuthValidationError, match="expired_auth_date"):
        validate_telegram_init_data(init_data, bot_token=FAKE_BOT_TOKEN, max_age_seconds=300, now_ts=NOW_TS)


def test_validate_telegram_init_data_handles_future_or_invalid_auth_date_deterministically():
    future_data = _build_signed_init_data({"auth_date": str(NOW_TS + 1), "query_id": "AAEAAAE"}, bot_token=FAKE_BOT_TOKEN)
    with pytest.raises(MiniAppAuthValidationError, match="invalid_auth_date"):
        validate_telegram_init_data(future_data, bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)

    invalid_data = _build_signed_init_data({"auth_date": "not_int", "query_id": "AAEAAAE"}, bot_token=FAKE_BOT_TOKEN)
    with pytest.raises(MiniAppAuthValidationError, match="invalid_auth_date"):
        validate_telegram_init_data(invalid_data, bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)


def test_validate_telegram_init_data_fails_on_malformed_user_json():
    init_data = _build_signed_init_data(
        {"auth_date": str(NOW_TS - 1), "user": "{bad_json}"},
        bot_token=FAKE_BOT_TOKEN,
    )

    with pytest.raises(MiniAppAuthValidationError, match="malformed_user_json"):
        validate_telegram_init_data(init_data, bot_token=FAKE_BOT_TOKEN, now_ts=NOW_TS)


def test_validate_telegram_init_data_fails_for_empty_bot_token():
    with pytest.raises(MiniAppAuthValidationError, match="empty_bot_token"):
        validate_telegram_init_data("auth_date=1700000000&hash=x", bot_token="", now_ts=NOW_TS)


def test_authorize_telegram_operator_passes_for_allowed_user_id():
    result = authorize_telegram_operator(
        {"user": {"id": 42, "username": "hk_operator"}},
        allowed_telegram_user_ids=[42, 99],
    )
    assert result == {
        "telegram_user_id": 42,
        "username": "hk_operator",
        "authorization_status": "authorized",
    }


def test_authorize_telegram_operator_fails_for_unauthorized_user_id():
    with pytest.raises(MiniAppAuthValidationError, match="unauthorized_user_id"):
        authorize_telegram_operator({"user": {"id": 77}}, allowed_telegram_user_ids=[42, 99])


def test_authorize_telegram_operator_fails_when_user_missing():
    with pytest.raises(MiniAppAuthValidationError, match="missing_user"):
        authorize_telegram_operator({}, allowed_telegram_user_ids=[42])


def test_authorize_telegram_operator_fails_when_user_id_missing():
    with pytest.raises(MiniAppAuthValidationError, match="missing_user_id"):
        authorize_telegram_operator({"user": {"username": "hk_operator"}}, allowed_telegram_user_ids=[42])


def test_authorize_telegram_operator_fails_when_user_id_type_invalid():
    with pytest.raises(MiniAppAuthValidationError, match="invalid_user_id_type"):
        authorize_telegram_operator({"user": {"id": "42"}}, allowed_telegram_user_ids=[42])


def test_authorize_telegram_operator_fails_when_user_id_is_bool():
    with pytest.raises(MiniAppAuthValidationError, match="invalid_user_id_type"):
        authorize_telegram_operator({"user": {"id": True}}, allowed_telegram_user_ids=[1])


def test_authorize_telegram_operator_fails_for_empty_allowlist():
    with pytest.raises(MiniAppAuthValidationError, match="empty_operator_allowlist"):
        authorize_telegram_operator({"user": {"id": 42}}, allowed_telegram_user_ids=[])


def test_authorize_telegram_operator_does_not_authorize_username_only_user():
    with pytest.raises(MiniAppAuthValidationError, match="missing_user_id"):
        authorize_telegram_operator({"user": {"username": "only_name"}}, allowed_telegram_user_ids=[42])


def test_authorize_telegram_operator_fails_for_invalid_allowlist_user_id_type():
    with pytest.raises(MiniAppAuthValidationError, match="invalid_allowlist_user_id_type"):
        authorize_telegram_operator({"user": {"id": 42}}, allowed_telegram_user_ids=[42, "99"])  # type: ignore[list-item]
