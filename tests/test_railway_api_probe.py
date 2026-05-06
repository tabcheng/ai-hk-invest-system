from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError

import scripts.railway_api_probe as s


def _run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert s.main() == 0
    return json.loads((tmp_path / s.REPORT_JSON).read_text(encoding="utf-8"))


def test_missing_token_not_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("RAILWAY_TOKEN", raising=False)
    payload = _run(tmp_path, monkeypatch)
    assert payload["overall_status"] == "NOT_CONFIGURED"
    assert payload["project_metadata_status"] == "NOT_CONFIGURED"


def test_metadata_services_logs_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e1")
    monkeypatch.setenv("RAILWAY_LOG_SERVICE_IDS", "s1")

    def fake(api_url, token, query, variables):
        if "project(id:$projectId){id name}" in query:
            return 200, {"data": {"project": {"id": "p1", "name": "P"}}}
        if "environments" in query:
            return 200, {"data": {"project": {"environments": {"edges": [{"node": {"id": "e1", "name": "prod"}}]}, "services": {"edges": [{"node": {"id": "s1", "name": "runner"}}]}}}}
        return 200, {"data": {"environmentLogs": [{"message": "secret", "timestamp": "2026-05-05T00:00:00Z"}]}}

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    assert p["project_metadata_status"] == "PASS"
    assert p["project_services_environments_status"] == "PASS"
    assert p["environment_logs_probe_status"] == "PASS"


def test_metadata_403_not_run_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    err = HTTPError("https://x", 403, "forbidden", hdrs=None, fp=BytesIO(b"forbidden"))
    monkeypatch.setattr(s, "_graphql", lambda *a, **k: (_ for _ in ()).throw(err))
    p = _run(tmp_path, monkeypatch)
    assert p["project_metadata_status"] == "FAIL"
    assert p["environment_logs_probe_status"] == "NOT_RUN"


def test_metadata_pass_logs_403(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e1")
    calls = {"n": 0}

    def fake(*_a, **_k):
        calls["n"] += 1
        if calls["n"] <= 2:
            if calls["n"] == 1:
                return 200, {"data": {"project": {"id": "p1", "name": "P"}}}
            return 200, {"data": {"project": {"environments": {"edges": [{"node": {"id": "e1"}}]}, "services": {"edges": []}}}}
        raise HTTPError("https://x", 403, "forbidden", hdrs=None, fp=BytesIO(b"bad token Bearer abc"))

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    assert p["project_metadata_status"] == "PASS"
    assert p["environment_logs_probe_status"] == "FAIL"
    assert p["environment_logs_http_status"] == 403


def test_missing_environment_or_service_ids_fail_diagnostic(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "missing")
    monkeypatch.setenv("RAILWAY_LOG_SERVICE_IDS", "s1,s2")

    def fake(*_a, **_k):
        q = _a[2]
        if "project(id:$projectId){id name}" in q:
            return 200, {"data": {"project": {"id": "p1"}}}
        if "environments" in q:
            return 200, {"data": {"project": {"environments": {"edges": [{"node": {"id": "e1"}}]}, "services": {"edges": [{"node": {"id": "s1"}}]}}}}
        return 200, {"data": {"environmentLogs": []}}

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    assert p["configured_environment_id_found"] is False
    assert p["missing_service_ids"] == ["s2"]
    assert p["overall_status"] == "FAIL"


def test_no_raw_message_and_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "e1")

    def fake(*_a, **_k):
        q = _a[2]
        if "project(id:$projectId){id name}" in q:
            return 200, {"data": {"project": {"id": "p1"}}}
        if "environments" in q:
            return 200, {"data": {"project": {"environments": {"edges": [{"node": {"id": "e1"}}]}, "services": {"edges": []}}}}
        return 200, {"errors": [{"message": "forbidden Bearer abc"}]}

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    report_text = json.dumps(p)
    assert "Bearer abc" not in report_text
    assert "forbidden Bearer abc" not in report_text
    assert "[REDACTED]" in (p["railway_api_error_excerpt_redacted"] or "")


def test_account_probe_default_not_run(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    p = _run(tmp_path, monkeypatch)
    assert p["account_probe_status"] == "NOT_RUN"


def test_account_probe_only_when_account(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)

    def fake(*_a, **_k):
        return 200, {"data": {"me": {"name": "n", "email": "e"}}}

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    assert p["account_probe_status"] == "PASS"
    assert p["project_metadata_status"] == "NOT_CONFIGURED"
    assert p["environment_logs_probe_status"] == "NOT_RUN"


def test_account_probe_fail_without_project_is_overall_fail(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)

    def fake(*_a, **_k):
        return 200, {"errors": [{"message": "forbidden"}]}

    monkeypatch.setattr(s, "_graphql", fake)
    p = _run(tmp_path, monkeypatch)
    assert p["account_probe_status"] == "FAIL"
    assert p["overall_status"] == "FAIL"
    assert p["project_metadata_status"] == "NOT_CONFIGURED"
    assert p["environment_logs_probe_status"] == "NOT_RUN"


def test_missing_project_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    payload = _run(tmp_path, monkeypatch)
    assert payload["project_metadata_status"] == "NOT_CONFIGURED"


def test_missing_environment_not_configured_logs_probe(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "p1")

    def fake(*_a, **_k):
        q = _a[2]
        if "project(id:$projectId){id name}" in q:
            return 200, {"data": {"project": {"id": "p1"}}}
        return 200, {"data": {"project": {"environments": {"edges": []}, "services": {"edges": []}}}}

    monkeypatch.setattr(s, "_graphql", fake)
    payload = _run(tmp_path, monkeypatch)
    assert payload["environment_logs_probe_status"] == "NOT_CONFIGURED"
