from datetime import datetime, timezone

from src.config import TICKERS, get_supabase_client
from src.db import save_signal
from src.notifications import send_daily_run_summary
from src.paper_trading import run_paper_trading_for_today
from src.runs import create_run, update_run
from src.signals import get_signal_for_ticker


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
                print(f"Error processing {ticker}: {e}")

        if ticker_errors:
            skip_reason = (
                "paper_trading skipped: daily signal generation had "
                f"{len(ticker_errors)} ticker-level failure(s)."
            )
            post_process_errors.append(skip_reason)
            print(skip_reason)
        else:
            try:
                paper_result = run_paper_trading_for_today(client, run_id)
                paper_trade_count_today = len(paper_result["trades"])
            except Exception as e:
                post_process_errors.append(f"paper_trading: {e}")
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
            }
            if error_summary is not None:
                payload["error_summary"] = error_summary
            elif status == "SUCCESS":
                payload["error_summary"] = None
            else:
                all_errors = ticker_errors + post_process_errors + notification_errors
                payload["error_summary"] = " | ".join(all_errors)[:1000] if all_errors else None
            return payload

        if run_id is not None:
            try:
                if not run_has_failures:
                    update_run(
                        client,
                        run_id,
                        _build_run_update_payload(status="SUCCESS"),
                    )
                else:
                    update_run(
                        client,
                        run_id,
                        _build_run_update_payload(status="FAILED"),
                    )
            except Exception as e:
                print(f"Run observability update failed after ticker processing: {e}")

        if not notification_sent:
            run_status = "SUCCESS" if not run_has_failures else "FAILED"
            all_errors = ticker_errors + post_process_errors + notification_errors
            warning_note = " | ".join(all_errors) if all_errors else None
            try:
                notification_sent = send_daily_run_summary(
                    client=client,
                    run_id=run_id,
                    run_date=run_date,
                    run_status=run_status,
                    tickers=TICKERS,
                    signal_outcomes=signal_outcomes,
                    paper_trade_count_today=paper_trade_count_today,
                    warning_note=warning_note,
                )
            except Exception as e:
                notification_errors.append(f"daily_summary_exception: {e}")
                print(f"Failed to send Telegram summary notification: {e}")

            if not notification_sent:
                notification_errors.append("daily_summary_not_sent")

            if run_id is not None and notification_errors:
                finished_at = datetime.now(timezone.utc).isoformat()
                try:
                    update_run(client, run_id, _build_run_update_payload(status="FAILED"))
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
