import os
from datetime import datetime, timezone

from src.config import TICKERS, get_supabase_client
from src.db import save_signal
from src.notifications import send_daily_run_summary, send_daily_run_summary_with_telemetry
from src.paper_trading import run_paper_trading_for_today
from src.runs import create_run, update_run
from src.signals import get_signal_for_ticker


def _build_ticker_error_record(ticker: str, error: Exception) -> dict:
    """Build stable ticker-level error records for structured run observability."""
    return {
        "ticker": ticker,
        "stage": "signal_generation",
        "error_type": error.__class__.__name__,
        "message": str(error)[:280],
    }


def _build_stage_error_record(stage: str, error: str | Exception) -> dict:
    """Capture non-ticker stage failures in the same structured shape for consistency."""
    if isinstance(error, Exception):
        error_type = error.__class__.__name__
        message = str(error)
    else:
        error_type = "RuntimeError"
        message = error
    return {
        "ticker": None,
        "stage": stage,
        "error_type": error_type,
        "message": message[:280],
    }


def _build_error_summary_json(
    ticker_errors: list[dict],
    post_process_errors: list[dict],
    notification_errors: list[dict],
) -> dict | None:
    """
    Build compact, versioned structured run errors without changing failure semantics.

    This JSON is observability-only and must never block signal generation,
    persistence, paper-trading, or delivery behavior.
    """
    if not (ticker_errors or post_process_errors or notification_errors):
        return None

    return {
        "schema_version": 1,
        "ticker_errors": ticker_errors,
        "post_process_errors": post_process_errors,
        "notification_errors": notification_errors,
        "counts": {
            "ticker": len(ticker_errors),
            "post_process": len(post_process_errors),
            "notification": len(notification_errors),
            "total": len(ticker_errors) + len(post_process_errors) + len(notification_errors),
        },
    }


def _build_delivery_summary_json(delivery_telemetry: dict | None) -> dict | None:
    """Normalize delivery telemetry payload into a bounded run-level summary schema."""
    if not delivery_telemetry:
        return None

    return {
        "schema_version": 1,
        "attempted": bool(delivery_telemetry.get("attempted", False)),
        "success": bool(delivery_telemetry.get("success", False)),
        "channel": delivery_telemetry.get("channel"),
        "messages": delivery_telemetry.get("messages", []),
        "counts": delivery_telemetry.get("counts", {}),
    }


