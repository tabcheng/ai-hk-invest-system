# AI Hong Kong Investment System — Architecture v3

## Purpose and scope
This document defines the **v3 architecture baseline** for the long-horizon AI-assisted Hong Kong equity system, with emphasis on maintainability, traceability, and system-of-record quality.

This architecture baseline includes runtime/documentation updates through Step 50 while preserving paper-trading/decision-support guardrails.

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
[Railway Scheduler + Webhook Ingress]
            |
            v
[Run Lifecycle + Observability]
            |
            v
[Market Data Provider Boundary]
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
[Operator Review Surfaces + Telegram Delivery]
            |
            v
[Human Review / Investment Decision]
```

## Current service topology (deployment reality)

### Service 1 — `telegram-webhook` (long-running)
- Start command: `python -m src.telegram_webhook_server`.
- Responsibility: receive Telegram webhook updates and execute operator read commands.
- Should not own daily signal schedule/cron.

### Service 2 — `paper-daily-runner` (scheduled batch)
- Start command: `python -m src.daily_runner`.
- Responsibility: run signal generation + persistence + paper-trading + summary delivery.
- Cron ownership: runner service only.

### Schedule baseline
- Business schedule baseline: **20:00 HKT**.
- Railway scheduler uses UTC; current mapping baseline is `0 12 * * *`.

## System layers

### 1) Orchestration layer
- Daily batch execution through runner service entrypoint.
- Webhook command processing through webhook service entrypoint.
- Deterministic run-date capture and single-run execution semantics.

### 2) Run observability layer
- Per-run lifecycle state (`RUNNING`, `SUCCESS`, `FAILED`) persisted in `runs`.
- Per-run counts, bounded summaries, and structured JSON summaries (`error_summary_json`, `delivery_summary_json`).
- Observability is best-effort; tracking failure must not corrupt signal/paper flows.

### 3) Data ingestion layer
- Market reads route through `MarketDataProvider` boundary.
- Contract includes `get_daily_ohlcv`, `get_latest_price`, `get_symbol_metadata`.
- Date-window semantics at boundary are inclusive (`start_date`/`end_date`), with adapter-level compensation for exclusive-end data sources.

### 4) Signal intelligence layer
- Deterministic strategy emits `BUY`, `SELL`, `HOLD`, `NO_DATA`, `INSUFFICIENT_DATA`.
- Strategy stability is prioritized for paper-trading evaluation consistency.

### 5) Persistence/system-of-record layer
- Signal persistence is idempotent on `(date, stock)`.
- `paper_trade_decisions` separates AI signal fields vs human decision fields.
- Storage/log semantics remain UTC/ISO-oriented for operational consistency.

### 6) Paper-trading evaluation layer
- Deterministic simulation from persisted signals.
- Persists trades/events/snapshots/positions for rerun-safe review.
- Paper-only; no live broker execution path.

### 7) Delivery + operator layer
- Telegram daily summary is best-effort/non-blocking.
- Daily-summary dedup identity is date/target/message_type/status based; message wording updates do not alter dedup identity.
- Retry/rerun semantics are intentionally best-effort:
  - no SENT marker yet -> rerun may deliver another summary;
  - SENT marker exists -> rerun should dedup-skip;
  - dedup-read/write failure -> system degrades to send-attempt path to avoid blocking core run flow.
- Operator command surfaces are read-only review surfaces:
  - `/runs`
  - `/runner_status`
  - `/risk_review`
  - `/pnl_review`
  - `/help` / `/h`
- Human-facing display policy: operator timestamps are rendered in HKT (`*_hkt` labels where applicable).

#### Observability evidence baseline (Step 46 docs)
- Primary evidence for delivery semantics validation is cross-surface:
  1. Telegram observed messages,
  2. `runs.delivery_summary_json`,
  3. runner logs (`execution_summary` + lifecycle lines),
  4. relevant `runs` records.
- Command-reply observability and daily-summary observability are related but distinct:
  - command replies are webhook-triggered per inbound command event;
  - daily summaries are runner-triggered per run lifecycle.
- Current gap: there is no fully automated cross-surface correlation artifact yet; operators still perform manual evidence matching (run id/date/timestamp context).
- Deferred follow-up: stronger runtime instrumentation/correlation should be implemented only in a later explicitly approved runtime step.

#### Runtime instrumentation baseline (Steps 48–50)
- **Implemented minimal fields (Step 48):** daily summary telemetry includes `correlation_id` and `dedup_check_result`, both projected into `runs.delivery_summary_json`.
- **Bounded dedup check semantics:** `send_path` (normal), `dedup_skip` (already-sent marker hit), `dedup_check_fallback` (dedup check failure with degraded send-attempt path).
- **Implemented minimal field (Step 50):** daily summary telemetry now also includes `dedup_persist_result` with bounded values:
  - `persisted`,
  - `persist_failed`,
  - `not_applicable`.
- **Step 49 refinement decision (now implemented in Step 50):** `dedup_persist_result` was prioritized as the next slice; `delivery_phase` remains deferred candidate scope.
- **Scope intentionally unchanged:** no DB migration, no send-path refactor, no queue/retry framework, no strategy or paper-trading logic mutation.

### 8) Human decision layer
- Human reviews outputs and retains final real-money decision authority.

## Config policy snapshot (current)
- `MARKET_DATA_PROVIDER` supports provider selection via registry.
- Current production baseline usage is `yfinance`.
- `mock` provider is deterministic and intended for local/test usage; not a production data-feed baseline.

## Deployment ownership split

### GitHub owns
- Code review + merge controls (branch protection, required checks/reviews).
- CI workflow execution and repository security scanning posture.
- System-of-record documentation updates in `docs/`.

### Railway owns
- Service process model (webhook vs runner split).
- Runner scheduling (UTC cron mapped from HKT baseline).
- Runtime env/secret management (Supabase/Telegram/provider config/allowlists).
- Runtime logs and process-level diagnostics.

## Architectural constraints for v3
- Preserve production behavior unless a task explicitly authorizes change.
- Keep deterministic ordering/output reproducibility in paper-trading paths.
- Keep run traceability/status semantics coherent across modules.
- Keep documentation synchronized with runtime truth after each completed step.
- Keep scope paper-trading/decision-support only (no autonomous real-money execution).


## Step 69 product architecture extension
### Product surfaces by role
- **Telegram Bot**: notification delivery, quick operator command actions, and smoke-test entry surface.
- **Telegram Mini App / Web UI**: daily review/product-review surface for richer multi-entity inspection.
- **Backend + Supabase**: canonical system-of-record persistence and audit boundary.

### Product architecture (expanded)
```text
[Telegram Bot: notify + quick actions + smoke test]
                 |
                 v
