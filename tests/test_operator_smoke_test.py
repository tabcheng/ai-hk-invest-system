from __future__ import annotations

import json
import pytest

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
    assert any(c["name"] == "send_result_delivered_true_when_available" and c["passed"] for c in result.checks)


def test_run_case_send_result_not_available_is_skipped(monkeypatch):
    payload = {
        "ok": True,
        "handled": True,
        "replied": True,
    }
    monkeypatch.setattr(smoke, "_send_command", lambda *args, **kwargs: (200, json.dumps(payload)))
    result = smoke._run_case("A_help", "/help", [], [], "https://example.com", None, "1", "2")
    assert result.passed is True
    assert any(
        c["name"] == "send_result_delivered_true_when_available"
        and c["actual"] == "SKIPPED_not_available"
        and c["passed"] is True
        and c["status"] == "SKIPPED_not_available"
        for c in result.checks
    )


def test_run_case_send_result_delivered_false_fails(monkeypatch):
    payload = {
        "ok": True,
        "handled": True,
        "replied": True,
        "send_result": {"delivered": False},
    }
    monkeypatch.setattr(smoke, "_send_command", lambda *args, **kwargs: (200, json.dumps(payload)))
    result = smoke._run_case("A_help", "/help", [], [], "https://example.com", None, "1", "2")
    assert result.passed is False
    assert any(
        c["name"] == "send_result_delivered_true_when_available"
        and c["passed"] is False
        and c["status"] == "FAIL"
        and c["actual"] is False
        for c in result.checks
    )


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

    smoke._write_reports(
        "production",
        "321",
        "2026-04-30T00:00:00+00:00",
        [result],
        verify_supabase=False,
        qa_marker="operator-smoke-qa",
    )

    md = (tmp_path / "operator_smoke_report.md").read_text(encoding="utf-8")
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))

    assert "SKIPPED_current_webhook_contract" in md
    assert "transport_verification" in md
    assert js["response_text_verification"] == "SKIPPED_current_webhook_contract"
    assert js["transport_verification"] == "PASS"
    assert js["supabase_verification"]["status"] == "SKIPPED"


def test_invalid_test_run_id_fails_fast_and_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPERATOR_WEBHOOK_TEST_URL", "https://example.com")
    monkeypatch.setenv("OPERATOR_TEST_CHAT_ID", "1")
    monkeypatch.setenv("OPERATOR_TEST_USER_ID", "2")
    monkeypatch.setattr(smoke, "_send_command", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call")))
    monkeypatch.setattr("sys.argv", ["operator_smoke_test.py", "--test-run-id", "abc"])
    with pytest.raises(smoke.SmokeHarnessError):
        smoke.main()

    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))
    assert js["overall_result"] == "FAIL"
    assert js["reason"] == "invalid test_run_id"
    assert "positive integer" in js["guidance"]


def test_verify_supabase_true_missing_url_fails_with_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPERATOR_WEBHOOK_TEST_URL", "https://example.com")
    monkeypatch.setenv("OPERATOR_TEST_CHAT_ID", "1")
    monkeypatch.setenv("OPERATOR_TEST_USER_ID", "2")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret")
    monkeypatch.setattr(
        smoke,
        "_send_command",
        lambda *args, **kwargs: (200, json.dumps({"ok": True, "handled": True, "replied": True, "send_result": {"delivered": True}})),
    )
    monkeypatch.setattr("sys.argv", ["operator_smoke_test.py", "--test-run-id", "31", "--verify-supabase", "true"])
    with pytest.raises(smoke.SmokeHarnessError):
        smoke.main()
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))
    assert js["supabase_verification"]["status"] == "FAIL"
    assert "SUPABASE_URL" in js["supabase_verification"]["reason"]


def test_verify_supabase_true_missing_service_role_key_fails_with_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPERATOR_WEBHOOK_TEST_URL", "https://example.com")
    monkeypatch.setenv("OPERATOR_TEST_CHAT_ID", "1")
    monkeypatch.setenv("OPERATOR_TEST_USER_ID", "2")
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setattr(
        smoke,
        "_send_command",
        lambda *args, **kwargs: (200, json.dumps({"ok": True, "handled": True, "replied": True, "send_result": {"delivered": True}})),
    )
    monkeypatch.setattr("sys.argv", ["operator_smoke_test.py", "--test-run-id", "31", "--verify-supabase", "true"])
    with pytest.raises(smoke.SmokeHarnessError):
        smoke.main()
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))
    assert js["supabase_verification"]["status"] == "FAIL"
    assert "SUPABASE_SERVICE_ROLE_KEY" in js["supabase_verification"]["reason"]


