import pandas as pd

from src.data import fetch_market_data
from src.market_data.provider import MarketDataProvider


def generate_signal_from_data(ticker: str, data: pd.DataFrame) -> dict:
    if data is None or data.empty:
        return {
            "stock": ticker,
            "signal": "NO_DATA",
            "price": None,
            "reason": "No market data returned from provider",
        }

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns:
        return {
            "stock": ticker,
            "signal": "NO_DATA",
            "price": None,
            "reason": "Close column not found in market data",
        }

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


def get_signal_for_ticker(ticker: str, provider: MarketDataProvider | None = None) -> dict:
    # Paper-trading guardrail: this path only generates decision-support signals.
    # It never places real-money orders regardless of provider choice.
    data = fetch_market_data(ticker, provider=provider)
    return generate_signal_from_data(ticker, data)
