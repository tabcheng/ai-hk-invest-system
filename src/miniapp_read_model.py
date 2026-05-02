from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.miniapp_data_provider import (
    LocalArtifactMiniAppReadDataProvider,
    MiniAppReadDataProvider,
    RailwayRuntimeEnvMiniAppReadDataProvider,
)

_HKT = timezone(timedelta(hours=8))


def _resolve_default_provider(
    env: Mapping[str, str] | None,
    now: datetime | None,
) -> MiniAppReadDataProvider:
    artifact_path = str((env or {}).get("MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH", "") or "").strip()
    if artifact_path:
        return LocalArtifactMiniAppReadDataProvider(artifact_path=artifact_path, env=env, now=now)
    return RailwayRuntimeEnvMiniAppReadDataProvider(env=env, now=now)


def build_runtime_status_section(
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    provider: MiniAppReadDataProvider | None = None,
) -> dict[str, Any]:
    data_provider = provider or _resolve_default_provider(env=env, now=now)
    return data_provider.get_runtime_status_summary()


def build_miniapp_review_shell_response(
    operator: dict[str, Any],
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    provider: MiniAppReadDataProvider | None = None,
) -> dict[str, Any]:
    generated_at = now.astimezone(_HKT) if now else datetime.now(_HKT)
    data_provider = provider or _resolve_default_provider(env=env, now=generated_at)

    return {
        "status": "ok",
        "generated_at_hkt": generated_at.isoformat(),
        "operator": operator,
        "sections": {
            "runner_status": data_provider.get_runtime_status_summary(),
            "latest_system_run": data_provider.get_latest_system_run_summary(),
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
