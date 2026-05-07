import re
from pathlib import Path


def test_step92c_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")

    required_text = [
        "AI HK Invest — Mini App Preview Shell",
        "Latest System Run",
        "Read-only",
        "paper_trade_only",
        "data_timestamp_hkt",
        "updated_at_hkt",
        "validate Telegram initData server-side",
        "Do not trust initDataUnsafe",
        "/miniapp/api/review-shell",
        "init_data",
        "no broker connection",
        "no real-money execution",
    ]

    forbidden_text = [
        "supabase-js",
        "cdn.jsdelivr.net/npm/@supabase",
        "createClient(",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_SERVICE_ROLE_KEY=",
    ]

    for text in required_text:
        assert text in html

    for text in forbidden_text:
        assert text not in html

    forbidden_init_data_unsafe_patterns = [
        r"window\.Telegram\.WebApp\.initDataUnsafe",
        r"Telegram\.WebApp\.initDataUnsafe",
        r"telegram\.initDataUnsafe",
        r"\.initDataUnsafe",
    ]
    for pattern in forbidden_init_data_unsafe_patterns:
        assert re.search(pattern, html, flags=re.IGNORECASE) is None

    assert "MINIAPP_API_BASE_URL" in html
    assert re.search(r"Telegram\.WebApp\.initData", html)
    assert "`${apiBaseUrl}/miniapp/api/review-shell`" in html
