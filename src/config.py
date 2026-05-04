import logging
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


logger = logging.getLogger(__name__)


def get_market_data_provider_name() -> str:
    return os.getenv("MARKET_DATA_PROVIDER", DEFAULT_MARKET_DATA_PROVIDER)


def _resolve_supabase_backend_key() -> str | None:
    supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY", "").strip()
    if supabase_secret_key:
        return supabase_secret_key

    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if supabase_service_role_key:
        return supabase_service_role_key

    supabase_key = os.getenv("SUPABASE_KEY", "").strip()
    if supabase_key:
        logger.warning(
            "SUPABASE_KEY is deprecated and supported as transitional fallback only. "
            "Please migrate backend runtime env to SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY."
        )
        return supabase_key

    return None


def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = _resolve_supabase_backend_key()

    if not url or not key:
        raise ValueError(
            "Missing SUPABASE_URL or backend Supabase key env. "
            "Supported key env priority: SUPABASE_SECRET_KEY, SUPABASE_SERVICE_ROLE_KEY, "
            "SUPABASE_KEY (transitional fallback)."
        )

    return create_client(url, key)
