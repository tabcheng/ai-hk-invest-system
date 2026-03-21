# Project Status

## Last reviewed date
2026-03-15

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py` (Railway entry point), now as a thin entry into modularized runtime code under `src/`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- Run-level observability is preserved via a `runs` table lifecycle (`RUNNING` at start, terminal `SUCCESS`/`FAILED` at finish) without changing ticker processing scope.
- End-to-end run traceability is hardened: `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, and `notification_logs` now persist `run_id` linkage for single-run reconstruction.
- Run observability now separates failure categories (`ticker`, `post-processing`, `notification`) with per-category counts and summaries on `runs`.
- Run observability now also persists structured JSON payloads for categorized errors and Telegram delivery telemetry (`error_summary_json`, `delivery_summary_json`) while preserving legacy text summaries for compatibility.
- Delivery telemetry now models one daily-summary message attempt per run (not per ticker), and dedup skips are tracked as `skipped` rather than failed sends.
- Paper-trading v1 remains deterministic and gated to full ticker-success runs.
- Paper-trading events and decision records now support compact structured `risk_evaluation` metadata (`allowed`, `severity`, `summary_message`, `rule_results`) for review traceability, including blocked BUY guardrail, already-holding add-check paths, and executed BUY outcomes (info/warning visibility).
- Paper-trading risk read-surface/reporting v1 now provides a compact per-run review helper that summarizes persisted BUY risk outcomes (`blocked`/`warning`/executed) and groups per-ticker review rows (`event_type`, `severity`, `summary_message`, compact rule summary) without log parsing.
- Telegram daily summary remains best-effort and non-blocking.
- Telegram summary formatting is deterministic HTML and includes stock name + stock id labels.
- Telegram daily summary now uses a versioned internal payload schema (`schema_version: 1`) with renderer separation (payload build -> render -> send).
- Notification schema evolution now has explicit runtime guardrails: a current version constant, supported-version allowlist, centralized renderer dispatch map, guardrail consistency validation, and fail-fast unsupported handling.
- Daily-summary equity prefers run-date snapshots with explicit fallback labeling to latest snapshot when run-date data is unavailable.
- Daily-summary notifications include minimal cross-run dedup persistence so the same run-date summary is not repeatedly re-sent to the same target.
- Paper-trading decision ledger v1 is now persisted in `paper_trade_decisions`, explicitly separating AI signal action from human decision state with both `stock_id` and `stock_name` retained.
- Paper-trading now also maintains a lightweight `paper_positions` state table (long-only) refreshed from simulated trades, with weighted-average cost and realized/unrealized PnL fields plus a reusable portfolio summary read helper.
- Paper-trading risk guardrails v1 now evaluate candidate BUY trades pre-execution (single-position concentration, daily new-allocation budget, add-to-existing exposure, and cash-floor/sufficiency) and block only explicit high-risk breaches while remaining paper-only decision support.
- No autonomous live-trading execution is enabled.
- The human user remains the final decision-maker for all real trade actions.

