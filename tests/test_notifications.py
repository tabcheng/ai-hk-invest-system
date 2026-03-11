from datetime import date

from src.notifications import build_daily_summary_message, send_daily_run_summary, send_telegram_message


def test_build_daily_summary_message_contains_required_fields():
    message = build_daily_summary_message(
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK", "0388.HK", "1299.HK"],
        signal_outcomes={"0700.HK": "BUY", "0388.HK": "HOLD", "1299.HK": "SELL"},
        paper_trade_count_today=2,
        latest_total_equity=101234.56,
        warning_note=None,
    )

    assert "date: 2026-03-11" in message
    assert "status: SUCCESS" in message
    assert "signals: 0700.HK:BUY, 0388.HK:HOLD, 1299.HK:SELL" in message
    assert "paper_trades_today: 2" in message
    assert "latest_total_equity: 101234.56 HKD" in message


def test_build_daily_summary_message_uses_na_equity_and_warning_note():
    message = build_daily_summary_message(
        run_date=date(2026, 3, 11),
        run_status="FAILED",
        tickers=["0700.HK"],
        signal_outcomes={"0700.HK": "ERROR"},
        paper_trade_count_today=0,
        latest_total_equity=None,
        warning_note="paper_trading skipped",
    )

    assert "latest_total_equity: N/A" in message
    assert "note: paper_trading skipped" in message


def test_send_telegram_message_skips_when_env_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    sent = send_telegram_message("hello")

    assert sent is False


def test_send_daily_run_summary_supports_missing_client(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    sent = send_daily_run_summary(
        client=None,
        run_date=date(2026, 3, 11),
        run_status="FAILED",
        tickers=["0700.HK"],
        signal_outcomes={},
        paper_trade_count_today=0,
        warning_note="startup failure",
    )

    assert sent is False
