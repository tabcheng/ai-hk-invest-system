import json
import subprocess
from pathlib import Path


INDEX_HTML = Path("miniapp/index.html").read_text(encoding="utf-8")


def _extract_inline_script_source() -> str:
    start = INDEX_HTML.index("<script>") + len("<script>")
    end = INDEX_HTML.rindex("</script>")
    return INDEX_HTML[start:end]


def _render_with_sample_payload() -> dict[str, object]:
    script_source = _extract_inline_script_source()
    payload = {
        "sections": {
            "latest_system_run": {
                "status": "ok",
                "runner_status": "ok",
                "business_date": "2026-05-08",
                "data_timestamp_hkt": "2026-05-08 20:00:00 HKT",
                "run_id": "run-113",
                "processed_tickers": 10,
                "successful_tickers": 8,
                "failed_tickers": 2,
            },
            "signals_summary": {
                "status": "ok",
                "review_readiness": "ok",
                "business_date": "2026-05-08",
                "data_timestamp_hkt": "2026-05-08 20:00:00 HKT",
                "covered_tickers": 3,
                "shown_signals": 3,
                "shown_positive_signals": 1,
                "shown_neutral_signals": 1,
                "shown_negative_signals": 1,
                "shown_unknown_signals": 0,
                "top_items": [],
            },
            "daily_review_summary": {
                "status": "ok",
                "review_readiness": "partial",
                "available_sections": ["latest_system_run"],
                "unavailable_sections": ["signals", "paper_pnl", "risk"],
            },
        }
    }

    node_script = f"""
const payload = {json.dumps(payload)};

class Element {{
  constructor(tagName) {{
    this.tagName = tagName;
    this.className = "";
    this._text = "";
    this.children = [];
  }}
  set textContent(v) {{ this._text = String(v); this.children = []; }}
  get textContent() {{ return this._text + this.children.map((c) => c.textContent || "").join(""); }}
  append(...nodes) {{ nodes.forEach((n) => this.appendChild(n)); }}
  appendChild(node) {{ this.children.push(node); return node; }}
}}

const byId = {{
  "overview-card": new Element("section"),
  "latest-card": new Element("section"),
  "daily-card": new Element("section"),
  "signals-card": new Element("section"),
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
    daily_has_signals: dailyCardText.includes("已有資料") && dailyCardText.includes("信號摘要"),
    daily_missing_has_signals: dailyCardText.includes("未有資料") && dailyCardText.includes("未有資料信號摘要"),
    daily_missing_has_pnl: dailyCardText.includes("未有資料") && dailyCardText.includes("模擬盈虧"),
    daily_missing_has_risk: dailyCardText.includes("未有資料") && dailyCardText.includes("風險摘要"),
    boundary_visible: byId["overview-card"].textContent.includes("Daily Overview"),
    system_row_has_chip_text: systemRowText.includes("System Run Status") && systemRowText.includes("成功"),
    coverage_row_has_chip_text: coverageRowText.includes("Daily Review Coverage") && coverageRowText.includes("部分完成"),
    full_render_text: Object.values(byId).map((n) => n.textContent).join("\\n"),
  }};
  process.stdout.write(JSON.stringify(summary));
}})().catch((err) => {{
  process.stderr.write(String(err && err.stack ? err.stack : err));
  process.exit(1);
}});
"""

    run = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    return json.loads(run.stdout)


def test_status_hierarchy_labels_present() -> None:
    assert "System Run Status" in INDEX_HTML
    assert "Daily Review Coverage" in INDEX_HTML
    assert "部分完成表示部分檢視區塊仍未有資料，並不代表最新系統運行失敗" in INDEX_HTML


def test_data_availability_card_wording_present() -> None:
    assert "最新系統運行" in INDEX_HTML
    assert "信號摘要" in INDEX_HTML
    assert "模擬盈虧" in INDEX_HTML
    assert "風險摘要" in INDEX_HTML
    assert "已載入" in INDEX_HTML
    assert "未有資料" in INDEX_HTML
    assert "data not available yet" in INDEX_HTML


def test_render_level_daily_summary_availability_consistency() -> None:
    rendered = _render_with_sample_payload()

    assert rendered["daily_has_signals"] is True
    assert rendered["daily_missing_has_signals"] is False
    assert rendered["daily_missing_has_pnl"] is True
    assert rendered["daily_missing_has_risk"] is True
    assert rendered["boundary_visible"] is True
    assert rendered["system_row_has_chip_text"] is True
    assert rendered["coverage_row_has_chip_text"] is True

    full_text = str(rendered["full_render_text"]).lower()
    assert "submit" not in full_text
    assert "order" not in full_text
    assert "broker" not in full_text


def test_layout_polish_rows_and_timestamp_wrap_guard_present() -> None:
    assert "row-inline" in INDEX_HTML
    assert "time-label" in INDEX_HTML
    assert "time-value" in INDEX_HTML
    assert "line4.append(timeLabel,timeValue);" in INDEX_HTML
    assert "line2.appendChild(renderStatusChip" in INDEX_HTML
    assert "line3.appendChild(renderStatusChip" in INDEX_HTML


def test_signal_warning_and_unknown_confidence_present() -> None:
    assert "未提供 / Unknown" in INDEX_HTML
    assert "目前只顯示技術信號方向；信心、風險、模擬盈虧未完整，因此不應視為完整決策。" in INDEX_HTML


def test_safety_boundary_copy_present() -> None:
    assert "只限模擬交易 · 決策支援 · 不連接券商 · 不作真實落盤" in INDEX_HTML
    assert "Telegram initData 只在後端驗證" in INDEX_HTML
    assert "前端不使用 initDataUnsafe 作授權" in INDEX_HTML
    assert "前端不保存 Supabase secret / service role key" in INDEX_HTML
    assert "所有信號只供模擬檢視，並非買賣指示" in INDEX_HTML