## Current progress
- Milestone 1 (Documentation Foundation): completed and validated; required docs remain in place and workflow rules are preserved.
- Milestone 2 (Signal framework + modularization/test baseline): completed with preserved runtime strategy semantics.
- Milestone 3 (Paper-trading v1): completed with deterministic persistence and rerun-safe same-day behavior.
- Milestone 4 Telegram delivery hardening: completed through deterministic summary format upgrade, run-date equity preference, and minimal cross-run dedup support.
- Documentation system-of-record maintenance review #1 completed with refreshed `docs/backlog.md` and `docs/status.md` alignment.
- Follow-up review fixes applied to notification hardening: redacted dedup log target, idempotent dedup marker upsert for rerun races, and unknown-ticker label fallback.
- Milestone 4 traceability hardening completed: run-linked persistence added for major outputs plus category-separated run failure observability.
- Post-review fix applied: notification delivery failures now enrich run observability fields without changing terminal run status semantics for core processing outcomes.
- Post-review fix applied: same-day rerun signal dedup now re-links existing `(date, stock)` signal rows to the current `run_id`, and intentionally disabled Telegram delivery no longer contributes notification failure counts.
- Follow-up traceability guardrail added: rerun signal relink path updates `run_id` only (not signal values), with test coverage for duplicate rows when `run_id` is absent.
- Step 15 completed: structured run observability JSON and delivery telemetry are now written best-effort during run finalization without changing signal/dedup/runtime semantics.
- Post-review Step 15 fix: run finalization now always persists delivery telemetry in the terminal run update (including successful notifications) while preserving non-blocking observability semantics.
- Post-review Step 15 fix: delivery telemetry schema is now explicitly message-attempt based in both notification output and run payload normalization (no ticker-level message list), with dedup skips counted as `skipped` not `failed`.
- Step 16 completed: added a conservative root `pytest.ini` for stable discovery and a GitHub Actions `tests` workflow that gates `pull_request` and `push` to `main` with `pytest`.
- Step 17 completed: introduced daily summary payload schema v1, schema-versioned renderer dispatch, and delivery telemetry context field `summary_schema_version` while preserving existing notification runtime semantics.
- Step 18 completed: codified schema evolution guardrails (current/supported version constants + centralized dispatch + fail-fast unsupported/misconfigured versions) and expanded tests/docs coverage without changing v1 send behavior.
- Post-review Step 17 fix: strengthened notification test guardrails with unsupported-schema renderer coverage and low-risk test cleanup (spacing/readability) without runtime behavior changes.
- Post-review Step 16 fix: CI now pins Python 3.10 (matching current repo test runtime) and enables pip caching for faster, more stable dependency installs without changing test behavior.
- Step 19 completed: added an operational baseline hardening pass in docs for GitHub, Railway, and Supabase (branch protection/status checks/security scanning, worker healthcheck posture, env/log hygiene, backup/PITR + RLS/free-tier risk expectations) with manual-action tasks tracked in backlog.
- Step 19B completed: clarified Supabase backend-only access model, documented core table inventory + current RLS-off posture, and defined a staged low-risk RLS hardening sequence starting with single-table rollout (`public.runs`) before wider adoption.
- Step 20 completed: added paper-trading decision ledger v1 (`paper_trade_decisions`) with run-linked AI signal + human decision records, plus minimal validation-backed helper integration and focused tests.
- Post-review Step 20 fix: extracted decision-ledger app integration into a dedicated best-effort helper, tightened payload validation guardrails for required text fields and numeric `signal_score`, and expanded app/ledger tests for metadata mapping and non-blocking ledger-write failures.
- Step 21 completed: added paper portfolio position/PnL foundation with `paper_positions` schema, long-only position state refresh after simulated trades, weighted-average cost updates across repeated buys, quantity reduction on sells, and a reusable `get_paper_portfolio_summary` helper for downstream reporting surfaces.
- Post-review Step 21 fix: prior-state reconstruction is now date-correct for reruns/backfills by rebuilding strictly from `paper_trades` rows before `trade_date`, and position refresh uses ticker upsert + stale-row cleanup while explicitly refreshing `updated_at` on each write.
- Post-review Step 21 test hardening: added explicit assertions for strict `< trade_date` prior-state filtering and stale-ticker cleanup in position refresh to lock rerun correctness and deterministic state deletion behavior.
- Step 22 completed: added paper-trading risk guardrails v1 via a dedicated pure evaluation module and integrated BUY pre-trade checks for concentration, daily allocation, add exposure, and cash floor/sufficiency with focused allowed/warning/blocked test coverage.
- Step 23 completed: added risk observability / decision-support record v1 by introducing a compact risk payload helper, attaching structured risk metadata to relevant paper events, extending decision-ledger payload support, and adding migration/tests for persisted `risk_evaluation` JSONB fields.
- Post-review Step 23 fix: successful BUY executions now emit `BUY_EXECUTED` paper events carrying normalized risk-evaluation payloads so allowed `info`/`warning` outcomes are persisted consistently alongside blocked/skip contexts.
- Step 24 completed: added a dedicated paper-risk review summarizer for single-run read surfaces, driven by persisted `paper_events.risk_evaluation` payloads with compact grouped output and focused formatting/grouping tests.
- Post-review Step 24 fix: run-level review summarization now normalizes persisted risk payloads (including unknown severities) before grouping/counting so read-surface outputs stay schema-stable.
- Step 25 completed: exposed a minimal operator-facing paper-risk read path via a dedicated CLI module (`python -m src.paper_risk_review_cli --run-id <id>`) that reuses `get_paper_risk_review_for_run(...)` and emits compact deterministic JSON from persisted `paper_events` risk payloads.
- Post-review Step 25 fix: CLI output now preserves a deterministic per-ticker mapping shape (instead of list-wrapped ticker objects), sorts review rows for stable ordering, and pins `run_id` to the requested CLI input for schema-stable operator exports.
- Post-review Step 22 fix: existing-position BUY-skip path now runs explicit add-exposure risk evaluation for decision-support context (without changing non-additive paper-trading behavior), with added tests for add-limit blocking and skip-event risk context.
- Post-review Step 22 fix #2: concentration guardrail valuation now uses mark-based position pricing (not average entry cost) so unrealized gain/loss is reflected in projected weights, with tests covering gain-allowed vs loss-blocked scenarios.
- Post-review Step 22 fix #3: concentration projected-weight denominator now uses post-trade equity (`total_equity - BUY fee impact`) to avoid understated concentration under high-fee assumptions; added focused unit coverage.
- Step 26 completed: added a beginner-friendly operator runbook for paper-risk review workflow with plain-language system overview, daily step-by-step usage, `run_id` explanation, CLI command usage (`python -m src.paper_risk_review_cli --run-id <id>`), output field interpretation (`total_blocked_buys`, `total_warning_buys`, `total_executed_buys`, `per_ticker`), and short troubleshooting guidance.
- Step 27 completed: added a beginner-friendly operator Telegram notification troubleshooting runbook (`docs/operator-runbook-telegram-troubleshooting.md`) covering simple checks for run completion, notify-worthy output, env-var configuration, bot/chat reachability, and skip/dedup/failure classification, plus an escalation checklist to separate “no signal,” “no notification needed,” and “delivery failure.”
- Step 28 completed: added a beginner-friendly paper-trading daily review summary helper (`get_paper_daily_review_summary_for_run(...)`) that composes persisted run risk/trade/snapshot data into a compact operator-facing shape (`run_id`, BUY totals, ticker activity count, notable plain-language items, and optional short portfolio-change summary).
- Post-review Step 28 fix: ticker activity counting now includes all persisted run event/trade rows (including non-risk events like `HOLD_EVENT`) so beginner-facing summaries report complete run activity coverage.

## Current documentation posture
- Core planning, status, architecture, and maintenance docs now form a traceable documentation stack for future Codex execution.
- Backlog clearly separates completed work from pending items and tracks follow-up notification work as active backlog.
- Runtime + docs now align on notification guardrails: best-effort delivery, deterministic formatting, and non-blocking failure posture.
- Traceability docs now align with runtime persistence: major daily artifacts can be audited back to a single run record.
- Decision-governance docs now align with runtime data capture: AI signal output and human decision state are explicitly separated in a review ledger.
- Platform-governance baseline is now documented for GitHub/Railway/Supabase with explicit manual verification ownership separated from code changes.
- Supabase access-control posture is now explicit in architecture docs: core runtime tables are backend-only by design, currently in `public`, with RLS hardening planned as staged single-table migrations.
- Operator documentation now includes a beginner-friendly runbook for routine paper-risk CLI review and basic failure triage.
- Operator documentation now also includes a beginner-friendly Telegram troubleshooting runbook for notification delivery triage and escalation.

## Next approved task
- Define Step 29 follow-up to add an operator-facing quick-reference mapping from notification log outcomes (sent/skipped/deduped/failed) to recommended first action and escalation threshold examples.
