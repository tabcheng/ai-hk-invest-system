from pathlib import Path


def test_human_journal_section_and_guardrail_wording_present():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert "人手模擬決策日誌" in html
    assert "Human Paper Decision Journal" in html
    assert "記錄人手模擬決策" in html
    assert "決策參考資料 / Decision Context" in html
    assert "不建立訂單" in html
    assert "不連接券商" in html
    assert "不作真實落盤" in html
    assert "journal labels only" in html
    assert "不改變 paper position" in html
    assert "不建立買入單" in html
    assert "不建立賣出單" in html


def test_human_journal_requires_guardrail_checkbox_in_ui():
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    assert 'id="journal-ack" type="checkbox" required' in html
    assert "日誌暫時未能寫入；未有資料被儲存。" in html
    assert "表單已修改，尚未保存目前變更。" in html
    assert "Journal 已保存" in html
    assert "snapshot_saved=true" in html
