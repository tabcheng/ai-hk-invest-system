# AI Hong Kong Investment System — Architecture v3

## Purpose and scope
This document defines the **v3 architecture baseline** for the long-horizon AI-assisted Hong Kong equity system, with emphasis on maintainability, traceability, and system-of-record quality.

This is a documentation-layer update only. Runtime behavior remains unchanged.

## Core philosophy
The platform is designed as an **AI investment firm operating model** with strict role separation:
1. **AI research + signal engine** generates repeatable decision-support outputs.
2. **Paper-trading execution layer** simulates disciplined execution and portfolio impact.
3. **Human decision authority** remains final for all real-money actions.

### Governance invariant
- AI outputs are advisory signals, not autonomous trading authority.
- Paper trading evaluates process quality and signal quality; it does not authorize live automation.
- Any live decision is human-reviewed and human-approved.

## v3 architecture overview

```text
[Scheduling / Runtime Trigger]
            |
            v
[Run Lifecycle + Observability]
            |
            v
[Market Data Ingestion]
            |
            v
[Signal Generation Engine]
            |
            v
[Signal Persistence + Dedup]
            |
            v
[Paper-Trading Simulation]
            |
            v
[Daily Summary + Delivery Layer (Telegram MVP)]
            |
            v
[Human Review / Investment Decision]
```

## System layers

### 1) Orchestration layer
- Daily job execution through Railway runtime entrypoint.
- Deterministic run-date capture and single-run execution semantics.
- Startup/terminal failure pathways include best-effort notification behavior.

### 2) Run observability layer
- Per-run lifecycle state (`RUNNING`, `SUCCESS`, `FAILED`) persisted in `runs`.
- Per-run counts, bounded text summaries, and structured JSON summaries (`error_summary_json`, `delivery_summary_json`) support post-run diagnosis without changing core processing semantics.
- Observability is best-effort; failures in run tracking should not corrupt core signal-generation execution.

### 3) Data ingestion layer
- Market price series retrieval for configured HK tickers now flows through a provider boundary (`MarketDataProvider`) so data-source adapters are replaceable.
- v1 provider contract supports only minimal capabilities (`get_daily_ohlcv`, `get_latest_price`, `get_symbol_metadata`) and keeps scope out of full ingestion orchestration.
- Input constraints and missing-data pathways preserved (`NO_DATA`, `INSUFFICIENT_DATA`).

### 4) Signal intelligence layer
- Deterministic strategy logic computes discrete actions (`BUY`, `SELL`, `HOLD`, `NO_DATA`, `INSUFFICIENT_DATA`).
- Behavior is intentionally stable to allow consistent paper-trading evaluation.

### 5) Persistence and system-of-record layer
- Signal writes persisted with idempotent daily dedup on `(date, stock)`.
- Migration-controlled schema evolution for reproducibility and rerun safety.
- Persistence is the canonical audit trail for later analytics and review.

### 6) Paper-trading evaluation layer
- Deterministic ledger simulation from persisted signals.
- Outputs include trade ledger, daily snapshots, and event logs.
- Rerun-safe same-day replacement behavior keeps outputs deterministic.

### 7) Delivery/notification layer (current + future role)
- Current MVP: Telegram end-of-run summary (best-effort, non-blocking) with run-level, message-attempt telemetry persisted for observability only (including explicit dedup-skip accounting).
- Future role: become a generalized **delivery bus** for structured daily intelligence packets (Telegram/email/dashboard/webhook) without altering strategy semantics.
- Design goal: delivery failures should never mutate signal or paper-trading truth.
- Daily summary payload contract is versioned with explicit evolution guardrails: a current version constant, an allowlisted supported-version set, centralized schema-dispatch renderer mapping, plus consistency validation to prevent supported/renderer drift.
- Delivery telemetry carries `context.summary_schema_version` so every attempt records which payload schema generated the notification.

### 8) Human decision layer
- Human reviews summarized outputs, trace artifacts, and risk posture.
- Human alone authorizes any real-trade action.

## Current modules (runtime map)
- `main.py`: process entrypoint.
- `src/app.py`: top-level run orchestration.
- `src/config.py`: environment/config loading.
- `src/data.py`: provider-resolved market data retrieval helpers and boundary entrypoint.
- `src/market_data/provider.py`: provider protocol + symbol metadata contract.
- `src/market_data/providers.py`: provider registry (`yfinance`, `mock`), symbol normalization assumptions, and adapter implementations.
- `src/signals.py`: strategy decision logic.
- `src/db.py`: signal persistence and DB access utilities.
- `src/runs.py`: run lifecycle persistence.
- `src/paper_trading.py`: deterministic paper-trading simulation + persistence.
- `src/notifications.py`: Telegram summary delivery (best-effort).

## Current runtime/data flow (aligned)

1. **Scheduler/trigger -> run setup**
   - Railway scheduler starts the worker process (`main.py` -> `src.app`).
   - A `runs` row is created and set to `RUNNING` for lifecycle traceability.

2. **Signal generation flow**
   - Runtime fetches market inputs for configured HK tickers.
   - Strategy logic computes deterministic signal actions (`BUY`, `SELL`, `HOLD`, `NO_DATA`, `INSUFFICIENT_DATA`).
   - Signals are persisted with dedup/idempotent behavior on `(date, stock)`.

3. **Decision record flow**
   - At signal persistence time, a decision-ledger record is written to `paper_trade_decisions`.
   - Ledger fields intentionally separate AI output (`signal_*`) from human decision state (`human_decision_*`) for auditability.

