from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import scripts.railway_step91c_log_evidence as s


def test_missing_token_not_configured(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e1")
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    assert s.main() == 0
    payload = json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))
    assert payload["fallback_warning_check"] == "NOT_CONFIGURED"
    assert payload["raw_logs_included"] is False


def test_scan_entries_blocks_secret_like_values():
    now = datetime.now(timezone.utc)
    entries = [
        {"message": "SUPABASE_KEY fallback detected", "timestamp": now.isoformat()},
        {"message": "SUPABASE_KEY fallback with sb_secret_x should be blocked", "timestamp": now.isoformat()},
    ]
    matches, snippets = s._scan_entries(entries, now - timedelta(minutes=10))
    assert matches == 1
    assert all("sb_secret_" not in x for x in snippets)


def test_scan_entries_respects_window():
    now = datetime.now(timezone.utc)
    old = (now - timedelta(hours=3)).isoformat()
    entries = [{"message": "SUPABASE_KEY fallback detected", "timestamp": old}]
    matches, _ = s._scan_entries(entries, now - timedelta(minutes=30))
    assert matches == 0
