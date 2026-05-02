from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.miniapp_data_provider import (
    MiniAppReadDataProvider,
    RailwayRuntimeEnvMiniAppReadDataProvider,
)

_HKT = timezone(timedelta(hours=8))


def build_runtime_status_section(
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    provider: MiniAppReadDataProvider | None = None,
) -> dict[str, Any]:
    data_provider = provider or RailwayRuntimeEnvMiniAppReadDataProvider(env=env, now=now)
    return data_provider.get_latest_system_run_summary()


def build_miniapp_review_shell_response(
    operator: dict[str, Any],
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
    provider: MiniAppReadDataProvider | None = None,
) -> dict[str, Any]:
    generated_at = now.astimezone(_HKT) if now else datetime.now(_HKT)
    runner_status = build_runtime_status_section(env=env, now=generated_at, provider=provider)

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
