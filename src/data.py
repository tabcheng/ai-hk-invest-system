import yfinance as yf


def fetch_market_data(ticker: str):
    return yf.download(
        ticker,
        period="1y",
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
