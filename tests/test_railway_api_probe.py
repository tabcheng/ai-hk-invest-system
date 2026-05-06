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
    assert payload["token_fingerprint_match"] is None


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


def test_account_http_error_still_runs_curl_probe(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setenv("RAILWAY_CURL_PROBE", "on")
    err = HTTPError("https://x", 403, "forbidden", hdrs=None, fp=BytesIO(b"forbidden Bearer abc"))
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (_ for _ in ()).throw(err))

    class R:
        stdout = "200"

    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    p = _run(tmp_path, monkeypatch)
    assert p["account_probe_status"] == "FAIL"
    assert p["account_probe_http_status"] == 403
    assert p["curl_account_probe_status"] == "PASS"
    assert p["curl_account_probe_http_status"] == 200
    assert p["project_metadata_status"] == "NOT_RUN"
    assert "Bearer abc" not in json.dumps(p)


def test_account_generic_error_still_runs_curl_probe(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setenv("RAILWAY_CURL_PROBE", "on")
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("tls timeout")))

    class R:
        stdout = "403"

    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    p = _run(tmp_path, monkeypatch)
    assert p["account_probe_status"] == "FAIL"
    assert p["curl_account_probe_status"] == "FAIL"
    assert p["curl_account_probe_http_status"] == 403
    assert p["project_metadata_status"] == "NOT_RUN"
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
    assert p["project_metadata_status"] == "NOT_RUN"
    assert p["environment_logs_probe_status"] == "NOT_RUN"
    assert p["limitation"] == "Account probe failed; project metadata probe was skipped."


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


def test_fingerprint_match_true(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_TOKEN_SHA256_PREFIX", "e3b98a4da31a")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    payload = _run(tmp_path, monkeypatch)
    assert payload["token_fingerprint_expected_configured"] is True
    assert payload["token_fingerprint_match"] is True


def test_fingerprint_mismatch_fail_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_TOKEN_SHA256_PREFIX", "deadbeef0000")
    payload = _run(tmp_path, monkeypatch)
    assert payload["overall_status"] == "FAIL"
    assert payload["limitation"] == "GitHub runner RAILWAY_TOKEN fingerprint does not match expected prefix."


def test_fingerprint_not_printed(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_TOKEN_SHA256_PREFIX", "deadbeef0000")
    payload = _run(tmp_path, monkeypatch)
    text = json.dumps(payload)
    assert "deadbeef0000" not in text
    assert "e3b98a4da31a" not in text


def test_curl_probe_default_off(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (200, {"data": {"me": {"name": "n"}}}))
    payload = _run(tmp_path, monkeypatch)
    assert payload["curl_account_probe_status"] == "NOT_RUN"
    assert payload["curl_account_probe_http_status"] is None


def test_account_fail_and_curl_off_stays_not_run(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("dns fail")))
    payload = _run(tmp_path, monkeypatch)
    assert payload["account_probe_status"] == "FAIL"
    assert payload["curl_account_probe_status"] == "NOT_RUN"


def test_curl_probe_records_http_status_without_body(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setenv("RAILWAY_CURL_PROBE", "on")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (200, {"data": {"me": {"name": "n"}}}))

    class R:
        stdout = "403"

    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    payload = _run(tmp_path, monkeypatch)
    assert payload["curl_account_probe_status"] == "FAIL"
    assert payload["curl_account_probe_http_status"] == 403


def test_curl_probe_handles_subprocess_error(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setenv("RAILWAY_CURL_PROBE", "on")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (200, {"data": {"me": {"name": "n"}}}))
    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    payload = _run(tmp_path, monkeypatch)
    assert payload["curl_account_probe_status"] == "FAIL"
    assert payload["curl_account_probe_http_status"] is None


def test_graphql_headers_include_accept_and_user_agent(monkeypatch):
    captured = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"data": {}}'

    def _fake(req, timeout):
        captured["accept"] = req.get_header("Accept")
        captured["user_agent"] = req.get_header("User-agent")
        return _Resp()

    monkeypatch.setattr(s.request, "urlopen", _fake)
    s._graphql(s.DEFAULT_API_URL, "t", "query{}", {})
    assert captured["accept"] == "application/json"
    assert "ai-hk-invest-system-step91c/1.0" in (captured["user_agent"] or "")


def test_markdown_includes_fingerprint_and_curl_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_TOKEN", "t")
    monkeypatch.setenv("RAILWAY_TOKEN_SHA256_PREFIX", "e3b98a4da31a")
    monkeypatch.setenv("RAILWAY_CONNECTIVITY_PROBE", "account")
    monkeypatch.setenv("RAILWAY_CURL_PROBE", "on")
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.setattr(s, "_graphql", lambda *_a, **_k: (200, {"data": {"me": {"name": "n"}}}))

    class R:
        stdout = "200"

    monkeypatch.setattr(s.subprocess, "run", lambda *a, **k: R())
    _run(tmp_path, monkeypatch)
    md = (tmp_path / s.REPORT_MD).read_text(encoding="utf-8")
    assert "token_fingerprint_expected_configured: True" in md
    assert "token_fingerprint_match: True" in md
    assert "curl_account_probe_status: PASS" in md
