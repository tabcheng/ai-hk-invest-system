from datetime import datetime, timezone

from src.config import TICKERS, get_supabase_client
from src.db import save_signal
from src.runs import create_run, update_run
from src.signals import get_signal_for_ticker


def main() -> None:
    client = get_supabase_client()
    run_id = None
    try:
        run_id = create_run(client)
    except Exception as e:
        print(f"Run observability disabled for this execution: create_run failed: {e}")

    failed_errors = []
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
                failed_errors.append(f"{ticker}: {e}")
                print(f"Error processing {ticker}: {e}")

        finished_at = datetime.now(timezone.utc).isoformat()
        failed_tickers = len(failed_errors)

        if run_id is not None:
            try:
                if failed_tickers == 0:
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
                            "error_summary": " | ".join(failed_errors)[:1000],
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
