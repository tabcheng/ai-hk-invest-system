from datetime import datetime, timezone

from src.config import TICKERS, get_supabase_client
from src.db import save_signal
from src.notifications import send_daily_run_summary
from src.paper_trading import run_paper_trading_for_today
from src.runs import create_run, update_run
from src.signals import get_signal_for_ticker


def main() -> None:
    client = get_supabase_client()
    run_id = None
    try:
        run_id = create_run(client)
    except Exception as e:
        print(f"Run observability disabled for this execution: create_run failed: {e}")

    ticker_errors = []
    post_process_errors = []
    processed_tickers = 0
    successful_tickers = 0
    signal_outcomes: dict[str, str] = {}
    paper_trade_count_today = 0
    notification_sent = False

    try:
        for ticker in TICKERS:
            processed_tickers += 1
            try:
                signal_data = get_signal_for_ticker(ticker)
                signal_outcomes[ticker] = signal_data["signal"]
                print(f"Generated signal for {ticker}: {signal_data}")
                save_signal(client, signal_data)
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
        all_errors = ticker_errors + post_process_errors

        if run_id is not None:
            try:
                if failed_tickers == 0 and not post_process_errors:
                    update_run(
                        client,
                        run_id,
                        {
                            "status": "SUCCESS",
                            "finished_at": finished_at,
                            "processed_tickers": processed_tickers,
                            "successful_tickers": successful_tickers,
                            "failed_tickers": failed_tickers,
                        },
                    )
                else:
                    update_run(
                        client,
                        run_id,
                        {
                            "status": "FAILED",
                            "finished_at": finished_at,
                            "processed_tickers": processed_tickers,
                            "successful_tickers": successful_tickers,
                            "failed_tickers": failed_tickers,
                            "error_summary": " | ".join(all_errors)[:1000],
                        },
                    )
            except Exception as e:
                print(f"Run observability update failed after ticker processing: {e}")

        if not notification_sent:
            run_status = "SUCCESS" if failed_tickers == 0 and not post_process_errors else "FAILED"
            warning_note = " | ".join(all_errors) if all_errors else None
            try:
                notification_sent = send_daily_run_summary(
                    client=client,
                    run_date=datetime.now(timezone.utc).date(),
                    run_status=run_status,
                    tickers=TICKERS,
                    signal_outcomes=signal_outcomes,
                    paper_trade_count_today=paper_trade_count_today,
                    warning_note=warning_note,
                )
            except Exception as e:
                print(f"Failed to send Telegram summary notification: {e}")
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
                        "error_summary": str(e)[:1000],
                    },
                )
            except Exception as update_error:
                print(f"Run observability update failed during exception handling: {update_error}")

        if not notification_sent:
            try:
                send_daily_run_summary(
                    client=client,
                    run_date=datetime.now(timezone.utc).date(),
                    run_status="FAILED",
                    tickers=TICKERS,
                    signal_outcomes=signal_outcomes,
                    paper_trade_count_today=paper_trade_count_today,
                    warning_note=str(e),
                )
            except Exception as notify_error:
                print(f"Failed to send failure Telegram summary notification: {notify_error}")
        raise
