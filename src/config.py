import os

from supabase import Client, create_client

TICKERS = ["0700.HK", "0388.HK", "1299.HK"]
STOCK_METADATA = {
    "0700.HK": "Tencent Holdings",
    "0388.HK": "Hong Kong Exchanges and Clearing",
    "1299.HK": "AIA Group",
}


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables")

    return create_client(url, key)
