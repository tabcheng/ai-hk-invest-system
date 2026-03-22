import os

from supabase import Client, create_client

TICKERS = ["0700.HK", "0388.HK", "1299.HK"]
STOCK_METADATA = {
    "0700.HK": "Tencent Holdings",
    "0388.HK": "Hong Kong Exchanges and Clearing",
    "1299.HK": "AIA Group",
}


# Minimal v1 provider selection knob for Railway/local runtime.
# Guardrail: provider controls data-source adapter only; this does not authorize
# live broker connectivity or real-money auto execution.
DEFAULT_MARKET_DATA_PROVIDER = "yfinance"


def get_market_data_provider_name() -> str:
    return os.getenv("MARKET_DATA_PROVIDER", DEFAULT_MARKET_DATA_PROVIDER)


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

    return create_client(url, key)
