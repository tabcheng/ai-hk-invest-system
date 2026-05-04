from __future__ import annotations

import json

import scripts.step91c_runtime_acceptance as s


def _http_error(code: int):
    return s.HTTPError("https://example.com", code, "x", None, None)


def test_required_table_404_is_fail(monkeypatch):
    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: (_ for _ in ()).throw(_http_error(404)))
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "runs", 1440, required=True)
    assert result["status"] == "FAIL"


def test_optional_latest_system_runs_404_is_not_configured(monkeypatch):
    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: (_ for _ in ()).throw(_http_error(404)))
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "latest_system_runs", 1440, required=False)
    assert result["status"] == "NOT_CONFIGURED"


def test_required_table_400_is_fail(monkeypatch):
    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: (_ for _ in ()).throw(_http_error(400)))
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "signals", 1440, required=True)
    assert result["status"] == "FAIL"


def test_optional_latest_system_runs_400_is_not_configured(monkeypatch):
    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: (_ for _ in ()).throw(_http_error(400)))
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "latest_system_runs", 1440, required=False)
    assert result["status"] == "NOT_CONFIGURED"


def test_required_table_stale_row_is_fail(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return b'[{"created_at":"2020-01-01T00:00:00Z"}]'

    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: _Resp())
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "runs", 1, required=True)
    assert result["status"] == "FAIL"
    assert result["freshness"] == "STALE"
    assert isinstance(result["age_minutes"], float)


def test_required_table_fresh_row_pass_with_age_minutes(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return b'[{"created_at":"2099-01-01T00:00:00Z"}]'

    monkeypatch.setattr(s.request, "urlopen", lambda req, timeout=30: _Resp())
    result = s._check_table("https://a.supabase.co", "sb_secret_x", "runs", 10_000_000, required=True)
    assert result["status"] == "PASS"
    assert "age_minutes" in result


def test_report_generated_when_smoke_reports_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://a.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_x")
    monkeypatch.setattr(s, "_check_table", lambda *args, **kwargs: {"status": "PASS", "freshness": "FRESH", "age_minutes": 1.0})
    monkeypatch.setattr("sys.argv", ["step91c_runtime_acceptance.py", "--test-run-id", "31"])
    rc = s.main()
    payload = json.loads((tmp_path / "step91c_runtime_acceptance_report.json").read_text(encoding="utf-8"))
    assert payload["operator_smoke_report_status"] == "MISSING"
    assert payload["miniapp_smoke_report_status"] == "MISSING"
    assert payload["overall_status"] == "FAIL"
    assert rc == 1


def test_overall_status_cannot_pass_when_required_not_configured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUPABASE_URL", "https://a.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_x")

    def _fake_check(_base, _key, table, _freshness, required):
        if table == "runs":
            return {"status": "NOT_CONFIGURED", "reason": "http_404"}
        return {"status": "PASS", "freshness": "FRESH", "age_minutes": 1.0}

    monkeypatch.setattr(s, "_check_table", _fake_check)
    monkeypatch.setattr("sys.argv", ["step91c_runtime_acceptance.py", "--test-run-id", "31"])
    rc = s.main()
    payload = json.loads((tmp_path / "step91c_runtime_acceptance_report.json").read_text(encoding="utf-8"))
    assert payload["overall_status"] == "FAIL"
    assert rc == 1
