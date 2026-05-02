#!/usr/bin/env python3
"""Step 82 Mini App API smoke test for POST /miniapp/api/review-shell."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

MAX_BODY_BYTES = 8192

REQUIRED_ENV_VARS = (
    "MINIAPP_SMOKE_ENDPOINT_URL",
    "MINIAPP_SMOKE_BOT_TOKEN",
    "MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID",
    "MINIAPP_SMOKE_UNAUTHORIZED_TELEGRAM_USER_ID",
)


@dataclass
class CaseResult:
    name: str
    status_code: int | None
    passed: bool
    detail: str


def _require_env() -> dict[str, str]:
    values: dict[str, str] = {}
    missing: list[str] = []
    for key in REQUIRED_ENV_VARS:
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(key)
        else:
            values[key] = value
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return values


def _build_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/miniapp/api/review-shell"):
        return normalized
    return f"{normalized}/miniapp/api/review-shell"


def _telegram_init_data(bot_token: str, user_id: str, tampered: bool = False) -> str:
    auth_date = str(int(time.time()))
    user = {
        "id": int(user_id),
        "first_name": "Smoke",
        "last_name": "User",
        "username": "smoke_user",
        "language_code": "en",
        "is_premium": False,
    }
    data = {
        "auth_date": auth_date,
        "query_id": "AAEAAAE",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    hash_hex = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if tampered:
        hash_hex = ("0" if hash_hex[0] != "0" else "1") + hash_hex[1:]
    data["hash"] = hash_hex
    return parse.urlencode(data)


def _send(url: str, body: bytes, content_type: str) -> tuple[int, str]:
    headers = {"Content-Type": content_type}
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"network_error={exc}") from exc


def _json_body(init_data: str, pad: str = "") -> bytes:
    return json.dumps({"init_data": init_data, "padding": pad}, separators=(",", ":")).encode("utf-8")


def _assert_json_field(payload: dict[str, Any], path: list[str], expected: Any) -> bool:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return current == expected


def _assert_sections_contract(payload: dict[str, Any]) -> bool:
    sections = payload.get("sections")
    if not isinstance(sections, dict) or not sections:
        return False

    runner_status = sections.get("runner_status")
    if not isinstance(runner_status, dict):
        return False
    if runner_status.get("status") not in {"ok", "unknown"}:
        return False
    if runner_status.get("source") != "railway_runtime_env":
        return False

    latest_system_run = sections.get("latest_system_run")
    if not isinstance(latest_system_run, dict):
        return False
    if latest_system_run.get("status") not in {"unavailable", "ok", "unknown"}:
        return False
    if latest_system_run.get("status") == "unavailable" and latest_system_run.get("source") not in {
        "not_configured",
        "local_artifact",
    }:
        return False

    for key in ("daily_review", "pnl_snapshot", "outcome_review"):
        section = sections.get(key)
        if not isinstance(section, dict):
            return False
        if section.get("status") != "mock":
            return False
    return True


def _assert_no_write_affordance(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, separators=(",", ":")).lower()
    blocked_tokens = (
        "supabase_service_role_key",
        "service_role_key",
        "broker_api_key",
        "broker_api_secret",
        "broker_secret",
        "insert",
        "update",
        "delete",
        "create_order",
        "place_order",
        "execute_order",
        "live_order",
        "real_order",
    )
    return not any(token in serialized for token in blocked_tokens)


def main() -> int:
    env = _require_env()
    endpoint = _build_endpoint(env["MINIAPP_SMOKE_ENDPOINT_URL"])

    valid_auth = _telegram_init_data(env["MINIAPP_SMOKE_BOT_TOKEN"], env["MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID"])
    valid_unauth = _telegram_init_data(env["MINIAPP_SMOKE_BOT_TOKEN"], env["MINIAPP_SMOKE_UNAUTHORIZED_TELEGRAM_USER_ID"])
    invalid = _telegram_init_data(env["MINIAPP_SMOKE_BOT_TOKEN"], env["MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID"], tampered=True)

    oversized_padding = "x" * (MAX_BODY_BYTES + 256)

    cases: list[tuple[str, bytes, str, int]] = [
        ("A_non_json_content_type", _json_body(valid_auth), "text/plain", 415),
        ("B_oversized_payload", _json_body(valid_auth, oversized_padding), "application/json", 413),
        ("C_invalid_init_data", _json_body(invalid), "application/json", 401),
        ("D_unauthorized_operator", _json_body(valid_unauth), "application/json", 403),
        ("E_authorized_operator", _json_body(valid_auth), "application/json", 200),
    ]

    results: list[CaseResult] = []
    all_passed = True

    for name, body, ct, expected in cases:
        status, text = _send(endpoint, body, ct)
        passed = status == expected
        detail = f"expected={expected} actual={status}"
        if name == "E_authorized_operator" and status == 200:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                passed = False
                detail += " json_parse_failed"
            else:
                checks = [
                    _assert_json_field(payload, ["status"], "ok"),
                    _assert_json_field(payload, ["guardrails", "read_only"], True),
                    _assert_json_field(payload, ["guardrails", "paper_trade_only"], True),
                    _assert_json_field(payload, ["guardrails", "decision_support_only"], True),
                    _assert_json_field(payload, ["guardrails", "no_broker_execution"], True),
                    _assert_json_field(payload, ["guardrails", "no_real_money_execution"], True),
                    _assert_sections_contract(payload),
                    _assert_no_write_affordance(payload),
                ]
                if not all(checks):
                    passed = False
                    detail += " response_contract_assert_failed"
        elif name != "E_authorized_operator":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                safe_err = payload.get("error") or payload.get("status")
                detail += f" safe_field={safe_err}"

        results.append(CaseResult(name=name, status_code=status, passed=passed, detail=detail))
        all_passed = all_passed and passed

    print(f"[miniapp_api_smoke] endpoint={endpoint}")
    for r in results:
        label = "PASS" if r.passed else "FAIL"
        print(f"[{label}] {r.name} status={r.status_code} {r.detail}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"[miniapp_api_smoke] ERROR: {exc}")
        sys.exit(2)