[Mini App / Web UI: daily review surface]
                 |
                 v
[Backend APIs + Orchestration + Risk Gate]
                 |
                 v
[Supabase System of Record]
                 |
                 v
[AI Team Paper Trading Track + Outcome Review]
```

### Market data integration boundary
- Vendor onboarding must be preceded by a stable `MarketDataProvider` interface boundary.
- Strategy logic and orchestration must depend on internal provider contracts, not vendor SDK primitives.

### AI team paper-trading + risk gate
- AI team paper-trading track is first-class and remains simulation-only.
- A risk gate check is required before any simulated order creation is accepted into system records.
- Simulated order creation metadata must include: `strategy_version`, `data_source`, `data_timestamp`, `risk_check`, `paper_trade_only=true`.

### Security notes (mandatory)
- Mini App / browser clients must **never** receive `SUPABASE_SERVICE_ROLE_KEY`.
- Vendor API keys/secrets must remain backend-only (Railway/GitHub Secrets/runtime env), never shipped to client surfaces.
- Future Mini App authentication must validate Telegram `initData` server-side before granting data access.
- No broker secrets are stored/used because no broker/live execution path is permitted.

## Step 71 implementation note — Mini App Read-only Review Shell MVP
- Added a low-risk static Mini App-compatible review shell entrypoint at `miniapp/index.html`.
- Scope is intentionally bounded to read-only placeholder sections (`Daily Review`, `Stock Decisions`, `Paper PnL / Risk`, `Outcome Review`, `Guardrails`).
- No write action, no strategy change path, no paper order creation path, no broker/live execution path.
- No production Supabase read in this step and no service-role backend endpoint.
- Security/auth is TODO-only in this step: server-side `initData` validation is required for future auth implementation; browser must not hold service-role/vendor secrets.
