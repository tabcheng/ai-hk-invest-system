from pathlib import Path


WORKFLOW_PATH = Path('.github/workflows/step92a-post-merge-smoke.yml')


def test_workflow_is_manual_only() -> None:
    text = WORKFLOW_PATH.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in text
    assert 'push:' not in text
    assert 'pull_request:' not in text
    assert 'schedule:' not in text


def test_workflow_has_runner_toggle_input() -> None:
    text = WORKFLOW_PATH.read_text(encoding='utf-8')
    assert 'run_paper_daily_runner:' in text
    assert 'default: "false"' in text
