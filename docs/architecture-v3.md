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
