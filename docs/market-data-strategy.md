# Market Data Strategy (Step 69 System-of-Record)

## Principles
- Market data vendors may be used where justified by coverage, quality, or reliability needs.
- Avoid vendor lock-in by enforcing a provider abstraction boundary.
- Build and stabilize `MarketDataProvider` interface contracts before any vendor-specific integration expansion.

## Required data categories
- Historical EOD OHLCV
- Latest quote / delayed quote
- Intraday bars
- Corporate actions
- Trading calendar
- Board lot / stock master
- Suspension / special status (if available)

## Data quality fields (system-of-record expectations)
- `source`
- `timestamp`
- `freshness`
- `adjustment_policy`
- `confidence` and/or explicit known limitations

## Architecture guardrails
- Strategy logic must not directly depend on vendor SDK implementation details.
- Vendor-specific adapters should map into internal provider contracts.
- Vendor API keys must remain secrets in backend-only environments.

## Execution boundary guardrails
- Market data strategy supports paper-trading and decision-support workflows only.
- No broker integration or live-execution path is introduced by this strategy.