def test_supabase_verification_pass_with_matching_row(monkeypatch):
    captured = {"url": ""}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return b'[{"id":1}]'

    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret")
    def _fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        return _Resp()
    monkeypatch.setattr(smoke.request, "urlopen", _fake_urlopen)
    result = smoke._verify_supabase_decision_note("31", "mk")
    assert result.status == "PASS"
    assert result.matched_rows_count == 1
    assert "source_command=eq.%2Fdaily_review" in captured["url"]


def test_supabase_verification_fail_when_no_rows(monkeypatch):
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self): return b'[]'

    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret")
    monkeypatch.setattr(smoke.request, "urlopen", lambda req, timeout=30: _Resp())
    result = smoke._verify_supabase_decision_note("31", "mk")
    assert result.status == "FAIL"
    assert result.matched_rows_count == 0


def test_supabase_query_error_is_redacted(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "super-secret")
    monkeypatch.setattr(smoke.request, "urlopen", lambda req, timeout=30: (_ for _ in ()).throw(RuntimeError("key=super-secret")))
    result = smoke._verify_supabase_decision_note("31", "mk")
    assert result.status == "FAIL"
    assert "super-secret" not in (result.guidance or "")
    assert "[REDACTED]" in (result.guidance or "")


def test_qa_marker_included_in_decision_note_command():
    marker = "operator-smoke-20260430T000000Z-aaaaaa"
    cmd = (
        "/decision_note scope=run run_id=31 source_command=/daily_review "
        f"human_action=observe note=QA smoke test only; no execution. marker={marker}"
    )
    cases = smoke._build_smoke_cases("31", cmd, "/decision_note scope=stock run_id=31 stock_id=0700.HK source_command=/daily_review human_action=observe note=ok")
    assert any(marker in command for _, command, _, _ in cases)


def test_command_coverage_includes_step64_cases():
    cases = smoke._build_smoke_cases("31", "/decision_note scope=run run_id=31 source_command=/daily_review human_action=observe note=ok", "/decision_note scope=stock run_id=31 stock_id=0700.HK source_command=/daily_review human_action=observe note=ok")
    commands = [command for _, command, _, _ in cases]
    assert "/runs" in commands
    assert "/runner_status" in commands
    assert "/risk_review 31" in commands
    assert "/pnl_review" in commands
    assert "/outcome_review" in commands
    assert any("/decision_note scope=run" in command for command in commands)
    assert any("/decision_note scope=stock" in command for command in commands)


def test_redact_no_secrets_printed(monkeypatch):
    monkeypatch.setenv("OPERATOR_WEBHOOK_TEST_URL", "https://secret.example")
    monkeypatch.setenv("OPERATOR_WEBHOOK_SECRET", "abc123")
    monkeypatch.setenv("SUPABASE_URL", "https://project.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    text = "url=https://secret.example token=abc123 sb=https://project.supabase.co key=service-role-secret"
    redacted = smoke._redact(text)
    assert "https://secret.example" not in redacted
    assert "abc123" not in redacted
    assert "https://project.supabase.co" not in redacted
    assert "service-role-secret" not in redacted
    assert "[REDACTED]" in redacted


def test_write_reports_transport_pass_supabase_fail_overall_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = smoke.SmokeCaseResult(
        name="A_help",
        command="/help",
        passed=True,
        checks=[],
        response_snippet="{}",
        status_code=200,
    )
    supabase_result = smoke.SupabaseVerificationResult(
        status="FAIL",
        table="human_decision_journal_entries",
        qa_marker="mk",
        matched_rows_count=0,
        reason="no row",
    )
    smoke._write_reports("production", "31", "2026-04-30T00:00:00+00:00", [result], True, "mk", supabase_result=supabase_result)
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))
    assert js["transport_verification"] == "PASS"
    assert js["supabase_verification"]["status"] == "FAIL"
    assert js["overall_result"] == "FAIL"


def test_write_reports_transport_fail_supabase_skipped_overall_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = smoke.SmokeCaseResult(
        name="A_help",
        command="/help",
        passed=False,
        checks=[],
        response_snippet="{}",
        status_code=500,
    )
    smoke._write_reports("production", "31", "2026-04-30T00:00:00+00:00", [result], False, "mk")
    js = json.loads((tmp_path / "operator_smoke_report.json").read_text(encoding="utf-8"))
    assert js["transport_verification"] == "FAIL"
    assert js["supabase_verification"]["status"] == "SKIPPED"
    assert js["overall_result"] == "FAIL"
