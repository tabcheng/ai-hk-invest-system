import json

from scripts.miniapp_api_smoke import _assert_no_write_affordance, _assert_sections_contract


def test_assert_sections_contract_accepts_step_86_bounded_contract():
    payload = {
        "sections": {
            "runner_status": {"status": "unknown", "source": "railway_runtime_env"},
            "latest_system_run": {
                "status": "unavailable",
                "source": "not_configured",
                "run_id": None,
                "run_status": None,
                "started_at_hkt": None,
                "completed_at_hkt": None,
                "data_timestamp_hkt": None,
                "summary": None,
                "limitations": ["No production data source configured in Step 86."],
            },
            "daily_review": {"status": "mock"},
            "pnl_snapshot": {"status": "mock"},
            "outcome_review": {"status": "mock"},
        }
    }
    assert _assert_sections_contract(payload) is True


def test_assert_sections_contract_accepts_local_artifact_unavailable_contract():
    payload = {
        "sections": {
            "runner_status": {"status": "ok", "source": "railway_runtime_env"},
            "latest_system_run": {
                "status": "unavailable",
                "source": "local_artifact",
                "run_id": None,
                "run_status": None,
                "started_at_hkt": None,
                "completed_at_hkt": None,
                "data_timestamp_hkt": None,
                "summary": None,
                "limitations": ["Local artifact is missing or invalid JSON."],
            },
            "daily_review": {"status": "mock"},
            "pnl_snapshot": {"status": "mock"},
            "outcome_review": {"status": "mock"},
        }
    }
    assert _assert_sections_contract(payload) is True


def test_assert_sections_contract_rejects_unavailable_with_unknown_source():
    payload = {
        "sections": {
            "runner_status": {"status": "ok", "source": "railway_runtime_env"},
            "latest_system_run": {"status": "unavailable", "source": "unexpected_source"},
            "daily_review": {"status": "mock"},
            "pnl_snapshot": {"status": "mock"},
            "outcome_review": {"status": "mock"},
        }
    }
    assert _assert_sections_contract(payload) is False


def test_assert_no_write_affordance_still_blocks_execution_tokens():
    payload = {
        "guardrails": {
            "no_broker_execution": True,
            "no_real_money_execution": True,
        },
        "sections": {
            "runner_status": {"status": "ok", "source": "railway_runtime_env"},
            "latest_system_run": {"status": "unavailable", "source": "not_configured"},
        },
        "note": "safe",
    }
    assert _assert_no_write_affordance(payload)

    bad = json.loads(json.dumps(payload))
    bad["leak"] = "create_order"
    assert _assert_no_write_affordance(bad) is False


def test_write_reports_generates_artifacts(tmp_path, monkeypatch):
    import scripts.miniapp_api_smoke as smoke
    monkeypatch.chdir(tmp_path)
    results = [smoke.CaseResult(name='E_authorized_operator', status_code=200, passed=True, detail='ok')]
    smoke._write_reports('https://example.com/miniapp/api/review-shell', results, 'PASS', True)
    payload = json.loads((tmp_path / 'miniapp_api_smoke_report.json').read_text(encoding='utf-8'))
    md = (tmp_path / 'miniapp_api_smoke_report.md').read_text(encoding='utf-8')
    assert payload['secrets_redacted'] is True
    assert payload['guardrails']['no_real_money_execution'] is True
    assert 'authorized_operator_result: PASS' in md
