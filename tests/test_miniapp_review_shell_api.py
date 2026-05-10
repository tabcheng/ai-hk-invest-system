import hashlib
import hmac
import io
import json
from urllib.parse import urlencode

from src.market_data.review_provider import MarketTickerSnapshot
from src.miniapp_data_provider import SupabaseLatestSystemRunMiniAppReadDataProvider
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
    daily = payload["sections"]["daily_review_summary"]
    assert daily["status"] == "ok"
    assert daily["paper_trade_only"] is True
    assert daily["review_readiness"] == "partial"
    assert daily["available_sections"] == ["latest_system_run"]
    assert daily["unavailable_sections"] == ["signals", "paper_pnl", "risk"]
    assert daily["data_timestamp_hkt"].endswith("HKT")
    assert daily["updated_at_hkt"].endswith("HKT")
    assert "data_timestamp" not in daily
    assert "updated_at" not in daily
    assert payload["sections"]["paper_pnl_summary"]["paper_trade_only"] is True
    assert payload["sections"]["risk_summary"]["paper_trade_only"] is True


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
    daily = payload["sections"]["daily_review_summary"]
    assert daily["status"] == "unavailable"
    assert daily["reason"] == "daily review summary is not available yet"
    assert payload["sections"]["paper_pnl_summary"]["status"] == "unavailable"
    assert payload["sections"]["risk_summary"]["status"] == "unavailable"
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


def test_miniapp_review_shell_paper_pnl_and_risk_summary_ok(monkeypatch):
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
    monkeypatch.setattr(
        "src.paper_trading.get_paper_position_pnl_review_snapshot",
        lambda _client: {
            "per_symbol": [{"stock": "0700.HK"}],
            "open_positions_count": 1,
            "closed_positions_count": 0,
            "total_realized_pnl": 12.0,
            "total_unrealized_pnl": -2.0,
        },
    )
    monkeypatch.setattr(
        "src.paper_trading.get_paper_risk_review_for_run",
        lambda _client, run_id: {"total_blocked_buys": 0, "total_warning_buys": 1, "total_executed_buys": 1},
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    pnl = payload["sections"]["paper_pnl_summary"]
    risk = payload["sections"]["risk_summary"]
    daily = payload["sections"]["daily_review_summary"]
    assert pnl["status"] == "ok"
    assert pnl["total_pnl"] == 10.0
    assert pnl["currency"] == "HKD"
    assert risk["status"] == "ok"
    assert risk["risk_level"] == "medium"
    assert daily["available_sections"] == ["latest_system_run", "paper_pnl", "risk"]


def test_miniapp_review_shell_paper_pnl_malformed_snapshot_is_unavailable_and_safe(monkeypatch):
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
    monkeypatch.setattr("src.paper_trading.get_paper_position_pnl_review_snapshot", lambda _client: "N/A")
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    assert payload["sections"]["paper_pnl_summary"]["status"] == "unavailable"


def test_miniapp_review_shell_risk_malformed_result_is_unavailable_and_safe(monkeypatch):
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
    monkeypatch.setattr(
        "src.paper_trading.get_paper_position_pnl_review_snapshot",
        lambda _client: {"per_symbol": [], "open_positions_count": "N/A", "closed_positions_count": True, "total_realized_pnl": "bad", "total_unrealized_pnl": False},
    )
    monkeypatch.setattr("src.paper_trading.get_paper_risk_review_for_run", lambda _client, run_id: "bad-risk-payload")
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    assert payload["sections"]["risk_summary"]["status"] == "unavailable"
    assert payload["sections"]["paper_pnl_summary"]["status"] == "ok"
    assert payload["sections"]["paper_pnl_summary"]["open_positions"] == 0
    assert payload["sections"]["paper_pnl_summary"]["closed_positions"] == 0
    assert payload["sections"]["paper_pnl_summary"]["total_pnl"] == 0.0
    assert payload["sections"]["paper_pnl_summary"]["limitations"]


def test_miniapp_review_shell_pnl_risk_helper_exceptions_do_not_leak_error_or_secret(monkeypatch):
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
    monkeypatch.setattr("src.paper_trading.get_paper_position_pnl_review_snapshot", lambda _client: (_ for _ in ()).throw(RuntimeError("secret-db-token")))
    monkeypatch.setattr("src.paper_trading.get_paper_risk_review_for_run", lambda _client, run_id: (_ for _ in ()).throw(RuntimeError("secret-risk-token")))
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    assert payload["sections"]["paper_pnl_summary"]["status"] == "unavailable"
    assert payload["sections"]["risk_summary"]["status"] == "unavailable"
    serialized = json.dumps(payload)
    assert "secret-db-token" not in serialized
    assert "secret-risk-token" not in serialized


def test_miniapp_review_shell_risk_bool_counts_are_bounded_with_limitation(monkeypatch):
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
    monkeypatch.setattr(
        "src.paper_trading.get_paper_position_pnl_review_snapshot",
        lambda _client: {"per_symbol": [], "open_positions_count": 0, "closed_positions_count": 0, "total_realized_pnl": 0.0, "total_unrealized_pnl": 0.0},
    )
    monkeypatch.setattr(
        "src.paper_trading.get_paper_risk_review_for_run",
        lambda _client, run_id: {"total_blocked_buys": False, "total_warning_buys": True, "total_executed_buys": True},
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    risk = payload["sections"]["risk_summary"]
    assert risk["status"] == "ok"
    assert risk["risk_level"] == "unknown"
    assert risk["limitations"]


def test_miniapp_review_shell_risk_summary_unavailable_when_latest_row_not_paper_only(monkeypatch):
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
            "summary_json": {"paper_trade_only": False},
        },
    )
    monkeypatch.setattr(
        "src.paper_trading.get_paper_risk_review_for_run",
        lambda _client, run_id: {"total_blocked_buys": 0, "total_warning_buys": 1, "total_executed_buys": 1},
    )
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    risk = payload["sections"]["risk_summary"]
    assert risk["status"] == "unavailable"


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
    daily = payload["sections"]["daily_review_summary"]
    assert daily["status"] == "unavailable"


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
    daily = payload["sections"]["daily_review_summary"]
    assert daily["processed_tickers"] == 0
    assert daily["successful_tickers"] == 0
    assert daily["failed_tickers"] == 0
    assert daily["review_readiness"] == "partial"


