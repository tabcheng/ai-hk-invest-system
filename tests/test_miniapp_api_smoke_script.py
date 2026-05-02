import json

from scripts.miniapp_api_smoke import _assert_no_write_affordance, _assert_sections_contract


def test_assert_sections_contract_accepts_bounded_runtime_runner_status():
    payload = {
        "sections": {
            "runner_status": {"status": "unknown", "source": "railway_runtime_env"},
            "daily_review": {"status": "mock"},
            "pnl_snapshot": {"status": "mock"},
            "outcome_review": {"status": "mock"},
        }
    }
    assert _assert_sections_contract(payload) is True


def test_assert_no_write_affordance_still_blocks_execution_tokens():
    payload = {
        "guardrails": {
            "no_broker_execution": True,
            "no_real_money_execution": True,
        },
        "sections": {"runner_status": {"status": "ok", "source": "railway_runtime_env"}},
        "note": "safe",
    }
    assert _assert_no_write_affordance(payload)

    bad = json.loads(json.dumps(payload))
    bad["leak"] = "create_order"
    assert _assert_no_write_affordance(bad) is False
