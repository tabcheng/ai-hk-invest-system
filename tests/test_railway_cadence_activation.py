from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.railway_cadence_activation import build_railway_cadence_activation_plan


def test_activation_plan_required_entries_and_guardrails():
    plan = build_railway_cadence_activation_plan()
    run_types = {x["run_type"] for x in plan}
    assert {"post_close_daily_review", "midday_market_monitor", "stale_risk_refresh"}.issubset(run_types)
    assert all(x["paper_only"] is True and x["creates_orders"] is False and x["broker_connection"] is False for x in plan)


def test_activation_states_and_manual_step_contract():
    plan = build_railway_cadence_activation_plan()
    by_type = {x["run_type"]: x for x in plan}
    assert by_type["post_close_daily_review"]["activation_state"] == "existing_baseline_to_verify"
    assert by_type["midday_market_monitor"]["activation_state"] == "candidate_requires_manual_railway_setup"
    assert by_type["stale_risk_refresh"]["activation_state"] == "candidate_requires_manual_railway_setup"
    assert all(x["manual_operator_step_required"] is True for x in plan)


def test_checklist_script_outputs_secret_safe_files(tmp_path: Path):
    md_path = tmp_path / "checklist.md"
    json_path = tmp_path / "checklist.json"
    script = Path("scripts/railway_cadence_activation_checklist.py")

    subprocess.run([sys.executable, str(script), "--output-md", str(md_path), "--output-json", str(json_path)], check=True)

    md = md_path.read_text(encoding="utf-8").lower()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert "workflow_dispatch" not in md
    assert payload["mutation_free"] is True
    assert payload["railway_api_calls"] is False
    assert payload["deploy_actions"] is False
    assert payload["cron_active_claimed"] is False
    assert "token" not in md
    assert "sb_secret_" not in md
    assert "railway api" not in md
