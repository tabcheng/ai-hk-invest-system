from pathlib import Path
import re


def _stock_review_block(html: str) -> str:
    start = html.index("function renderStockReview")
    end = html.index("function renderRisk")
    return html[start:end]


def test_stock_review_tab_and_first_layer_labels_exist() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "股票檢視 / Stock Review" in html
    for label in [
        "一句總結",
        "檢視結論",
        "策略週期判斷",
        "短線判斷",
        "中線資料狀態",
        "長線資料狀態",
        "主要缺口",
        "風險提示",
        "AI 模擬方向",
        "你下一步要做咩",
    ]:
        assert label in block


def test_stock_review_empty_state_and_safety_text() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "暫時未有可檢視的股票簡報。系統會在有 signals / risk / portfolio context 後顯示。" in block
    assert "第一層只顯示重點，完整資料放在可展開區塊。只供模擬檢視。" in html
    assert "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議" in block
    assert "短線只供監察 / 提示 / 觀察，不建立任何模擬或真實訂單" in block
    assert "長線資料不足：缺少基本面 / 估值 / 現金流等資料" in block


def test_stock_review_uses_textcontent_no_html_injection() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "card.innerHTML" not in block
    assert "textContent" in block
    assert "opt.textContent = String(item.ticker || \"\")" in block
    assert "p.textContent = `${label}：${String(value || \"未有資料\")}`;" in block
    assert "chosen?.catalyst_observation" in block
    assert "chosen?.news_catalyst_observation" not in block


def test_stock_review_prevents_duplicate_prefixed_strings() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "AI 模擬方向：AI 模擬方向" not in block
    assert "模擬組合背景：模擬組合背景" not in block


def test_stock_review_horizon_first_layer_uses_human_labels_not_raw_enum() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "缺少日線 / 週線信號" in block
    assert "缺少風險脈絡" in block
    assert "缺少模擬組合背景" in block
    assert "缺少個股層級決策 / 結果脈絡" in block
    assert "const mediumGaps = Array.from(new Set((Array.isArray(horizon.horizon_data_gaps)" in block
    assert "if (!mediumReady && !mediumGaps.length) mediumGaps.push(\"中線資料不足：請先補充信號、風險、模擬組合與個股決策脈絡\")" in block
    assert 'horizon.recommended_review_horizon' in block
    assert '`建議：${horizonLabel(horizon.recommended_review_horizon)}`' not in block
    assert "decision_context_summary.status" not in block
    assert "technical_observation: chosen?.technical_observation" in block
    assert "fundamental_observation: chosen?.fundamental_observation" in block
    assert "catalyst_observation: chosen?.catalyst_observation" in block
    assert "portfolio_context: chosen?.portfolio_context" in block


def test_stock_review_first_layer_avoids_english_only_gap_labels() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)
    assert 'addRow("主要缺口", mediumGaps.slice(0, 3).join("；"));' in block
    assert 'if (lower.includes("daily/weekly signals")) return "缺少日線 / 週線信號";' in block
    assert 'if (lower.includes("risk context")) return "缺少風險脈絡";' in block
    assert 'if (lower.includes("paper portfolio context")) return "缺少模擬組合背景";' in block
    assert 'if (lower.includes("outcome review/context") || lower.includes("個股層級脈絡資料")) return "缺少個股層級決策 / 結果脈絡";' in block
    assert "mediumGaps.push(\"缺少日線 / 週線信號\")" not in block
    assert "mediumGaps.push(\"缺少風險脈絡\")" not in block
    assert "mediumGaps.push(\"缺少模擬組合背景\")" not in block
    assert "mediumGaps.push(\"缺少個股層級決策 / 結果脈絡\")" not in block


def test_stock_review_no_execution_wording_and_no_secret_exposure() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    for forbidden in ["Buy now", "Sell now", "Execute", "Order", "Trade action"]:
        assert forbidden not in block
    forbidden_init_data_unsafe_patterns = [
        r"window\.Telegram\.WebApp\.initDataUnsafe",
        r"Telegram\.WebApp\.initDataUnsafe",
        r"telegram\.initDataUnsafe",
        r"\.initDataUnsafe",
    ]
    for pattern in forbidden_init_data_unsafe_patterns:
        assert re.search(pattern, html, flags=re.IGNORECASE) is None
    for forbidden_secret in ["SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_"]:
        assert forbidden_secret not in html
