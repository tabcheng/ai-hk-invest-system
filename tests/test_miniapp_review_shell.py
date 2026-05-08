import re
from pathlib import Path


def test_step92c_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    config_js = Path("miniapp/config.js").read_text(encoding="utf-8")

    required_text = [
        "負面模擬信號",
        "觀望 / 中性信號",
        "正面模擬信號",
        "檢視狀態",
        "交易模式",
        "更新時間（香港時間）",
        "資料時間（香港時間）",
        "信號摘要",
        "AI HK Invest — Mini App Preview Shell",
        "https://telegram.org/js/telegram-web-app.js",
        "最新系統運行",
        "每日檢視摘要",
        "Read-only",
        "paper_trade_only",
        "data_timestamp_hkt",
        "updated_at_hkt",
        "review_readiness",
        "available_sections",
        "unavailable_sections",
        "operator_note",
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

    assert '<script src="/config.js"></script>' in html
    assert html.index('<script src="/config.js"></script>') < html.index("function resolveApiBaseUrl()")
    assert "MINIAPP_API_BASE_URL" in html
    assert "window.MINIAPP_API_BASE_URL = window.MINIAPP_API_BASE_URL || \"\";" in config_js
    assert re.search(r"Telegram\.WebApp\.initData", html)
    assert "`${apiBaseUrl}/miniapp/api/review-shell`" in html
    assert "missing_daily_review_summary_section" not in html
    assert "每日檢視摘要暫時未有資料" in html

    raw_key_as_label_patterns = [
        r"dt\.textContent\s*=\s*key",
    ]
    for pattern in raw_key_as_label_patterns:
        assert re.search(pattern, html) is None


def test_step92c_runtime_config_container_contract() -> None:
    dockerfile = Path("miniapp/Dockerfile").read_text(encoding="utf-8")
    entrypoint = Path("miniapp/entrypoint.sh").read_text(encoding="utf-8")
    caddyfile = Path("miniapp/Caddyfile").read_text(encoding="utf-8")

    assert "FROM caddy:" in dockerfile
    assert "COPY config.js /srv/config.js" in dockerfile
    assert "COPY entrypoint.sh /entrypoint.sh" in dockerfile
    assert "RUN chmod +x /entrypoint.sh" in dockerfile
    assert "MINIAPP_API_BASE_URL" in entrypoint
    assert 'window.MINIAPP_API_BASE_URL = "${escaped_base_url}";' in entrypoint
    assert "set -eu" in entrypoint
    assert "root * /srv" in caddyfile
    assert "file_server" in caddyfile
