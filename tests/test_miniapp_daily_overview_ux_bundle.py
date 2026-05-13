import json
import subprocess
from pathlib import Path


INDEX_HTML = Path("miniapp/index.html").read_text(encoding="utf-8")


def _extract_inline_script_source() -> str:
    start = INDEX_HTML.index("<script>") + len("<script>")
    end = INDEX_HTML.rindex("</script>")
    return INDEX_HTML[start:end]


def _render_with_sample_payload(payload: dict[str, object]) -> dict[str, object]:
    script_source = _extract_inline_script_source()

    node_script = f"""
const payload = {json.dumps(payload)};

class Element {{
  constructor(tagName) {{
    this.tagName = tagName;
    this.className = "";
    this._text = "";
    this.children = [];
    this.value = "";
    this.checked = false;
    this._listeners = {{}};
  }}
  set textContent(v) {{ this._text = String(v); this.children = []; }}
  get textContent() {{ return this._text + this.children.map((c) => c.textContent || "").join(""); }}
  append(...nodes) {{ nodes.forEach((n) => this.appendChild(n)); }}
  appendChild(node) {{ this.children.push(node); return node; }}
  addEventListener(name, handler) {{ this._listeners[name] = handler; }}
  set innerHTML(v) {{
    this._text = String(v || "");
    const ids = ["journal-result-banner","journal-context-details","journal-context-content","journal-snapshot-details","journal-snapshot-content","journal-outcome-details","journal-outcome-content","journal-form","journal-ticker","journal-decision-type","journal-rationale","journal-counter","journal-confidence","journal-ack","journal-submit","journal-result"];
    ids.forEach((id) => {{
      if (this._text.includes(`id="${{id}}"`) && !byId[id]) {{
        byId[id] = new Element(id === "journal-form" ? "form" : "div");
      }}
    }});
  }}
  get innerHTML() {{ return this._text; }}
}}

const byId = {{
  "overview-card": new Element("section"),
  "team-card": new Element("section"),
  "latest-card": new Element("section"),
  "daily-card": new Element("section"),
  "signals-card": new Element("section"),
  "context-shell": new Element("section"),
  "paper-pnl-card": new Element("section"),
  "risk-card": new Element("section"),
  "journal-card": new Element("section"),
  "build-meta": new Element("p"),
}};

const document = {{
  createElement: (tag) => new Element(tag),
  getElementById: (id) => byId[id],
}};

const window = {{
  MINIAPP_API_BASE_URL: "https://example.invalid",
  Telegram: {{ WebApp: {{ initData: "fake-init-data" }} }},
}};

const fetch = async () => ({{ json: async () => payload }});
globalThis.document = document;
globalThis.window = window;
globalThis.fetch = fetch;

{script_source}

(async () => {{
  await loadReviewShell();
  const dailyCardText = byId["daily-card"].textContent;
  const overviewChildren = byId["overview-card"].children;
  const systemRowText = overviewChildren[2]?.textContent || "";
  const coverageRowText = overviewChildren[3]?.textContent || "";
  const summary = {{
    context_text_before_change: byId["context-shell"] ? byId["context-shell"].textContent : "",
    daily_has_signals: dailyCardText.includes("已有資料") && dailyCardText.includes("信號摘要"),
    daily_missing_has_signals: dailyCardText.includes("未有資料") && dailyCardText.includes("未有資料信號摘要"),
    daily_missing_has_pnl: dailyCardText.includes("未有資料") && dailyCardText.includes("模擬盈虧"),
    daily_missing_has_risk: dailyCardText.includes("未有資料") && dailyCardText.includes("風險摘要"),
    pnl_card_unavailable: byId["paper-pnl-card"].textContent.includes("未有資料"),
    risk_card_unavailable: byId["risk-card"].textContent.includes("未有資料"),
    build_meta_visible: byId["build-meta"].textContent.includes("UI build:") && byId["build-meta"].textContent.includes("Deployed build:"),
    boundary_visible: byId["overview-card"].textContent.includes("Daily Brief"),
    system_row_has_chip_text: systemRowText.includes("一句總結"),
    coverage_row_has_chip_text: coverageRowText.includes("資料狀態"),
    journal_selected_ticker: byId["journal-ticker"] ? byId["journal-ticker"].value : "",
    journal_ticker_options: byId["journal-ticker"] ? byId["journal-ticker"].children.map((c) => c.textContent) : [],
    journal_context_text: byId["journal-context-content"] ? byId["journal-context-content"].textContent : "",
    journal_context_html: byId["journal-context-content"] ? byId["journal-context-content"].innerHTML : "",
    full_render_text: Object.values(byId).map((n) => n.textContent).join("\\n"),
  }};
  if (byId["context-shell"] && byId["context-shell"].children[0] && byId["context-shell"].children[0].children[0]) {{
    const picker = byId["context-shell"].children[0].children[0];
    picker.value = "0388.HK";
    if (picker._listeners && picker._listeners["change"]) picker._listeners["change"]();
    summary.context_text_after_change = byId["context-shell"].textContent;
  }} else {{
    summary.context_text_after_change = "";
  }}
  process.stdout.write(JSON.stringify(summary));
}})().catch((err) => {{
  process.stderr.write(String(err && err.stack ? err.stack : err));
  process.exit(1);
}});
"""

    run = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    return json.loads(run.stdout)


