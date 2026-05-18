from __future__ import annotations

from typing import Any

_ALLOWED_STATUS = {"working", "working_basic", "partial", "deferred"}


def build_ai_team_operating_model_v1() -> dict[str, Any]:
    desks = [
        {
            "name": "Market Data Desk",
            "name_zh": "市場資料組",
            "status": "partial",
            "current_capability": "已有 MarketDataProvider 抽象、market smoke、source/timestamp/freshness 處理。",
            "limitation": "供應商覆蓋仍有限，擴展屬上線後優化。",
            "evidence": "market_data provider + smoke + freshness read model",
            "next_action": "保持抽象邊界，按 post-launch backlog 擴展供應商。",
            "safety_boundary": "只供模擬檢視，不連接券商，不建立訂單。",
        },
        {
            "name": "Signal / Strategy Desk",
            "name_zh": "訊號與策略組",
            "status": "working_basic",
            "current_capability": "已有 deterministic MA signal 與 signals read model。",
            "limitation": "未涵蓋完整策略研究引擎與多模型對比。",
            "evidence": "signals pipeline + miniapp/telegram signals summary",
            "next_action": "維持 deterministic 基線；高階研究留待 post-launch。",
            "safety_boundary": "輸出只屬 AI simulated decision，不等於真實買賣指示。",
        },
        {
            "name": "Paper Trading Desk",
            "name_zh": "模擬交易組",
            "status": "working",
            "current_capability": "支援 simulated events、paper PnL 與 review surfaces。",
            "limitation": "僅 paper-trading；無 broker/live execution。",
            "evidence": "paper trades + pnl/risk/journal read surfaces",
            "next_action": "持續做 smoke + QA，維持 human-in-the-loop。",
            "safety_boundary": "不連接券商、不做真金白銀執行。",
        },
        {
            "name": "Risk Desk",
            "name_zh": "風險組",
            "status": "working_basic",
            "current_capability": "有 risk summary、stale risk refresh、限制提示。",
            "limitation": "更深入風險 attribution 與 dashboard 仍未完成。",
            "evidence": "risk summary + stale_risk_refresh runtime",
            "next_action": "先保持可讀風險提示，進階 attribution 放 post-launch。",
            "safety_boundary": "風險輸出只供 review，不觸發 execution。",
        },
        {
            "name": "Decision Journal Desk",
            "name_zh": "決策日誌組",
            "status": "working",
            "current_capability": "可記錄 human paper decision journal 並做 outcome review。",
            "limitation": "屬 review workflow，非自動化落盤引擎。",
            "evidence": "journal entry + outcome review surfaces",
            "next_action": "保持可審計性與 read-only outcome 顯示。",
            "safety_boundary": "人手最終真實交易決定在系統外。",
        },
        {
            "name": "AI Team Packet Desk",
            "name_zh": "AI 團隊摘要組",
            "status": "working",
            "current_capability": "有 deterministic bounded packet，已供 Mini App + Telegram 使用。",
            "limitation": "未接入 LLM 摘要。",
            "evidence": "ai_team_analysis_packet summary in latest_system_runs",
            "next_action": "先維持 deterministic；LLM provider 抽象留 post-launch。",
            "safety_boundary": "只供模擬檢視，只供決策支援。",
        },
        {
            "name": "Operator Surface Desk",
            "name_zh": "操作介面組",
            "status": "working",
            "current_capability": "Mini App + Telegram 提供 read-only review surfaces。",
            "limitation": "以營運檢視為主，非投資建議引擎。",
            "evidence": "Mini App tabs + Telegram operator commands",
            "next_action": "維持中文優先與 fail-closed 呈現。",
            "safety_boundary": "不顯示 real order/action 指令，不做 execution。",
        },
        {
            "name": "LLM Research Desk",
            "name_zh": "LLM 研究組",
            "status": "deferred",
            "current_capability": "目前未啟用；保持 deterministic read-only。",
            "limitation": "需 backend-only provider abstraction、mock-first、token backend-only。",
            "evidence": "guardrail: no llm call in current runtime",
            "next_action": "post-launch 再按審批引入 backend-only 抽象。",
            "safety_boundary": "未啟用前不得引入 live LLM call。",
        },
        {
            "name": "Vendor Expansion Desk",
            "name_zh": "供應商擴展組",
            "status": "deferred",
            "current_capability": "目前以既有資料來源與抽象邊界運作。",
            "limitation": "尚未擴展多供應商覆蓋。",
            "evidence": "market data abstraction boundary already present",
            "next_action": "post-launch 以 MarketDataProvider 抽象逐步擴展。",
            "safety_boundary": "擴展前後都不得突破 paper-only boundary。",
        },
    ]

    for desk in desks:
        if desk["status"] not in _ALLOWED_STATUS:
            raise ValueError("unsupported operating-model status")

    counts = {"working": 0, "partial": 0, "deferred": 0}
    for desk in desks:
        if desk["status"] in {"working", "working_basic"}:
            counts["working"] += 1
        elif desk["status"] == "partial":
            counts["partial"] += 1
        else:
            counts["deferred"] += 1

    readiness = "條件式可用"
    return {
        "status": "ok",
        "model_version": "ai_team_operating_model.v1",
        "read_only": True,
        "paper_trade_only": True,
        "decision_support_only": True,
        "no_broker_execution": True,
        "no_live_execution": True,
        "no_real_money_execution": True,
        "overall_readiness": readiness,
        "summary": {
            "working_desks": counts["working"],
            "partial_desks": counts["partial"],
            "deferred_desks": counts["deferred"],
            "total_desks": len(desks),
        },
        "desks": desks,
        "safety_note": "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議｜真實買賣決定由人類在系統外作出",
    }
