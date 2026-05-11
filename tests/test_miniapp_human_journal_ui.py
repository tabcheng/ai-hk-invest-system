from pathlib import Path
import json
import subprocess


def test_human_journal_section_and_guardrail_wording_present():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "人手模擬決策日誌" in html
    assert "Human Paper Decision Journal" in html
    assert "記錄人手模擬決策" in html
    assert "決策參考資料 / Decision Context" in html
    assert "不建立訂單" in html
    assert "不連接券商" in html
    assert "不作真實落盤" in html
    assert "journal labels only" in html
    assert "不改變 paper position" in html
    assert "不建立買入單" in html
    assert "不建立賣出單" in html


def test_human_journal_requires_guardrail_checkbox_in_ui():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert 'id="journal-ack" type="checkbox" required' in html
    assert "日誌暫時未能寫入；未有資料被儲存。" in html
    assert "表單已修改，尚未保存目前變更。" in html
    assert 'id="journal-submit-result-card"' in html
    assert "Journal 已保存" in html
    assert "saved_at_hkt=" in html
    assert "Snapshot: failed" in html


def test_human_journal_submit_result_card_copy_contract_present():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "✅ 已保存人手模擬決策" in html
    assert "journal-submit-result-card" in html
    assert "未改變 paper position" in html
    assert "不連接券商 · 只限 paper trading" in html
    assert "上一個已保存：" in html
    assert "保存中..." in html
    assert "showToast(`✅ 已保存" in html
    assert "loadJournalSnapshots();" in html
    assert "appendLine(String(row?.rationale_text || \"N/A\").slice(0, 80));" in html
    assert "rows.map((row) =>" not in html


def _simulate_journal_submit_flow(fetch_responses: list[dict], *, edit_after_retry: bool) -> dict:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    script_source = html[html.index("<script>") + len("<script>"): html.rindex("</script>")]
    node_script = f"""
const scripted = {json.dumps(fetch_responses)};
class Element {{
  constructor(tagName, id="") {{
    this.tagName = tagName; this.id = id; this.children = []; this._text=""; this._listeners={{}};
    this.style = {{}}; this.className = ""; this.value = ""; this.checked = false; this.disabled = false; this.attributes = {{}};
  }}
  set textContent(v) {{ this._text = String(v || ""); this.children = []; }}
  get textContent() {{ return this._text + this.children.map((c) => c.textContent || "").join(""); }}
  appendChild(node) {{ this.children.push(node); node.parentNode = this; return node; }}
  append(...nodes) {{ nodes.forEach((n) => this.appendChild(n)); }}
  addEventListener(name, fn) {{ this._listeners[name] = fn; }}
  setAttribute(k,v) {{ this.attributes[k] = String(v); }}
  getAttribute(k) {{ return this.attributes[k] || null; }}
  removeChild(node) {{ this.children = this.children.filter((c) => c !== node); }}
  set innerHTML(v) {{
    this._text = String(v || "");
    const ids = ["journal-result-banner","journal-context","journal-form","journal-ticker","journal-decision-type","journal-rationale","journal-counter","journal-confidence","journal-ack","journal-submit","journal-result","journal-submit-result-card"];
    ids.forEach((id) => {{ if (this._text.includes(`id="${{id}}"`) && !byId[id]) byId[id] = new Element(id === "journal-form" ? "form" : "div", id); }});
  }}
  get innerHTML() {{ return this._text; }}
}}
const byId = {{
  "overview-card": new Element("section","overview-card"),
  "latest-card": new Element("section","latest-card"),
  "daily-card": new Element("section","daily-card"),
  "signals-card": new Element("section","signals-card"),
  "context-shell": new Element("section","context-shell"),
  "context-card": new Element("section","context-card"),
  "paper-pnl-card": new Element("section","paper-pnl-card"),
  "risk-card": new Element("section","risk-card"),
  "journal-card": new Element("section","journal-card"),
  "tab-today": new Element("button","tab-today"),
  "tab-signals": new Element("button","tab-signals"),
  "tab-context": new Element("button","tab-context"),
  "tab-journal": new Element("button","tab-journal"),
  "build-meta": new Element("p","build-meta"),
}};
const document = {{ createElement: (tag) => new Element(tag), getElementById: (id) => byId[id] }};
const window = {{ MINIAPP_API_BASE_URL: "https://example.invalid", Telegram: {{ WebApp: {{ initData: "safe-init" }} }} }};
const fetch = async (url) => {{
  if (url.includes("/miniapp/api/review-shell")) return {{ ok: true, json: async () => ({{ sections: {{ latest_system_run: {{ status: "ok", business_date: "2026-05-11", run_id: "r1", data_timestamp_hkt: "2026-05-11 20:00:00 HKT" }}, signals_summary: {{ status: "ok", top_items: [{{ ticker: "0700.HK", signal_label: "neutral", reason_short: "test" }}] }}, decision_context_summary: {{ context_readiness: "basic", tickers: [] }} }} }}) }};
  const next = scripted.shift() || {{ ok: false, payload: {{ ok: false }} }};
  return {{ ok: Boolean(next.ok), json: async () => next.payload }};
}};
globalThis.document = document; globalThis.window = window; globalThis.fetch = fetch; globalThis.setTimeout = (fn) => {{ fn(); return 1; }};
{script_source}
(async () => {{
  await loadReviewShell();
  byId["journal-ack"].checked = true;
  byId["journal-rationale"].value = "r1";
  await byId["journal-form"]._listeners["submit"]({{ preventDefault: () => {{}} }});
  byId["journal-rationale"].value = "r2";
  await byId["journal-form"]._listeners["submit"]({{ preventDefault: () => {{}} }});
  const doEditAfterRetry = {json.dumps(edit_after_retry)};
  if (doEditAfterRetry) {{
    byId["journal-rationale"].value = "r3";
    byId["journal-rationale"]._listeners["input"]();
  }}
  const card = byId["journal-submit-result-card"];
  const result = byId["journal-result"];
  process.stdout.write(JSON.stringify({{
    result_card_text: card ? card.textContent : "",
    result_card_display: card ? String(card.style.display || "") : "",
    result_role: card ? card.getAttribute("role") : null,
    result_text: result ? result.textContent : "",
  }}));
}})().catch((err) => {{ process.stderr.write(String(err)); process.exit(1); }});
"""
    run = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    return json.loads(run.stdout)


