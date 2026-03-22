# Project Implementation Plan (System-of-Record View)

## Purpose
This document aligns:
- strategic intent (`docs/spec.md`),
- execution truth (`docs/status.md`),
- pending/completed work (`docs/backlog.md`),
- deployment ownership boundaries (GitHub vs Railway).

It is intentionally concise and optimized for small-step execution.

## Completed implementation steps (aligned)

### Steps 1–12 ✅
Documentation foundation, signal framework, dedup/run observability baseline, runtime modularization, regression tests, and Telegram MVP + initial hardening are complete.

### Steps 13–20 ✅
Traceability hardening, structured observability telemetry, CI test gating, notification schema guardrails, platform baseline docs, Supabase access-model clarification, and decision ledger v1 are complete.

### Steps 21–44 ✅
Paper-trading review/read-surface expansion, Telegram operator workflow hardening, dual-service deployment documentation, HKT display policy, market-data provider boundary, and docs consistency hardening are complete and reflected as merged/completed in `docs/status.md`.

## Current implementation state (operator/developer view)
- Runtime remains human-in-the-loop and paper-trading only.
- Telegram operator commands are read-only review surfaces (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/help`).
- Service topology is dual-service, same repository:
  - **webhook service**: long-running Telegram ingress (`python -m src.telegram_webhook_server`).
  - **runner service**: scheduled batch runner (`python -m src.daily_runner`, Railway cron in UTC).
- Business schedule baseline is **20:00 HKT**, currently mapped to Railway cron `0 12 * * *`.
- `MARKET_DATA_PROVIDER` boundary is active with default `yfinance`; `mock` exists for local/test determinism and should not be treated as production feed configuration.
- Human-facing operator timestamps are displayed in HKT; persisted/logged timestamps remain raw storage semantics (UTC/ISO).

## Deployment/config ownership split (must stay explicit)

### GitHub responsibilities
- Branch protection + required reviews + required status checks (`tests`).
- CI workflow integrity and dependency/update governance.
- Secret scanning / push protection posture.
- Source-of-truth documentation in `docs/`.

### Railway responsibilities
- Runtime service topology (separate webhook and runner services).
- Runner schedule ownership (UTC cron mapped from HKT baseline).
- Runtime environment variables and secret injection (Supabase, Telegram, provider selection, allowlists).
- Process-level runtime/log observation for operator troubleshooting.

## Next small-step candidates (do not over-plan)
1. **Step 45 candidate — Dedup semantics documentation validation**
   - Consolidate operator-facing wording/examples for `sent` / `skipped` / `deduped` / `failed`.
   - Keep scope docs-first unless a runtime defect is proven.

2. **Step 46 candidate — Platform checklist evidence pass**
   - Refresh explicit evidence checkpoints for GitHub/Railway/Supabase manual controls.
   - No runtime or strategy logic changes.

3. **Step 47 candidate — Paper-trading analytics scope note**
   - Define one minimal analytics increment and validation rubric (no broad implementation).

## Planning guardrails
- Keep each step small, testable, and reviewable.
- Preserve runtime behavior unless a step explicitly approves runtime change.
- Do not introduce autonomous real-money execution.
- Mark uncertain facts as `unknown / needs confirmation`.
