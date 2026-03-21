# Project Status

## Last reviewed date
2026-03-21

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
- Step 33 operator-help uplift: Telegram `/help` and `/h` now return a compact bilingual usage guide that covers system scope, guardrails, and command list (`/runs`, `/runs <days>d`, `/help`, `/h`).
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
- No autonomous live-money execution is enabled; human remains final decision-maker.
- Deploy/config stability note: Railway/Railpack build previously failed when defaulting to Python `3.13.12` (mise install failure path); repository now pins Python to `3.12.9` via `.python-version` as a deploy stability guardrail (no strategy/paper-trading/signal-flow logic change).

## Milestone status
- Milestone 1 (Documentation Foundation): completed.
- Milestone 2 (Signal framework + modularization/test baseline): completed.
- Milestone 3 (Paper-trading v1): completed.
- Milestone 4 (Controlled production hardening): in-progress, with Steps 19–33 completed and follow-up hardening still pending.

## Step 21–37 status ledger (Step 37 dedicated daily runner entrypoint + HK schedule codification)

| Step | Goal | Primary deliverable(s) | Merge / acceptance status |
|---|---|---|---|
| 21 | Add paper position + PnL foundation | `paper_positions` schema/state refresh + portfolio summary helper | **Repo evidence:** completed in current code/docs. **Manual acceptance:** unknown / needs confirmation. |
| 22 | Add paper risk guardrails v1 for BUY path | Concentration/allocation/add/cash checks with blocking only for high-risk breaches | **Repo evidence:** completed (plus documented post-review fixes). **Manual acceptance:** unknown / needs confirmation. |
| 23 | Persist risk observability / decision-support record v1 | Structured `risk_evaluation` payload in events + decision ledger fields | **Repo evidence:** completed (including BUY executed context follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 24 | Add paper-risk run review read surface | Aggregated per-run risk review helper + normalization | **Repo evidence:** completed (including normalization follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 25 | Expose operator CLI for paper-risk review | `python -m src.paper_risk_review_cli --run-id <id>` deterministic JSON output | **Repo evidence:** completed (including output-shape follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 26 | Add beginner paper-risk operator runbook | `docs/operator-runbook-paper-risk-review.md` | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 27 | Add beginner Telegram troubleshooting runbook | `docs/operator-runbook-telegram-troubleshooting.md` | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 28 | Add beginner daily review summary helper | `get_paper_daily_review_summary_for_run(...)` + focused tests/fix | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 29 | Add Telegram outcome quick reference | `docs/operator-quick-reference-telegram-outcomes.md` (+ doc tightening follow-up) | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 30 | Docs maintenance + project state alignment | Refreshed `docs/status.md`, `docs/backlog.md`, `docs/project-implementation-plan.md`, and runtime/data-flow alignment in architecture docs | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 31 | Telegram message readability improvement | Telegram summary formatting now separates `stock` / `signal/action` / `key_reason/indicator`, keeps `stock_name + stock_id`, adds explicit run-level `risk_note`, and adds focused message-format tests | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 32 | Telegram operator run-id lookup command | Added operator `/runs` command handler (default 5-day window, optional `/runs <days>d`) backed by durable `runs` table query with chat/user guardrail and focused tests | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 33 | Telegram operator help command discoverability | Added `/help` and `/h` operator handlers (same response), with bilingual scope/guardrail copy and command usage summary; added focused alias/content tests and kept `/runs` behavior unchanged | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34A | Telegram inbound webhook integration foundation | Added dedicated Telegram webhook ingress route (`POST /telegram/webhook`) wired to existing operator command handler and reply path; added minimal ingress/auth/send logging + setup runbook (`docs/telegram-webhook-setup.md`) with review hardening for optional webhook secret verification + explicit infra error responses | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34A-doc-hotfix | Webhook setup doc optional-secret clarification | Split runbook `setWebhook` into with-secret vs without-secret examples; explicitly documented that `TELEGRAM_WEBHOOK_SECRET_TOKEN` is optional and marked “fix webhook setup doc so optional secret token is truly optional” as completed | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34A-msg-hotfix | Telegram help message HTML-safe placeholder formatting | Replaced operator command placeholder angle brackets with bracket-safe text (for example `/runs [days]d`) in runtime help/usage responses and added focused test coverage (including malformed `/runs` usage text) to prevent parse-mode regressions | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34B | Telegram `/risk_review` operator command + Railway service-variable documentation | Added `/risk_review [run_id]` handler path with allowlist/auth guardrail, strict input validation, run existence checks, synchronous paper-risk review summary response, failure sanitization, and focused tests; added deployment variable reference doc `docs/railway-service-variables.md` and related doc/status updates | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34B-review-hotfix | Webhook/operator exception isolation hardening for `/risk_review` | Added defensive exception isolation around operator handler + run-lookup path so failures are logged and sanitized in Telegram response without crashing webhook processing; added focused tests for handler-exception and lookup-failure sanitization paths | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 34B-test-hotfix | Operator command dependency lazy-load for test execution stability | Refactored `/risk_review` path to lazy-load paper-risk helper dependency at execution time (instead of module import time), reducing hard dependency coupling and enabling focused operator/webhook tests in constrained environments | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 35 | Split Railway deployment into webhook service + scheduled runner service (same repo) | Added deployment/docs guidance for dual-service topology, explicit service responsibilities, start commands, cron ownership (`0 12 * * *` runner-only), and service-scoped variable reference (`shared` / `webhook-only` / `runner-only`) | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |
| 37 | Introduce dedicated daily runner entrypoint + codify HK business schedule | Added `src.daily_runner` as scheduled entrypoint (`python -m src.daily_runner`) with startup/completion/failure logging + deterministic exit codes, kept `main.py` backward-compatible wrapper, added focused runner success/failure smoke coverage, and documented HKT 20:00 target with Railway UTC cron mapping (`0 12 * * *`) across deployment docs | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |

## Known unknowns / needs confirmation
- Exact PR numbers and explicit human acceptance timestamps for Steps 21–29 are not derivable from repository files alone and need manual confirmation.
- Production platform settings (GitHub/Railway/Supabase) still require periodic manual verification outside repo state.

## Next approved task candidate
- Step 38 candidate: platform/documentation hardening follow-up focused on remaining active backlog items (dedup semantics docs validation, platform hardening checklist closure, and paper-trading analytics follow-up scoping) without strategy/runtime behavior changes unless explicitly approved.