def test_success_then_journal_unavailable_preserves_previous_saved_summary() -> None:
    out = _simulate_journal_submit_flow([
        {"ok": True, "payload": {"ok": True, "ticker": "0700.HK", "decision_type": "watch", "confidence_label": "medium", "journal_id": "11", "snapshot_id": "22", "snapshot_saved": True, "saved_at_hkt": "2026-05-11 20:01:00 HKT"}},
        {"ok": False, "payload": {"ok": False, "error": "journal_unavailable"}},
    ], edit_after_retry=False)
    assert "今次提交失敗；上一個已保存紀錄仍然有效" in out["result_card_text"]
    assert "上一個已保存：0700.HK · watch · Journal #11 · Snapshot #22" in out["result_card_text"]
    assert out["result_card_display"] == "block"
    assert out["result_role"] == "alert"


def test_success_then_generic_error_preserves_previous_saved_summary() -> None:
    out = _simulate_journal_submit_flow([
        {"ok": True, "payload": {"ok": True, "ticker": "0700.HK", "decision_type": "watch", "confidence_label": "medium", "journal_id": "11", "snapshot_id": "22", "snapshot_saved": True, "saved_at_hkt": "2026-05-11 20:01:00 HKT"}},
        {"ok": False, "payload": {"ok": False, "error": "other_error"}},
    ], edit_after_retry=False)
    assert "今次提交失敗；上一個已保存紀錄仍然有效" in out["result_card_text"]
    assert "上一個已保存：0700.HK · watch · Journal #11 · Snapshot #22" in out["result_card_text"]
    assert out["result_card_display"] == "block"
    assert out["result_role"] == "alert"


def test_no_prior_save_failure_does_not_show_fake_saved_summary() -> None:
    out = _simulate_journal_submit_flow([
        {"ok": False, "payload": {"ok": False, "error": "journal_unavailable"}},
        {"ok": False, "payload": {"ok": False, "error": "other_error"}},
    ], edit_after_retry=False)
    assert "上一個已保存：" not in out["result_card_text"]
    assert "今次提交失敗；上一個已保存紀錄仍然有效" not in out["result_card_text"]
    assert out["result_card_display"] != "block"


def test_form_edit_after_failed_retry_still_shows_previous_saved_summary() -> None:
    out = _simulate_journal_submit_flow([
        {"ok": True, "payload": {"ok": True, "ticker": "0700.HK", "decision_type": "watch", "confidence_label": "medium", "journal_id": "11", "snapshot_id": "22", "snapshot_saved": True, "saved_at_hkt": "2026-05-11 20:01:00 HKT"}},
        {"ok": False, "payload": {"ok": False, "error": "journal_unavailable"}},
    ], edit_after_retry=True)
    assert "表單已修改，尚未保存目前變更。" in out["result_card_text"]
    assert "上一個已保存：0700.HK · watch · Journal #11 · Snapshot #22" in out["result_card_text"]
