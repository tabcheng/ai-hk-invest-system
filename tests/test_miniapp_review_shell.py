import re
from pathlib import Path


def test_step92c_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    config_js = Path("miniapp/config.js").read_text(encoding="utf-8")

    required_text = [
        "AI HK Invest — Mini App Preview Shell",
        "https://telegram.org/js/telegram-web-app.js",
        "Latest System Run",
        "Daily Review Summary",
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
    assert "return;" not in html.split("if (section.status !== \"ok\")", 1)[1].split("if (dailySummary.status !== \"ok\")", 1)[0]
    assert "missing_daily_review_summary_section" not in html
    assert "daily review summary is not available yet" in html


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
