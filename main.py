import os
from datetime import datetime, UTC

import pandas as pd
import yfinance as yf
from supabase import create_client, Client

TICKERS = ["0700.HK", "0388.HK", "1299.HK"]


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

    return create_client(url, key)


def get_signal_for_ticker(ticker: str) -> dict:
    # 用 1y 而不是 6mo，確保有足夠資料計 MA200
    data = yf.download(
        ticker,
        period="1y",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )

    if data is None or data.empty:
        return {
            "stock": ticker,
            "signal": "NO_DATA",
            "price": None,
            "reason": "No market data returned from yfinance",
        }

    # 若 yfinance 回傳 MultiIndex columns，先壓平
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns:
        return {
            "stock": ticker,
            "signal": "NO_DATA",
            "price": None,
            "reason": "Close column not found in market data",
        }

    # 建立 MA 欄位
    data["MA50"] = data["Close"].rolling(window=50).mean()
    data["MA200"] = data["Close"].rolling(window=200).mean()

    latest_valid = data.dropna(subset=["MA50", "MA200"]).tail(1)

    if latest_valid.empty:
        return {
            "stock": ticker,
            "signal": "INSUFFICIENT_DATA",
            "price": float(data["Close"].iloc[-1]) if not data["Close"].empty else None,
            "reason": "Not enough historical data to calculate both MA50 and MA200",
        }

    row = latest_valid.iloc[0]
    price = float(row["Close"])
    ma50 = float(row["MA50"])
    ma200 = float(row["MA200"])

    if ma50 > ma200:
        signal = "BUY"
        reason = f"MA50 ({ma50:.2f}) is above MA200 ({ma200:.2f})"
    elif ma50 < ma200:
        signal = "SELL"
        reason = f"MA50 ({ma50:.2f}) is below MA200 ({ma200:.2f})"
    else:
        signal = "HOLD"
        reason = f"MA50 ({ma50:.2f}) equals MA200 ({ma200:.2f})"

    return {
        "stock": ticker,
        "signal": signal,
        "price": price,
        "reason": reason,
    }

def save_signal(client: Client, signal_data: dict) -> None:
    signal_date = datetime.now(UTC).date().isoformat()
    payload = {
        "date": signal_date,
        "stock": signal_data["stock"],
        "signal": signal_data["signal"],
        "price": signal_data["price"],
        "reason": signal_data["reason"],
    }

    result = (
        client.table("signals")
        .upsert(
            payload,
            on_conflict="date,stock",
            ignore_duplicates=True,
            returning="representation",
        )
        .execute()
    )

    if result.data:
        print(f"Inserted into Supabase: {payload}")
    else:
        print(
            "Duplicate protection triggered: "
            f"signal already exists for {signal_data['stock']} on {signal_date}."
        )

    print(f"Supabase response: {result}")


def create_run(client: Client) -> int:
    result = (
        client.table("runs")
        .insert({"status": "RUNNING"}, returning="representation")
        .execute()
    )
    run_id = result.data[0]["id"]
    print(f"Created run record: id={run_id}")
    return run_id


def update_run(client: Client, run_id: int, payload: dict) -> None:
    (
        client.table("runs")
        .update(payload)
        .eq("id", run_id)
        .execute()
    )


def main():
    client = get_supabase_client()
    run_id = create_run(client)
    failed_errors = []
    successful_tickers = 0

    try:
        for ticker in TICKERS:
            try:
                signal_data = get_signal_for_ticker(ticker)
                print(f"Generated signal for {ticker}: {signal_data}")
                save_signal(client, signal_data)
                successful_tickers += 1
            except Exception as e:
                failed_errors.append(f"{ticker}: {e}")
                print(f"Error processing {ticker}: {e}")

        finished_at = datetime.now(UTC).isoformat()
        processed_tickers = len(TICKERS)
        failed_tickers = len(failed_errors)

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
        update_run(
            client,
            run_id,
            {
                "status": "FAILED",
                "finished_at": datetime.now(UTC).isoformat(),
                "processed_tickers": len(TICKERS),
                "successful_tickers": successful_tickers,
                "failed_tickers": len(TICKERS) - successful_tickers,
                "error_summary": str(e)[:1000],
            },
        )
        raise


if __name__ == "__main__":
    main()
