from pathlib import Path

HTML = Path("miniapp/index.html").read_text(encoding="utf-8")


def test_stock_review_data_gap_action_mapping_strings_present():
    required = [
        "先補看：風險摘要與限制說明",
        "先補看：最近模擬決策日誌、決策脈絡或結果",
        "先補看：最新業績、盈利能力、資產負債與公司公告",
        "先補看：估值比較、歷史估值、同業比較",
        "先補看：現金流／盈利／資產負債表財務細項",
        "先補看：資料時間、更新狀態與市場 smoke 檢查證據",
        "先補看：模擬組合／風險頁的持倉與盈虧脈絡",
        "保持觀察：補官方或已授權來源，避免單一訊號",
        "下一步資料行動：繼續檢視風險、信號與人手模擬決策紀錄",
    ]
    for text in required:
        assert text in HTML


def test_stock_review_no_execution_wording_in_data_gap_actions():
    for forbidden in ["立即買入", "立即賣出", "馬上落盤", "立即執行", "Buy now", "Sell now", "Execute now", "Place order", "Trade action"]:
        assert forbidden not in HTML



def test_stock_review_allows_safety_negation_wording():
    assert "不作真實落盤" in HTML


def test_market_smoke_trigger_uses_market_specific_fields_only():
    assert "market_data_status" in HTML
    assert "freshness_status" in HTML
    assert "market_data_acceptance_status" in HTML
    block = HTML.split("const marketStatusHints", 1)[1].split("if (hasMarketStaleFlag)", 1)[0]
    assert "risk_brief" not in block
    assert "data_sufficiency" not in block


def test_ticker_context_insufficient_variant_maps_to_context_action():
    assert 'gapText.includes("個股層級脈絡資料不足")' in HTML


def test_frontend_prefers_backend_data_gap_actions_contract():
    assert "const backendGapActions = Array.isArray(chosen?.data_gap_actions) ? chosen.data_gap_actions : [];" in HTML
    assert "if (backendGapActions.length)" in HTML
    assert "backendGapActions.forEach((entry) => {" in HTML
    assert "chosen?.data_gap_interpretation_summary ||" in HTML


def test_stock_review_renders_route_and_confidence_metadata():
    assert "去向：" in HTML
    assert "影響：" in HTML
    assert "target_surface_label" in HTML
    assert "confidence_effect" in HTML
    assert "confidence_effect_label" in HTML


def test_today_next_actions_can_use_routed_backend_actions():
    assert "const routedActions = Array.isArray(stockReview?.items?.[0]?.data_gap_actions)" in HTML
    assert "先看 ${target}：" in HTML


def test_stock_review_first_layer_route_text_does_not_render_raw_confidence_enum():
    block = HTML.split("const routeText = ", 1)[1].split("pushGapAction", 1)[0]
    for raw_enum in ["context_required", "caps_long_term", "caps_medium_term", "blocks_short_term", "watch_only"]:
        assert raw_enum not in block
