from pathlib import Path


def test_miniapp_includes_ai_team_packet_safety_labels_and_no_raw_json_dump():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "AI Team Packet" in html
    assert "只供模擬檢視" in html
    assert "只供決策支援" in html
    assert "不連接券商" in html
    assert "不建立訂單" in html
    assert "不是真實買賣建議" in html
