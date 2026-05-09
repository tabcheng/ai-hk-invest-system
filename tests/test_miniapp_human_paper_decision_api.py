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
    status, _, payload = _call("/miniapp/api/human-paper-decision", "POST", _decision_body(monkeypatch))
    assert status.startswith("200")
    assert payload["no_order_created"] is True
    assert payload["paper_trade_only"] is True
    assert captured["operator_user_id_hash_or_label"].startswith("tg_user_hash:")
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
