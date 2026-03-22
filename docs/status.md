# Project Status

## Last reviewed date
2026-03-22

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
- No autonomous live-money execution is enabled; human remains final decision-maker.
- Deploy/config stability note: Railway/Railpack build previously failed when defaulting to Python `3.13.12` (mise install failure path); repository now pins Python to `3.12.9` via `.python-version` as a deploy stability guardrail (no strategy/paper-trading/signal-flow logic change).

## Milestone status
- Milestone 1 (Documentation Foundation): completed.
- Milestone 2 (Signal framework + modularization/test baseline): completed.
- Milestone 3 (Paper-trading v1): completed.
- Milestone 4 (Controlled production hardening): in-progress, with Steps 19–45 completed and follow-up hardening/documentation validation still pending.

## Step 21–45 status ledger (Step 45 dedup/delivery semantics docs validation)

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

## Known unknowns / needs confirmation
- Production platform settings (GitHub/Railway/Supabase project posture) still require periodic manual verification outside repository files.

## Next approved task candidate
- Step 46 candidate: delivery semantics observability evidence pass (operator checklist + validation plan, docs-first unless a concrete runtime defect is proven).
