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
        "資料夠唔夠",
        "策略週期判斷",
        "技術觀察",
        "基本面觀察",
        "新聞 / 催化觀察",
        "風險提示",
        "模擬組合背景",
        "AI 模擬方向",
        "你下一步要做咩",
    ]:
        assert label in block


def test_stock_review_empty_state_and_safety_text() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    block = _stock_review_block(html)

    assert "暫時未有可檢視的股票簡報。系統會在有 signals / risk / portfolio context 後顯示。" in block
    assert "AI 模擬方向只分為：偏正面觀察、繼續觀察、謹慎、資料不足。只供模擬檢視。" in html
    assert "只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議" in block
    assert "短線：只供觀察" in block


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

    assert 'if (key === "sufficient") return "足夠";' in block
    assert 'if (key === "partial") return "部分";' in block
    assert 'if (key === "unavailable") return "未能提供";' in block
    assert 'horizon.recommended_review_horizon' in block
    assert '`建議：${horizonLabel(horizon.recommended_review_horizon)}`' in block


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
