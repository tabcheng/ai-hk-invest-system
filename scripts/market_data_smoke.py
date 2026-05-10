from __future__ import annotations

import argparse
import json
import os

from src.market_data.review_provider import build_review_shell_market_data_provider, snapshot_to_dict


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--provider", default="null")
    args = parser.parse_args()

    env = dict(os.environ)
    env["MARKET_DATA_PROVIDER"] = args.provider
    provider = build_review_shell_market_data_provider(env=env)
    snap = provider.get_ticker_market_snapshot(args.ticker)
    print(json.dumps(snapshot_to_dict(snap), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
