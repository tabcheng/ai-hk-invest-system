import json
from datetime import datetime, timezone

import pytest

import src.daily_runner as daily_runner


def _extract_execution_summary(output: str) -> dict:
    marker = "[daily_runner] execution_summary="
    for line in output.splitlines():
        if line.startswith(marker):
            return json.loads(line.split(marker, 1)[1])
    raise AssertionError("execution summary line not found")


def test_run_success_returns_zero_and_logs_consistent_summary(monkeypatch, capsys):
    called = {"main": 0}

    def fake_app_main():
        called["main"] += 1

    timestamps = iter(
        [
            datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 21, 12, 0, 5, tzinfo=timezone.utc),
        ]
    )

    monkeypatch.setattr(daily_runner, "_run_daily_pipeline", fake_app_main)
    monkeypatch.setattr(daily_runner, "_utc_now", lambda: next(timestamps))

    exit_code = daily_runner.run()

    assert exit_code == 0
    assert called["main"] == 1

    output = capsys.readouterr().out
    assert "[daily_runner] started entrypoint=python -m src.daily_runner" in output
    assert "[daily_runner] completed entrypoint=python -m src.daily_runner" in output

    summary = _extract_execution_summary(output)
    assert summary["status"] == "success"
    assert summary["started_at"] == "2026-03-21T12:00:00+00:00"
    assert summary["finished_at"] == "2026-03-21T12:00:05+00:00"
    assert summary["duration_seconds"] == 5.0
    assert summary["entrypoint"] == "python -m src.daily_runner"
    assert summary["schedule_basis"] == "HKT 20:00 (Railway cron UTC: 0 12 * * *)"
    assert "error_summary" not in summary


def test_run_failure_returns_one_and_logs_failure_summary(monkeypatch, capsys):
    def fail_app_main():
        raise RuntimeError("boom")

    timestamps = iter(
        [
            datetime(2026, 3, 21, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 3, 21, 12, 0, 2, tzinfo=timezone.utc),
        ]
    )

    monkeypatch.setattr(daily_runner, "_run_daily_pipeline", fail_app_main)
    monkeypatch.setattr(daily_runner, "_utc_now", lambda: next(timestamps))

    exit_code = daily_runner.run()

    assert exit_code == 1

    captured = capsys.readouterr()
    assert "[daily_runner] started entrypoint=python -m src.daily_runner" in captured.out
    assert "[daily_runner] failed entrypoint=python -m src.daily_runner" in captured.out
    assert "RuntimeError: boom" in captured.err

    summary = _extract_execution_summary(captured.out)
    assert summary["status"] == "failed"
    assert summary["duration_seconds"] == 2.0
    assert summary["entrypoint"] == "python -m src.daily_runner"
    assert summary["schedule_basis"] == "HKT 20:00 (Railway cron UTC: 0 12 * * *)"
    assert summary["error_summary"] == "RuntimeError: boom"


def test_main_exits_with_run_exit_code(monkeypatch):
    monkeypatch.setattr(daily_runner, "run", lambda: 0)

    with pytest.raises(SystemExit) as exc_info:
        daily_runner.main()

    assert exc_info.value.code == 0


def test_summarize_error_normalizes_whitespace_and_truncates():
    long_message = "boom\nwith   extra\tspaces " + ("x" * 500)
    summary = daily_runner._summarize_error(RuntimeError(long_message))

    assert "\n" not in summary
    assert "\t" not in summary
    assert summary.startswith("RuntimeError: boom with extra spaces")
    assert len(summary) == daily_runner._MAX_ERROR_SUMMARY_LENGTH
    assert summary.endswith("...")
