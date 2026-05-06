from pathlib import Path
import re


WORKFLOW_PATH = Path('.github/workflows/step91c-runtime-acceptance.yml')


def _extract_step_block(text: str, step_name: str) -> str:
    pattern = re.compile(
        rf"^\s*- name: {re.escape(step_name)}\n(?P<body>(?:^\s{{8,}}.*\n)*)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    assert match, f"missing step: {step_name}"
    return match.group(0)


def test_optional_railway_diagnostics_vars_wired_only_to_api_probe_step() -> None:
    workflow_text = WORKFLOW_PATH.read_text(encoding='utf-8')

    api_probe_block = _extract_step_block(workflow_text, 'Run Railway API probe (read-only)')
    log_evidence_block = _extract_step_block(workflow_text, 'Run Railway log evidence (read-only)')

    assert 'RAILWAY_TOKEN_SHA256_PREFIX: ${{ vars.RAILWAY_TOKEN_SHA256_PREFIX }}' in api_probe_block
    assert 'RAILWAY_CURL_PROBE: ${{ vars.RAILWAY_CURL_PROBE }}' in api_probe_block

    assert 'RAILWAY_TOKEN_SHA256_PREFIX' not in log_evidence_block
    assert 'RAILWAY_CURL_PROBE' not in log_evidence_block
