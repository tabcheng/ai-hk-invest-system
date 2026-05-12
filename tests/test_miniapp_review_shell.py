import re
from pathlib import Path


def test_step92f_ui_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")
    config_js = Path("miniapp/config.js").read_text(encoding="utf-8")

    required_text = [
        "AI 港股投資系統",
        "今日簡報 / Daily Brief",
        "AI 團隊正在幫你檢查乜",
        "風險提示：",
        "AI 模擬方向：",
        "Human Operator 下一步",
        "查看 Outcome Review",
        "寫入人類 paper decision journal",
        "查看技術資料",
        "最新系統運行",
        "每日檢視摘要",
        "信號摘要",
        "安全與邊界說明",
        "只限模擬交易",
        "不連接券商",
        "不作真實落盤",
        "只供模擬檢視",
        "不是真實買賣建議",
        "並非買賣指示",
        "app-shell",
        "section-card",
        "status-chip",
        "metric-grid",
        "signal-list",
        "footer-guardrail",
        "https://telegram.org/js/telegram-web-app.js",
        "/miniapp/api/review-shell",
        "init_data",
        "Paper trading only",
        "Human Paper Decision Journal",
        "journal-form",
        "journal-ack",
        "記錄人手模擬決策",
        "決策參考資料 / Decision Context",
        "不建立訂單",
        "不連接券商",
        "不作真實落盤",
    ]

    forbidden_text = [
        "supabase-js",
        "cdn.jsdelivr.net/npm/@supabase",
        "createClient(",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_SERVICE_ROLE_KEY=",
        "Read-only partial daily review summary from latest system run only; human final decision remains outside system.",
        "read-only latest-state row; no broker/live execution",
        "read-only review surface; no decision capture, no order creation, no broker/live execution",
        "Buy now",
        "Sell now",
        "Execute",
        "Order",
        "Trade action",
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
    assert "暫時未有資料" in html
    assert "renderBuildMeta();" in html
    assert "UI build:" in html
    assert "Deployed build:" in html

    raw_key_as_label_patterns = [
        r"dt\.textContent\s*=\s*key",
    ]
    for pattern in raw_key_as_label_patterns:
        assert re.search(pattern, html) is None

    forbidden_write_ui_patterns = [
        r"<button[^>]*>\s*(提交決策|建立訂單|立即落盤|place order|submit decision|decision capture|execute trade|broker execution|live execution|真實買入|真實賣出|落盤)\s*</button>",
        r"<input[^>]*type=['\"]submit['\"]",
    ]
    for pattern in forbidden_write_ui_patterns:
        assert re.search(pattern, html, flags=re.IGNORECASE) is None


def test_step92c_runtime_config_container_contract() -> None:
    dockerfile = Path("miniapp/Dockerfile").read_text(encoding="utf-8")
    entrypoint = Path("miniapp/entrypoint.sh").read_text(encoding="utf-8")
    caddyfile = Path("miniapp/Caddyfile").read_text(encoding="utf-8")

    assert "FROM caddy:" in dockerfile
    assert "COPY config.js /srv/config.js" in dockerfile
    assert "COPY entrypoint.sh /entrypoint.sh" in dockerfile
    assert "RUN chmod +x /entrypoint.sh" in dockerfile
    assert "MINIAPP_API_BASE_URL" in entrypoint
    assert "RAILWAY_GIT_COMMIT_SHA" in entrypoint
    assert "MINIAPP_UI_BUILD_VERSION" in entrypoint
    assert "MINIAPP_DEPLOYED_BUILD" in entrypoint
    assert 'window.MINIAPP_API_BASE_URL = "${escaped_base_url}";' in entrypoint
    assert 'window.MINIAPP_UI_BUILD_VERSION = "${escaped_ui_build_version}";' in entrypoint
    assert 'window.MINIAPP_DEPLOYED_BUILD = "${escaped_deployed_build}";' in entrypoint
    assert "set -eu" in entrypoint
    assert "root * /srv" in caddyfile
    assert "@index path / /index.html" in caddyfile
    assert "@config path /config.js" in caddyfile
    assert 'header @index Cache-Control "no-cache, no-store, must-revalidate"' in caddyfile
    assert 'header @config Cache-Control "no-cache, must-revalidate"' in caddyfile
    assert "file_server" in caddyfile