4. **Paper-trading flow**
   - Paper simulation runs from persisted signals (paper-only; no live execution).
   - Trade/event/snapshot outputs are persisted (`paper_trades`, `paper_events`, `paper_daily_snapshots`) with `run_id` linkage.
   - Position state is refreshed into `paper_positions` for compact portfolio/PnL read surfaces.

5. **Telegram + observability flow**
   - End-of-run summary payload is built with versioned schema and rendered to Telegram format.
   - Delivery attempt is best-effort/non-blocking; dedup logic can skip repeated run-date sends.
   - Run finalization updates status (`SUCCESS`/`FAILED`) and writes summary observability fields, including delivery telemetry JSON.

6. **Human review flow**
   - Human operator reviews Telegram/docs/CLI read surfaces and remains final authority for any real-money action.

## Architectural constraints for v3
- Preserve current production behavior unless a task explicitly authorizes change.
- Keep deterministic ordering and output reproducibility in paper-trading paths.
- Keep run traceability and status semantics coherent across modules.
- Keep documentation synchronized with runtime truth after each completed task.

## Near-term architecture priorities
1. Keep scheduler -> signal -> paper-trading -> notification documentation synchronized with runtime truth.
2. Continue notification clarity/dedup hardening without breaking non-blocking delivery invariants.
3. Close manual platform hardening follow-ups (GitHub/Railway/Supabase) with explicit verification records.
4. Scope the next small analytics increment for paper-trading evaluation without strategy churn.

## Step 19 operational baseline hardening (GitHub / Railway / Supabase)

### GitHub baseline controls (repository governance)
- Protect `main` with branch protection rules: require pull requests, require at least one review, dismiss stale approvals on new commits, and block force-push/deletion for non-admin contributors.
- Require the `tests` status check (from `.github/workflows/tests.yml`) to pass before merge.
- Enable Dependabot security updates and version updates for Python/GitHub Actions dependencies.
- Enable secret scanning and push protection for all supported token types.
- These controls are platform settings, not runtime code behavior; enforce through repository settings and keep documented for periodic verification.

### Railway baseline controls (runtime operations)
- Current runtime is a scheduled worker/script entrypoint (`main.py` -> `src.app.main`) rather than a long-lived HTTP service.
- Decision for this baseline pass: **do not add a `/health` HTTP endpoint** because no web server exists in the deployed runtime path, and introducing one would add unnecessary process behavior.
- Required Railway healthcheck setting: disable HTTP healthcheck probing for this worker service; if Railway requires checks, use process/startup success semantics rather than URL probing.
- Environment variable hygiene expectations:
  - Store all credentials in Railway managed secrets (never hardcoded).
  - Keep `.env` local-only and excluded from git.
  - Rotate Supabase/Telegram credentials on leakage or team membership changes.
- Observability/logging expectations:
  - Keep structured run observability in Supabase (`runs` + JSON summaries) as source-of-truth.
  - Keep Railway logs enabled for process-level diagnostics and exception traces.

### Supabase baseline controls (data platform safety)
- Backup/PITR: verify daily backups and point-in-time recovery are enabled for production-tier projects before live dependency.
- RLS/exposure review: review every table exposed to API access; ensure least-privilege policies and avoid exposing service-role credentials to clients.
- Free-plan pause risk: if running on free tier, document that project pausing can delay scheduled jobs and notifications; treat free-tier as non-production.
- Production safety for run/telemetry data:
  - Treat `runs`, `signals`, `paper_*`, and `notification_logs` as audit records.
  - Keep mutation paths controlled to runtime writes/migrations only.
  - Preserve retention/export expectations so telemetry is available for post-run review.

## Step 19B Supabase access model clarification + safe RLS hardening plan

### Current runtime access model
- Runtime access is backend-worker initiated via server-side environment configuration (`SUPABASE_URL`, `SUPABASE_KEY`) in `src/config.py`.
- No first-party browser/mobile client path exists in this repository that needs direct table access.
- Current production expectation: Supabase runtime tables are backend-only operational records.

### Core table inventory + current exposure posture

| Table | Schema | In `public`? | Backend-only? | Anon/client access needed now? | RLS state (manual review) |
|---|---|---:|---:|---:|---|
| `runs` | `public` | Yes | Yes | No | Not enabled |
| `signals` | `public` | Yes | Yes | No | Not enabled |
| `paper_trades` | `public` | Yes | Yes | No | Not enabled |
| `paper_daily_snapshots` | `public` | Yes | Yes | No | Not enabled |
| `paper_events` | `public` | Yes | Yes | No | Not enabled |
| `notification_logs` | `public` | Yes | Yes | No | Not enabled |

### Hardening approach (safe + staged)
1. Keep Step 19B limited to documentation and rollout planning (no broad production schema mutation in this step).
2. Prefer table-by-table RLS enablement in `public` with minimal explicit backend-safe policies and verification after each table.
3. Keep private-schema migration as a later option after the initial RLS rollout proves stable.
4. Verify API exposure settings for `public`; if `public` remains exposed, complete RLS coverage for all runtime tables.

### Exact next migration step (follow-up task)
- Introduce a dedicated migration targeting only one low-risk table (`public.runs`) first:
  - `alter table public.runs enable row level security;`
  - add explicit backend policy for service-role usage;
  - include post-deploy verification and rollback notes.
- After verification, roll forward sequentially to `signals`, `notification_logs`, and `paper_*` tables.

### Rollout guardrails
- Preserve backend runtime behavior and run observability writes.
- Avoid one-shot all-table RLS flips.
- Keep each migration small, reviewable, and reversible.
