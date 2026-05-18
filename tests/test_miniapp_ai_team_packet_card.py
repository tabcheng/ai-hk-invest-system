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
    assert "`Run ID：${packet.run_id || \"未有資料\"}`" not in html.split("const rows=[", 1)[1].split("];", 1)[0]
    assert "`排程基準：${packet.schedule_basis || \"未有資料\"}`" not in html.split("const rows=[", 1)[1].split("];", 1)[0]
    assert "查看技術資料" in html
    assert "`Run ID：${packet.run_id || \"未有資料\"}`" in html
    assert "`排程基準：${packet.schedule_basis || \"未有資料\"}`" in html
    assert "`來源：${packet.source || 'latest_system_runs'}`" in html
    assert "Buy now" not in html
    assert "Sell now" not in html
    assert "Execute" not in html
    assert "slot readiness：" not in html

def test_miniapp_includes_ai_team_operating_model_sections():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "AI 團隊狀態" in html
    assert "AI 團隊運作狀態 / Operating Model" in html
    assert "已可用" in html
    assert "部分可用" in html
    assert "上線後優化 / Deferred" in html
    assert "詳情請到「系統」分頁查看 AI 團隊運作狀態" in html
    assert "JSON.stringify" not in html
