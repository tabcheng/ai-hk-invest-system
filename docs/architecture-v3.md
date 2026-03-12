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
- Market price series retrieval for configured HK tickers.
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
- Current MVP: Telegram end-of-run summary (best-effort, non-blocking) with run-level delivery telemetry persisted for observability only.
- Future role: become a generalized **delivery bus** for structured daily intelligence packets (Telegram/email/dashboard/webhook) without altering strategy semantics.
- Design goal: delivery failures should never mutate signal or paper-trading truth.

### 8) Human decision layer
- Human reviews summarized outputs, trace artifacts, and risk posture.
- Human alone authorizes any real-trade action.

## Current modules (runtime map)
- `main.py`: process entrypoint.
- `src/app.py`: top-level run orchestration.
- `src/config.py`: environment/config loading.
- `src/data.py`: market data retrieval and normalization.
- `src/signals.py`: strategy decision logic.
- `src/db.py`: signal persistence and DB access utilities.
- `src/runs.py`: run lifecycle persistence.
- `src/paper_trading.py`: deterministic paper-trading simulation + persistence.
- `src/notifications.py`: Telegram summary delivery (best-effort).

## Architectural constraints for v3
- Preserve current production behavior unless a task explicitly authorizes change.
- Keep deterministic ordering and output reproducibility in paper-trading paths.
- Keep run traceability and status semantics coherent across modules.
- Keep documentation synchronized with runtime truth after each completed task.

## Near-term architecture priorities
1. End-to-end traceability key linkage (`run_id`) across signals + paper outputs.
2. Structured `error_summary` schema for diagnosability.
3. Notification layer hardening while preserving non-blocking behavior.
4. CI/test harness consistency to protect deterministic behavior over time.
