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
    for forbidden in ["立即買入", "立即賣出", "真實落盤", "Buy now", "Sell now", "Execute", "Order", "Trade action"]:
        assert forbidden not in HTML
