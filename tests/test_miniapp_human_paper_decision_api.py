import json
from tests.test_miniapp_review_shell_api import _authorized_request, _call


def _decision_body(monkeypatch):
    base = json.loads(_authorized_request(monkeypatch).decode())
    base.update({
        "business_date": "2026-05-09",
        "run_id": "run-1",
        "ticker": "0700.HK",
        "decision_type": "watch",
        "rationale_text": "paper review only",
        "guardrail_ack": True,
    })
    return json.dumps(base).encode()


def test_human_paper_decision_rejects_missing_content_type(monkeypatch):
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch), content_type=None)
    assert status.startswith("415")
    assert payload["error"] == "unsupported_media_type"


def test_human_paper_decision_validation_and_bounded_success(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    captured = {}
    def _record(*args, **kwargs):
        captured.update(kwargs)
        return {"id": "j-1"}
    monkeypatch.setattr("src.telegram_webhook_server.record_miniapp_human_paper_decision_journal", _record)
    monkeypatch.setattr("src.telegram_webhook_server.persist_decision_context_snapshot", lambda *args, **kwargs: {"id": "s-1", "status": "saved"})
    monkeypatch.setattr("src.telegram_webhook_server.build_human_decision_context_snapshot", lambda **kwargs: {"ticker": "0700.HK"})
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_decision_context_summary", lambda self: {"tickers": []})
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_ticker_level_paper_portfolio_review", lambda self: {"rows": []})
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch))
    assert status.startswith("200")
    assert payload["no_order_created"] is True
    assert payload["paper_trade_only"] is True
    assert captured["operator_user_id_hash_or_label"].startswith("tg_user_hash:")
    assert payload["journal_saved"] is True
    assert payload["snapshot_saved"] is True
    assert payload["journal_id"] == "j-1"
    assert payload["snapshot_id"] == "s-1"
    assert payload["ticker"] == "0700.HK"
    assert payload["decision_type"] == "watch"
    assert payload["confidence_label"] == "unknown"
    assert "HKT" in payload["saved_at_hkt"]
    assert "42" not in captured["operator_user_id_hash_or_label"]
    assert captured["operator_user_id_hash_or_label"] != "tg_user_hash:unknown"
    assert "init_data" not in captured
    assert "MINIAPP_ALLOWED_TELEGRAM_USER_IDS" not in json.dumps(captured)


def test_human_paper_decision_rejects_invalid_decision_type(monkeypatch):
    body = json.loads(_decision_body(monkeypatch).decode())
    body["decision_type"] = "buy"
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_decision_type"


def test_human_paper_decision_requires_guardrail_ack(monkeypatch):
    body = json.loads(_decision_body(monkeypatch).decode())
    body["guardrail_ack"] = False
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "guardrail_ack_required"


def test_human_paper_decision_rejects_invalid_business_date(monkeypatch):
    body = json.loads(_decision_body(monkeypatch).decode())
    body["business_date"] = "20260509"
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_business_date"


def test_human_paper_decision_rejects_invalid_quantity_and_notional(monkeypatch):
    body = json.loads(_decision_body(monkeypatch).decode())
    body["quantity_intent"] = -1
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_quantity_intent"

    body = json.loads(_decision_body(monkeypatch).decode())
    body["notional_intent"] = -1
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_notional_intent"


def test_human_paper_decision_rejects_bool_numeric_intents(monkeypatch):
    body = json.loads(_decision_body(monkeypatch).decode())
    body["quantity_intent"] = True
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_quantity_intent"

    body = json.loads(_decision_body(monkeypatch).decode())
    body["notional_intent"] = False
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", json.dumps(body).encode())
    assert status.startswith("400")
    assert payload["error"] == "invalid_notional_intent"


def test_human_paper_decision_unavailable_masks_exception(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    monkeypatch.setattr("src.telegram_webhook_server.record_miniapp_human_paper_decision_journal", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("secret x")))
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch))
    assert status.startswith("503")
    assert payload["error"] == "journal_unavailable"
    assert "secret" not in json.dumps(payload)


def test_human_paper_decision_snapshot_failure_still_returns_journal_saved(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    monkeypatch.setattr("src.telegram_webhook_server.record_miniapp_human_paper_decision_journal", lambda *args, **kwargs: {"id": "j-1"})
    monkeypatch.setattr("src.telegram_webhook_server.build_human_decision_context_snapshot", lambda **kwargs: {"ticker": "0700.HK"})
    monkeypatch.setattr("src.telegram_webhook_server.persist_decision_context_snapshot", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("secret token")))
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_decision_context_summary", lambda self: {"tickers": []})
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_ticker_level_paper_portfolio_review", lambda self: {"rows": []})
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch))
    assert status.startswith("200")
    assert payload["journal_saved"] is True
    assert payload["snapshot_saved"] is False
    assert payload["snapshot_id"] is None


def test_human_paper_decision_builder_failure_after_journal_write_is_partial_success(monkeypatch):
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    monkeypatch.setattr("src.telegram_webhook_server.record_miniapp_human_paper_decision_journal", lambda *args, **kwargs: {"id": "j-1"})
    monkeypatch.setattr("src.telegram_webhook_server.build_human_decision_context_snapshot", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider secret")))
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_decision_context_summary", lambda self: {"tickers": []})
    monkeypatch.setattr("src.miniapp_data_provider.SupabaseLatestSystemRunMiniAppReadDataProvider.get_ticker_level_paper_portfolio_review", lambda self: {"rows": []})
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch))
    assert status.startswith("200")
    assert payload["journal_saved"] is True
    assert payload["snapshot_saved"] is False


def test_miniapp_journal_snapshots_api_bounded_and_auth(monkeypatch):
    body = json.loads(_authorized_request(monkeypatch).decode())
    body["limit"] = 30
    monkeypatch.setattr("src.telegram_webhook_server._load_supabase_client", lambda: object())
    monkeypatch.setattr("src.telegram_webhook_server.build_recent_decision_context_snapshots_review", lambda *_a, **_k: {"items":[{"snapshot_id":"s1","ticker":"0700.HK"}], "limit":20})
    status, _, payload = _call("/miniapp/api/journal-snapshots", "POST", json.dumps(body).encode())
    assert status.startswith("200")
    assert payload["ok"] is True
    assert payload["limit"] == 20
    assert "snapshot_json" not in json.dumps(payload)
    assert "init_data" not in json.dumps(payload)


def test_miniapp_journal_snapshots_api_rejects_invalid_init_data():
    status, _, payload = _call("/miniapp/api/journal-snapshots", "POST", json.dumps({"init_data": "bad"}).encode())
    assert status.startswith("401")
    assert payload["ok"] is False
