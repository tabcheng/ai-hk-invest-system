from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
_HKT = timezone(timedelta(hours=8))
RUN_TYPE_PRE_MARKET = "pre_market_readiness_check"
RUN_TYPE_MIDDAY = "midday_market_monitor"
RUN_TYPE_POST_CLOSE = "post_close_daily_review"
RUN_TYPE_STALE_RISK = "stale_risk_refresh"
RUN_TYPE_EVENT_CONTEXT = "event_context_refresh"
RUN_TYPE_MANUAL_FALLBACK = "manual_operator_refresh_fallback"
DEFAULT_RUN_TYPE = RUN_TYPE_POST_CLOSE


def get_effective_run_type(env: Mapping[str, str] | None = None) -> str:
    candidate = str((env or {}).get("AIHK_RUN_TYPE") or "").strip().lower()
    allowed = {RUN_TYPE_PRE_MARKET, RUN_TYPE_MIDDAY, RUN_TYPE_POST_CLOSE, RUN_TYPE_STALE_RISK, RUN_TYPE_EVENT_CONTEXT, RUN_TYPE_MANUAL_FALLBACK}
    return candidate if candidate in allowed else DEFAULT_RUN_TYPE


def _entry(run_type: str, window: str, purpose: str, freshness: str, surface: str, manual_fallback: bool = False) -> dict[str, Any]:
    return {"run_type": run_type, "schedule_window_hkt": window, "purpose": purpose, "data_requirements": "市場資料 + 風險摘要 + 決策脈絡（按 run_type）", "freshness_expectation": freshness, "operator_surface": surface, "paper_only": True, "creates_orders": False, "broker_connection": False, "manual_fallback_only": manual_fallback}


def build_backend_data_cadence_policy() -> list[dict[str, Any]]:
    return [
        _entry(RUN_TYPE_PRE_MARKET, "08:30-09:20", "開市前檢查資料可用性與風險摘要", "morning readiness", "today_system"),
        _entry(RUN_TYPE_MIDDAY, "12:00-13:15", "午市期間檢查資料更新與風險變化", "midday monitor", "today_system"),
        _entry(RUN_TYPE_POST_CLOSE, "19:45-20:30", "收市後正式每日模擬檢視", "post-close review", "daily_brief"),
        _entry(RUN_TYPE_STALE_RISK, "event-driven", "資料過舊/風險脈絡不足時補刷新", "stale-risk refresh", "system_market_data"),
        _entry(RUN_TYPE_EVENT_CONTEXT, "event-driven", "預留公告/業績事件脈絡刷新（本步未接 vendor）", "event context", "stock_review"),
        _entry(RUN_TYPE_MANUAL_FALLBACK, "operator emergency", "人手後備刷新（只作 fallback）", "manual fallback only", "operator_tools", manual_fallback=True),
    ]


def plan_backend_auto_refreshes(*, latest_system_run: Mapping[str, Any] | None, risk_summary: Mapping[str, Any] | None, stock_dossier_items: list[Mapping[str, Any]] | None, max_items: int = 5, now: datetime | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    def add(run_type: str, scope: str, priority: int, trigger: str, reason: str, surface: str, label: str, freshness: str, hint: str, fallback: bool) -> None:
        items.append({"run_type": run_type, "scope": scope, "priority": priority, "trigger": trigger, "reason": reason, "target_surface": surface, "target_surface_label": label, "freshness_requirement": freshness, "operator_hint": hint, "paper_only": True, "creates_orders": False, "broker_connection": False, "manual_fallback_allowed": fallback})

    flags = [str((latest_system_run or {}).get("market_data_acceptance_status") or "").lower(), str((latest_system_run or {}).get("market_data_status") or "").lower(), str((latest_system_run or {}).get("freshness_status") or "").lower()]
    if any(f in {"stale_do_not_use_for_intraday", "stale"} for f in flags):
        add(RUN_TYPE_STALE_RISK, "market", 1, "market_data_stale", "市場資料 stale", "system_market_data", "System / Market Data", "refresh before interpretation", "先補市場資料，再作模擬檢視。", True)
    if any(f in {"unknown", "unavailable", "delayed", "caution_last_available_close"} for f in flags):
        add(RUN_TYPE_STALE_RISK, "market", 2, "market_data_unavailable", "市場資料未知/延遲/只得收市", "system_market_data", "System / Market Data", "refresh recommended", "系統應先安排自動刷新，不以手動為主。", True)

    risk_level = str((risk_summary or {}).get("risk_level") or "unknown").lower()
    warnings = " ".join(str(x).lower() for x in list((risk_summary or {}).get("warnings") or []))
    if risk_level == "unknown" or "insufficient" in warnings:
        add(RUN_TYPE_STALE_RISK, "risk", 2, "risk_context_insufficient", "風險脈絡不足", "portfolio_risk", "Portfolio/Risk", "risk context must be refreshed", "先補風險脈絡。", True)

    for row in list(stock_dossier_items or []):
        ticker = str(row.get("ticker") or "").strip().upper()
        for action in list(row.get("data_gap_actions") or []):
            c = str(action.get("category") or "")
            if c == "ticker_decision_context":
                add(RUN_TYPE_EVENT_CONTEXT, ticker or "ticker", 3, "ticker_decision_context_missing", "個股決策脈絡不足", "journal_outcome", "Journal / Outcome", "context refresh", f"補 {ticker} 最近決策脈絡。", True)
            if c == "paper_exposure_pnl":
                add(RUN_TYPE_STALE_RISK, ticker or "portfolio", 3, "paper_exposure_context_missing", "缺少模擬持倉/盈虧脈絡", "portfolio_risk", "Portfolio/Risk", "portfolio context refresh", "補組合脈絡再解讀。", True)
            if c == "source_confidence":
                add(RUN_TYPE_EVENT_CONTEXT, ticker or "market", 4, "source_confidence_low", "來源一致性不足", "operator_review", "Operator Review", "await more context", "保持觀察，補授權來源。", True)
            if c in {"fundamentals", "valuation", "cashflow_earnings_balance_sheet"}:
                add(RUN_TYPE_EVENT_CONTEXT, ticker or "research", 5, "event_context_pending", "長線研究資料缺口", "external_authorized_research", "授權資料", "long-horizon research", "屬中長線研究，不作即時訊號。", False)

    add(RUN_TYPE_PRE_MARKET, "market", 4, "scheduled_pre_market", "固定開市前檢查", "today_system", "Today/System", "scheduled", "由系統自動安排。", False)
    add(RUN_TYPE_MIDDAY, "market", 4, "scheduled_midday", "固定午市檢查", "today_system", "Today/System", "scheduled", "由系統自動安排。", False)
    add(RUN_TYPE_POST_CLOSE, "market", 4, "scheduled_post_close", "固定收市後每日檢視", "daily_brief", "Daily Brief", "scheduled", "保持現有 20:00 HKT 節奏。", False)

    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in sorted(items, key=lambda x: (int(x["priority"]), x["run_type"], x["scope"], x["trigger"])):
        dedup.setdefault((item["run_type"], item["scope"], item["trigger"]), item)

    return {"status": "ok", "generated_at_hkt": (now or datetime.now(_HKT)).astimezone(_HKT).isoformat(), "manual_refresh_primary": False, "manual_refresh_fallback_only": True, "items": list(dedup.values())[: max(1, max_items)]}
