from __future__ import annotations

import json

import scripts.operator_smoke_test as smoke


def test_run_case_transport_checks_pass(monkeypatch):
    payload = {
        "ok": True,
        "handled": True,
        "replied": True,
        "send_result": {"delivered": True},
    }
    monkeypatch.setattr(smoke, "_send_command", lambda *args, **kwargs: (200, json.dumps(payload)))

    result = smoke._run_case(
        name="A_help",
        command="/help",
        must_include=["/daily_review"],
        must_exclude_patterns=[],
        webhook_url="https://example.com",
        webhook_secret=None,
        chat_id="1",
        user_id="2",
    )

    assert result.passed is True
    assert result.response_text_verification == "SKIPPED_current_webhook_contract"
    assert any(c["name"] == "http_status_200" and c["passed"] for c in result.checks)
    assert any(c["name"] == "json_ok_true" and c["passed"] for c in result.checks)
    assert any(c["name"] == "json_handled_true" and c["passed"] for c in result.checks)
    assert any(c["name"] == "json_replied_true" and c["passed"] for c in result.checks)
    assert any(c["name"] == "send_result_delivered_true" and c["passed"] for c in result.checks)


def test_write_reports_contains_skipped_marker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = smoke.SmokeCaseResult(
        name="A_help",
        command="/help",
        passed=True,
        checks=[{"name": "http_status_200", "passed": True}],
        response_snippet='{"ok":true}',
        status_code=200,
    )

    smoke._write_reports("production", "321", "2026-04-30T00:00:00+00:00", [result], verify_supabase=False)

    md = (tmp_path / "operator_smoke_report.md").read_text(encoding="utf-8")
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))

    assert "SKIPPED_current_webhook_contract" in md
    assert js["response_text_verification"] == "SKIPPED_current_webhook_contract"
