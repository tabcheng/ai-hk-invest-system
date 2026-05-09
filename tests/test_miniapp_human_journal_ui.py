from pathlib import Path


def test_human_journal_section_and_guardrail_wording_present():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "Human Paper Decision Journal / 人手模擬決策日誌" in html
    assert "記錄模擬決策日誌" in html
    assert "不建立訂單" in html
    assert "不連接券商" in html
    assert "不作真實落盤" in html


def test_human_journal_requires_guardrail_checkbox_in_ui():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert 'id="journal-ack" type="checkbox" required' in html
