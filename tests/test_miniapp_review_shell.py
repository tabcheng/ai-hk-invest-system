from pathlib import Path


def test_step74_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")

    required_text = [
        "AI HK Invest — Mini App Preview Shell",
        "Phase 1",
        "Read-only",
        "Mock / placeholder",
        "Daily Review",
        "Stock Decisions",
        "Paper PnL / Risk",
        "Outcome Review",
        "Guardrails",
        "Decision Boundaries",
        "Security / Auth TODO",
        "AI simulated decision",
        "Human paper decision",
        "Real trade decision outside system",
        "paper trading only",
        "decision support only",
        "no broker connection",
        "no real-money execution",
        "human final decision outside system",
        "validate Telegram initData server-side",
        "Do not trust <code>initDataUnsafe</code>",
        "No SUPABASE_SERVICE_ROLE_KEY in browser/client code",
        "No vendor API secret in browser/client code",
    ]

    forbidden_text = [
        "supabase-js",
        "cdn.jsdelivr.net/npm/@supabase",
        "createClient(",
        "SUPABASE_SERVICE_ROLE_KEY=",
        "telegram.initDataUnsafe",
    ]

    for text in required_text:
        assert text in html

    for text in forbidden_text:
        assert text not in html

    assert "<main" in html
    assert "<form" not in html
    assert "<button" not in html.lower()
