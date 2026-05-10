from __future__ import annotations

import argparse
import json
import os

from src.market_data.review_provider import build_review_shell_market_data_provider, snapshot_to_dict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--provider", default="null")
    parser.add_argument("--business-date")
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    env = dict(os.environ)
    env["MARKET_DATA_PROVIDER"] = args.provider
    if args.timeout is not None:
        env["MARKET_DATA_TIMEOUT_SECONDS"] = str(args.timeout)
    provider = build_review_shell_market_data_provider(env=env)
    snap = provider.get_ticker_market_snapshot(args.ticker, args.business_date)
    output = json.dumps(snapshot_to_dict(snap), ensure_ascii=False, indent=2 if args.pretty else None)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