def test_miniapp_review_shell_signals_summary_ok(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Result:
        def __init__(self, data): self.data = data
    class _Query:
        def __init__(self, data): self._data = data
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self): return _Result(self._data)
    class _Client:
        def table(self, name):
            if name == "signals":
                return _Query([
                    {"stock": "0005.HK", "signal": "BUY", "reason": "trend up"},
                    {"stock": "0700.HK", "signal": "HOLD", "reason": "wait"},
                    {"stock": "1299.HK", "signal": "SELL", "reason": "trend down"},
                ])
            return _Query([])

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr("src.latest_system_runs_repository.get_latest_system_run", lambda client, source="paper_daily_runner": {"business_date":"2026-05-06","run_id":"42","status":"success","data_timestamp":"2026-05-06T01:02:03+00:00","updated_at":"2026-05-06T01:03:03+00:00","summary_json":{"paper_trade_only":True}})
    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["signals_summary"]
    assert section["status"] == "ok"
    assert section["paper_trade_only"] is True
    assert section["data_timestamp_hkt"].endswith("HKT")
    assert section["updated_at_hkt"].endswith("HKT")
    assert section["shown_positive_signals"] == 1
    assert section["shown_neutral_signals"] == 1
    assert section["shown_negative_signals"] == 1
    assert section["shown_unknown_signals"] == 0
    assert section["shown_signals"] == 3
    assert section["top_items_limit"] == 5
    assert "data_timestamp" not in section
    assert "updated_at" not in section



def test_miniapp_review_shell_signals_summary_requires_matching_run_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Result:
        def __init__(self, data):
            self.data = data

    class _Query:
        def __init__(self):
            self.filters = []
        def select(self, *_a, **_k): return self
        def eq(self, key, value):
            self.filters.append((key, value))
            return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self):
            if ("date", "2026-05-06") in self.filters and ("run_id", 42) in self.filters:
                return _Result([])
            return _Result([{"stock": "0005.HK", "signal": "BUY", "reason": "x"}])

    query = _Query()
    class _Client:
        def table(self, name):
            assert name == "signals"
            return query

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr("src.latest_system_runs_repository.get_latest_system_run", lambda client, source="paper_daily_runner": {"business_date":"2026-05-06","run_id":42,"status":"success","data_timestamp":"2026-05-06T01:02:03+00:00","updated_at":"2026-05-06T01:03:03+00:00","summary_json":{"paper_trade_only":True}})

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["signals_summary"]
    assert ("date", "2026-05-06") in query.filters
    assert ("run_id", 42) in query.filters
    assert section["status"] == "unavailable"

def test_miniapp_review_shell_decision_context_summary_partial_with_unavailable_market_data(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", FAKE_BOT_TOKEN)
    monkeypatch.setenv("MINIAPP_ALLOWED_TELEGRAM_USER_IDS", "42")
    monkeypatch.setattr("src.miniapp_auth.time.time", lambda: NOW_TS)

    class _Result:
        def __init__(self, data):
            self.data = data

    class _Query:
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self):
            return _Result([{"stock": "0700.HK", "signal": "BUY", "reason": "momentum"}])

    class _Client:
        def table(self, name):
            assert name == "signals"
            return _Query()

    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": 42,
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"paper_trade_only": True},
        },
    )

    status, _headers, payload = _call("/miniapp/api/review-shell", "POST", _authorized_request(monkeypatch))
    assert status.startswith("200")
    section = payload["sections"]["decision_context_summary"]
    assert section["status"] == "partial"
    assert section["context_readiness"] == "insufficient"
    assert section["tickers"][0]["market"]["status"] == "unavailable"
    assert any(x.get("key") == "strategy_version_missing" for x in section["tickers"][0]["missing_context"])

