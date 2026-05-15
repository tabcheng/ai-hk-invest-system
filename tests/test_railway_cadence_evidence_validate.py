from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.railway_cadence_evidence_validate import (
    _derive_expected_schedule_basis_fragment,
    to_markdown,
    validate_evidence,
)


def _sample(run_type: str = "post_close_daily_review", status: str = "success", schedule_basis: str | None = None) -> list[dict[str, str]]:
    return [
        {"message": "deployment id=8a1957b5-8187-46b2-b2f2-1968633377aa run record: id=51"},
        {"message": "started_at=2026-05-15T06:58:59.550516+00:00"},
        {"message": f'execution_summary={{"run_type":"{run_type}","entrypoint":"python -m src.daily_runner","schedule_basis":"{schedule_basis or "HKT 20:00 (Railway cron UTC: 0 12 * * *)"}","status":"{status}"}}'},
        {"message": "trades=0, events=3"},
        {"message": "Telegram message sent to chat_id=123456789"},
        {"message": "completed"},
        {"message": "finished_at=2026-05-15T06:59:06.904696+00:00"},
    ]


def _args(tmp_path: Path, payload: list[dict[str, str]], expected: str = "post_close_daily_review"):
    p = tmp_path / "in.json"
    p.write_text(json.dumps(payload), encoding="utf-8")

    class A:
        input_json = str(p)
        input_text = None
        expected_run_type = expected
        expected_entrypoint = "python -m src.daily_runner"
        expected_schedule_basis_contains = None

    return A()


def test_daily_baseline_pass(tmp_path: Path):
    res = validate_evidence(_args(tmp_path, _sample()))
    assert res["status"] == "pass"
    assert res["telegram_sent"] is True
    assert res["telegram_chat_id_redacted"] is True
    assert res["duration_seconds"] is not None
    assert abs(res["duration_seconds"] - 7.35418) < 0.001


def test_mismatch_run_type_fails(tmp_path: Path):
    res = validate_evidence(_args(tmp_path, _sample(run_type="midday_market_monitor")))
    assert res["status"] == "fail"


def test_missing_execution_summary_fails(tmp_path: Path):
    payload = _sample()
    payload = [x for x in payload if "execution_summary" not in x["message"]]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "fail"


def test_non_success_fails(tmp_path: Path):
    res = validate_evidence(_args(tmp_path, _sample(status="failed")))
    assert res["status"] == "fail"


def test_secret_not_emitted_in_markdown(tmp_path: Path):
    payload = _sample() + [{"message": "token=abc"}]
    res = validate_evidence(_args(tmp_path, payload))
    md = to_markdown(res)
    assert "chat_id=123456789" not in md
    assert "token=abc" not in md
    assert res["status"] == "fail"


