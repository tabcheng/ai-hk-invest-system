from datetime import datetime, timezone

from src.config import TICKERS, get_supabase_client
from src.db import save_signal
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

    try:
        for ticker in TICKERS:
            processed_tickers += 1
            try:
                signal_data = get_signal_for_ticker(ticker)
                print(f"Generated signal for {ticker}: {signal_data}")
                save_signal(client, signal_data)
                successful_tickers += 1
            except Exception as e:
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
                run_paper_trading_for_today(client, run_id)
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
        raise
