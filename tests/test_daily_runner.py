import pytest

import src.daily_runner as daily_runner


def test_run_success_returns_zero_and_logs_start_and_completion(monkeypatch, capsys):
    called = {"main": 0}

    def fake_app_main():
        called["main"] += 1

    monkeypatch.setattr(daily_runner, "_run_daily_pipeline", fake_app_main)

    exit_code = daily_runner.run()

    assert exit_code == 0
    assert called["main"] == 1

    output = capsys.readouterr().out
    assert "[daily_runner] started_at=" in output
    assert "[daily_runner] completed_at=" in output


def test_run_failure_returns_one_and_logs_failure(monkeypatch, capsys):
    def fail_app_main():
        raise RuntimeError("boom")

    monkeypatch.setattr(daily_runner, "_run_daily_pipeline", fail_app_main)

    exit_code = daily_runner.run()

    assert exit_code == 1

    captured = capsys.readouterr()
    assert "[daily_runner] started_at=" in captured.out
    assert "[daily_runner] failed_at=" in captured.out
    assert "RuntimeError: boom" in captured.err


def test_main_exits_with_run_exit_code(monkeypatch):
    monkeypatch.setattr(daily_runner, "run", lambda: 0)

    with pytest.raises(SystemExit) as exc_info:
        daily_runner.main()

    assert exc_info.value.code == 0
