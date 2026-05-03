# Latest System Runs Repository Contract (Step 91 Proposal)

## Scope
Step 91 defines **proposal-only** backend repository/provider contract for future Supabase/internal table `latest_system_runs` usage.

This step does **not**:
- enable runtime Supabase write in `paper-daily-runner`;
- enable runtime Supabase read in Telegram Mini App API;
- enable Mini App frontend Supabase fetch;
- introduce any write/order/execution path.

## Canonical storage target
- Table: `public.latest_system_runs`
- Canonical read order: `completed_at desc nulls last, created_at desc, id desc`
- Bounded payload mapping target: existing `sections.latest_system_run` response contract only.

## Proposed repository interfaces (future step)

```text
write_latest_system_run(record) -> None
get_latest_system_run() -> dict
```

### `write_latest_system_run(record) -> None`
- Caller: `paper-daily-runner` only.
- Use explicit allowlisted columns only (no `insert ... select *` style dynamic pass-through).
- Enforce bounded contract before persistence:
  - `run_status in {'success','failed','partial','unknown'}`
  - `run_id` length `1..80`
  - `summary` length `<= 500` when provided
  - `limitations` array length `<= 5`
  - each `limitations` item string length `<= 160`
- No arbitrary JSON passthrough.
- No raw logs storage.
- No secret fields.

### `get_latest_system_run() -> dict`
- Caller: Telegram webhook Mini App API read path only.
- Query exactly one latest row ordered by:
  - `completed_at desc nulls last`
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

## Non-goals (Step 91)
- No runtime repository implementation.
- No Mini App route read switch to Supabase.
- No runner write integration to Supabase.
- No Railway topology change.
- No broker/live execution behavior.

## Step 91A note (RLS runtime-impact readiness)
- Step 91A adds RLS runtime impact audit + key-boundary cleanup guidance only.
- No runtime repository implementation is added in Step 91A.
- No runner write integration and no Mini App Supabase read integration are added in Step 91A.
- Step 92 should proceed only after Step 91A RLS runtime acceptance evidence is recorded.
