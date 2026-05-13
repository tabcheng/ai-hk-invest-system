from pathlib import Path


def test_today_first_view_is_single_hero_summary_card() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    assert 'data-tab-panel="today"' in html
    assert 'id="overview-card" class="overview-card" data-tab-panel="today"' in html
    assert 'id="team-card" class="section-card" data-tab-panel="today"' not in html
    assert 'id="latest-card" class="section-card" data-tab-panel="today"' not in html
    assert 'id="paper-pnl-card" class="section-card" data-tab-panel="today"' not in html


def test_today_hero_has_required_operator_fields_and_safety_wording() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    for required in ['一句總結：', '資料夠唔夠：', '風險提示：', 'AI 模擬方向：', '你下一步要做咩', '只供模擬檢視｜不建立訂單｜不連接券商｜不是真實買賣建議']:
        assert required in html


def test_tabs_use_traditional_chinese_primary_labels() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    for label in ['>今日<', '>股票檢視<', '>模擬組合<', '>日誌<', '>系統<']:
        assert label in html
    assert '>Journal<' not in html


def test_system_tab_owns_runtime_metadata_and_diagnostics_cards() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    assert 'id="latest-card" class="section-card" data-tab-panel="system"' in html
    assert 'id="daily-card" class="section-card" data-tab-panel="system"' in html
    assert 'id="signals-card" class="section-card" data-tab-panel="system"' in html
    assert 'id="context-card" class="section-card" data-tab-panel="system"' in html


def test_portfolio_tab_owns_pnl_and_risk_not_today() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    assert 'id="paper-pnl-card" class="section-card" data-tab-panel="portfolio"' in html
    assert 'id="risk-card" class="section-card" data-tab-panel="portfolio"' in html


def test_stock_review_keeps_horizon_and_technical_details_contract() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    assert '策略週期判斷' in html
    assert '查看技術資料' in html


def test_tabpanel_aria_labelledby_matches_new_tabs() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    required = {
        'overview-card': 'tab-today',
        'stock-review-card': 'tab-stock-review',
        'paper-pnl-card': 'tab-portfolio',
        'risk-card': 'tab-portfolio',
        'journal-card': 'tab-journal',
        'team-card': 'tab-system',
        'latest-card': 'tab-system',
        'daily-card': 'tab-system',
        'signals-card': 'tab-system',
        'context-card': 'tab-system',
    }
    for panel_id, label_id in required.items():
        needle = f'id="{panel_id}" class="section-card" data-tab-panel=' if panel_id != 'overview-card' else f'id="{panel_id}" class="overview-card" data-tab-panel='
        assert needle in html
        assert f'id="{panel_id}"' in html and f'aria-labelledby="{label_id}"' in html


def test_stale_tab_ids_removed_and_no_wrong_today_labels_for_system_portfolio() -> None:
    html = Path('miniapp/index.html').read_text(encoding='utf-8')
    assert 'tab-signals' not in html
    assert 'tab-context' not in html
    for panel_id in ['paper-pnl-card', 'risk-card', 'team-card', 'latest-card', 'daily-card', 'signals-card', 'context-card']:
        bad = f'id="{panel_id}"'
        segment = html[html.index(bad): html.index(bad) + 220]
        assert 'aria-labelledby="tab-today"' not in segment
