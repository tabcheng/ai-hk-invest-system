from __future__ import annotations

import json
from io import BytesIO
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

import scripts.railway_step91c_log_evidence as s


def _run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railway_step91c_log_evidence.py"])
    assert s.main() == 0
    return json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))


def test_missing_config_not_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    payload = _run(tmp_path, monkeypatch)
    assert payload["overall_status"] == "NOT_CONFIGURED"


def test_environmentlogs_pass_no_warning(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": [{"message": "all good", "timestamp": datetime.now(timezone.utc).isoformat(), "severity": "INFO"}]}})
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "PASS"
    assert p["railway_query_stage"] == "environment_logs"
    assert p["logs_read_count"] == 1


def test_environmentlogs_fail_warning_secret_redacted(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": [{"message": "SUPABASE_KEY fallback sb_secret_x", "timestamp": datetime.now(timezone.utc).isoformat()}]}})
    p = _run(tmp_path, monkeypatch)
    assert p["fallback_warning_check"] == "FAIL"
    assert p["redacted_warning_matches_count"] == 1
    assert p["safe_snippets"] == []


def test_environmentlogs_edges_shape_supported(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": {"edges": [{"node": {"message": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}}]}}})
    p = _run(tmp_path, monkeypatch)
    assert p["logs_read_count"] == 1


def test_configured_zero_logs_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": []}})
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "FAIL"
    assert p["logs_read_count"] == 0
    assert p["logs_returned_count"] == 0


def test_http_403_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    err = HTTPError("https://example", 403, "forbidden", hdrs=None, fp=BytesIO(b'{"message":"forbidden","Authorization":"Bearer abc"}'))
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: (_ for _ in ()).throw(err))
    p = _run(tmp_path, monkeypatch)
    assert p["railway_log_query_mode"] == "environment"
    assert p["railway_query_stage"] == "environment_logs"
    assert p["railway_api_http_status"] == 403
    assert p["railway_api_error_kind"] == "HTTPError"


def test_service_ids_build_filter(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setenv("RAILWAY_LOG_SERVICE_IDS", "svc1,svc2")
    captured = {}

    def _fake(_token, _query, variables, _api_url):
        captured["variables"] = variables
        return {"data": {"environmentLogs": [{"message": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}]}}

    monkeypatch.setattr(s, "_read_only_graphql", _fake)
    p = _run(tmp_path, monkeypatch)
    assert p["checked_service_ids"] == ["svc1", "svc2"]
    assert captured["variables"]["filter"] == "@service:svc1 OR @service:svc2"


def test_report_never_includes_raw_logs_or_unredacted_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(
        s,
        "_read_only_graphql",
        lambda *a, **k: {
            "data": {
                "environmentLogs": [
                    {"message": "SUPABASE_KEY fallback using sb_secret_foo", "timestamp": datetime.now(timezone.utc).isoformat()}
                ]
            }
        },
    )
    p = _run(tmp_path, monkeypatch)
    assert p["raw_logs_included"] is False
    assert p["secrets_redacted"] is True
    assert "sb_secret_" not in json.dumps(p)


def test_only_old_clean_logs_fail_not_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": [{"message": "old clean", "timestamp": old_ts}]}})
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "FAIL"
    assert p["fallback_warning_check"] == "FAIL"
    assert p["logs_returned_count"] == 1
    assert p["logs_read_count"] == 0


def test_old_warning_with_recent_clean_is_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    new_ts = datetime.now(timezone.utc).isoformat()
    monkeypatch.setattr(
        s,
        "_read_only_graphql",
        lambda *a, **k: {"data": {"environmentLogs": [{"message": "SUPABASE_KEY fallback old", "timestamp": old_ts}, {"message": "recent clean", "timestamp": new_ts}]}},
    )
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "PASS"
    assert p["fallback_warning_matches_count"] == 0
    assert p["logs_read_count"] == 1


def test_recent_warning_is_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(
        s,
        "_read_only_graphql",
        lambda *a, **k: {"data": {"environmentLogs": [{"message": "SUPABASE_KEY fallback recent", "timestamp": datetime.now(timezone.utc).isoformat()}]}},
    )
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "FAIL"
    assert p["fallback_warning_check"] == "FAIL"


def test_unknown_timestamp_alone_does_not_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e")
    monkeypatch.setattr(s, "_read_only_graphql", lambda *a, **k: {"data": {"environmentLogs": [{"message": "clean unknown ts"}]}})
    p = _run(tmp_path, monkeypatch)
    assert p["overall_status"] == "FAIL"
    assert p["logs_unknown_timestamp_count"] == 1
    assert p["logs_read_count"] == 0


def test_scan_window():
    now = datetime.now(timezone.utc)
    m, r, in_window, unknown_ts, _ = s._scan_entries([{"message": "SUPABASE_KEY fallback", "timestamp": (now - timedelta(hours=3)).isoformat()}], now - timedelta(minutes=5))
    assert (m, r, in_window, unknown_ts) == (0, 0, 0, 0)