def main() -> None:
    run_date = datetime.now(timezone.utc).date()
    signal_outcomes: dict[str, str] = {}
    paper_trade_count_today = 0
    notification_sent = False

    try:
        client = get_supabase_client()
    except Exception as e:
        try:
            send_daily_run_summary(
                client=None,
                run_id=None,
                run_date=run_date,
                run_status="FAILED",
                tickers=TICKERS,
                signal_outcomes=signal_outcomes,
                paper_trade_count_today=paper_trade_count_today,
                warning_note=f"supabase_client: {e}",
            )
        except Exception as notify_error:
            print(f"Failed to send startup failure Telegram summary notification: {notify_error}")
        raise

    run_id = None
    try:
        run_id = create_run(client)
    except Exception as e:
        print(f"Run observability disabled for this execution: create_run failed: {e}")

    ticker_errors = []
    post_process_errors = []
    notification_errors = []
    ticker_error_records = []
    post_process_error_records = []
    notification_error_records = []
    delivery_telemetry = None
    notification_delivery_enabled = bool(
        os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")
    )
    processed_tickers = 0
    successful_tickers = 0

    try:
        for ticker in TICKERS:
            processed_tickers += 1
            try:
                signal_data = get_signal_for_ticker(ticker)
                signal_outcomes[ticker] = signal_data["signal"]
                print(f"Generated signal for {ticker}: {signal_data}")
                save_signal(client, signal_data, run_id=run_id)
                successful_tickers += 1
            except Exception as e:
                signal_outcomes[ticker] = "ERROR"
                ticker_errors.append(f"{ticker}: {e}")
                ticker_error_records.append(_build_ticker_error_record(ticker, e))
                print(f"Error processing {ticker}: {e}")

        if ticker_errors:
            skip_reason = (
                "paper_trading skipped: daily signal generation had "
                f"{len(ticker_errors)} ticker-level failure(s)."
            )
            post_process_errors.append(skip_reason)
            post_process_error_records.append(_build_stage_error_record("paper_trading", skip_reason))
            print(skip_reason)
        else:
            try:
                paper_result = run_paper_trading_for_today(client, run_id)
                paper_trade_count_today = len(paper_result["trades"])
            except Exception as e:
                post_process_errors.append(f"paper_trading: {e}")
                post_process_error_records.append(_build_stage_error_record("paper_trading", e))
                print(f"Error running paper trading: {e}")

        finished_at = datetime.now(timezone.utc).isoformat()
        failed_tickers = len(ticker_errors)
        run_has_failures = bool(ticker_errors or post_process_errors or notification_errors)

        def _build_run_update_payload(status: str, error_summary: str | None = None) -> dict:
            # Persist bounded, category-specific error slices so run rows clearly
            # distinguish ticker failures vs post-processing vs notification issues.
            payload = {
                "status": status,
                "finished_at": finished_at,
                "processed_tickers": processed_tickers,
                "successful_tickers": successful_tickers,
                "failed_tickers": failed_tickers,
                "ticker_error_count": len(ticker_errors),
                "post_process_error_count": len(post_process_errors),
                "notification_error_count": len(notification_errors),
                "ticker_error_summary": " | ".join(ticker_errors)[:1000] if ticker_errors else None,
                "post_process_error_summary": " | ".join(post_process_errors)[:1000]
                if post_process_errors
                else None,
                "notification_error_summary": " | ".join(notification_errors)[:1000]
                if notification_errors
                else None,
                "error_summary_json": _build_error_summary_json(
                    ticker_error_records,
                    post_process_error_records,
                    notification_error_records,
                ),
                "delivery_summary_json": _build_delivery_summary_json(delivery_telemetry),
            }
            if error_summary is not None:
                payload["error_summary"] = error_summary
            elif status == "SUCCESS":
                payload["error_summary"] = None
            else:
                all_errors = ticker_errors + post_process_errors + notification_errors
                payload["error_summary"] = " | ".join(all_errors)[:1000] if all_errors else None
            return payload

        if not notification_sent:
            run_status = "SUCCESS" if not run_has_failures else "FAILED"
            all_errors = ticker_errors + post_process_errors + notification_errors
            warning_note = " | ".join(all_errors) if all_errors else None
            try:
                delivery_telemetry = send_daily_run_summary_with_telemetry(
                    client=client,
                    run_id=run_id,
                    run_date=run_date,
                    run_status=run_status,
                    tickers=TICKERS,
                    signal_outcomes=signal_outcomes,
                    paper_trade_count_today=paper_trade_count_today,
                    warning_note=warning_note,
                )
                notification_sent = bool(delivery_telemetry.get("success"))
            except Exception as e:
                notification_errors.append(f"daily_summary_exception: {e}")
                notification_error_records.append(_build_stage_error_record("notification", e))
                print(f"Failed to send Telegram summary notification: {e}")

            # Missing Telegram configuration means delivery is intentionally disabled.
            # Keep runs best-effort/non-blocking and avoid treating disabled delivery
            # as a notification failure signal.
            if not notification_sent and notification_delivery_enabled:
                notification_errors.append("daily_summary_not_sent")
                notification_error_records.append(
                    _build_stage_error_record("notification", "daily_summary_not_sent")
                )

        if run_id is not None:
            finished_at = datetime.now(timezone.utc).isoformat()
            try:
                # Keep terminal status coupled to core processing outcomes only;
                # notification outcomes enrich observability fields but do not
                # flip run status when ticker/post-processing succeeded.
                terminal_status = "FAILED" if (ticker_errors or post_process_errors) else "SUCCESS"
                update_run(client, run_id, _build_run_update_payload(status=terminal_status))
            except Exception as e:
                print(f"Run observability update failed after notification handling: {e}")
    except Exception as e:
        if run_id is not None:
            try:
                update_run(
                    client,
                    run_id,
                    {
                        "status": "FAILED",
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "processed_tickers": processed_tickers,
                        "successful_tickers": successful_tickers,
                        "failed_tickers": processed_tickers - successful_tickers,
                        "ticker_error_count": len(ticker_errors),
                        "post_process_error_count": len(post_process_errors),
                        "notification_error_count": len(notification_errors),
                        "ticker_error_summary": " | ".join(ticker_errors)[:1000] if ticker_errors else None,
                        "post_process_error_summary": " | ".join(post_process_errors)[:1000]
                        if post_process_errors
                        else None,
                        "notification_error_summary": " | ".join(notification_errors)[:1000]
                        if notification_errors
                        else None,
                        "error_summary_json": _build_error_summary_json(
                            ticker_error_records,
                            post_process_error_records,
                            notification_error_records
                            + [_build_stage_error_record("run", e)],
                        ),
                        "delivery_summary_json": _build_delivery_summary_json(delivery_telemetry),
                        "error_summary": str(e)[:1000],
                    },
                )
            except Exception as update_error:
                print(f"Run observability update failed during exception handling: {update_error}")

        if not notification_sent:
            try:
                send_daily_run_summary(
                    client=client,
                    run_id=run_id,
                    run_date=run_date,
                    run_status="FAILED",
                    tickers=TICKERS,
                    signal_outcomes=signal_outcomes,
                    paper_trade_count_today=paper_trade_count_today,
                    warning_note=str(e),
                )
            except Exception as notify_error:
                print(f"Failed to send failure Telegram summary notification: {notify_error}")
        raise
