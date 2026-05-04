from __future__ import annotations

import json

import scripts.step91c_runtime_acceptance as s


def test_report_generation_without_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    # call via argv path
    monkeypatch.setattr('sys.argv', ['step91c_runtime_acceptance.py', '--test-run-id', '31'])
    out = s.main()
    assert out == 1
    payload = json.loads((tmp_path / 'step91c_runtime_acceptance_report.json').read_text())
    assert payload['preflight_status'] == 'FAIL'
    assert payload['secrets_redacted'] is True


def test_check_table_not_configured(monkeypatch):
    monkeypatch.setattr(s.request, 'urlopen', lambda req, timeout=30: (_ for _ in ()).throw(s.HTTPError(req.full_url, 404, 'x', None, None)))
    r = s._check_table('https://a.supabase.co', 'sb_secret_x', 'latest_system_runs', 1440)
    assert r['status'] == 'NOT_CONFIGURED'
