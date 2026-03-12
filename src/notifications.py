from __future__ import annotations

import html
import os
from datetime import date

import requests
from supabase import Client

from src.config import STOCK_METADATA

DAILY_SUMMARY_MESSAGE_TYPE = "DAILY_SUMMARY"
DAILY_SUMMARY_SENT_STATUS = "SENT"
DELIVERY_CHANNEL_TELEGRAM = "telegram"


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
    result = send_telegram_message_with_result(text)
    return bool(result["delivered"])


def send_telegram_message_with_result(text: str) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram notification skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return {
            "delivered": False,
            "channel": DELIVERY_CHANNEL_TELEGRAM,
            "telegram_message_id": None,
            "failure_reason": "missing_telegram_config",
        }

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if response.ok:
            print("Telegram notification sent.")
            telegram_message_id = None
            try:
                payload = response.json()
                telegram_message_id = payload.get("result", {}).get("message_id")
            except Exception:
                # Response parsing is observability-only; delivery already succeeded.
                telegram_message_id = None
            return {
                "delivered": True,
                "channel": DELIVERY_CHANNEL_TELEGRAM,
                "telegram_message_id": telegram_message_id,
                "failure_reason": None,
            }
        print(
            "Telegram notification failed: "
            f"status={response.status_code}, body={response.text[:300]}"
        )
        return {
            "delivered": False,
            "channel": DELIVERY_CHANNEL_TELEGRAM,
            "telegram_message_id": None,
            "failure_reason": f"http_{response.status_code}",
        }
    except Exception as exc:
        print(f"Telegram notification failed with exception: {exc}")
        return {
            "delivered": False,
            "channel": DELIVERY_CHANNEL_TELEGRAM,
            "telegram_message_id": None,
            "failure_reason": str(exc)[:280],
        }


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
    telemetry = send_daily_run_summary_with_telemetry(
        client=client,
        run_date=run_date,
        run_status=run_status,
        tickers=tickers,
        signal_outcomes=signal_outcomes,
        paper_trade_count_today=paper_trade_count_today,
        warning_note=warning_note,
        run_id=run_id,
    )
    return bool(telemetry["success"])


def send_daily_run_summary_with_telemetry(
    client: Client | None,
    run_date: date,
    run_status: str,
    tickers: list[str],
    signal_outcomes: dict[str, str],
    paper_trade_count_today: int,
    warning_note: str | None = None,
    run_id: int | None = None,
) -> dict:
    total_equity = None
    equity_source = "none"
    target = os.getenv("TELEGRAM_CHAT_ID", "")
    base_messages = [
        {
            "ticker": ticker,
            "stock_name": STOCK_METADATA.get(ticker),
            "delivered": False,
            "telegram_message_id": None,
            "failure_reason": None,
        }
        for ticker in tickers
    ]

    # Dedup/read errors should never block summary delivery; we degrade gracefully to send attempt.
    if client is not None and target:
        try:
            if _has_sent_daily_summary(client, run_date, target):
                print(f"Telegram notification skipped by dedup for date={run_date} target=<redacted>.")
                return {
                    "attempted": False,
                    "success": True,
                    "channel": DELIVERY_CHANNEL_TELEGRAM,
                    "messages": base_messages,
                    "counts": {
                        "total": len(base_messages),
                        "delivered": 0,
                        "failed": len(base_messages),
                    },
                }
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

    send_result = send_telegram_message_with_result(message)
    sent = bool(send_result["delivered"])
    if sent and client is not None and target:
        try:
            _record_daily_summary_sent(client, run_date, target, run_id)
        except Exception as exc:
            print(f"Could not persist notification dedup marker: {exc}")

    messages = [
        {
            "ticker": ticker,
            "stock_name": STOCK_METADATA.get(ticker),
            "delivered": sent,
            "telegram_message_id": send_result.get("telegram_message_id"),
            "failure_reason": send_result.get("failure_reason"),
        }
        for ticker in tickers
    ]
    delivered_count = len(messages) if sent else 0
    return {
        "attempted": True,
        "success": sent,
        "channel": DELIVERY_CHANNEL_TELEGRAM,
        "messages": messages,
        "counts": {
            "total": len(messages),
            "delivered": delivered_count,
            "failed": len(messages) - delivered_count,
        },
    }
