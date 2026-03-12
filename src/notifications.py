from __future__ import annotations

import html
import os
from datetime import date

import requests
from supabase import Client

from src.config import STOCK_METADATA

DAILY_SUMMARY_MESSAGE_TYPE = "DAILY_SUMMARY"
DAILY_SUMMARY_SENT_STATUS = "SENT"


def _format_ticker_label(ticker: str) -> str:
    """Render deterministic stock labels as '<Name> (<Ticker>)' for human-readable summaries."""
    stock_name = STOCK_METADATA.get(ticker)
    safe_ticker = html.escape(ticker)
    if not stock_name:
        return safe_ticker

    safe_name = html.escape(stock_name)
    return f"{safe_name} ({safe_ticker})"


def _format_signal_summary(tickers: list[str], signal_outcomes: dict[str, str]) -> str:
    lines: list[str] = []
    for ticker in tickers:
        signal = html.escape(signal_outcomes.get(ticker, "UNKNOWN"))
        lines.append(f"• {_format_ticker_label(ticker)}: <b>{signal}</b>")
    return "\n".join(lines)


def _get_total_equity_for_date(client: Client, run_date: date) -> tuple[float | None, str]:
    """
    Prefer run-date equity for deterministic summaries.

    We fall back to the latest snapshot only when the run-date snapshot is unavailable,
    so daily messaging remains useful even when downstream snapshot writes were skipped.
    """
    run_date_result = (
        client.table("paper_daily_snapshots")
        .select("total_equity")
        .eq("snapshot_date", run_date.isoformat())
        .limit(1)
        .execute()
    )
    if run_date_result.data:
        return float(run_date_result.data[0]["total_equity"]), "run_date"

    latest_result = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date,total_equity")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    if latest_result.data:
        return float(latest_result.data[0]["total_equity"]), "latest"

    return None, "none"


def build_daily_summary_message(
    run_date: date,
    run_status: str,
    tickers: list[str],
    signal_outcomes: dict[str, str],
    paper_trade_count_today: int,
    total_equity: float | None,
    equity_source: str,
    warning_note: str | None = None,
) -> str:
    equity_text = "N/A" if total_equity is None else f"{total_equity:.2f} HKD"
    equity_label = {
        "run_date": "total_equity (run_date)",
        "latest": "total_equity (latest)",
        "none": "total_equity",
    }.get(equity_source, "total_equity")

    lines = [
        "<b>AI HK Daily Run Summary</b>",
        f"<b>date:</b> {html.escape(run_date.isoformat())}",
        f"<b>status:</b> {html.escape(run_status)}",
        "<b>signals:</b>",
        _format_signal_summary(tickers, signal_outcomes),
        f"<b>paper_trades_today:</b> {paper_trade_count_today}",
        f"<b>{equity_label}:</b> {html.escape(equity_text)}",
    ]
    if warning_note:
        lines.append(f"<b>note:</b> {html.escape(warning_note[:280])}")
    return "\n".join(lines)


def _has_sent_daily_summary(client: Client, run_date: date, target: str) -> bool:
    result = (
        client.table("notification_logs")
        .select("id")
        .eq("notification_date", run_date.isoformat())
        .eq("target", target)
        .eq("message_type", DAILY_SUMMARY_MESSAGE_TYPE)
        .eq("status", DAILY_SUMMARY_SENT_STATUS)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def _record_daily_summary_sent(
    client: Client,
    run_date: date,
    target: str,
    run_id: int | None,
) -> None:
    # This durable marker enables cross-run dedup for the same run date and target.
    # Upsert keeps dedup idempotent during near-simultaneous reruns that race to persist logs.
    payload = {
        "notification_date": run_date.isoformat(),
        "target": target,
        "message_type": DAILY_SUMMARY_MESSAGE_TYPE,
        "status": DAILY_SUMMARY_SENT_STATUS,
    }
    if run_id is not None:
        payload["run_id"] = run_id

    client.table("notification_logs").upsert(
        payload,
        on_conflict="notification_date,target,message_type,status",
        ignore_duplicates=True,
    ).execute()


def send_telegram_message(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
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
    run_id: int | None = None,
) -> bool:
    total_equity = None
    equity_source = "none"
    target = os.getenv("TELEGRAM_CHAT_ID", "")

    # Dedup/read errors should never block summary delivery; we degrade gracefully to send attempt.
    if client is not None and target:
        try:
            if _has_sent_daily_summary(client, run_date, target):
                print(f"Telegram notification skipped by dedup for date={run_date} target=<redacted>.")
                return True
        except Exception as exc:
            print(f"Could not check notification dedup state: {exc}")

    if client is not None:
        try:
            total_equity, equity_source = _get_total_equity_for_date(client, run_date)
        except Exception as exc:
            print(f"Could not fetch total equity for notification: {exc}")

    message = build_daily_summary_message(
        run_date=run_date,
        run_status=run_status,
        tickers=tickers,
        signal_outcomes=signal_outcomes,
        paper_trade_count_today=paper_trade_count_today,
        total_equity=total_equity,
        equity_source=equity_source,
        warning_note=warning_note,
    )

    sent = send_telegram_message(message)
    if sent and client is not None and target:
        try:
            _record_daily_summary_sent(client, run_date, target, run_id)
        except Exception as exc:
            print(f"Could not persist notification dedup marker: {exc}")
    return sent
