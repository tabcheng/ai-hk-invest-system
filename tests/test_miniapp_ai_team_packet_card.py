from pathlib import Path


def test_miniapp_includes_ai_team_packet_safety_labels_and_no_raw_json_dump():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "AI 團隊摘要 / AI Team Packet" in html
    assert "詳情請到「系統」分頁查看 AI Team Packet" in html
    assert "資料狀態：" in html
    assert "資料準備度" in html
    assert "可用" in html
    assert "部分" in html
    assert "缺少" in html
    assert "未知" in html
    assert "只觀察" in html
    assert "混合觀察" in html
    assert "資料不足" in html
    assert "只供模擬檢視" in html
    assert "只供決策支援" in html
    assert "不連接券商" in html
    assert "不建立訂單" in html
    assert "不是真實買賣建議" in html
    assert "slot readiness：" not in html
