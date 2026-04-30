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

### Steps 21–61 ✅
Paper-trading review/read-surface expansion, Telegram operator workflow hardening, dual-service deployment documentation, HKT display policy, market-data provider boundary, delivery-semantics observability hardening through `dedup_persist_result`, post-merge dual acceptance governance formalization, platform evidence-pass documentation, paper-trade outcome review usability increments, and Step 61 Human Decision Journal Contract v1 (docs-first) are complete and reflected as merged/completed in `docs/status.md`.

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

## Post-merge dual acceptance discipline (required for every merged step)
1. **Post-merge QA Check (mandatory)**
   - Verify new output/function behavior matches expected intent.
   - Verify success path and error path are both explicit and understandable.
   - Verify display, docs, and tests remain consistent with each other.
2. **Post-merge Domain Check (mandatory)**
   - Verify alignment with AI-assisted Hong Kong investing-system mainline intent.
   - Verify paper-trading / decision-support-only boundary remains intact.
   - Verify no unacceptable calculation/interpretation risk is introduced.
3. **Triage outcome discipline**
   - **Blocker:** correctness/safety/domain-boundary breach; must be resolved before acceptance closes.
   - **Backlog follow-up:** non-blocking improvement item; record in `docs/backlog.md`.
4. **System-of-record wording discipline**
   - `docs/status.md`: merged completion truth + acceptance result wording.
   - `docs/backlog.md`: pending follow-up work only; never the canonical merged-state record.

## Next small-step candidates (do not over-plan)
1. **Step 62 candidate — `/decision_note` runtime MVP (bounded)**
   - Implement Step 61 contract as the smallest runtime slice.
   - Prefer run-level journaling first if stock-level expands scope; include stock-level only if still bounded.
   - Keep command strictly journaling-only (no trade execution semantics).

2. **Telegram command registration follow-up (optional)**
   - Decide whether to add `setMyCommands` for discoverability.
   - Keep isolated from strategy and paper-trading logic.

3. **Platform evidence cadence/process follow-up**
   - Define lightweight recurring manual verification cadence and evidence artifact location policy.
   - Keep docs/process scope only unless a separate infra/runtime step is explicitly approved.

## Planning guardrails
- Keep each step small, testable, and reviewable.
- Preserve runtime behavior unless a step explicitly approves runtime change.
- Do not introduce autonomous real-money execution.
- Mark uncertain facts as `unknown / needs confirmation`.

- Step 62 implementation (runtime): `/decision_note` run-level only with persistence + validation + tests.


## Step 63 implementation note (completed)
- Added manual operator smoke QA harness only (`scripts/operator_smoke_test.py` + `.github/workflows/operator-smoke-test.yml`).
- No schedule trigger, no push/PR production webhook trigger, no strategy or paper-trading calculation changes.
- Optional Supabase verification input exists but defaults to skipped in Step 63; full row verification deferred candidate for Step 65.
- Step 67 scheduled daily health check remains future plan only.

## Step 64 implementation note (completed)
- Expanded operator smoke coverage (manual `workflow_dispatch` only) to include `/runs`, `/runner_status`, `/risk_review <test_run_id>`, `/pnl_review`, `/outcome_review`, while preserving existing `/help`, `/daily_review`, and `/decision_note` cases.
- Report wording now distinguishes transport/delivery verification vs response-text limitation (`response_text_verification=SKIPPED_current_webhook_contract`).
- Added fail-fast `--test-run-id` validation (positive integer only) with readable FAIL report output and guidance.
- No strategy logic changes, no paper-trading calculation changes, no Railway topology/env/webhook changes, and no Supabase row verification in this step (deferred to Step 65).
- Step 66 post-deploy acceptance checklist remains deferred, and Step 67 scheduled daily health check remains future plan only.

## Step 65 implementation note (completed)
- Added optional Supabase verification layer to manual operator smoke harness (still `workflow_dispatch` only).
- `verify_supabase=false` remains default and returns `supabase_verification_status=SKIPPED` with no DB query requirement.
- `verify_supabase=true` now requires GitHub Actions secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, generates per-run `qa_marker`, and performs read-only verification query on `human_decision_journal_entries` for `/decision_note` run-level persistence evidence.
- Reports now include `supabase_verification_status`, `supabase_table`, `qa_marker`, `matched_rows_count`, and safe failure reason/guidance while keeping secrets redacted.
- No Supabase schema migration, no Railway topology/cron/env/webhook routing change, no strategy logic/paper-trading calculation change, and no broker/live-money execution semantics.
- Step 66 post-deploy acceptance checklist remains deferred; Step 67 scheduled daily health check remains future plan only.
