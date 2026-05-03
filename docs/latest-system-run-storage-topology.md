# Latest System Run Storage / Topology Decision (Step 90)

## Scope
Step 90 is a **design decision + docs sync + implementation-ready contract** step only.

This step does **not** implement:
- Supabase schema migration/RLS change,
- runtime Supabase read/write,
- Mini App frontend fetch wiring,
- Railway topology/volume creation changes,
- any write/order/execution behavior.

## Current state (post Step 87/88/89)
- Mini App backend can read a bounded backend-local artifact for `latest_system_run` when `MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH` is configured and the file exists with valid bounded JSON.
- `miniapp_artifact_writer` can build/write bounded `latest_system_run` JSON artifact with field and size constraints.
- GitHub Actions Mini App API smoke has validated the Step 87 contract path.
- There is still **no live runner-to-miniapp data flow** between `paper-daily-runner` and `telegram-webhook` services.

## Problem
`paper-daily-runner` output must be made available to Mini App API in `telegram-webhook` safely and deterministically.

Because these are separate Railway services/surfaces, Step 90 must **not** assume cross-service local filesystem sharing. Any handoff must use an explicit topology/storage decision.

## Options considered

### A) Same-service local filesystem
- **Pros:** simple; low implementation overhead.
- **Cons:** does not fit current split-service topology where runner and webhook are separate services.
- **Risk:** couples architecture to co-location assumptions.

### B) Railway volume/local artifact path
- **Pros:** keeps JSON artifact model; can support bounded local file contract.
- **Cons:** introduces infra/topology dependency details and service-mount semantics; cross-service sharing is not implicit.
- **Risk:** operational ambiguity and environment-specific coupling.

### C) Supabase internal table (recommended for future step)
- **Pros:** clear producer/consumer boundary; durable audit trail; deterministic “latest record” query; backend-only secret handling.
- **Cons:** requires migration/RLS/repository implementation in a later step.
- **Risk:** moderate implementation effort, but clearer long-term governance.

### D) Internal HTTP handoff
- **Pros:** explicit service-to-service API boundary.
- **Cons:** adds runtime coupling, retry/idempotency concerns, and availability dependencies.
- **Risk:** extra operational complexity compared with DB-backed system-of-record approach.

## Decision
For future implementation, choose **Option C: Supabase internal table** as the canonical runner-to-miniapp `latest_system_run` path.

**Step 90 does not implement this decision in runtime.**

## Rationale
- Better audit trail and historical traceability.
- Clear producer (`paper-daily-runner`) vs consumer (`telegram-webhook` Mini App API) boundary.
- Avoids ambiguity of cross-service filesystem behavior.
- Keeps Supabase credentials backend-only (no browser/client exposure).
- Preserves bounded Mini App response contract discipline.

## Non-decision / preserved fallback
Local artifact provider/writer remains valid for:
- local development,
- bounded smoke testing,
- single-service/co-located deployments,
- fallback/readiness debugging.

It is not removed by Step 90.

## Implementation-ready proposed data contract (future Step 91+)
Proposed internal table: `latest_system_runs`

- `id`: uuid (PK)
- `run_id`: text (max 80)
- `run_status`: text allowlist: `success | failed | partial | unknown`
- `started_at`: timestamptz nullable
- `completed_at`: timestamptz nullable
- `data_timestamp`: timestamptz nullable
- `summary`: text max 500
- `limitations`: jsonb array (max 5 strings, each max 160)
- `source`: text (example: `paper_daily_runner`)
- `strategy_version`: text nullable
- `data_source`: text nullable
- `data_timestamp_source`: text nullable
- `created_at`: timestamptz default `now()`

### Bounded Mini App read rule (future runtime contract)
- Read **latest one** record only.
- Ordering: `completed_at DESC NULLS LAST, created_at DESC`.
- Map to existing bounded `latest_system_run` response fields only.
- Do not return raw strategy instructions.
- Do not return order placement instructions.
- Do not add broker/live execution fields.
- Do not expose full logs.
- Do not expose secrets.
- Do not allow arbitrary JSON passthrough.

## Guardrails reaffirmed
- System remains paper-trading / decision-support only.
- AI simulated decision, human paper decision, and real trade decision outside system remain explicitly separated.
- No broker/live execution is introduced.

## Step 91 schema/repository proposal update
- Step 91 adds proposal artifacts for Option C canonical path: Supabase migration draft `supabase/migrations/20260503_step91_create_latest_system_runs.sql` and backend contract doc `docs/latest-system-runs-repository-contract.md`.
- Scope remains proposal-only: no runtime Supabase read/write wiring, no Mini App frontend fetch addition, and no Railway topology/volume change in this step.
- Step 87 local artifact provider + Step 89 artifact writer remain fallback/dev/smoke path until Step 92 runtime provider implementation is accepted.
