from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from src.miniapp_data_provider import (
    LocalArtifactMiniAppReadDataProvider,
    MiniAppReadDataProvider,
    RailwayRuntimeEnvMiniAppReadDataProvider,
)

_HKT = timezone(timedelta(hours=8))


def build_stock_dossiers_v1_section(
    signals_summary: Mapping[str, Any],
    risk_summary: Mapping[str, Any],
    decision_context_summary: Mapping[str, Any],
    ticker_level_paper_portfolio_review: Mapping[str, Any],
    latest_system_run: Mapping[str, Any] | None = None,
    daily_review_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    items = list(signals_summary.get("top_items") or [])
    context_rows = {str(row.get("ticker") or ""): row for row in list(decision_context_summary.get("tickers") or [])}
    portfolio_rows = {str(row.get("ticker") or ""): row for row in list(ticker_level_paper_portfolio_review.get("rows") or [])}
    candidate_tickers: list[str] = []
    for row in items:
        ticker = str(row.get("ticker") or "").strip()
        if ticker and ticker not in candidate_tickers:
            candidate_tickers.append(ticker)
    for ticker in list(context_rows.keys()) + list(portfolio_rows.keys()):
        t = str(ticker or "").strip()
        if t and t not in candidate_tickers:
            candidate_tickers.append(t)

    signal_lookup = {
        str(row.get("ticker") or "").strip(): str(row.get("signal") or row.get("signal_label") or "unknown").lower()
        for row in items
        if str(row.get("ticker") or "").strip()
    }
    output_items = []
    for ticker in candidate_tickers:
        signal = signal_lookup.get(ticker, "unknown")
        risk_level = str((context_rows.get(ticker, {}).get("risk", {}) or {}).get("risk_level") or risk_summary.get("risk_level") or "unknown").lower()
        has_enough_data = signal in {"positive", "neutral", "negative"} and risk_level in {"low", "medium", "high"}
        data_sufficiency = "資料足夠，可作模擬檢視。" if has_enough_data else "資料不足，暫時只可觀察。"
        if signal == "positive":
            simulated_direction = "偏正面觀察"
            technical_observation = "技術觀察偏正面，但仍要人手覆核。"
        elif signal == "negative":
            simulated_direction = "偏審慎觀察"
            technical_observation = "技術觀察偏弱，建議先控制風險。"
        elif signal == "neutral":
            simulated_direction = "繼續觀察"
            technical_observation = "技術觀察中性，未見明確方向。"
        else:
            simulated_direction = "資料不足"
            technical_observation = "技術資料不足，暫不作方向判斷。"
        if risk_level == "high":
            risk_brief = "風險較高，請先保守處理，唔好急於判斷。"
        elif risk_level == "medium":
            risk_brief = "風險中等，請先查看風險來源再作人手判斷。"
        elif risk_level == "low":
            risk_brief = "風險較低，但仍需人手覆核。"
        else:
            risk_brief = "未有足夠風險資料，請先觀察。"
        p = portfolio_rows.get(ticker, {})
        ticker_context = context_rows.get(ticker, {})
        has_ticker_context = bool(ticker_context)
        ticker_context_state = str(ticker_context.get("context_readiness") or ticker_context.get("status") or "unknown").lower()
        horizon_policy = _compute_horizon_policy(
            signal=signal,
            risk_level=risk_level,
            has_portfolio=bool(p),
            decision_context_status=str(decision_context_summary.get("status") or "unknown"),
            has_ticker_context=has_ticker_context,
            ticker_context_state=ticker_context_state,
        )
        action_context = {
            "signal": signal,
            "risk_level": risk_level,
            "market_data_status": ((latest_system_run or {}).get("market_data_status") if isinstance(latest_system_run, Mapping) else None),
            "freshness_status": ((latest_system_run or {}).get("freshness_status") if isinstance(latest_system_run, Mapping) else None),
            "market_data_acceptance_status": ((latest_system_run or {}).get("market_data_acceptance_status") if isinstance(latest_system_run, Mapping) else None),
        }
        data_gap_actions, data_gap_interpretation_summary = _build_data_gap_actions(horizon_policy, action_context)
        if p:
            portfolio_context = f"持倉={p.get('quantity', 0)}，總盈虧={p.get('total_pnl', '未有資料')}。"
        else:
            portfolio_context = "未有持倉資料。"
        output_items.append(
            {
                "ticker": ticker,
                "headline_summary": f"{ticker}：先看風險，再看方向；只供模擬檢視。",
                "data_sufficiency": data_sufficiency,
                "technical_observation": technical_observation,
                "fundamental_observation": "未有基本面資料，暫不作基本面判斷。",
                "catalyst_observation": "未有新聞/催化資料，暫不作催化判斷。",
                "risk_brief": risk_brief,
                "portfolio_context": portfolio_context,
                "simulated_direction": (
                    "資料不足，繼續觀察（短線只供觀察）"
                    if signal == "unknown"
                    else simulated_direction
                ),
                "operator_next_actions": [
                    "先補看主要資料缺口。",
                    "再核對風險摘要與限制說明。",
                    "保持觀察，並由人手在系統外作出真實買賣決定。",
                ],
                "strategy_horizon_policy": horizon_policy,
                "data_gap_actions": data_gap_actions,
                "data_gap_interpretation_summary": data_gap_interpretation_summary,
                "data_gap_action_source": "backend_read_model",
                "technical_details": {
                    "signal": signal,
                    "risk_level": risk_level,
                    "decision_context_status": decision_context_summary.get("status"),
                    "signals_status": signals_summary.get("status"),
                    "risk_status": risk_summary.get("status"),
                    "latest_run_id": latest_system_run.get("run_id") if isinstance(latest_system_run, Mapping) else None,
                    "daily_review_status": daily_review_summary.get("status") if isinstance(daily_review_summary, Mapping) else None,
                    "horizon_policy": horizon_policy,
                },
                "safety_note": "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議｜真實買賣決定由人類在系統外作出",
            }
        )
    return {"status": "ok", "source": "stock_dossier_v1_read_model", "items": output_items}


def _compute_horizon_policy(
    signal: str,
    risk_level: str,
    has_portfolio: bool,
    decision_context_status: str,
    has_ticker_context: bool,
    ticker_context_state: str,
) -> dict[str, Any]:
    short_term_policy = "短線：只供觀察；短線只作監察，不作模擬買賣方向。"
    medium_gaps=[]
    if signal not in {"positive","neutral","negative"}: medium_gaps.append("缺少 daily/weekly signals")
    if risk_level not in {"low","medium","high"}: medium_gaps.append("缺少 risk context")
    if not has_portfolio: medium_gaps.append("缺少 paper portfolio context")
    if decision_context_status not in {"ok", "partial"}:
        medium_gaps.append("缺少 outcome review/context")
    if not has_ticker_context:
        medium_gaps.append("缺少個股層級脈絡資料")
    elif ticker_context_state in {"insufficient", "unavailable", "unknown"}:
        medium_gaps.append("個股層級脈絡資料不足")
    if len(medium_gaps)==0: medium_state='sufficient'
    elif len(medium_gaps)<=2: medium_state='partial'
    elif len(medium_gaps)>=4: medium_state='unavailable'
    else: medium_state='insufficient'
    long_gaps=["缺少基本面資料","缺少估值資料","缺少盈利資料","缺少現金流資料","缺少資產負債表資料","缺少行業/週期資料"]
    recommended='medium' if medium_state=='sufficient' else 'observation_only'
    paper_scope='medium_term_review_only' if medium_state=='sufficient' else 'observation_only'
    medium_policy = (
        "中線：資料足夠，可作模擬檢視。"
        if medium_state == "sufficient"
        else "中線：資料未齊，先補風險/組合/結果脈絡，再作模擬檢視。"
    )
    return {
      'recommended_review_horizon': recommended,
      'short_term_policy': short_term_policy,
      'medium_term_policy': medium_policy,
      'long_term_policy': '長線：需要基本面/估值/盈利/現金流/資產負債表/行業週期資料，否則只可保守觀察。',
      'medium_term_data_state': medium_state,
      'long_term_data_state': 'insufficient',
      'horizon_data_gaps': medium_gaps+long_gaps,
      'horizon_confidence_notes': ['短線訊號不足以形成 paper decision','長線資料不足，長線信心有限'],
      'paper_decision_scope': paper_scope,
    }


def _build_data_gap_actions(horizon_policy: Mapping[str, Any], technical_details: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str]:
    gaps = list(horizon_policy.get("horizon_data_gaps") or [])
    gap_text = "；".join(str(x) for x in gaps)
    lower_gap_text = gap_text.lower()
    actions: list[dict[str, Any]] = []

    confidence_labels = {
        "context_required": "需要先補脈絡",
        "blocks_short_term": "限制短線判斷",
        "caps_medium_term": "限制中線信心",
        "caps_long_term": "限制長線信心",
        "watch_only": "只可觀察",
    }
    route_meta = {
        "risk_context": {"target_surface": "portfolio_risk", "target_surface_label": "Portfolio/Risk", "action_type": "review_internal_surface", "action_type_label": "檢視內部頁面", "confidence_effect": "context_required", "priority": 1, "operator_hint": "先睇風險摘要同限制，唔好將已載入理解為安全。"},
        "ticker_decision_context": {"target_surface": "journal_outcome", "target_surface_label": "Journal / Outcome", "action_type": "review_journal_context", "action_type_label": "檢視日誌脈絡", "confidence_effect": "caps_medium_term", "priority": 2, "operator_hint": "先睇最近人手模擬決策、理由同後續結果。"},
        "fundamentals": {"target_surface": "external_authorized_research", "target_surface_label": "授權資料 / 公司資料", "action_type": "review_external_authorized_source", "action_type_label": "補看授權資料", "confidence_effect": "caps_long_term", "priority": 3, "operator_hint": "補看業績、盈利能力、資產負債同公告後先做長線 review。"},
        "valuation": {"target_surface": "external_authorized_research", "target_surface_label": "授權資料 / 估值比較", "action_type": "review_external_authorized_source", "action_type_label": "補看授權資料", "confidence_effect": "caps_long_term", "priority": 4, "operator_hint": "補估值比較、歷史估值、同業比較；未補前只可觀察。"},
        "cashflow_earnings_balance_sheet": {"target_surface": "external_authorized_research", "target_surface_label": "授權資料 / 財務細項", "action_type": "review_external_authorized_source", "action_type_label": "補看授權資料", "confidence_effect": "caps_long_term", "priority": 5, "operator_hint": "補現金流、盈利、資產負債表後再 review。"},
        "market_freshness": {"target_surface": "system_market_data", "target_surface_label": "System / Market Data", "action_type": "review_market_freshness", "action_type_label": "核對市場資料時間", "confidence_effect": "blocks_short_term", "priority": 1, "operator_hint": "先核對資料時間、freshness、market smoke；不可當即時訊號。"},
        "paper_exposure_pnl": {"target_surface": "portfolio_risk", "target_surface_label": "Portfolio/Risk", "action_type": "review_portfolio_context", "action_type_label": "檢視組合背景", "confidence_effect": "context_required", "priority": 2, "operator_hint": "先睇模擬持倉與 PnL，唔好推斷 exposure 安全。"},
        "source_confidence": {"target_surface": "operator_review", "target_surface_label": "Operator Review", "action_type": "observe_only", "action_type_label": "保持觀察", "confidence_effect": "watch_only", "priority": 6, "operator_hint": "來源或訊號未一致，保持觀察，補官方或已授權來源。"},
        "general_review": {"target_surface": "stock_review", "target_surface_label": "Stock Review", "action_type": "review_internal_surface", "action_type_label": "檢視內部頁面", "confidence_effect": "context_required", "priority": 9, "operator_hint": "繼續檢視風險、信號同人手模擬決策紀錄。"},
    }

    def push(category: str, label: str, interpretation: str) -> None:
        if any(row.get("category") == category for row in actions):
            return
        meta = route_meta.get(category, route_meta["general_review"])
        confidence_key = str(meta.get("confidence_effect") or "context_required")
        actions.append(
            {
                "category": category,
                "label": label,
                "interpretation": interpretation,
                "review_only": True,
                **meta,
                "confidence_effect_label": confidence_labels.get(confidence_key, "需要先補脈絡"),
            }
        )

    if "risk context" in lower_gap_text:
        push("risk_context", "先補看：風險摘要與限制說明", "已載入不等於可安全判斷")
    if ("outcome review/context" in lower_gap_text) or ("缺少個股層級脈絡資料" in gap_text) or ("個股層級脈絡資料不足" in gap_text):
        push("ticker_decision_context", "先補看：最近模擬決策日誌、決策脈絡或結果", "未足夠支持提高檢視信心")
    if "缺少基本面資料" in gap_text:
        push("fundamentals", "先補看：最新業績、盈利能力、資產負債與公司公告", "長線 review 暫不提高信心")
    if "缺少估值資料" in gap_text:
        push("valuation", "先補看：估值比較、歷史估值、同業比較", "長線只可觀察")
    if any(x in gap_text for x in ["缺少現金流資料", "缺少盈利資料", "缺少資產負債表資料"]):
        push("cashflow_earnings_balance_sheet", "先補看：現金流／盈利／資產負債表財務細項", "不應輸出強長線結論")

    market_flags = [
        str(technical_details.get("market_data_status") or "").lower(),
        str(technical_details.get("freshness_status") or "").lower(),
        str(technical_details.get("market_data_acceptance_status") or "").lower(),
    ]

    def _is_market_freshness_gap(flag: str) -> bool:
        value = str(flag or "").strip().lower()
        if not value:
            return False
        # Explicitly allow paper-review acceptance status on its own.
        # Separate freshness/market status fields can still independently mark stale/delayed.
        if value == "acceptable_for_paper_review":
            return False
        if value.startswith("stale") or value.startswith("unknown") or value.startswith("unavailable") or value.startswith("delayed"):
            return True
        return any(token in value for token in ["stale", "unknown", "unavailable", "delayed", "caution_last_available_close"])

    if any(_is_market_freshness_gap(flag) for flag in market_flags):
        push("market_freshness", "先補看：資料時間、更新狀態與市場 smoke 檢查證據", "短線只可觀察，不可當即時訊號")
    if "paper portfolio context" in lower_gap_text:
        push("paper_exposure_pnl", "先補看：模擬組合／風險頁的持倉與盈虧脈絡", "不可推斷目前 paper exposure 安全")

    signal = str(technical_details.get("signal") or "").lower()
    risk_level = str(technical_details.get("risk_level") or "").lower()
    if signal not in {"positive", "neutral", "negative"} or risk_level not in {"low", "medium", "high"}:
        push("source_confidence", "保持觀察：補官方或已授權來源，避免單一訊號", "來源或訊號未一致，不可升級為明確方向")

    if not actions:
        push("general_review", "下一步資料行動：繼續檢視風險、信號與人手模擬決策紀錄", "仍只供模擬檢視，不代表買賣建議")

    return actions, f"解讀限制：{'；'.join(row['interpretation'] for row in actions[:2])}"


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
        sim_direction = "資料不足，暫時只可觀察"
    elif risk_level in {"unknown", "unavailable"} or data_state == "insufficient":
        sim_direction = "資料不足，暫時只可觀察"
    elif dominant == "positive":
        sim_direction = "模擬偏向正面觀察"
    elif dominant == "negative":
        sim_direction = "模擬偏向審慎，暫時以防守為主"
    else:
        sim_direction = "繼續觀察，等待更多確認訊號"
    if risk_level == "high":
        risk_brief = "風險偏高，先做風險檢查，唔好急住跟方向。"
    elif risk_level == "medium":
        risk_brief = "有中等風險提示，請先查看風險詳情，不要只靠方向判斷。"
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
    sections["stock_dossier_review"] = build_stock_dossiers_v1_section(
        sections["signals_summary"],
        sections["risk_summary"],
        sections["decision_context_summary"],
        sections["ticker_level_paper_portfolio_review"],
        latest_system_run=sections["latest_system_run"],
        daily_review_summary=sections["daily_review_summary"],
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
