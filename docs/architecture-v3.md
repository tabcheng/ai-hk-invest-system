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


## Step 72 deployment-path decision — Mini App Preview / Deployment Path
- Recommended default path: deploy `miniapp/index.html` via a **dedicated Railway static site/static service** with its own preview URL.
- Rationale: keeps preview hosting isolated from Telegram webhook ingress runtime, reducing routing/operational coupling risk while enabling operator-accessible URL preview.
- Explicit non-goals in Step 72: no production Supabase read, no backend service-role endpoint, no vendor SDK integration, no write action, and no broker/live execution path.
- Security guardrails remain mandatory: browser/client must never contain `SUPABASE_SERVICE_ROLE_KEY` or vendor secrets; future data-enabled Mini App auth must validate Telegram `initData` server-side before granting access.
- Alternative paths evaluated and not selected as long-term default:
  - existing webhook service static serving: acceptable only as short-lived fallback preview, not long-term due to ingress coupling risk;
  - external static host: viable but adds cross-platform operations overhead;
  - local-only preview: safe but insufficient for real operator URL-based usage and Telegram Mini App linkage rehearsal.

## Step 71 implementation note — Mini App Read-only Review Shell MVP
- Added a low-risk static Mini App-compatible review shell entrypoint at `miniapp/index.html`.
- Scope is intentionally bounded to read-only placeholder sections (`Daily Review`, `Stock Decisions`, `Paper PnL / Risk`, `Outcome Review`, `Guardrails`).
- No write action, no strategy change path, no paper order creation path, no broker/live execution path.
- No production Supabase read in this step and no service-role backend endpoint.
- Security/auth is TODO-only in this step: server-side `initData` validation is required for future auth implementation; browser must not hold service-role/vendor secrets.


## Step 75 read-only data surface boundary plan (docs-only)
- Source-of-truth plan: `docs/miniapp-readonly-data-boundary.md`.
- Future Mini App data path must follow strict backend-mediated flow: browser sends Telegram `initData` -> backend validates server-side -> backend enforces operator authorization -> backend reads bounded internal/Supabase data -> backend returns bounded read-only JSON -> Mini App renders read-only review cards.
- Explicitly rejected for first data-enabled phase: direct browser Supabase production reads, any browser-held service-role/vendor/broker secret, and any `initDataUnsafe`-based authorization logic.
- First read-only candidates are review-only sections (`runner_status`, recent runs/latest run id, daily review summary, paper PnL/risk snapshot, outcome review summary); no write-capable endpoints.

## Step 77 backend authorization boundary helper (backend-only prerequisite)
- Mini App auth boundary is now explicitly two-step on backend:
  1. `validate_telegram_init_data(...)` verifies Telegram-signed payload freshness/integrity.
  2. `authorize_telegram_operator(...)` verifies validated `context["user"]["id"]` is inside backend-managed operator allowlist.
- Authorization key is stable Telegram numeric user id only; username is non-authoritative metadata.
- This step adds helper/tests only and does not introduce endpoint wiring, Supabase read path, or frontend data fetch.
- Platform impact for Step 77:
  - GitHub: runtime helper/tests/docs updates.
  - Railway: unchanged.
  - Supabase: unchanged.
- Deferred scope remains unchanged: strategy mutation, decision capture, paper order creation, broker/live execution, unrestricted table browsing, and browser-initiated secret-backed market-data calls.

## Step 76 implementation note — Backend-only Mini App initData validation helper
- Added server-side utility `src/miniapp_auth.py` to validate raw Telegram Mini App `initData` using Telegram HMAC check, required `hash`/`auth_date`, and bounded freshness window.
- Helper is backend-only input contract: `initData` query string + backend bot token parameter; no trust is placed on browser `initDataUnsafe` for authorization.
- Current step is prerequisite utility only: no HTTP endpoint, no Supabase read integration, no Mini App frontend fetch wiring, and no Railway topology/env changes.
- Therefore, production Mini App data-read path remains blocked pending endpoint wiring + operator authorization enforcement + bounded read-only response contract acceptance.

## Step 78 Mini App auth-gated read-only API skeleton (backend-only)
- Added backend route `POST /miniapp/api/review-shell` in existing WSGI app.
- Request boundary: JSON body with `init_data` only; raw Telegram `initData` is validated server-side and never trusted from `initDataUnsafe`.
- Access boundary: valid Telegram signature/freshness plus backend allowlist authorization by stable numeric Telegram `user.id`.
- Response boundary: mock read-only bounded JSON only (no Supabase production data read).
- Explicit non-goals preserved: no Mini App frontend fetch integration, no write action, no decision capture, no paper order creation, no broker/live execution.


## Step 79 readiness note (Mini App API skeleton hardening)
- `POST /miniapp/api/review-shell` now enforces explicit JSON Content-Type and bounded request size cap before auth processing.
- Endpoint remains bounded mock-only/read-only and does not read Supabase production data.
- No Mini App frontend fetch wiring is introduced in this step.
- No Railway manual env/config change is required in-step unless separately approved.
- Production data-enabled Mini App remains blocked until a separately designed/accepted bounded read implementation is approved.


## Step 80 service ownership clarification (controlled Railway smoke planning, docs-only)
- Backend route ownership remains with Railway service `telegram-webhook` for `POST /miniapp/api/review-shell`.
- `miniapp-static-preview` remains static frontend hosting only and must not host backend API routes.
- `paper-daily-runner` remains unaffected by Mini App API smoke activities.
- Production Supabase data-read path for Mini App remains blocked until separately designed and explicitly accepted bounded read implementation.


## Step 81 platform smoke evidence boundary (docs/evidence)
- Step 81 is limited to controlled Railway smoke evidence recording for `POST /miniapp/api/review-shell`.
- This step does **not** enable production Supabase data read.
- Backend smoke route ownership remains with Railway service `telegram-webhook`.
- `miniapp-static-preview` remains static-only and does not host backend API logic.
- `paper-daily-runner` remains unaffected by Step 81 smoke activity.


## Step 82 QA automation note (manual GitHub Actions smoke)
- Added a manual GitHub Actions smoke workflow for Mini App API endpoint verification (`workflow_dispatch` only).
- Smoke automation targets `telegram-webhook` endpoint path `POST /miniapp/api/review-shell` and does not involve `miniapp-static-preview` backend hosting.
- `miniapp-static-preview` remains static-only; `paper-daily-runner` remains unaffected.
- Smoke script signs Telegram `initData` locally and validates bounded response contracts (`415/413/401/403/200`) with safe logging only.

## Step 84 Mini App read-model boundary increment
- Mini App backend review-shell API now includes a first bounded runtime read source for `sections.runner_status` via `src/miniapp_read_model.py`.
- Source is runtime metadata only (`railway_runtime_env`), not system-of-record business data.
- This increment does not add Supabase production reads, market-data reads, paper-PnL reads, decision capture, paper order creation, or broker/live execution.
- Remaining Mini App review-shell sections (`daily_review`, `pnl_snapshot`, `outcome_review`) remain mock-only.
- `miniapp-static-preview` remains static-only; `paper-daily-runner` remains unaffected.
