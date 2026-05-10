# Latest System Runs Repository Contract (Step 92A)

## Scope
Step 92A implements backend repository/provider contract for Supabase/internal table `latest_system_runs`.

This step does **not**:
- enable Telegram webhook runtime read integration yet;
- enable Mini App backend/frontend read-only fetch path yet;
- introduce any write/order/execution path.

## Canonical storage target
- Table: `public.latest_system_runs`
- Canonical read order: `updated_at desc, created_at desc, id desc`
- Bounded payload mapping target: existing `sections.latest_system_run` response contract only.
- Surface intent: bounded latest-state/upsert-by-source read model (not a full audit/event ledger).

## Repository interfaces

```text
write_latest_system_run(record) -> None
get_latest_system_run() -> dict
```

### `write_latest_system_run(record) -> None`
- Caller: `paper-daily-runner` only.
- Use explicit allowlisted columns only (no `insert ... select *` style dynamic pass-through).
- Enforce bounded contract before persistence:
  - `status in {'success','failed','partial','unknown'}`
  - `run_id` length `1..80`
  - `summary_json.paper_trade_only=true`
- No arbitrary JSON passthrough.
- No raw logs storage.
- No secret fields.

### `get_latest_system_run() -> dict`
- Caller: Telegram webhook Mini App API read path only.
- Query exactly one latest row ordered by:
  - `updated_at desc`
  - `created_at desc`
  - `id desc`
- Select explicit allowlisted columns only (never `select *`).
- Map DB row to bounded `sections.latest_system_run` fields only.
- On empty/no-data, return bounded unavailable contract (not raw DB errors).

## Access boundary and RLS posture
- Supabase access remains **backend-only**.
- No browser/client Supabase SDK usage.
- No anon/authenticated browser-access policies in this step.
- RLS is enabled with deny-by-default posture; future step will add restricted backend role/service-role usage details.
- `SUPABASE_SERVICE_ROLE_KEY` must remain server-only and never appear in client/logs/docs examples.

## Non-goals (Step 92A)
- No Mini App route read switch to Supabase.
- No Telegram webhook read integration to Supabase.
- No Railway topology change.
- No broker/live execution behavior.

## Step 91A note (RLS runtime-impact readiness)
- Step 91A adds RLS runtime impact audit + key-boundary cleanup guidance only.
- No runtime repository implementation is added in Step 91A.
- No runner write integration and no Mini App Supabase read integration are added in Step 91A.
- Step 92 should proceed only after Step 91A RLS runtime acceptance evidence is recorded.


## Step 92A implemented interfaces
- `build_latest_system_run_upsert_payload(...)`
- `upsert_latest_system_run(client, payload)`
- `get_latest_system_run(client, source="paper_daily_runner")`

Write integration is best-effort from paper daily runner completion and does not block run success/failure terminal semantics.


## Step 92A-S2 contract evidence RPC
- Add backend-only evidence function `public.step92a_latest_system_runs_contract_evidence()` for smoke/runtime acceptance checks.
- Function returns booleans only: `table_exists`, `rls_enabled`, `source_unique_index_exists`, `latest_read_index_exists`.
- Security posture: `security invoker`, fixed search path `pg_catalog, public, pg_temp`, `revoke all` from `public`/`anon`/`authenticated`, `grant execute` to `service_role` only.
- Access boundary: backend-only service-role / `sb_secret_*` key class; no browser/client access to this RPC.
- No secrets/raw rows/tokens/initData/allowlist identifiers/vendor payloads/market data are returned.

## Step 92B Telegram webhook read surface
- Telegram operator command `/latest_system_run` now uses `get_latest_system_run(client, source="paper_daily_runner")` to fetch exactly one latest row.
- Operator-facing timestamp labels for this command are display-only HKT fields: `data_timestamp_hkt` and `updated_at_hkt`.
- Persistence semantics remain unchanged: storage keeps database UTC/ISO timestamp semantics; HKT conversion is render-time only.
- `latest_system_runs` remains bounded latest-state surface (not an audit ledger).

## Step 92B-1 freshness + display hardening
- Upsert payload now carries timezone-aware UTC `updated_at` so both insert and conflict-update paths refresh row freshness deterministically.
- Telegram response is bounded to safe summary fields only and must not include raw Supabase errors, secrets, tokens, initData, allowlist identifiers, vendor payloads, or raw logs.
- On missing row: bounded unavailable/no-data response. On lookup failure: bounded operator-safe failure response.
- Step 92C: Mini App now fetches backend POST /miniapp/api/review-shell and displays read-only latest_system_run card from latest_system_runs with server-side initData validation + operator allowlist authorization + HKT display fields only; no frontend Supabase direct read/write, no decision capture/order creation/broker/live execution.
- Step 92D: Mini App backend read model can derive read-only `daily_review_summary` from the same bounded latest-state row (`source=paper_daily_runner`) plus safe defaults/unavailable fallback; this remains latest-state projection only and not an audit ledger.

- Step 119 compatibility note: `decision_context_summary` may consume `summary_json.strategy_version` when present; absence must remain explicit (`strategy_version missing`) and must not block response.
\n## 2026-05-10 — Step 120 Mini App IA redesign\n- Step 119 post-deploy smoke passed with build 7f5c5d6 (baseline).\n- Mini App shifted from single long scroll to segmented tabs: 今日/信號/Context/Journal.\n- Decision Context readiness semantics tightened to conservative labels (insufficient/basic/partial; unknown=>不足) and current no-market-data state is 不足.\n- Missing Context now Chinese-first labels; no raw internal English-only keys in UI-facing payload.\n- Current system still lacks canonical market data source; market data may remain unavailable/unknown.\n- No vendor integration, no broker/live/real-money execution, no order/simulated-order creation, no Supabase schema migration, no Telegram auth change.\n