def _base_sections() -> dict[str, object]:
    return {
        "latest_system_run": {"status": "ok", "runner_status": "success", "business_date": "2026-05-08", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT", "run_id": "run-113", "processed_tickers": 10, "successful_tickers": 8, "failed_tickers": 2},
        "signals_summary": {"status": "ok", "review_readiness": "ok", "business_date": "2026-05-08", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT", "covered_tickers": 3, "shown_signals": 3, "shown_positive_signals": 1, "shown_neutral_signals": 1, "shown_negative_signals": 1, "shown_unknown_signals": 0, "top_items": []},
        "daily_review_summary": {"status": "ok", "review_readiness": "partial", "available_sections": ["latest_system_run"], "unavailable_sections": ["signals", "paper_pnl", "risk"]},
        "daily_brief": {
            "status": "ok",
            "headline_summary": "今日先檢查資料與風險，再做人手模擬決定。",
            "risk_brief": "有中等風險提示，請先查看風險詳情，不要只靠方向判斷。",
            "simulated_direction": "繼續觀察，等待更多確認訊號",
            "operator_next_actions": ["先看風險摘要。", "再看信號原因。"],
            "technical_details": {"review_readiness": "partial", "risk_level": "medium", "signals_status": "ok"},
            "safety_note": "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議",
        },
        "paper_pnl_summary": {"status": "unavailable"},
        "risk_summary": {"status": "unavailable"},
    }


def test_status_hierarchy_labels_present() -> None:
    assert "今日簡報 / Daily Brief" in INDEX_HTML
    assert "一句總結" in INDEX_HTML
    assert "資料夠唔夠" in INDEX_HTML
    assert "風險提示" in INDEX_HTML
    assert "AI 模擬方向" in INDEX_HTML
    assert "你下一步要做咩" in INDEX_HTML
    assert "查看技術資料" in INDEX_HTML


def test_data_availability_card_wording_present() -> None:
    assert "最新系統運行" in INDEX_HTML
    assert "信號摘要" in INDEX_HTML
    assert "模擬盈虧" in INDEX_HTML
    assert "風險摘要" in INDEX_HTML
    assert "已載入" in INDEX_HTML
    assert "未有資料" in INDEX_HTML
    assert "data not available yet" in INDEX_HTML


def test_render_level_daily_summary_availability_consistency() -> None:
    rendered = _render_with_sample_payload({"sections": _base_sections()})

    assert rendered["daily_has_signals"] is True
    assert rendered["daily_missing_has_signals"] is False
    assert rendered["daily_missing_has_pnl"] is True
    assert rendered["daily_missing_has_risk"] is True
    assert rendered["pnl_card_unavailable"] is True
    assert rendered["risk_card_unavailable"] is True
    assert rendered["boundary_visible"] is True
    assert rendered["system_row_has_chip_text"] is True
    assert rendered["coverage_row_has_chip_text"] is True
    assert rendered["build_meta_visible"] is True

    full_text = str(rendered["full_render_text"]).lower()
    assert "place order" not in full_text
    assert "execute trade" not in full_text
    assert "broker execution" not in full_text
    assert "查看技術資料" in full_text
    assert "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議" in full_text


def test_ready_copy_and_no_empty_missing_chip_area() -> None:
    sections = _base_sections()
    sections["daily_review_summary"] = {"status": "ok", "available_sections": ["latest_system_run", "signals", "paper_pnl", "risk"], "unavailable_sections": []}
    sections["paper_pnl_summary"] = {"status": "ok", "currency": "HKD", "total_positions": 1, "open_positions": 1, "closed_positions": 0, "realized_pnl": 0, "unrealized_pnl": 1, "total_pnl": 1, "data_timestamp_hkt": "2026-05-08 20:00:00 HKT", "limitations": ["bounded"]}
    sections["risk_summary"] = {"status": "ok", "risk_level": "low", "warnings": [], "limitations": ["bounded"], "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"}
    rendered = _render_with_sample_payload(
        {"sections": sections}
    )
    full_text = str(rendered["full_render_text"])
    assert "今日先檢查資料與風險，再做人手模擬決定。" in full_text
    assert "暫無缺失區塊" in full_text
    assert "未有資料信號摘要" not in full_text
    assert "以上為模擬 / paper-trading 盈虧" in full_text
    assert "貨幣HKD" in full_text
    assert "資料時間：" in full_text
    assert "風險摘要只供 review，不會自動阻止或建立任何真實交易。" in full_text
    assert "暫無風險警示" in full_text


def test_unavailable_coverage_copy_present() -> None:
    sections = _base_sections()
    sections["latest_system_run"] = {"status": "unavailable"}
    sections["signals_summary"] = {"status": "unavailable"}
    sections["daily_review_summary"] = {"status": "ok", "available_sections": [], "unavailable_sections": []}
    rendered = _render_with_sample_payload({"sections": sections})
    assert "今日先檢查資料與風險，再做人手模擬決定。" in str(rendered["full_render_text"])


def test_ai_direction_positive_dominant_wording() -> None:
    sections = _base_sections()
    sections["daily_review_summary"] = {"status": "ok", "available_sections": ["latest_system_run", "signals", "paper_pnl", "risk"], "unavailable_sections": []}
    sections["daily_brief"]["simulated_direction"] = "模擬偏向正面觀察"
    sections["risk_summary"] = {"status": "ok", "risk_level": "low", "warnings": []}
    rendered = _render_with_sample_payload({"sections": sections})
    full_text = str(rendered["full_render_text"])
    assert "AI 模擬方向：模擬偏向正面觀察" in full_text
    assert "AI 模擬方向：AI 模擬方向偏正面" not in full_text


def test_ai_direction_negative_dominant_wording() -> None:
    sections = _base_sections()
    sections["daily_brief"]["simulated_direction"] = "模擬偏向審慎，暫時以防守為主"
    sections["risk_summary"] = {"status": "ok", "risk_level": "high", "warnings": ["r1"]}
    rendered = _render_with_sample_payload({"sections": sections})
    full_text = str(rendered["full_render_text"])
    assert "AI 模擬方向：模擬偏向審慎，暫時以防守為主" in full_text


def test_medium_risk_uses_caution_wording_not_controllable() -> None:
    sections = _base_sections()
    sections["daily_brief"]["risk_brief"] = "有中等風險提示，請先查看風險詳情，不要只靠方向判斷。"
    sections["risk_summary"] = {"status": "ok", "risk_level": "medium", "warnings": ["r1"]}
    rendered = _render_with_sample_payload({"sections": sections})
    full_text = str(rendered["full_render_text"])
    assert "有中等風險提示，請先查看風險詳情，不要只靠方向判斷。" in full_text
    assert "風險可控" not in full_text


def test_low_risk_wording_and_no_signal_risk_unavailable_fallback() -> None:
    sections = _base_sections()
    sections["daily_brief"]["risk_brief"] = "暫未見重大風險警示，但仍要人手覆核。"
    sections["risk_summary"] = {"status": "ok", "risk_level": "low", "warnings": []}
    rendered_low = _render_with_sample_payload({"sections": sections})
    assert "暫未見重大風險警示，但仍要人手覆核。" in str(rendered_low["full_render_text"])

    sections2 = _base_sections()
    sections2["daily_brief"]["risk_brief"] = "風險資料不足，暫時未有足夠資訊。"
    sections2["daily_brief"]["simulated_direction"] = "資料不足，暫時只可觀察"
    sections2["signals_summary"] = {"status": "unavailable"}
    sections2["risk_summary"] = {"status": "unavailable"}
    rendered_unavailable = _render_with_sample_payload({"sections": sections2})
    full_text2 = str(rendered_unavailable["full_render_text"])
    assert "AI 模擬方向：資料不足，暫時只可觀察" in full_text2
    assert "風險資料不足，暫時未有足夠資訊。" in full_text2
    assert full_text2.count("只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議") == 1


def test_daily_brief_missing_uses_risk_fallback_mapping() -> None:
    sections = _base_sections()
    sections.pop("daily_brief", None)

    sections["risk_summary"] = {"status": "ok", "risk_level": "high", "warnings": ["r1"]}
    high = str(_render_with_sample_payload({"sections": sections})["full_render_text"])
    assert "風險提示：風險偏高，先做風險檢查，唔好急住跟方向。" in high

    sections["risk_summary"] = {"status": "ok", "risk_level": "medium", "warnings": ["r1"]}
    medium = str(_render_with_sample_payload({"sections": sections})["full_render_text"])
    assert "風險提示：有中等風險提示，請先查看風險詳情，不要只靠方向判斷。" in medium

    sections["risk_summary"] = {"status": "ok", "risk_level": "low", "warnings": []}
    low = str(_render_with_sample_payload({"sections": sections})["full_render_text"])
    assert "風險提示：暫未見重大風險警示，但仍要人手覆核。" in low

    sections["risk_summary"] = {"status": "unavailable", "risk_level": "unknown", "warnings": []}
    unknown = str(_render_with_sample_payload({"sections": sections})["full_render_text"])
    assert "風險提示：風險資料不足，暫時未有足夠資訊。" in unknown
    assert "AI 模擬方向：AI 模擬方向" not in unknown


def test_layout_polish_rows_and_timestamp_wrap_guard_present() -> None:
    assert "row-inline" in INDEX_HTML
    assert "time-label" in INDEX_HTML
    assert "time-value" in INDEX_HTML
    assert "line4.append(timeLabel,timeValue);" in INDEX_HTML
    assert "line2.appendChild(summary)" in INDEX_HTML
    assert "line3.appendChild(renderStatusChip" in INDEX_HTML


def test_signal_warning_and_unknown_confidence_present() -> None:
    assert "未提供 / Unknown" in INDEX_HTML
    assert "目前只顯示技術信號方向；信心、風險、模擬盈虧未完整，因此不應視為完整決策。" in INDEX_HTML


def test_safety_boundary_copy_present() -> None:
    assert "只限模擬交易 · 決策支援 · 不連接券商 · 不作真實落盤" in INDEX_HTML
    assert "Telegram initData 只在後端驗證" in INDEX_HTML
    assert "前端不使用 initDataUnsafe 作授權" in INDEX_HTML
    assert "前端不保存 Supabase secret / service role key" in INDEX_HTML
    assert "只供模擬檢視，不建立訂單，不連接券商" in INDEX_HTML
    assert "UI build:" in INDEX_HTML
    assert "Deployed build:" in INDEX_HTML


def test_system_safety_card_is_system_tab_only() -> None:
    assert 'id="system-safety-card"' in INDEX_HTML
    assert 'data-tab-panel="system"' in INDEX_HTML
    assert 'system:["signals-card","context-card","team-card","latest-card","daily-card","system-safety-card"]' in INDEX_HTML


def test_risk_warning_wording_branches_present() -> None:
    assert "暫無明確風險警示" in INDEX_HTML
    assert "暫無明確警示，但風險資料不足" in INDEX_HTML
    assert 'const hasInsufficientRisk = riskRaw === "unknown" || hasLimitations' in INDEX_HTML
    assert 'none.textContent=hasInsufficientRisk ? "暫無明確警示，但風險資料不足" : "暫無明確風險警示"' in INDEX_HTML


def test_journal_ticker_picker_and_context_updates() -> None:
    sections = _base_sections()
    sections["signals_summary"]["top_items"] = [
        {"ticker": "0700.HK", "signal_label": "positive", "confidence_label": "high", "reason_short": "動能改善", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"},
        {"ticker": "0388.HK", "signal_label": "neutral", "confidence_label": "medium", "reason_short": "等待突破", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"},
    ]
    sections["paper_pnl_summary"] = {"status": "ok", "total_pnl": 1, "realized_pnl": 2, "unrealized_pnl": -1, "limitations": ["pnl bounded"]}
    sections["risk_summary"] = {"status": "ok", "risk_level": "low", "warnings": [], "limitations": ["risk bounded"]}
    rendered = _render_with_sample_payload({"sections": sections})
    assert rendered["journal_selected_ticker"] == "0700.HK"
    assert "0700.HK — 正面模擬信號" in rendered["journal_ticker_options"]
    assert "0388.HK — 觀望 / 中性信號" in rendered["journal_ticker_options"]
    assert "暫無風險警示" in rendered["journal_context_text"]
    assert "Paper PnL 限制" in rendered["journal_context_text"]
    assert "Risk 限制" in rendered["journal_context_text"]


def test_context_picker_change_rerenders_context_body() -> None:
    sections = _base_sections()
    sections["signals_summary"]["top_items"] = [
        {"ticker": "0700.HK", "signal_label": "positive", "confidence_label": "high", "reason_short": "動能改善", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"},
        {"ticker": "0388.HK", "signal_label": "neutral", "confidence_label": "medium", "reason_short": "等待突破", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"},
    ]
    sections["decision_context_summary"] = {
        "status": "partial",
        "context_readiness": "insufficient",
        "tickers": [
            {"ticker": "0700.HK", "signal": {"direction": "positive", "reason": "A"}, "market": {}, "risk": {"risk_level": "low", "warnings": []}, "missing_context": [{"label_zh": "A缺失"}]},
            {"ticker": "0388.HK", "signal": {"direction": "neutral", "reason": "B"}, "market": {}, "risk": {"risk_level": "medium", "warnings": ["R2"]}, "missing_context": [{"label_zh": "B缺失"}]},
        ],
    }
    rendered = _render_with_sample_payload({"sections": sections})
    assert "A缺失" in str(rendered["context_text_before_change"])
    assert "B缺失" in str(rendered["context_text_after_change"])


def test_journal_context_renders_untrusted_text_safely() -> None:
    sections = _base_sections()
    sections["signals_summary"]["top_items"] = [
        {"ticker": "0700.HK", "signal_label": "positive", "confidence_label": "high", "reason_short": "<img src=x onerror=alert(1)>", "data_timestamp_hkt": "2026-05-08 20:00:00 HKT"},
    ]
    sections["risk_summary"] = {"status": "ok", "risk_level": "medium", "warnings": ["<svg onload=alert(1)>"], "limitations": []}
    rendered = _render_with_sample_payload({"sections": sections})
    assert "<img src=x onerror=alert(1)>" in rendered["journal_context_text"]
    assert "<svg onload=alert(1)>" in rendered["journal_context_text"]
    assert "<img" not in rendered["journal_context_html"]
    assert "<svg" not in rendered["journal_context_html"]


def test_journal_ticker_picker_no_top_items_disables_selector() -> None:
    rendered = _render_with_sample_payload({"sections": _base_sections()})
    assert rendered["journal_ticker_options"] == ["未有可選股票；請等待信號摘要載入"]
    assert "股票 ticker：未有資料 / not available yet" in rendered["journal_context_text"]
