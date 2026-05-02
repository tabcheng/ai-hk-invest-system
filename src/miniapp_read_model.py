from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Mapping


_HKT = timezone(timedelta(hours=8))
_RUNTIME_SOURCE = "railway_runtime_env"
_MAX_SHA_SHORT_LEN = 12


def _safe_env_get(env: Mapping[str, str], key: str) -> str | None:
    value = str(env.get(key, "") or "").strip()
    return value or None


def _short_commit_sha(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(re.findall(r"[0-9a-fA-F]", value.strip()))
    if not normalized:
        return None
    return normalized.lower()[:_MAX_SHA_SHORT_LEN]


def build_runtime_status_section(
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    runtime_env = env or {}
    generated_at = now.astimezone(_HKT) if now else datetime.now(_HKT)

    service_name = _safe_env_get(runtime_env, "RAILWAY_SERVICE_NAME")
    environment = _safe_env_get(runtime_env, "RAILWAY_ENVIRONMENT_NAME")
    git_branch = _safe_env_get(runtime_env, "RAILWAY_GIT_BRANCH")
    git_commit_sha_short = _short_commit_sha(_safe_env_get(runtime_env, "RAILWAY_GIT_COMMIT_SHA"))
    deployment_id = _safe_env_get(runtime_env, "RAILWAY_DEPLOYMENT_ID")

    status = (
        "ok"
        if all([service_name, environment, git_branch, git_commit_sha_short])
        else "unknown"
    )

    return {
        "status": status,
        "source": _RUNTIME_SOURCE,
        "service_name": service_name,
        "environment": environment,
        "git_branch": git_branch,
        "git_commit_sha_short": git_commit_sha_short,
        "deployment_id_present": bool(deployment_id),
        "generated_at_hkt": generated_at.isoformat(),
    }


def build_miniapp_review_shell_response(
    operator: dict[str, Any],
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    runtime_env = env or {}
    generated_at = now.astimezone(_HKT) if now else datetime.now(_HKT)

    runner_status = build_runtime_status_section(env=runtime_env, now=generated_at)

    return {
        "status": "ok",
        "generated_at_hkt": generated_at.isoformat(),
        "operator": operator,
        "sections": {
            "runner_status": runner_status,
            "daily_review": {"status": "mock"},
            "pnl_snapshot": {"status": "mock"},
            "outcome_review": {"status": "mock"},
        },
        "guardrails": {
            "read_only": True,
            "paper_trade_only": True,
            "decision_support_only": True,
            "no_broker_execution": True,
            "no_real_money_execution": True,
        },
    }
