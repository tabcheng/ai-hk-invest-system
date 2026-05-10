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


## Step 90 cross-doc note (storage/topology decision)
- Step 90 decides runner-to-miniapp `latest_system_run` storage/topology direction (future Supabase/internal table), but introduces no market-data provider/runtime changes.
- No vendor SDK boundary or market-data freshness semantics are changed in this step.

- Step 119 implementation note: Mini App decision context uses existing-source-only market context contract; no new vendor adapter/SDK added in strategy path. Provider output is bounded (`ok/partial/unavailable`) and includes source/timestamp/freshness/limitations fields.

## 2026-05-10 — Step 120 Mini App IA redesign
- Step 119 post-deploy smoke passed with build 7f5c5d6 (baseline).
- Mini App shifted from single long scroll to segmented tabs: 今日/信號/Context/Journal.
- Decision Context readiness semantics tightened to conservative labels (insufficient/basic/partial; unknown=>不足) and current no-market-data state is 不足.
- Missing Context now Chinese-first labels; no raw internal English-only keys in UI-facing payload.
- Current system still lacks canonical market data source; market data may remain unavailable/unknown.
- No vendor integration, no broker/live/real-money execution, no order/simulated-order creation, no Supabase schema migration, no Telegram auth change.



### Step 123 vendor-ready boundary update (2026-05-10)
- Introduced backend-only market provider boundary for Mini App decision context.
- Runtime env: `MARKET_DATA_PROVIDER=null|existing|eodhd`, `EODHD_API_TOKEN` (backend-only), `MARKET_DATA_TIMEOUT_SECONDS` (default 3), optional `MARKET_DATA_DELAY_POLICY`.
- Default behavior remains unavailable-safe when provider/key absent; no frontend vendor key exposure.
- EODHD is first adapter skeleton candidate only; Twelve Data/Finnhub remain comparison candidates; HKEX official/vendor licensing path remains production-grade consideration.

### Step 124 runtime adapter update (2026-05-10)
- Step 123 baseline confirmed with post-deploy smoke pass and build `d1df5e8`.
- EODHD adapter now performs backend-only runtime HTTP fetch with `EODHD_API_TOKEN` in Railway backend service only.
- Vendor projection remains bounded and sanitized (`reference_price`, `previous_close`, `change`, `change_pct`, `volume`, `turnover`, source/time/freshness/limitations).
- EODHD is first vendor candidate only, not final production-grade vendor commitment; future production may require HKEX licensed/stronger vendor service.
- Missing token/provider unavailable path must stay unavailable-safe and must not fabricate market values.

## 2026-05-10 — Step 125 Mobile Operator Market Data Smoke
- Step 124 merged; Android operator cannot run CLI smoke locally.
- Added /market_smoke (0700.HK/0388.HK/1299.HK) as allowlist-protected, read-only diagnostics command with sanitized bounded snapshot output only.
- Mini App Context tab now shows market smoke diagnostics status/source/timestamp/freshness/delay/limitations from backend review-shell payload only.
- Security/domain boundary preserved: no frontend vendor key, no raw EODHD token/payload exposure, no broker/live/real-money execution, no order/simulated-order creation.
- EODHD remains first vendor candidate, not final production vendor commitment.


## Step 126 — Market Data Freshness + Operator Formatting Bundle (2026-05-10)
- Step 125 post-deploy smoke passed for 0700.HK / 0388.HK / 1299.HK; EODHD backend-only path returned status=ok with bounded fields and timestamp evidence.
- EODHD remains first vendor candidate only, not final production-grade commitment.
- Step 126 adds conservative freshness semantics (`fresh`, `delayed`, `last_available_close`, `stale`, `unknown`) and operator-facing warnings so delayed/last-available data is not interpreted as live data.
- Telegram `/market_smoke` now formats price/percent/volume/timestamp/freshness for readability with Chinese-first freshness labeling and caution wording.
- Mini App Context market section now displays formatted values and freshness warnings for `last_available_close`/`stale`/`unknown` using backend payload only.
- Boundaries unchanged: read-only diagnostics + decision support, paper trading only, no broker/live execution, no real-money execution, no order or simulated-order creation, no frontend vendor key, no token/raw vendor payload exposure, no fake data.
