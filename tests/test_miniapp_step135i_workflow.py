from pathlib import Path

HTML = Path('miniapp/index.html').read_text(encoding='utf-8')


def test_today_and_stockreview_contract_strings():
    assert '資料狀態：可檢視，但風險資料不足' in HTML
    assert '檢視結論' in HTML
    assert '策略週期' in HTML
    assert 'AI 模擬方向' in HTML
    assert '查看技術資料' in HTML
    assert '建議：' not in HTML


def test_journal_create_first_collapsed_sections():
    assert '<h2>新增人手模擬決策</h2>' in HTML
    assert '<details id="journal-context-details" data-tab-panel="journal"><summary>決策參考資料</summary>' in HTML
    assert '<details id="journal-context-details" data-tab-panel="journal" open' not in HTML
    assert 'id="journal-context-content"' in HTML
    assert '<details id="journal-snapshot-details" data-tab-panel="journal"><summary>最近紀錄</summary>' in HTML
    assert '<details id="journal-snapshot-details" data-tab-panel="journal" open' not in HTML
    assert 'id="journal-snapshot-content"' in HTML
    assert '<details id="journal-outcome-details" data-tab-panel="journal"' in HTML
    assert '<details id="journal-outcome-details" data-tab-panel="journal" open' not in HTML
    assert 'id="journal-outcome-content"' in HTML


def test_system_safety_and_tab_mapping_present():
    assert 'data-tab-panel="system"' in HTML
    assert 'aria-labelledby="tab-system"' in HTML
    assert '只供模擬檢視 · 不建立訂單 · 不連接券商 · 不是真實買賣建議' in HTML


def test_set_active_tab_uses_stable_journal_ids():
    assert 'journal:["journal-card","journal-context-details","journal-snapshot-details","journal-outcome-details"]' in HTML
    assert "journal-context-details" in HTML
    assert "journal-context\"" not in HTML
