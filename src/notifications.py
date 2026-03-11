from __future__ import annotations

import os
from datetime import date

import requests
from supabase import Client


def _format_signal_summary(tickers: list[str], signal_outcomes: dict[str, str]) -> str:
    parts: list[str] = []
    for ticker in tickers:
        parts.append(f"{ticker}:{signal_outcomes.get(ticker, 'UNKNOWN')}")
    return ", ".join(parts)


def _get_latest_total_equity(client: Client) -> float | None:
    result = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date,total_equity")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return float(result.data[0]["total_equity"])


def build_daily_summary_message(
    run_date: date,
    run_status: str,
    tickers: list[str],
    signal_outcomes: dict[str, str],
    paper_trade_count_today: int,
    latest_total_equity: float | None,
    warning_note: str | None = None,
) -> str:
    equity_text = "N/A" if latest_total_equity is None else f"{latest_total_equity:.2f} HKD"
    lines = [
        "AI HK Daily Run Summary",
        f"date: {run_date.isoformat()}",
        f"status: {run_status}",
        f"signals: {_format_signal_summary(tickers, signal_outcomes)}",
        f"paper_trades_today: {paper_trade_count_today}",
        f"latest_total_equity: {equity_text}",
    ]
    if warning_note:
        lines.append(f"note: {warning_note[:280]}")
    return "\n".join(lines)


def send_telegram_message(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        if response.ok:
            print("Telegram notification sent.")
            return True
        print(
            "Telegram notification failed: "
            f"status={response.status_code}, body={response.text[:300]}"
        )
    except Exception as exc:
        print(f"Telegram notification failed with exception: {exc}")

    return False


def send_daily_run_summary(
    client: Client | None,
    run_date: date,
    run_status: str,
    tickers: list[str],
    signal_outcomes: dict[str, str],
    paper_trade_count_today: int,
    warning_note: str | None = None,
) -> bool:
    latest_total_equity = None
    if client is not None:
        try:
            latest_total_equity = _get_latest_total_equity(client)
        except Exception as exc:
            print(f"Could not fetch latest total equity for notification: {exc}")

    message = build_daily_summary_message(
        run_date=run_date,
        run_status=run_status,
        tickers=tickers,
        signal_outcomes=signal_outcomes,
        paper_trade_count_today=paper_trade_count_today,
        latest_total_equity=latest_total_equity,
        warning_note=warning_note,
    )

    return send_telegram_message(message)
