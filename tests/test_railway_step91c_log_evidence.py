from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

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
