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
