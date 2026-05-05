from __future__ import annotations

import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

import scripts.railway_step91c_log_evidence as s


def test_missing_token_not_configured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e1")
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py", "--service-names", "paper-daily-runner"])
    assert s.main() == 0
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["overall_status"] == "NOT_CONFIGURED"
    assert payload["fallback_warning_check"] == "NOT_CONFIGURED"


def test_secret_warning_counts_match_but_not_snippet():
    now = datetime.now(timezone.utc)
    entries = [{"message": "SUPABASE_KEY fallback with sb_secret_x", "timestamp": now.isoformat()}]
    matches, redacted, snippets = s._scan_entries(entries, now - timedelta(minutes=10))
    assert matches == 1
    assert redacted == 1
    assert snippets == []


def test_scan_entries_respects_window():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=3)).isoformat()
    entries = [{"message": "SUPABASE_KEY fallback detected", "timestamp": old}]
    matches, redacted, _ = s._scan_entries(entries, now - timedelta(minutes=30))
    assert matches == 0
    assert redacted == 0


def test_configured_graphql_error_is_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("graphql_errors")))
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["overall_status"] == "FAIL"
    assert payload["fallback_warning_check"] == "FAIL"
    assert payload["connectivity_check"] == "NOT_RUN"


def test_configured_no_logs_is_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"project": {"service": {"deployments": {"edges": []}}}}})
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["logs_read_count"] == 0
    assert payload["overall_status"] == "FAIL"
    assert payload["fallback_warning_check"] == "FAIL"
    assert payload["raw_logs_included"] is False


def test_configured_warning_with_secret_makes_fail_and_redacted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    payload = {
        "data": {
            "project": {
                "service": {
                    "deployments": {
                        "edges": [{"node": {"logs": {"edges": [{"node": {"message": "SUPABASE_KEY fallback sb_secret_x", "timestamp": datetime.now(timezone.utc).isoformat()}}]}}}]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: payload)
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py", "--service-names", "paper-daily-runner"])
    s.main()
    report = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert report["fallback_warning_check"] == "FAIL"
    assert report["fallback_warning_matches_count"] == 1
    assert report["redacted_warning_matches_count"] == 1
    assert report["safe_snippets"] == []
    assert report["raw_logs_included"] is False


def test_scan_entries_counts_service_role_warning_redacted():
    now = datetime.now(timezone.utc)
    entries = [{"message": "SUPABASE_KEY fallback using SUPABASE_SERVICE_ROLE_KEY service_role value", "timestamp": now.isoformat()}]
    matches, redacted, snippets = s._scan_entries(entries, now - timedelta(minutes=5))
    assert matches == 1
    assert redacted == 1
    assert snippets == []


def test_console_summary_includes_safe_diagnostic_fields(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    payload = {
        "data": {
            "project": {
                "service": {
                    "deployments": {
                        "edges": [{"node": {"logs": {"edges": [{"node": {"message": "all good", "timestamp": datetime.now(timezone.utc).isoformat()}}]}}}]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: payload)
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py", "--service-names", "paper-daily-runner"])
    s.main()
    out = capsys.readouterr().out
    assert "overall_status=PASS" in out
    assert "fallback_warning_check=PASS" in out
    assert "logs_read_count=1" in out
    assert "railway_api_http_status=None" in out
    assert "railway_api_error_kind=None" in out
    assert "limitation=Staged changes check remains NOT_CONFIGURED in this step." in out


def test_http_401_reports_safe_excerpt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    body = b'{"error":"token bad","token":"abc","SUPABASE_SECRET_KEY=sb_secret_123"}'
    err = HTTPError("https://example", 401, "unauthorized", hdrs=None, fp=BytesIO(body))
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: (_ for _ in ()).throw(err))
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["overall_status"] == "FAIL"
    assert payload["railway_api_http_status"] == 401
    assert payload["railway_api_error_kind"] == "HTTPError"
    assert "sb_secret_" not in payload["railway_api_error_excerpt_redacted"]
    assert "token" in payload["railway_api_error_excerpt_redacted"]


def test_http_422_reports_safe_excerpt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    body = b'{"errors":[{"message":"Cannot query field logsX on type Deployment"}]}'
    err = HTTPError("https://example", 422, "unprocessable", hdrs=None, fp=BytesIO(body))
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: (_ for _ in ()).throw(err))
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["railway_api_http_status"] == 422
    assert "Cannot query field" in payload["railway_api_error_excerpt_redacted"]


def test_http_403_reports_safe_excerpt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    body = b'{"message":"forbidden","Authorization":"Bearer abc123"}'
    err = HTTPError("https://example", 403, "forbidden", hdrs=None, fp=BytesIO(body))
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: (_ for _ in ()).throw(err))
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["railway_api_http_status"] == 403
    assert "Bearer" not in payload["railway_api_error_excerpt_redacted"]


def test_api_url_override_used(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setenv("RAILWAY_API_URL", "https://backboard.railway.com/graphql/v2")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"project": {"service": {"deployments": {"edges": []}}}}})
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["railway_api_url_host_only"] == "backboard.railway.com"
    assert payload["railway_api_endpoint_label"] == "https://backboard.railway.com"


def test_workspace_default_mode_does_not_call_me_query(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    calls = []

    def _fake(token, query, variables, api_url):
        calls.append(query)
        return {"data": {"project": {"service": {"deployments": {"edges": []}}}}}

    monkeypatch.setattr(s, "_read_only_graphql", _fake)
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    assert all("me { email }" not in q for q in calls)
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["connectivity_check"] == "NOT_RUN"
    assert payload["connectivity_reason"] == "workspace_probe_not_configured"


def test_account_mode_calls_me_query(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    calls = []

    def _fake(token, query, variables, api_url):
        calls.append(query)
        if "me { email }" in query:
            return {"data": {"me": {"email": "x@example.com"}}}
        return {"data": {"project": {"service": {"deployments": {"edges": []}}}}}

    monkeypatch.setattr(s, "_read_only_graphql", _fake)
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    s.main()
    assert any("me { email }" in q for q in calls)
