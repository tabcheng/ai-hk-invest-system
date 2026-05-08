from pathlib import Path


INDEX_HTML = Path("miniapp/index.html").read_text(encoding="utf-8")


def test_status_hierarchy_labels_present() -> None:
    assert "System Run Status" in INDEX_HTML
    assert "Daily Review Coverage" in INDEX_HTML
    assert "部分完成表示部分檢視區塊仍未有資料，並不代表最新系統運行失敗" in INDEX_HTML


def test_data_availability_card_wording_present() -> None:
    assert "最新系統運行" in INDEX_HTML
    assert "信號摘要" in INDEX_HTML
    assert "模擬盈虧" in INDEX_HTML
    assert "風險摘要" in INDEX_HTML
    assert "已載入" in INDEX_HTML
    assert "未有資料" in INDEX_HTML
    assert "data not available yet" in INDEX_HTML


def test_signal_warning_and_unknown_confidence_present() -> None:
    assert "未提供 / Unknown" in INDEX_HTML
    assert "目前只顯示技術信號方向；信心、風險、模擬盈虧未完整，因此不應視為完整決策。" in INDEX_HTML


def test_safety_boundary_copy_present() -> None:
    assert "只限模擬交易 · 決策支援 · 不連接券商 · 不作真實落盤" in INDEX_HTML
    assert "Telegram initData 只在後端驗證" in INDEX_HTML
    assert "前端不使用 initDataUnsafe 作授權" in INDEX_HTML
    assert "前端不保存 Supabase secret / service role key" in INDEX_HTML
    assert "所有信號只供模擬檢視，並非買賣指示" in INDEX_HTML