def test_decision_context_reuses_cached_signals_and_risk_summaries(monkeypatch):
    class _Result:
        def __init__(self, data):
            self.data = data

    class _Query:
        def __init__(self, counter):
            self.counter = counter
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self):
            self.counter["signals_query"] += 1
            return _Result([{"stock": "0700.HK", "signal": "BUY", "reason": "ok"}])

    class _Client:
        def __init__(self, counter):
            self.counter = counter
        def table(self, name):
            assert name == "signals"
            return _Query(self.counter)

    counter = {"signals_query": 0, "risk_helper": 0}

    def _risk_helper(_client, run_id):
        counter["risk_helper"] += 1
        return {"total_blocked_buys": 0, "total_warning_buys": 1, "total_executed_buys": 1}

    monkeypatch.setattr("src.paper_trading.get_paper_risk_review_for_run", _risk_helper)

    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": 42,
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"paper_trade_only": True},
        },
    )
    provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=_Client(counter))

    signals = provider.get_signals_summary()
    risk = provider.get_risk_summary()
    decision_context = provider.get_decision_context_summary()

    assert signals["status"] == "ok"
    assert risk["status"] == "ok"
    assert decision_context["status"] == "partial"
    assert counter["signals_query"] == 1
    assert counter["risk_helper"] == 1
    assert decision_context["tickers"][0]["signal"]["direction"] == signals["top_items"][0]["signal_label"]
    assert decision_context["tickers"][0]["risk"]["risk_level"] == risk["risk_level"]
    assert "raw_rows" not in decision_context
    assert "exception" not in decision_context
    assert "broker_execution" not in decision_context
    assert "order_creation" not in decision_context


def test_decision_context_data_source_missing_kept_when_market_unavailable(monkeypatch):
    class _Result:
        def __init__(self, data):
            self.data = data

    class _Query:
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self):
            return _Result([{"stock": "0700.HK", "signal": "BUY", "reason": "ok"}])

    class _Client:
        def table(self, name):
            assert name == "signals"
            return _Query()

    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": 42,
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"paper_trade_only": True},
        },
    )
    provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=_Client(), env={"MARKET_DATA_PROVIDER": "null"})
    section = provider.get_decision_context_summary()
    missing_keys = {x["key"] for x in section["tickers"][0]["missing_context"]}
    assert "data_source_missing" in missing_keys


def test_decision_context_data_source_missing_kept_for_existing_and_eodhd_unavailable(monkeypatch):
    class _Result:
        def __init__(self, data):
            self.data = data
    class _Query:
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self): return _Result([{"stock": "0700.HK", "signal": "BUY", "reason": "ok"}])
    class _Client:
        def table(self, name):
            assert name == "signals"
            return _Query()
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06", "run_id": 42, "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00", "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"paper_trade_only": True},
        },
    )
    for env in ({"MARKET_DATA_PROVIDER": "existing"}, {"MARKET_DATA_PROVIDER": "eodhd", "EODHD_API_TOKEN": ""}):
        provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=_Client(), env=env)
        section = provider.get_decision_context_summary()
        missing_keys = {x["key"] for x in section["tickers"][0]["missing_context"]}
        assert "data_source_missing" in missing_keys


def test_decision_context_data_source_missing_removed_when_market_ok(monkeypatch):
    class _Result:
        def __init__(self, data):
            self.data = data

    class _Query:
        def select(self, *_a, **_k): return self
        def eq(self, *_a, **_k): return self
        def order(self, *_a, **_k): return self
        def limit(self, *_a, **_k): return self
        def execute(self):
            return _Result([{"stock": "0700.HK", "signal": "BUY", "reason": "ok"}])

    class _Client:
        def table(self, name):
            assert name == "signals"
            return _Query()

    class _FakeProvider:
        def get_ticker_market_snapshot(self, ticker, business_date=None):
            return MarketTickerSnapshot(
                ticker=ticker,
                status="ok",
                reference_price=100.0,
                previous_close=99.0,
                change=1.0,
                change_pct=1.01,
                volume=1000.0,
                turnover=100000.0,
                currency="HKD",
                market="HKEX",
                data_source="eodhd",
                data_timestamp_hkt="2026-05-06T10:00:00+08:00",
                freshness_status="fresh",
                delay_minutes=0,
                adjustment_policy="vendor_default",
                confidence="medium",
                limitations=[],
            )

    monkeypatch.setattr("src.miniapp_data_provider.build_review_shell_market_data_provider", lambda env=None: _FakeProvider())
    monkeypatch.setattr(
        "src.latest_system_runs_repository.get_latest_system_run",
        lambda client, source="paper_daily_runner": {
            "business_date": "2026-05-06",
            "run_id": 42,
            "status": "success",
            "data_timestamp": "2026-05-06T01:02:03+00:00",
            "updated_at": "2026-05-06T01:03:03+00:00",
            "summary_json": {"paper_trade_only": True},
        },
    )
    provider = SupabaseLatestSystemRunMiniAppReadDataProvider(client=_Client())
    section = provider.get_decision_context_summary()
    missing_keys = {x["key"] for x in section["tickers"][0]["missing_context"]}
    assert "data_source_missing" not in missing_keys