def test_cli_json_and_md_output(tmp_path: Path):
    in_path = tmp_path / "in.json"
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    in_path.write_text(json.dumps(_sample()), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/railway_cadence_evidence_validate.py",
            "--input-json",
            str(in_path),
            "--expected-run-type",
            "post_close_daily_review",
            "--expected-schedule-basis-contains",
            "Railway cron UTC",
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert "real-money execution" in out_md.read_text(encoding="utf-8")
    assert "token=" not in proc.stdout


def test_cli_direct_invocation_derives_midday_schedule_without_pythonpath(tmp_path: Path, monkeypatch):
    in_path = tmp_path / "midday.json"
    out_json = tmp_path / "midday.out.json"
    in_path.write_text(
        json.dumps(
            _sample(
                run_type="midday_market_monitor",
                schedule_basis="HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)",
            )
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/railway_cadence_evidence_validate.py",
            "--input-json",
            str(in_path),
            "--expected-run-type",
            "midday_market_monitor",
            "--output-json",
            str(out_json),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert "schedule basis mismatch" not in proc.stdout


def test_cli_direct_invocation_derives_stale_schedule_without_pythonpath(tmp_path: Path):
    in_path = tmp_path / "stale.json"
    out_json = tmp_path / "stale.out.json"
    in_path.write_text(
        json.dumps(
            _sample(
                run_type="stale_risk_refresh",
                schedule_basis="HKT around 15:30 weekday (Railway cron UTC: 30 7 * * 1-5)",
            )
        ),
        encoding="utf-8",
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/railway_cadence_evidence_validate.py",
            "--input-json",
            str(in_path),
            "--expected-run-type",
            "stale_risk_refresh",
            "--output-json",
            str(out_json),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["status"] == "pass"
    assert "schedule basis mismatch" not in proc.stdout


def test_support_midday_and_stale(tmp_path: Path):
    midday = validate_evidence(
        _args(
            tmp_path,
            _sample(
                run_type="midday_market_monitor",
                schedule_basis="HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)",
            ),
            expected="midday_market_monitor",
        )
    )
    stale = validate_evidence(
        _args(
            tmp_path,
            _sample(
                run_type="stale_risk_refresh",
                schedule_basis="HKT around 15:30 weekday (Railway cron UTC: 30 7 * * 1-5)",
            ),
            expected="stale_risk_refresh",
        )
    )
    assert midday["status"] == "pass"
    assert stale["status"] == "pass"


def test_structured_tags_deployment_id_supported(tmp_path: Path):
    payload = _sample()
    payload[0] = {"message": "run record: id=51", "tags": {"deploymentId": "8a1957b5-8187-46b2-b2f2-1968633377aa"}}
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "pass"
    assert res["deployment_id"] == "8a1957b5-8187-46b2-b2f2-1968633377aa"


def test_negative_guardrail_wording_not_treated_as_execution(tmp_path: Path):
    payload = _sample() + [{"message": "no broker connection, no live execution, no real-money execution observed"}]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "pass"


def test_positive_execution_phrase_with_no_word_still_fails(tmp_path: Path):
    payload = _sample() + [{"message": "order created successfully; no retries"}]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "fail"
    assert res["broker_live_order_execution_observed"] is True


def test_mixed_negative_and_positive_execution_phrase_fails(tmp_path: Path):
    payload = _sample() + [{"message": "no live execution; order created successfully"}]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "fail"
    assert res["broker_live_order_execution_observed"] is True


def test_but_clause_with_order_created_fails(tmp_path: Path):
    payload = _sample() + [{"message": "no broker connection but order created successfully"}]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "fail"
    assert res["broker_live_order_execution_observed"] is True


def test_no_real_money_but_place_order_called_fails(tmp_path: Path):
    payload = _sample() + [{"message": "no real-money execution; place order called"}]
    res = validate_evidence(_args(tmp_path, payload))
    assert res["status"] == "fail"
    assert res["broker_live_order_execution_observed"] is True


def test_secret_like_schedule_basis_redacted_everywhere(tmp_path: Path):
    payload = _sample()
    payload[2] = {
        "message": 'execution_summary={"run_type":"post_close_daily_review","entrypoint":"python -m src.daily_runner","schedule_basis":"token=abc","status":"success"}'
    }
    res = validate_evidence(_args(tmp_path, payload))
    md = to_markdown(res)
    assert res["status"] == "fail"
    assert res["secrets_observed"] is True
    assert res["schedule_basis"] == "[REDACTED_SECRET_LIKE_VALUE]"
    assert "token=abc" not in md
    assert "token=abc" not in json.dumps(res)


def test_secret_like_entrypoint_redacted_everywhere(tmp_path: Path):
    payload = _sample()
    payload[2] = {
        "message": 'execution_summary={"run_type":"post_close_daily_review","entrypoint":"sb_secret_123456","schedule_basis":"HKT 20:00 (Railway cron UTC: 0 12 * * *)","status":"success"}'
    }
    res = validate_evidence(_args(tmp_path, payload))
    md = to_markdown(res)
    assert res["status"] == "fail"
    assert res["secrets_observed"] is True
    assert res["entrypoint"] == "[REDACTED_SECRET_LIKE_VALUE]"
    assert "sb_secret_123456" not in md
    assert "sb_secret_123456" not in json.dumps(res)


def test_telegram_bot_token_like_string_not_emitted(tmp_path: Path):
    payload = _sample() + [{"message": "bot12345678:ABCDefghijklmnopqrstuvwxy"}]
    res = validate_evidence(_args(tmp_path, payload))
    md = to_markdown(res)
    dumped = json.dumps(res)
    assert res["status"] == "fail"
    assert "bot12345678:ABCDefghijklmnopqrstuvwxy" not in md
    assert "bot12345678:ABCDefghijklmnopqrstuvwxy" not in dumped


def test_midday_derived_schedule_pass_and_mismatch_fail(tmp_path: Path):
    ok = validate_evidence(_args(tmp_path, _sample(run_type="midday_market_monitor", schedule_basis="HKT around 12:30 weekday (Railway cron UTC: 30 4 * * 1-5)"), expected="midday_market_monitor"))
    bad = validate_evidence(_args(tmp_path, _sample(run_type="midday_market_monitor", schedule_basis="HKT 20:00 (Railway cron UTC: 0 12 * * *)"), expected="midday_market_monitor"))
    assert ok["status"] == "pass"
    assert bad["status"] == "fail"


def test_stale_risk_derived_schedule_pass(tmp_path: Path):
    res = validate_evidence(_args(tmp_path, _sample(run_type="stale_risk_refresh", schedule_basis="HKT around 15:30 weekday (Railway cron UTC: 30 7 * * 1-5)"), expected="stale_risk_refresh"))
    assert res["status"] == "pass"


def test_derived_expected_schedule_fragment_includes_railway_cron_prefix():
    assert _derive_expected_schedule_basis_fragment("post_close_daily_review") == "Railway cron UTC: 0 12 * * *"
    assert _derive_expected_schedule_basis_fragment("midday_market_monitor") == "Railway cron UTC: 30 4 * * 1-5"
