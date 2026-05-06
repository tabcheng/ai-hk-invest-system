from pathlib import Path

import yaml


def _find_step(workflow: dict, name: str) -> dict:
    steps = workflow["jobs"]["step91c-acceptance"]["steps"]
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"missing step: {name}")


def test_optional_railway_diagnostics_vars_wired_only_to_api_probe_step() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/step91c-runtime-acceptance.yml").read_text(encoding="utf-8")
    )

    api_probe = _find_step(workflow, "Run Railway API probe (read-only)")
    log_evidence = _find_step(workflow, "Run Railway log evidence (read-only)")

    api_probe_env = api_probe.get("env", {})
    log_evidence_env = log_evidence.get("env", {})

    assert api_probe_env.get("RAILWAY_TOKEN_SHA256_PREFIX") == "${{ vars.RAILWAY_TOKEN_SHA256_PREFIX }}"
    assert api_probe_env.get("RAILWAY_CURL_PROBE") == "${{ vars.RAILWAY_CURL_PROBE }}"

    assert "RAILWAY_TOKEN_SHA256_PREFIX" not in log_evidence_env
    assert "RAILWAY_CURL_PROBE" not in log_evidence_env
