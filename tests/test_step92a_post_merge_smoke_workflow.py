from pathlib import Path


WORKFLOW_PATH = Path('.github/workflows/step92a-post-merge-smoke.yml')
SCRIPT_PATH = Path('scripts/step92a_post_merge_smoke.py')


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


def test_smoke_script_no_direct_catalog_rest_paths() -> None:
    text = SCRIPT_PATH.read_text(encoding='utf-8')
    assert 'pg_catalog.pg_tables' not in text
    assert 'pg_indexes?select=' not in text
    assert 'rpc/step92a_latest_system_runs_contract_evidence' in text
