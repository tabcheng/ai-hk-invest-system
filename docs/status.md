# Project Status

## Last reviewed date
2026-05-02

## Post-merge acceptance + wording discipline (system-of-record)
- Every merged step must complete two mandatory acceptance checks:
  1. **Post-merge QA Check** — verify output/function correctness, success/error path clarity, and display/docs/tests consistency.
  2. **Post-merge Domain Check** — verify AI HK investing-system alignment, paper-trading/decision-support-only boundary, and calculation/interpretation risk posture.
- Triage classification:
  - **Blocker:** correctness/safety/domain-boundary issue requiring fix before acceptance closure.
  - **Backlog follow-up:** non-blocking improvement item; track in `docs/backlog.md`.
- Wording discipline to reduce ambiguity:
  - `docs/status.md` records merge completion truth + acceptance outcomes (`repo merge completed`, `manual platform acceptance completed`).
  - `docs/backlog.md` records pending follow-up work only (including docs maintenance follow-up), not canonical merge-state truth.
- Recommended status wording template per merged step:
  - `repo merge completed: yes/no`
  - `manual platform acceptance completed: yes/no`
  - `docs maintenance follow-up: none` or `tracked in docs/backlog.md #<item>`

## Current production behavior (repo-confirmed)
- Scheduled runner entrypoint now supports dedicated module execution via `python -m src.daily_runner` (with `main.py` retained as backward-compatible wrapper), while orchestration remains in modular runtime code under `src/`.
- Daily signal persistence remains idempotent on `(date, stock)` and supports rerun-safe behavior.
- Run lifecycle observability remains in `runs` with terminal status + structured summaries (`error_summary_json`, `delivery_summary_json`).
- Paper-trading remains deterministic and paper-only, with run-linked persistence across trades/snapshots/events.
- Decision record separation is implemented via `paper_trade_decisions` (AI signal vs human decision state).
- Telegram delivery remains best-effort/non-blocking with deterministic summary formatting and run-date dedup tracking.
- Telegram daily summary readability is improved with explicit per-stock sections (`stock`, `signal/action`, `key_reason/indicator`) and run-level `risk_note`, while keeping existing dedup identity keys unchanged.
- Operator command read-surface now supports Telegram `/runs` query for recent run ids (default last 5 days) sourced from persistent `runs` table metadata (no log-file scraping).
- Step 32 review hardening: `/runs` invalid parameter input now returns usage guidance text instead of raising handler exceptions.
- Step 32 hotfix: `/runs` metadata query now uses schema-safe `runs` fields only (`id,status,created_at`) to prevent runtime query failures from non-existent columns.
- Step 33 operator-help uplift: Telegram `/help` and `/h` now return a compact bilingual usage guide that covers system scope, guardrails, and command list (`/runs`, `/runs [days]d`, `/help`, `/h`).
- Step 33 review hardening: `/help` and `/h` now follow the same operator chat/user authorization guardrail as `/runs`.
- Step 33 discoverability note: repo currently has no Telegram bot command-registration setup (for example `setMyCommands` registry), so this step intentionally adds handler-only support and keeps runtime changes minimal.
- Step 34A Telegram inbound foundation: repo-confirmed previous state was outbound-only Telegram delivery (no webhook endpoint, no polling loop). A new dedicated webhook ingress server now exposes `POST /telegram/webhook`, forwards inbound updates to `handle_telegram_operator_command(...)`, and replies to source chat via Telegram `sendMessage` for `/help`, `/h`, `/runs`.
- Step 34A observability: webhook ingress logs now include request received, command text, authorization decision, and sendMessage success/failure outcome for operator troubleshooting.
- Step 34A review hardening: webhook ingress now supports optional transport-level secret verification (`TELEGRAM_WEBHOOK_SECRET_TOKEN`), returns explicit `401` for bad secret and `503` for Supabase client init failures to improve operator diagnosability.
- Step 34A docs hotfix: `docs/telegram-webhook-setup.md` now explicitly separates `setWebhook` usage for with-secret vs no-secret paths, clarifies optional secret semantics, and adds deployment guardrail guidance to prevent treating `secret_token` as mandatory.
- Step 34A message-format hotfix: Telegram operator help/usage text now replaces angle-bracket placeholders (for example `/runs <days>d`) with HTML-safe bracket format (`/runs [days]d`) so Telegram `sendMessage` HTML parse mode no longer raises unsupported-tag errors.
- Step 34A message-format review hardening: focused tests now assert both `/help` content and malformed `/runs` usage responses do not include HTML-like placeholder tags.
- Step 34B operator command uplift: Telegram operator command surface now adds `/risk_review [run_id]` with strict run-id parsing, chat/user allowlist enforcement, safe failure responses, and paper-risk review execution via internal Python path (no shell-out).
- Step 34B observability hardening: `/risk_review` logs command received, caller/chat context, requested run_id, and accepted/failed/completed transitions; internal exception details are logged but sanitized in Telegram replies.
- Step 34B deployment docs: added `docs/railway-service-variables.md` as deployment-facing reference for Railway environment variables (Telegram/webhook, operator allowlist, Supabase, runtime).
- Step 34B review hardening: command-handler and run-lookup unexpected exceptions are now isolated/sanitized so webhook ingress stays healthy and operators receive safe failure text instead of transport-level crashes.
- Step 34B testability hardening: `telegram_operator` now lazy-loads the paper-risk review dependency so operator command tests can run without importing optional Supabase runtime packages during module import.
- Step 35 deployment topology hardening: Railway deployment is now documented as two same-repo services with split responsibilities — `telegram-webhook` (long-running ingress, start command `python -m src.telegram_webhook_server`, no cron) and `paper-daily-runner` (scheduled batch run, start command `python -m src.daily_runner`, cron `0 12 * * *`).
- Step 37 runner-entrypoint hardening: scheduled runner now has a dedicated entrypoint (`python -m src.daily_runner`) with explicit startup/completion/failure logging and deterministic exit codes; `main.py` remains a backward-compatible thin wrapper.
- Step 37 schedule codification: business schedule baseline is Hong Kong Time (HKT), current target run time is 20:00 HKT, Railway cron uses UTC, and current runner cron is `0 12 * * *`.
- Step 38 runner observability hardening: daily runner output now emits consistent started/completed/failed lifecycle lines plus single-line JSON `execution_summary` with required fields (`started_at`, `finished_at`, `duration_seconds`, `status`, `entrypoint`, `schedule_basis`) for reviewability.
- Step 38 failure-summary hardening: failed runs now include a concise/safe error summary in both failure lifecycle log and execution summary while still emitting traceback to stderr for diagnostics.
- Step 38 review hardening: failure `error_summary` normalization now strips multiline/irregular whitespace into single-line text before truncation to keep log lines safe/consistent; focused test coverage now includes normalization + truncation behavior.
- Step 39 operator usability uplift: Telegram operator command surface now adds `/runner_status` with allowlisted chat/user gating and safe reply behavior for success/no-data/lookup-failure/format-failure paths.
- Step 39 traceability hardening: `/runner_status` reads latest runner metadata from durable `runs` persistence (`id,status,created_at,finished_at,error_summary`) and renders required summary fields (`status`, `started_at`, `finished_at`, `duration_seconds`, `entrypoint`, `schedule_basis`, `error_summary`) without exposing raw internal exceptions.
- Step 39 review hardening: `/runner_status` timestamp parsing now normalizes unexpected naive ISO timestamps as UTC for deterministic operator output across environments.
- Step 39 review hotfix (HTML-safe output): `/runner_status` now HTML-escapes dynamic `error_summary` content before Telegram reply formatting so persisted `<`, `>`, `&` cannot break Telegram HTML parse mode delivery.
- Step 39 review hotfix (HTML-safe follow-up): `/runner_status` now also HTML-escapes other dynamic metadata fields (`status`, `run_id`) to keep operator replies parse-safe even if persisted metadata becomes irregular.
- Step 40 operator-format contract: `/runs`, `/runner_status`, and `/risk_review` replies now follow a shared operator response shape (`Command`, `Status`, optional `Result`/`Reason`, deterministic `- key: value` rows) to improve fast scan readability and wording consistency across success/failure/no-data/unauthorized paths.
- Step 40 HTML-safe rendering contract: dynamic operator reply fields are now rendered through one centralized HTML-escaping helper so command-specific formatting no longer needs ad-hoc escaping and parse-mode safety behavior is consistent.
- Step 40 review follow-up: `/runs` and `/risk_review` input-validation/usage failure replies now also emit the same shared response shape (instead of raw parser strings) to keep failure wording/layout consistency end-to-end.
- Step 40 review hotfix (header HTML-safe rendering): `_build_operator_message` now HTML-escapes header-level dynamic values (`command_label`, `status`, `result`, `reason`) so malformed command text (for example `/runs<bad>`) cannot break Telegram HTML parse-mode reply delivery on unauthorized/internal-failure paths.
- Step 40 review hardening: focused Telegram operator tests now assert shared message-shape consistency and HTML-safe dynamic rendering for command status and detail fields, while webhook-level non-crash behavior coverage remains in place.
- Step 41 paper review snapshot v1: added read-only paper-trading position/PnL snapshot helper sourced from persisted `paper_trades`, `paper_positions`, and `paper_daily_snapshots` with explicit count/totals/per-symbol output.
- Step 41 operator usability uplift: Telegram operator command surface now adds `/pnl_review` with allowlist/chat guardrail, safe failure response, and deterministic summary rows (open/closed counts, realized/unrealized totals, per-symbol lines).
- Step 41 traceability note: current `/pnl_review` response includes stock id and uses `stock_name=N/A` when no dedicated stock-name source exists in current read-path schema.
- Step 41 review hardening: `/pnl_review` now rejects malformed extra-argument variants (for example `/pnl_review now`) with explicit usage guidance instead of silent ignore behavior.
- Step 41 data-quality hardening: closed-position counting now requires BUY lineage so malformed SELL-only history is surfaced as `FLAT` and excluded from closed-position totals.
- Step 41 correctness hotfix: paper position/PnL snapshot replay ordering now matches position-refresh contract (`trade_date` then `id`) to prevent rerun/backfill `id` drift from skewing quantity/avg-cost/realized-PnL/closed-count outputs.
- Step 42 market-data boundary v1: signal data reads now go through a provider abstraction (`MarketDataProvider`) with registry-based selection (`MARKET_DATA_PROVIDER`, default `yfinance`) and a deterministic `mock` provider for local/test usage.
- Step 42 review hardening: yfinance latest-price adapter now compensates for exclusive `end` semantics by requesting `end_date + 1 day`; provider registry now fail-fast rejects blank `MARKET_DATA_PROVIDER` values with explicit error messaging.
- Step 42 correctness hotfix: provider contract now explicitly defines inclusive `end_date`; yfinance compensation is centralized in `get_daily_ohlcv` so daily signal generation path (`fetch_market_data`) also includes latest available bar and avoids one-day-late BUY/SELL decisions.
- Step 43 human-facing display policy: Telegram/review operator-facing timestamp outputs are now normalized to Hong Kong Time (`Asia/Hong_Kong`) at render-time boundary, with explicit `HKT` labeling for readability and timezone context.
- Step 43 boundary hardening: timestamp conversion is display-only (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`) and does not alter persistence/log storage semantics (UTC/ISO raw values remain unchanged in storage paths).
- Step 43 operator clarity hardening: representative Telegram operator replies now include clearer intent context (for example read-only review wording, paper-trading scope reminder, and HKT-labeled fields such as `started_at_hkt`, `finished_at_hkt`, `valuation_timestamp_hkt`, `run_started_at_hkt`).
- Step 45 docs validation: documented Telegram/operator-facing delivery semantics reality (command replies, runner summary delivery, review response behavior, retry/rerun/duplicate cases), clarified operator expectation for normal vs expected-duplicate vs suspicious patterns, and refreshed backlog follow-ups with docs-only scope (no runtime behavior change).
- Step 46 observability evidence pass (docs-only): added operator-executable delivery semantics checklist and validation guidance spanning Telegram observed messages, `runs.delivery_summary_json`, runner logs, and relevant run records.
- Step 46 gap analysis baseline (docs-only): explicitly separated known current behavior, verifiable evidence surfaces, unresolved observability gaps, and deferred runtime/instrumentation follow-ups; no runtime/API/schema/strategy change.
- Step 46 platform ownership clarification: GitHub changes are documentation/system-of-record updates only; Railway runtime topology/cron/env configuration requires no change in this step.
- Step 47 instrumentation scoping proposal (docs-only): delivery observability gaps are now explicitly prioritized (correlation gap, dedup fallback evidence gap, phase-visibility gap, attempt-identity gap) with clear P0/P1/P2 ordering.
- Step 47 candidate classification (docs-only): minimal instrumentation candidates (`correlation_id`, `message_delivery_attempt_id`, `delivery_phase`, `dedup_check_result`, `dedup_persist_result`, `fallback_activated`) are documented with value/risk/scope and recommended-first vs conditional ordering.
- Step 47 guardrail codification (docs-only): explicit non-goals recorded for this step — no runtime implementation, no DB migration, no `delivery_summary_json` schema change, no Telegram send-path refactor, no queue/retry framework, no strategy logic change.
- Step 47 platform ownership clarification: GitHub changed docs/system-of-record artifacts only; Railway topology/cron/runtime env remains unchanged in this step.
- Step 48 minimal runtime instrumentation v1: Telegram daily summary telemetry now includes `correlation_id` and `dedup_check_result`, and both are persisted into `runs.delivery_summary_json` for operator-facing cross-surface traceability.
- Step 48 bounded dedup semantics: `dedup_check_result` is now explicitly classified as `send_path` (normal send attempt), `dedup_skip` (dedup marker hit), or `dedup_check_fallback` (dedup check failure with graceful send-path fallback).
- Step 48 focused validation: tests now cover normal send, dedup skip, dedup-check fallback, and run-level delivery-summary projection of the new instrumentation fields.
- Step 48 platform ownership clarification: GitHub includes code/tests/docs updates; Railway requires no topology/cron/env/deployment mutation.
- Step 48 review hotfix: `tests/test_app.py` success-path telemetry fixture now includes `correlation_id` + `dedup_check_result` so delivery-summary projection assertions remain consistent with mocked telemetry payload shape.
- Step 49 delivery semantics follow-up refinement (docs-only): post-Step-48 reassessment now narrows remaining observability ambiguity to dedup-persist evidence vs phase progression detail, with explicit comparison of `dedup_persist_result` and `delivery_phase`.
- Step 49 single-slice recommendation: next runtime increment should implement `dedup_persist_result` only (defer `delivery_phase`), preserving bounded rollout and operator triage clarity.
- Step 49 platform ownership clarification: GitHub changed docs/system-of-record artifacts only; Railway topology/cron/runtime env/deployment remain unchanged.
- Step 50 minimal runtime instrumentation v2: daily summary telemetry now includes `dedup_persist_result` with bounded values (`persisted`, `persist_failed`, `not_applicable`) and persists this field into `runs.delivery_summary_json`.
- Step 50 focused validation: tests now cover normal send + persist success, send success + persist failure, dedup-skip N/A semantics, and delivery summary projection shape including `correlation_id`, `dedup_check_result`, and `dedup_persist_result`.
- Step 50 platform ownership clarification: GitHub includes runtime/tests/docs updates for bounded telemetry increment; Railway requires no topology/cron/runtime env/deployment mutation.
- Step 50 review hardening: test harness now installs lightweight local stubs (`requests`, `supabase`, `pandas`, `yfinance`) in `tests/conftest.py` so focused tests can run in constrained environments without external package installation, while production runtime dependency expectations remain unchanged.
- Step 51 post-merge governance formalization (docs-only): dual acceptance workflow is now explicit and mandatory after every merge (`Post-merge QA Check` + `Post-merge Domain Check`) with blocker vs backlog-follow-up triage criteria and status/backlog wording discipline.
- Step 52 test-harness pandas stub coverage fix: `tests/conftest.py` now gates pandas stubbing on actual package availability and provides a minimal, test-scoped pandas compatibility surface (`date_range`, `DataFrame(...)`, `.empty`, rolling mean, indexing helpers) so market-data/signals tests run correctly in constrained CI environments.
- Step 53 platform hardening evidence pass (docs-only): added a platform evidence summary and manual verification checklist across GitHub/Railway/Supabase with explicit classification (`repo-confirmed`, `manual verification required`, `backlog follow-up`) and no runtime/deployment topology change.
- Step 53 GitHub evidence posture: repo confirms CI workflow (`.github/workflows/tests.yml`) and ownership expectations docs, while branch protection / required reviewers / required status-check enforcement remains manual verification on the GitHub settings UI.
- Step 53 Railway evidence posture: repo confirms dual-service split, cron baseline (`0 12 * * *` UTC => 20:00 HKT), and env/secret variable documentation; actual service settings and secret values remain manual verification on Railway project/service settings.
- Step 53 Supabase evidence posture: repo confirms backend-only access-model intent and staged RLS hardening plan documentation, but backup posture, current RLS enablement/policies, and production role/key exposure require manual verification in Supabase dashboard/SQL editor.
- Step 54 paper-trading analytics follow-up scoping (docs-only): selected one minimal increment (`win/loss and holding-period summary` for closed paper trades), defined operator questions, current-feasible data dependencies, insufficient-data follow-ups, validation rubric, interpretation-risk reminders, and explicit non-goals without runtime/deployment changes.
- Step 54 review hardening (docs-only): clarified minimal metric formulas/denominators (`flat_count`, `win_rate` N/A handling), deterministic top-contributor ranking basis/tie-break policy, and simplified round-trip pairing limitation wording to reduce analytics interpretation ambiguity.
- Step 55 paper-trade outcome summary implementation: added bounded read-only closed-trade outcome helper from `paper_trades` with deterministic BUY/SELL pairing order (`trade_date`, then `id`) and stable top-contributor ranking tie-break.
- Step 55 operator review surface: Telegram `/outcome_review` now returns closed-trade summary metrics (`closed_trade_count`, `win/loss/flat`, `win_rate`, holding-period stats, top realized winners/losers) with explicit denominator formula and empty-window wording.
- Step 55 guardrail posture: output is review/diagnostic only and remains paper-trading decision-support boundary; no strategy-rule mutation, no attribution redesign, no real-money execution behavior.
- Step 55 platform ownership clarification: GitHub changed code/tests/docs for bounded analytics slice; Railway deployment topology/cron/env/service split remains unchanged.
- Step 55 Post-merge QA Check: pass — focused tests cover empty-window/no-closed-trades, deterministic pairing/order, flat handling, denominator-safe win-rate behavior, and top-contributor tie-break stability.
- Step 55 Post-merge Domain Check: pass — AI HK investing-system alignment and paper-trading-only boundary preserved; interpretation-risk remains documented and output avoids causal/automation claims.
- Step 55 review hotfix: outcome summary date parsing now defensively skips malformed `trade_date` rows instead of failing the whole review path; percentile rank calculation now uses explicit `ceil(...)` nearest-rank math for readability without behavior expansion.
- Step 56 outcome review windowing increment: `/outcome_review` now supports minimal optional bounded grammar (`/outcome_review <days>`) while preserving no-argument default behavior.
- Step 56 deterministic window contract: optional window filter is read-only, anchored to latest available `paper_trades.trade_date` in the fetched snapshot, and applied on paired closed-trade exit `trade_date` so cross-boundary entry lots remain correctly paired.
- Step 56 wording/guardrail continuity: empty-window wording, denominator-safe formula labeling, and review-boundary note are preserved under windowed and non-windowed paths.
- Step 56 docs/help/runbook alignment: operator help text now documents `/outcome_review [days]`, Telegram troubleshooting runbook adds quick usage/window-basis note, and spec/backlog/status wording is synchronized for bounded scope with unchanged analytics/pairing contracts.
- Step 56 platform ownership clarification: GitHub changed bounded command parsing/filtering/tests/docs only; Railway service topology/cron/env/webhook/deployment process remains unchanged.
- Step 56 Post-merge QA Check: pass — focused tests cover no-argument default path, valid window success path, invalid token handling, out-of-range window handling, empty-window wording under window metadata, and help text synchronization.
- Step 56 Post-merge Domain Check: pass — AI HK investing-system decision-support boundary preserved; no analytics-scope expansion, no pairing-contract mutation, no autonomous execution semantics introduced.
- Step 57 operator surface consistency normalization: applied bounded wording consistency updates for `/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review` without changing paper-trading business logic.
- Step 57 stock display policy normalization: operator output now prefers `stock_name + stock_id` and explicitly falls back to `stock_id=<id> | name_unavailable` when name data is unavailable.
- Step 57 wording normalization: usage/invalid-input paths now use explicit `Usage: ...` + `Invalid input: ...` style on affected commands; no-data wording is normalized around `no matching records ...` with command-specific context preserved.
- Step 57 platform ownership clarification: GitHub changed bounded operator rendering/parsing/tests/docs only; Railway topology/cron/env/webhook/deployment process remains unchanged.
- Step 57 Post-merge QA Check: pass — focused tests cover usage/invalid-input wording updates, no-data/empty-window wording, stock-display fallback behavior, and backward-compatible success paths.
- Step 57 Post-merge Domain Check: pass — AI HK investing-system alignment and paper-trading decision-support boundary preserved; no strategy logic/DB schema/deployment topology mutation introduced.
- Step 58 operator runbook examples alignment (docs-only): added `docs/operator-runbook.md` covering compact interpretation examples for `/runs`, `/runner_status`, `/risk_review <run_id>`, `/pnl_review`, `/outcome_review`, `/outcome_review <days>` across normal/no-data/invalid-input paths with paper-trading decision-support boundary reminders.
- Step 58 stock display policy documentation alignment: runbook/spec now explicitly records Step 57 rendering policy (`stock_name=<name> | stock_id=<id>` preferred; fallback `stock_id=<id> | name_unavailable`) and prohibits implying missing stock names.
- Step 58 platform ownership clarification: GitHub changed docs only (`docs/operator-runbook.md`, status/backlog/spec synchronization); Railway service/cron/env/webhook/deployment process remains unchanged.
- Step 58 Post-merge QA Check: pass — docs-only scope verified against Step 57 normalized wording requirements (normal/no-data/invalid-input example coverage and stock-display fallback policy consistency) with no runtime/test behavior mutation.
- Step 58 Post-merge Domain Check: pass — AI HK investing-system alignment and paper-trading/decision-support boundary preserved; no autonomous live-money execution semantics introduced.
- Step 59 daily operator review packet MVP: added read-only `/daily_review` command to produce a short packet integrating existing review surfaces (`runner_status`, `latest_run_id`, `pnl_snapshot`, `outcome_summary`) with explicit section-level partial no-data/internal-error tolerance and unchanged execution/paper-trading boundaries.
- Step 59 platform ownership clarification: GitHub changed command wiring/tests/docs only (`src/telegram_operator.py`, `tests/test_telegram_operator.py`, `docs/operator-runbook.md`, `docs/spec.md`, `docs/status.md`, `docs/backlog.md`); Railway service topology/cron/env/webhook/deployment settings remain unchanged.
- Step 59 Post-merge QA Check: pass — focused tests cover `/daily_review` success path, partial no-data path, helper internal-error path, unauthorized gating parity, and `/help` command-list inclusion.
- Step 59 Post-merge Domain Check: pass — AI HK investing-system alignment preserved; output remains paper-trading decision-support only, does not generate autonomous buy/sell decisions, and introduces no real-money execution semantics.
- Step 60 `/daily_review` v2 usability: added `business_date_hkt`, `latest_run_time_hkt`, deterministic `daily_review_health` (`ok`/`attention_needed`/`internal_error`), `next_action_hint`, and `detail_commands` (`/runner_status`, `/runs`, `/pnl_review`, `/outcome_review`, plus `/risk_review <run_id>` when latest run exists) while keeping output read-only and section-scoped error/no-data tolerance.
- Step 60 platform ownership clarification: GitHub changed bounded operator command/tests/docs only (`src/telegram_operator.py`, `tests/test_telegram_operator.py`, `docs/operator-runbook.md`, `docs/spec.md`, `docs/status.md`, `docs/backlog.md`); Railway service topology/cron/env/webhook/deployment settings remain unchanged.
- Step 60 Post-merge QA Check: pass — focused tests cover new daily-review fields, success path, partial no-data health status, helper internal-error health status, and malformed `/daily_review now` usage behavior.
- Step 60 Post-merge Domain Check: pass — AI HK investing-system alignment preserved; `/daily_review` health/hint fields are review-readiness signals only, command remains read-only decision support, and no autonomous live-money execution semantics are introduced.
- Step 60 follow-up health-rule refinement: `/daily_review` now treats latest runner status `failed`/`unknown` as `attention_needed` even when pnl/outcome sections are available, and `next_action_hint` explicitly points to `/runner_status`, `/runs`, and logs when runner readiness needs attention.
- Step 61 Human Decision Journal Contract v1 (docs-only): defined minimum decision-journal contract for future `/decision_note` covering run-level and stock-level scope, required/recommended fields, value vocabularies (`system_signal`, `human_action`, `confidence`, `reason_tag`), validation rules, outcome-linkage placeholders, and explicit non-execution guardrails.
- Step 61 contract consistency refinement: required fields now explicitly split into user-supplied (`scope`, `run_id`, `human_action`, `note`, `source_command`, plus `stock_id` when `scope=stock`) vs system-generated (`created_at`, plus `operator_user_id_hash_or_label` when available/applicable); `/decision_note` examples now include `source_command`.
- Step 61 platform ownership clarification: GitHub changed docs only (`docs/spec.md`, `docs/operator-runbook.md`, `docs/status.md`, `docs/backlog.md`, `docs/strategy-spec.md`, `docs/project-implementation-plan.md`); Railway service topology/cron/env/webhook/deployment settings remain unchanged.
- Step 61 Post-merge QA Check: pass — docs-only scope verified for contract completeness and cross-doc consistency; no runtime behavior/test/schema mutation.
- Step 61 Post-merge Domain Check: pass — AI HK investing-system alignment preserved; paper-trading decision-support boundary and human-final-decision governance remain explicit; no autonomous live-money execution semantics introduced.

- Step 54 Post-merge QA Check (docs-only scope): pass — scope remains documentation-only, output contract/rubric wording is explicit, and system-of-record docs stay aligned with no runtime behavior mutation.
- Step 54 Post-merge Domain Check (docs-only scope): pass — AI HK investing-system alignment and paper-trading/decision-support-only boundary remain intact; interpretation-risk and limitation statements are explicitly recorded.
- No autonomous live-money execution is enabled; human remains final decision-maker.
- Deploy/config stability note: Railway/Railpack build previously failed when defaulting to Python `3.13.12` (mise install failure path); repository now pins Python to `3.12.9` via `.python-version` as a deploy stability guardrail (no strategy/paper-trading/signal-flow logic change).

## Milestone status
- Milestone 1 (Documentation Foundation): completed.
- Milestone 2 (Signal framework + modularization/test baseline): completed.
- Milestone 3 (Paper-trading v1): completed.
- Milestone 4 (Controlled production hardening): in-progress, with Steps 19–61 completed and runtime hardening follow-ups still pending.

## Step 21–61 status ledger (Step 61 Human Decision Journal Contract v1)

| Step | Goal | Primary deliverable(s) | Status |
|---|---|---|---|
| 21 | Add paper position + PnL foundation | `paper_positions` schema/state refresh + portfolio summary helper | **Completed (merged).** Baseline paper position/PnL foundation is active in current runtime/docs. |
| 22 | Add paper risk guardrails v1 for BUY path | Concentration/allocation/add/cash checks with blocking only for high-risk breaches | **Completed (merged).** Guardrails + follow-up fixes are reflected in current runtime/docs. |
| 23 | Persist risk observability / decision-support record v1 | Structured `risk_evaluation` payload in events + decision ledger fields | **Completed (merged).** Current runtime persists risk context + decision-support records. |
| 24 | Add paper-risk run review read surface | Aggregated per-run risk review helper + normalization | **Completed (merged).** Read-only run risk review surface is available. |
| 25 | Expose operator CLI for paper-risk review | `python -m src.paper_risk_review_cli --run-id <id>` deterministic JSON output | **Completed (merged).** CLI review surface is available for operator diagnostics. |
| 26 | Add beginner paper-risk operator runbook | `docs/operator-runbook-paper-risk-review.md` | **Completed (merged).** |
| 27 | Add beginner Telegram troubleshooting runbook | `docs/operator-runbook-telegram-troubleshooting.md` | **Completed (merged).** |
| 28 | Add beginner daily review summary helper | `get_paper_daily_review_summary_for_run(...)` + focused tests/fix | **Completed (merged).** |
| 29 | Add Telegram outcome quick reference | `docs/operator-quick-reference-telegram-outcomes.md` (+ doc tightening follow-up) | **Completed (merged).** |
| 30 | Docs maintenance + project state alignment | Refreshed status/backlog/plan + architecture/runtime alignment docs | **Completed (merged).** |
| 31 | Telegram message readability improvement | Summary readability uplift (`stock`, `signal/action`, `key_reason/indicator`, `risk_note`) + focused tests | **Completed (merged).** |
| 32 | Telegram operator run-id lookup command | `/runs` command (+ usage hardening, schema-safe run metadata lookup hotfix) | **Completed (merged).** |
| 33 | Telegram operator help command discoverability | `/help` + `/h` handlers with guardrails/usage guidance | **Completed (merged).** |
| 34A | Telegram inbound webhook integration foundation | Dedicated webhook ingress + logging + setup runbook + optional secret verification hardening | **Completed (merged).** |
| 34A-doc-hotfix | Webhook setup doc optional-secret clarification | Clear with-secret vs without-secret `setWebhook` examples | **Completed (merged).** |
| 34A-msg-hotfix | Telegram help message HTML-safe placeholder formatting | Bracket-safe usage placeholders + focused tests | **Completed (merged).** |
| 34B | Telegram `/risk_review` command + Railway variable docs | Guardrailed `/risk_review [run_id]` path + `docs/railway-service-variables.md` | **Completed (merged).** |
| 34B-review-hotfix | Webhook/operator exception isolation for `/risk_review` | Failure isolation + sanitized response behavior + focused tests | **Completed (merged).** |
| 34B-test-hotfix | Lazy-load `/risk_review` dependency for test stability | Reduced import-time coupling for operator tests | **Completed (merged).** |
| 35 | Split Railway deployment into webhook + runner services | Dual-service topology docs, start commands, cron ownership, service-scoped variable guidance | **Completed (merged).** |
| 37 | Dedicated daily runner entrypoint + HK schedule codification | `python -m src.daily_runner`, deterministic exit/log behavior, HKT 20:00 baseline (`0 12 * * *` UTC) | **Completed (merged).** |
| 38 | Daily runner execution-summary observability hardening | Lifecycle log contract + execution summary JSON + failure-safe summary | **Completed (merged).** |
| 38-review-hotfix | Runner failure-summary normalization hardening | Single-line normalized failure summaries + focused coverage | **Completed (merged).** |
| 39 | Telegram `/runner_status` operator command | Guardrailed latest-run read surface + safe fallback/failure behavior | **Completed (merged).** |
| 39-review-hotfix | `/runner_status` timezone parsing normalization | Naive timestamp -> UTC normalization for deterministic output | **Completed (merged).** |
| 39-review-hotfix-html | `/runner_status` HTML-safe error-summary output | HTML-safe `error_summary` rendering + focused coverage | **Completed (merged).** |
| 39-review-hotfix-html-followup | `/runner_status` additional dynamic-field HTML safety | HTML-safe `status` / `run_id` rendering + focused coverage | **Completed (merged).** |
| 40 | Operator response format + HTML-safe rendering contract | Shared operator response shape + centralized dynamic escaping + focused tests | **Completed (merged).** Follow-up now tracked only as docs/ops clarity work (no runtime delta in this step). |
| 41 | Paper-trading position/PnL review snapshot v1 | Read-only snapshot helper + `/pnl_review` + input/correctness hardening | **Completed (merged).** |
| 42 | Market data provider boundary v1 | Provider protocol/registry (`MARKET_DATA_PROVIDER`) + `yfinance` default + deterministic `mock` provider | **Completed (merged).** Current production default remains `yfinance`; `mock` is local/test-oriented. |
| 43 | Human-facing HKT timestamp normalization + operator clarity hardening | Display-layer HKT normalization for operator/review commands with storage semantics unchanged | **Completed (merged).** |
| 44 | Status/docs/backlog consistency + deployment/config hardening docs | Align status wording with merge reality; clarify webhook vs runner topology, HKT baseline, provider/mock policy, read-only review surfaces, and GitHub vs Railway responsibilities | **Completed (merged in-repo docs state).** Runtime behavior/API/schema/strategy unchanged. |
| 45 | Dedup/delivery semantics documentation validation + operator expectation clarification | Document current Telegram/operator delivery reality (dedup/retry/rerun/duplicate semantics), define operator expectation baseline, and update backlog/state for unresolved follow-ups | **Completed (merged in-repo docs state).** Docs-only clarification; runtime/API/schema/strategy unchanged. |
| 46 | Delivery semantics observability evidence pass | Add scenario-based evidence checklist + operator validation guidance + observability gap analysis (known reality vs evidence vs unresolved gaps vs future follow-up), and sync system-of-record docs | **Completed (merged in-repo docs state).** Docs-only scope; no runtime behavior/API/schema/strategy/deployment topology change. |
| 47 | Delivery semantics runtime instrumentation scoping proposal | Prioritize delivery observability gaps, evaluate minimal instrumentation candidates with value/risk/scope, codify explicit no-implementation guardrails, and sync docs/backlog ownership split (GitHub vs Railway) | **Completed (merged in-repo docs state).** Docs-only scope; no runtime behavior/API/schema/strategy/deployment topology change. |
| 48 | Delivery semantics minimal runtime instrumentation v1 | Implement `correlation_id` + `dedup_check_result` in daily summary telemetry and `runs.delivery_summary_json` projection, add focused send/skip/fallback tests, and sync docs/backlog/status ownership notes | **Completed (merged in-repo runtime+docs state).** Minimal observability increment only; no DB migration, no queue/retry framework, no Telegram send-path refactor, no strategy/paper-trading logic or deployment topology change. |
| 49 | Delivery semantics follow-up instrumentation scope refinement | Reassess post-Step-48 observability gaps, compare `dedup_persist_result` vs `delivery_phase` (value/risk/scope/complexity/operator payoff), select one next slice, and sync docs/backlog/status/implement with GitHub-vs-Railway ownership split | **Completed (merged in-repo docs state).** Docs-only scope; no runtime behavior change, no telemetry/schema mutation, no send-path refactor, no queue/retry framework, no strategy/paper-trading logic or deployment topology change. |
| 50 | Delivery semantics minimal runtime instrumentation v2 | Add one bounded telemetry field `dedup_persist_result` (`persisted`/`persist_failed`/`not_applicable`) to summary telemetry and `runs.delivery_summary_json` projection, add focused tests, and sync docs/backlog/status/implement with GitHub-vs-Railway ownership split | **Completed (merged in-repo runtime+docs state).** Single-field observability increment only; no `delivery_phase`, no DB migration, no queue/retry framework, no Telegram send-path refactor, no strategy/paper-trading logic or deployment topology change. |
| 50-review-hotfix | Step 50 testability hardening in constrained environments | Add `tests/conftest.py` import-time dependency stubs for optional runtime packages (`requests`, `supabase`, `pandas`, `yfinance`) so focused Step 50 tests execute without network/package-install preconditions | **Completed (merged in-repo test-harness state).** Test-environment-only adjustment; production runtime behavior, Telegram delivery semantics, strategy logic, and deployment topology unchanged. |
| 51 | Formalize post-merge dual acceptance workflow in docs and status discipline | Update AGENTS/plans/implement/status/backlog/project-plan docs to mandate Post-merge QA + Post-merge Domain checks, define blocker vs backlog-follow-up triage, and codify status-vs-backlog wording roles (`repo merge completed`, `manual platform acceptance completed`, `docs maintenance follow-up`) | **Completed (merged in-repo docs state).** Docs-only governance formalization; no runtime behavior/API/schema/strategy/deployment change. |
| 52 | Test-harness pandas stub coverage fix for market-data/signals tests | Update `tests/conftest.py` pandas fallback shim to cover required API surface (`date_range`, `DataFrame(...)`, `.empty`, rolling mean, indexing) and only activate when pandas is unavailable | **Completed (merged in-repo test-harness state).** Test-only harness correction; production runtime behavior/API/schema/strategy/paper-trading/deployment topology unchanged. |
| 53 | Platform hardening evidence pass (GitHub / Railway / Supabase) | Add docs-first evidence summary + manual verification checklist with explicit classification (`repo-confirmed`, `manual verification required`, `backlog follow-up`) and sync status/backlog/project-plan records | **Completed (merged in-repo docs state).** Docs-only evidence refresh; no runtime behavior/API/schema/strategy/paper-trading/deployment topology change. |
| 54 | Paper-trading analytics follow-up scoping | Define one minimal paper-trading analytics increment (`win/loss and holding-period summary` for closed trades), dependency map, validation rubric, interpretation-risk reminders, and non-goals with docs-first bounded scope | **Completed (merged in-repo docs state).** Docs-only scoping; no runtime behavior/API/schema/strategy/paper-trading/deployment topology change. |
| 54-review-hardening | Paper-trading analytics scoping rubric precision pass | Tighten metric-definition contract (denominator clarity, flat outcome handling, ranking basis/tie-break, simplified pairing limitation wording) to reduce future implementation ambiguity | **Completed (merged in-repo docs state).** Docs-only wording hardening; no runtime/API/schema/strategy/paper-trading/deployment topology change. |
| 55 | Paper-trade outcome summary implementation (bounded) | Implement read-only closed-trade outcome summary helper + `/outcome_review` operator surface with deterministic pairing/order, empty-window + denominator-safe wording, stable top-contributor tie-break, and focused tests | **Completed (merged in-repo runtime+docs state).** Bounded analytics/review increment only; no DB migration, no strategy-rule change, no attribution redesign, no real-money execution path, no deployment topology change. |
| 55-review-hotfix | Step 55 robustness/readability hardening | Defensive `trade_date` parsing skip for malformed historical rows + explicit nearest-rank percentile math (`ceil`) + focused malformed-date test coverage | **Completed (merged in-repo runtime+docs state).** Read-only analytics hardening only; no schema/deployment/strategy/real-money behavior change. |
| 56 | Outcome review windowing + runbook alignment (bounded) | Add minimal `/outcome_review <days>` optional windowing with bounded integer validation, deterministic `trade_date` window filtering, focused tests, and help/spec/status/backlog wording sync | **Completed (merged in-repo runtime+docs state).** Bounded read-only review enhancement only; no analytics-scope expansion, no pairing-contract change, no schema/deployment topology change. |
| 57 | Operator surface consistency check + wording normalization (bounded) | Perform minimal consistency/wording normalization for `/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review`, apply explicit stock-display fallback policy, add focused tests, and sync docs/spec/status/backlog | **Completed (merged in-repo runtime+docs state).** Bounded operator-clarity increment only; no new commands/analytics type, no strategy logic change, no DB schema change, no deployment topology change. |
| 58 | Operator runbook examples alignment for normalized Telegram command output (docs-only) | Add/update operator runbook examples for `/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review` normal/no-data/invalid-input interpretations + Step 57 stock-display policy documentation sync across spec/status/backlog | **Completed (merged in-repo docs state).** Docs-only scope; no runtime behavior/test/schema/strategy/deployment topology change. |
| 59 | Daily operator review packet MVP | Add read-only `/daily_review` Telegram command that aggregates short section statuses (`runner_status`, `latest_run_id`, `pnl_snapshot`, `outcome_summary`) with partial no-data/internal-error tolerance, plus focused tests and docs sync | **Completed (merged in-repo runtime+docs state).** Bounded operator review aggregation only; no strategy logic/paper-trading calculation/DB schema/deployment topology mutation. |
| 60 | `/daily_review` v2 usability | Add read-only operator-review usability fields (`business_date_hkt`, `latest_run_time_hkt`, `daily_review_health`, `next_action_hint`, `detail_commands`) with deterministic section-status-based health rules, while preserving command-level completion and section-scoped failure tolerance | **Completed (merged in-repo runtime+docs state).** Bounded operator usability enhancement only; no DB schema/strategy logic/paper-trading calculation/Railway topology mutation. |
| 61 | Human Decision Journal Contract v1 (docs-first) | Define minimum future `/decision_note` contract for run-level + stock-level decision journaling, including required/recommended fields, allowed vocabularies, validation rules, non-execution guardrails, and future storage concept; synchronize runbook/backlog/plan/status docs | **Completed (merged in-repo docs state).** Docs-only scope; no runtime code/schema/strategy/deployment topology mutation. |

## Known unknowns / needs confirmation
- Production platform settings (GitHub/Railway/Supabase project posture) still require periodic manual verification outside repository files.

## Recent completion notes
- Step 62 `/decision_note` runtime MVP implemented (run-level only), with explicit journaling-only boundary and stock-level not-implemented response.
- Step 62 platform ownership: GitHub runtime/tests/docs + Supabase table migration; Railway no change.
- Step 62 Post-merge QA Check: pass (local focused tests for success/validation/auth/help coverage).
- Step 62 Post-merge Domain Check: pass (decision-support journaling only; no execution/broker/live trading).

- Step 63 Telegram Operator QA Harness MVP: added manual GitHub Actions smoke-test workflow (`workflow_dispatch` only) and script-based webhook command checks for `/help`, `/daily_review`, and `/decision_note` success/validation/not-implemented paths; reports are emitted as markdown/json artifacts with short retention and explicit no-execution guardrail confirmation.
- Step 63 platform ownership: GitHub changed script/workflow/docs only; Railway service topology/cron/env/webhook routing unchanged; Supabase schema unchanged (optional verification deferred).
- Step 63 Post-merge QA Check: pending manual GitHub Actions workflow run against configured webhook test endpoint and artifact review.
- Step 63 Post-merge Domain Check: pending post-merge review confirmation (expected scope remains manual QA harness only with no strategy/paper-trading/runtime execution-path mutation).
- Step 64 Telegram Operator QA Harness coverage expansion: extended smoke command set to include `/runs`, `/runner_status`, `/risk_review <test_run_id>`, `/pnl_review`, and `/outcome_review` while preserving Step 63 cases; report contract now explicitly separates `transport_verification` from `response_text_verification=SKIPPED_current_webhook_contract`.
- Step 64 platform ownership: GitHub changed script/tests/workflow wording/docs only; Railway service topology/cron/env/webhook routing unchanged; Supabase schema/row verification unchanged (Step 65 deferred).
- Step 64 Post-merge QA Check: pending post-merge manual workflow acceptance (GitHub Actions `workflow_dispatch` run + artifact review against configured webhook endpoint).
- Step 64 Post-merge Domain Check: pending post-merge review confirmation (expected scope remains QA-harness-only transport verification with no strategy/paper-trading/runtime execution-path mutation).
- Step 65 Supabase verification layer for Operator Smoke Test: added optional DB persistence verification for `/decision_note` run-level journal row when `verify_supabase=true`, including per-run `qa_marker` injection and read-only Supabase query on `human_decision_journal_entries`; default `verify_supabase=false` remains `SKIPPED` with no DB requirement.
- Step 65 platform ownership: GitHub changed script/tests/workflow/docs only; Supabase schema unchanged with read-only query usage only; Railway service topology/cron/env/webhook routing unchanged.
- Step 65 Post-merge QA Check: pass — manual Operator Smoke Test completed with `verify_supabase=true`; transport checks passed; Supabase verification accepted; artifact/report produced.
- Step 65 Post-merge Domain Check: pass — paper-trading / decision-support boundary preserved; no broker/live-money execution, no strategy logic change, no paper-trading calculation change, no Railway topology change, and no Supabase schema change.

- Step 66 checklist formalization (docs-only): created `docs/post-deploy-acceptance-checklist.md` and aligned runbook/status/backlog/project-plan wording so future runtime/Telegram/DB/paper-trading PRs must declare required post-deploy QA coverage explicitly.
- Step 66 platform ownership: GitHub docs/workflow-governance wording only; Railway settings unchanged; Supabase schema unchanged.
- Step 66 Post-merge QA Check: pass — docs-only checklist formalization merged; post-deploy acceptance checklist, operator runbook flow, and backlog/status/project-plan wording were aligned; no runtime behavior changed.
- Step 66 Post-merge Domain Check: pass — AI HK investing-system alignment preserved; checklist reinforces paper-trading / decision-support-only boundary, human final decision authority, and no broker/live-money execution guardrail.
- Step 68 Stock-level Decision Journal MVP: completed/accepted — stock-level `/decision_note` merged with post-merge Operator Smoke Test (`verify_supabase=true`) evidence and decision-support boundary preserved.
- Step 68 Post-merge QA Check: pass — stock-level `/decision_note` runtime was merged and accepted with manual Operator Smoke Test using `verify_supabase=true`; run-level and stock-level decision journal smoke cases passed; artifact/report was produced.
- Step 68 Post-merge Domain Check: pass — stock-level decision journal remained paper-trading / decision-support only; no broker integration, no live-money execution, no strategy logic change, no paper-trading calculation change, no Railway topology change, and no Supabase schema migration.


## Next approved task candidate
- Step 67 scheduled daily health check remains future plan only; do not implement scheduled automation until explicitly approved in a future step.


- Step 68 completed/accepted: stock-level `/decision_note` runtime MVP merged and accepted with post-merge Operator Smoke Test (`verify_supabase=true`) evidence.
- Step 69 repo merge completed: yes.
- Step 69 manual platform acceptance completed: yes.
- Step 69 Post-merge QA Check: pass.
- Step 69 Post-merge Domain Check: pass.
- Step 70 in progress: GitHub / Codex instruction guardrails update (docs-only), PR pending.
- Step 70 Post-merge QA Check: pending (must be recorded only after merge).
- Step 70 Post-merge Domain Check: pending (must be recorded only after merge).
- Step 71 repo merge completed: yes.
- Step 71 manual platform acceptance completed: yes.
- Step 71 Post-merge QA Check: pass — Mini App read-only static shell merged; static contract test present; shell remains static/mock with no form/button controls, no production Supabase read, no backend endpoint, no Railway setting change, no vendor SDK, and no broker/live execution.
- Step 71 Post-merge Domain Check: pass — Phase 1 UI remains read-only paper-trading / decision-support review surface only; no write action, no strategy change, no paper order creation, human final decision preserved, and real-money execution stays outside the system.
- Step 72 recommendation (docs decision): use dedicated Railway static site/static service as default Phase 1 preview path; keep shell read-only/no-data/no-write/no-vendor/no-broker boundary.
- Step 72 security boundary reminder: browser/client must not hold `SUPABASE_SERVICE_ROLE_KEY` or vendor secrets; future data access must validate Telegram `initData` server-side.
- Step 72 repo merge completed: yes (PR #70 merged).
- Step 72 manual platform acceptance completed: yes (docs-only decision step; no Railway runtime mutation in-step).
- Step 72 Post-merge QA Check: pass.
- Step 72 Post-merge Domain Check: pass.
- Step 73 repo merge completed: yes (PR #71 merged).
- Step 73 manual platform acceptance completed: yes.
- Step 73 preview URL: https://miniapp-static-preview-production.up.railway.app/
- Step 73 Post-merge QA Check: pass — Railway `miniapp-static-preview` (Root Directory `/miniapp`) rendered successfully; no deployment errors/logs observed; no env vars added; no Supabase production read observed; no write action/order creation observed; `telegram-webhook` unaffected; `paper-daily-runner` unaffected.
- Step 73 Post-merge Domain Check: pass — Mini App preview remains Phase 1 static read-only mock/placeholder shell with paper-trading / decision-support-only boundary, no broker connection, and no real-money execution path.

- Step 75 planning kickoff (docs-only): defined Mini App read-only data surface boundary plan in `docs/miniapp-readonly-data-boundary.md` (recommended backend-mediated auth/data path, explicit rejected paths, candidate read-only sections, deferred scope, conceptual response contract, and future implementation acceptance criteria).
- Step 75 dependency reminder: Mini App next phase remains blocked on server-side Telegram `initData` validation + authorization boundary before any production data-enabled read path.
- Step 75 scope boundary: no runtime API/auth/Supabase schema/RLS/Mini App fetch/write changes; webhook + daily runner remain unaffected in this step.

- Step 76 repo merge target: backend-only Telegram Mini App `initData` validation helper + focused tests (no API endpoint / no Supabase integration / no Mini App frontend changes).
- Step 76 scope boundary: validation utility prerequisite only; production data-enabled Mini App read remains blocked until endpoint wiring + operator authorization + bounded response contract acceptance are completed.
- Step 76 platform ownership: GitHub runtime helper/tests/docs changes only; Railway unchanged; Supabase unchanged.
