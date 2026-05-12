from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.miniapp_data_provider import (
    LocalArtifactMiniAppReadDataProvider,
    MiniAppReadDataProvider,
    RailwayRuntimeEnvMiniAppReadDataProvider,
)

_HKT = timezone(timedelta(hours=8))


def build_daily_brief_section(
    daily_review_summary: Mapping[str, Any],
    signals_summary: Mapping[str, Any],
    risk_summary: Mapping[str, Any],
) -> dict[str, Any]:
    signal_counts = {
        "positive": int(signals_summary.get("shown_positive_signals") or 0),
        "neutral": int(signals_summary.get("shown_neutral_signals") or 0),
        "negative": int(signals_summary.get("shown_negative_signals") or 0),
    }
    dominant = "unknown"
    if signals_summary.get("status") == "ok":
        peak = max(signal_counts.values())
        peak_labels = [k for k, v in signal_counts.items() if v == peak and peak > 0]
        dominant = peak_labels[0] if len(peak_labels) == 1 else "mixed"
    total = sum(signal_counts.values())
    risk_level = str(risk_summary.get("risk_level") or "unknown") if risk_summary.get("status") == "ok" else "unknown"
    readiness = str(daily_review_summary.get("review_readiness") or "unavailable")
    data_state = "enough" if readiness == "ready" else ("partial" if readiness == "partial" else "insufficient")
    data_explain = {
        "enough": "主要資料已到齊，可作模擬檢視。",
        "partial": "部分資料未齊，需要先補看風險或信號內容。",
        "insufficient": "資料不足，暫時未能作方向判斷。",
    }[data_state]
    if total <= 0 or dominant == "unknown":
        sim_direction = "資料不足，暫時只可觀察。"
    elif risk_level in {"unknown", "unavailable"} or data_state == "insufficient":
        sim_direction = "資料不足，暫時只可觀察。"
    elif dominant == "positive":
        sim_direction = "AI 模擬方向偏正面，但只供模擬檢視。"
    elif dominant == "negative":
        sim_direction = "AI 模擬方向偏審慎，暫時以防守為主。"
    else:
        sim_direction = "AI 模擬方向偏觀望，先等更多確認訊號。"
    if risk_level == "high":
        risk_brief = "風險偏高，先做風險檢查，唔好急住跟方向。"
    elif risk_level == "medium":
        risk_brief = "有中等風險提示，要小心解讀，唔可以當作風險可控。"
    elif risk_level == "low":
        risk_brief = "暫未見重大風險警示，但仍要人手覆核。"
    else:
        risk_brief = "風險資料不足，暫時未有足夠資訊。"
    actions = ["先查看風險摘要同限制說明。", "再看信號原因是否一致。"]
    if data_state == "enough":
        actions.append("如要記錄，寫低人手模擬決策理由。")
    headline = "今日以模擬檢視為主，先確認資料與風險，再由人手決定下一步。"
    return {
        "status": "ok",
        "source": "daily_brief_read_model",
        "headline_summary": headline,
        "data_sufficiency": {"state": data_state, "explanation": data_explain},
        "risk_brief": risk_brief,
        "simulated_direction": sim_direction,
        "operator_next_actions": actions[:3],
        "technical_details": {
            "review_readiness": readiness,
            "risk_level": risk_level,
            "signal_counts": signal_counts,
            "signals_status": signals_summary.get("status"),
        },
        "safety_note": "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議",
    }


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

    sections = {
        "runner_status": data_provider.get_runtime_status_summary(),
        "latest_system_run": data_provider.get_latest_system_run_summary(),
        "daily_review_summary": data_provider.get_daily_review_summary(),
        "signals_summary": data_provider.get_signals_summary(),
        "paper_pnl_summary": data_provider.get_paper_pnl_summary(),
        "risk_summary": data_provider.get_risk_summary(),
        "decision_context_summary": data_provider.get_decision_context_summary(),
        "ticker_level_paper_portfolio_review": data_provider.get_ticker_level_paper_portfolio_review(),
        "daily_review": {"status": "mock"},
        "pnl_snapshot": {"status": "mock"},
        "outcome_review": {"status": "mock"},
    }
    sections["daily_brief"] = build_daily_brief_section(
        sections["daily_review_summary"], sections["signals_summary"], sections["risk_summary"]
    )
    return {
        "status": "ok",
        "generated_at_hkt": generated_at.isoformat(),
        "operator": operator,
        "sections": sections,
        "guardrails": {
            "read_only": True,
            "paper_trade_only": True,
            "decision_support_only": True,
            "no_broker_execution": True,
            "no_real_money_execution": True,
        },
    }
