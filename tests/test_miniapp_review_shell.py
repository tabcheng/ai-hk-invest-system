from pathlib import Path


def test_step71_review_shell_static_contract() -> None:
    html = Path("miniapp/index.html").read_text(encoding="utf-8")

    required_text = [
        "AI HK Invest — Review Shell",
        "Read-only Review Shell",
        "Daily Review",
        "Stock Decisions",
        "Paper PnL / Risk",
        "Outcome Review",
        "Guardrails",
        "Decision Boundaries",
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

    for text in required_text:
        assert text in html

    assert "<form" not in html
    assert "button" not in html.lower()
