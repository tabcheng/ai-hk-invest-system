import os
import yfinance as yf
from supabase import create_client


TICKERS = ["0700.HK", "0388.HK", "1299.HK"]


def get_supabase_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set.")

    return create_client(url, key)


def get_signal_for_ticker(ticker: str):
    data = yf.download(ticker, period="1y", interval="1d", auto_adjust=False, progress=False)

    if data.empty:
        return None

    data["MA50"] = data["Close"].rolling(window=50).mean()
    data["MA200"] = data["Close"].rolling(window=200).mean()

    latest = data.dropna(subset=["MA50", "MA200"]).tail(1)
    if latest.empty:
        return None

    row = latest.iloc[0]
    ma50 = float(row["MA50"])
    ma200 = float(row["MA200"])
    price = float(row["Close"])
    date = latest.index[0].to_pydatetime().date().isoformat()

    if ma50 > ma200:
        signal = "BUY"
        reason = f"MA50 ({ma50:.2f}) > MA200 ({ma200:.2f})"
    elif ma50 < ma200:
        signal = "SELL"
        reason = f"MA50 ({ma50:.2f}) < MA200 ({ma200:.2f})"
    else:
        signal = "HOLD"
        reason = f"MA50 ({ma50:.2f}) == MA200 ({ma200:.2f})"

    return {
        "date": date,
        "stock": ticker,
        "signal": signal,
        "price": price,
        "reason": reason,
    }


def save_signals_to_supabase(records):
    client = get_supabase_client()
    result = client.table("signals").insert(records).execute()
    return result


def main():
    signals = []

    for ticker in TICKERS:
        signal = get_signal_for_ticker(ticker)
        if signal:
            signals.append(signal)
            print(f"{ticker}: {signal['signal']} at {signal['price']:.2f}")
        else:
            print(f"{ticker}: not enough data to calculate MA50/MA200")

    if not signals:
        print("No signals generated.")
        return

    save_signals_to_supabase(signals)
    print(f"Saved {len(signals)} signal(s) to Supabase table 'signals'.")


if __name__ == "__main__":
    main()
