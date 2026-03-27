# Implementation Runbook (Codex)

## Purpose
Provide a consistent execution workflow for long-horizon Codex contributions.

## Core rules
- `docs/plans.md` is the source of truth for milestone sequence and scope.
- Work on one milestone at a time.
- Keep diffs small and tightly scoped to the current task.
- Validate outcomes after each milestone before moving forward.
- Do not break Railway production flow.
- Update `docs/status.md` after each completed task.
- If validation fails, stop progression and repair issues before continuing.

## Standard execution loop
1. Read `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, and `docs/status.md`.
2. Select the next approved milestone task from `docs/status.md`.
3. Implement only the scoped change for that task.
4. Run validation checks defined in `docs/plans.md`.
5. If any validation fails, stop and repair before taking new scope.
6. Commit with a clear milestone/task summary.
7. Open PR and complete review/merge per repository governance.

## Post-merge acceptance workflow
1. After merge, execute dual acceptance checks and record outcomes:
   - **Post-merge QA Check** (output/function behavior, success+error path clarity, display/docs/tests consistency).
   - **Post-merge Domain Check** (AI HK investing-system alignment, paper-trading/decision-support boundary, calculation/interpretation risk).
2. Update `docs/status.md` with:
   - merge completion + acceptance outcomes,
   - blocker/backlog classification,
   - next approved task.
3. Use explicit wording keys to reduce ambiguity:
   - `repo merge completed`,
   - `manual platform acceptance completed`,
   - `docs maintenance follow-up`.

## Step 15 implementation note (structured observability JSON)
- Add nullable `runs.error_summary_json` and `runs.delivery_summary_json` via migration.
- Keep legacy text `error_summary` and category text summaries unchanged for backward compatibility.
- Build structured ticker/stage error records and message-level Telegram delivery telemetry (single daily-summary attempt per run, with explicit dedup-skip semantics) in Python, then persist on run finalization in best-effort updates.
- Guardrail: telemetry writes are observability-only and must never block signal generation, dedup persistence, paper-trading, or Telegram delivery attempts.

## Step 16 implementation note (pytest config + CI test gating)
- Add a conservative root `pytest.ini` (`minversion`, `testpaths`, `addopts`) to stabilize test discovery from repository root across local and CI runs.
- Add GitHub Actions test workflow at `.github/workflows/tests.yml` that runs on `pull_request` and `push` to `main` using `ubuntu-latest` + `actions/setup-python`.
- Reuse existing dependency flow (`pip install -r requirements.txt`) and run `pytest` directly, avoiding extra tooling or runtime-path behavior changes.

## Step 17 implementation note (versioned daily summary payload + renderer separation)
- Introduce a compact internal `build_daily_summary_payload_v1(...)` contract with `schema_version`, run identity/date, market, summary type, totals, and per-stock rows (`stock_id`, `stock_name`, `signal`).
- Render Telegram text via `render_daily_summary_message(payload)` with schema-version dispatch (v1 renderer), so message formatting can evolve without changing aggregation inputs.
- Keep send path ordering explicit and stable: fetch equity -> build payload -> render message -> send -> dedup marker write.
- Include `context.summary_schema_version` in delivery telemetry so run-level observability records the payload schema used for each attempt.
- Guardrail: preserve existing best-effort/non-blocking delivery semantics and dedup/retry/transport behavior.

## Step 18 implementation note (schema evolution guardrails + summary contract hardening)
- Define explicit notification schema constants in `src/notifications.py`: `CURRENT_DAILY_SUMMARY_SCHEMA_VERSION` and `SUPPORTED_DAILY_SUMMARY_SCHEMA_VERSIONS` (currently `{1}`), while preserving v1 runtime behavior.
- Keep renderer dispatch centralized through a single schema->renderer mapping so future version additions remain reviewable and testable.
- Validate guardrail consistency before dispatch (`current` version must be in the supported set, and supported versions must match renderer-map keys).
- Fail fast for unsupported schema versions with explicit supported-version context so schema drift is surfaced early in tests/CI.
- Keep telemetry `context.summary_schema_version` aligned to the payload schema used at send-time for stable run-level observability.
- Expand tests to cover current-version dispatch, supported-version mapping guarantees, unsupported-version handling, telemetry version propagation, and renderer entrypoint stability.

## Step 19 implementation note (operational baseline hardening)
- Document platform baseline controls across GitHub, Railway, and Supabase with explicit separation between code-enforceable and manual settings.
- Keep runtime behavior unchanged: no trading-logic changes and no new web server path for the worker runtime.
- For Railway healthchecks, document worker-appropriate settings (no HTTP `/health` dependency for current script execution model).
- Capture environment-variable hygiene, log/observability expectations, and Supabase backup/RLS/free-tier risk checks as explicit operational guardrails.
- Record manual follow-ups in `docs/backlog.md` and reflect completion + next approved task in `docs/status.md`.

## Step 19B implementation note (Supabase access model + RLS hardening plan)
- Keep this step scoped to access-model clarification and explicit rollout planning; do not perform broad production RLS toggles in one pass.
- Document the current runtime access model as backend-only (no direct anon/client table access path in this repo).
- Maintain an explicit table inventory (`runs`, `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, `notification_logs`) with schema location, `public` exposure, and current RLS state.
- Recommend staged hardening: enable RLS table-by-table with minimal backend-safe policies and post-deploy verification per table.
- Defer private-schema migration to a follow-up after initial RLS enablement is validated.
- Record exact next migration scope (start with `public.runs`) and required rollback/verification notes before expanding to other tables.

## Step 20 implementation note (paper-trading decision ledger / decision record v1)
- Add a new persistence table for paper-trading decision records with explicit AI-vs-human separation fields (`signal_action` vs `human_decision`) plus `stock_id` and `stock_name` for analytics-grade traceability.
- Add a small application helper/model layer that validates required decision fields before insert.
- Integrate decision-record creation at the signal-save path as best-effort observability (must not block signal generation or paper-trading execution).
- Keep real-money execution out-of-scope: this ledger records review decisions only and does not place orders.

## Step 42 implementation note (market data provider boundary v1)
- Introduce a provider abstraction (`MarketDataProvider`) with minimal required methods: `get_daily_ohlcv`, `get_latest_price`, and `get_symbol_metadata`.
- Keep orchestration and signal modules source-agnostic by routing market reads through provider boundary helpers in `src/data.py`.
- Add a deterministic `mock` provider for local development and tests; keep `yfinance` as default provider.
- Add minimal provider selection config using env var `MARKET_DATA_PROVIDER` (for Railway/local), with fail-fast validation on unsupported provider names.
- Guardrails: provider work is paper-trading/decision-support only, no broker integration, no live-money execution, and no large ingestion-pipeline expansion in this step.

## Step 43 implementation note (human-facing HKT display + operator clarity hardening)
- Normalize human-facing/operator-facing timestamp display to HKT (`Asia/Hong_Kong`) at render time only (Telegram replies, review/status summaries); keep persisted/log/raw timestamps unchanged.
- Apply the display policy to representative command surfaces first (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`) and avoid broad refactors.
- Keep scope guardrails explicit in message copy/comments: paper trading + decision support only, no autonomous real-money execution.
- Prefer deterministic, scan-friendly operator wording (`*_hkt` fields, explicit status/result/reason rows) and preserve existing strategy/paper-trading decision logic.

## Step 44 implementation note (docs/deployment/config hardening)
- Documentation scope only: align status wording with merged reality for Steps 40–43 and normalize backlog state markers.
- Keep topology explicit in system-of-record docs:
  - `telegram-webhook` service handles inbound operator commands.
  - `paper-daily-runner` service handles scheduled batch execution.
- Keep schedule language explicit: business target is 20:00 HKT; Railway scheduler is UTC (`0 12 * * *` baseline).
- Keep market-data policy explicit: `MARKET_DATA_PROVIDER=yfinance` is current production baseline; `mock` is for local/test deterministic workflows, not production.
- Keep human-facing display policy explicit: operator/review outputs show HKT labels; storage/logging semantics remain unchanged.
- Keep operator command surfaces explicitly read-only review surfaces (decision support only).
- Separate deployment ownership in docs:
  - **GitHub:** branch protection/CI/check governance.
  - **Railway:** service split, cron ownership, runtime secrets/env management.
- Guardrails: no runtime logic changes, no new API integration, no strategy change, no schema refactor.


## Step 45 implementation note (dedup/delivery semantics docs validation)
- Scope is documentation validation/clarification only; runtime behavior, queueing, retry framework, schema, and strategy logic stay unchanged.
- Document current Telegram/operator-facing delivery reality in plain language:
  - command reply behavior (operator commands are synchronous webhook-triggered sendMessage replies),
  - runner summary behavior (best-effort + dedup-aware daily summary),
  - review-response behavior (`/risk_review`, `/pnl_review`, `/runner_status`, `/runs` are read-only and bounded),
  - retry/rerun/duplicate scenarios and why some duplicates are expected in best-effort flows.
- Keep operator expectation explicit: what is normal, what duplicate patterns are expected, and what conditions should be tracked as follow-up.
- Record unresolved delivery/dedup follow-ups in `docs/backlog.md` with clear active vs completed separation.
- Guardrail reminder: decision support + paper trading only, no autonomous real-money execution.

## Step 46 implementation note (delivery semantics observability evidence pass)
- Scope remains docs-only/system-of-record alignment: no Telegram runtime refactor, no queue/retry framework, no schema refactor, no new API integration, no strategy logic change.
- Add an operator-facing evidence checklist that is executable against current artifacts:
  - Telegram observed messages,
  - `runs.delivery_summary_json`,
  - runner logs (`execution_summary` and lifecycle lines),
  - relevant `runs` table records.
- Explicitly document scenario-based validation paths:
  - normal daily summary delivery,
  - rerun behavior,
  - duplicate skipped behavior,
  - dedup persistence failure fallback,
  - operator command reply vs runner summary delivery distinction.
- Include observability gap analysis in system-of-record wording:
  - what evidence is already strong,
  - what remains ambiguous/manual,
  - what should be deferred to a future runtime/instrumentation step.
- Keep deployment ownership wording explicit:
  - **GitHub:** this step updates documentation/system-of-record only.
  - **Railway:** no topology/cron/runtime-variable change required in this step.

## Step 47 implementation note (delivery semantics runtime instrumentation scoping proposal)
- Scope is strictly plan/spec/scoping; do not implement runtime behavior changes in this step.
- Document and prioritize current delivery observability gaps with explicit system-of-record separation:
  - current known gap,
  - scoping proposal,
  - not-yet-approved runtime change,
  - future follow-up.
- Define minimal candidate instrumentation fields for future runtime consideration (for example `correlation_id`, `message_delivery_attempt_id`, `delivery_phase`, `dedup_check_result`, `dedup_persist_result`, `fallback_activated`) and classify by priority/value/risk.
- Keep guardrails explicit:
  - no runtime implementation,
  - no DB migration,
  - no `delivery_summary_json` schema change,
  - no Telegram send-path refactor,
  - no queue/retry framework introduction,
  - no strategy logic change.
- Keep platform ownership split explicit:
  - **GitHub:** docs/system-of-record update only.
  - **Railway:** no topology/cron/runtime-env/config change required in this step.

## Step 48 implementation note (delivery semantics minimal runtime instrumentation v1)
- Scope is a minimal runtime observability increment only; preserve existing best-effort/non-blocking summary delivery behavior.
- Implement only two telemetry fields in daily summary delivery telemetry + `runs.delivery_summary_json` projection:
  - `correlation_id`,
  - `dedup_check_result`.
- Keep `dedup_check_result` semantics bounded and explicit:
  - `send_path` (normal send attempt),
  - `dedup_skip` (dedup marker already exists, skip send),
  - `dedup_check_fallback` (dedup check failed, fallback to send attempt).
- Keep correlation format deterministic and review-friendly so one value can be reused across logs/run records/operator troubleshooting notes.
- Add focused tests for:
  - normal send path,
  - dedup skip path,
  - dedup-check fallback path,
  - delivery summary projection includes new fields.
- Guardrails:
  - no DB migration,
  - no queue/retry framework introduction,
  - no Telegram send-path refactor,
  - no broad delivery summary schema redesign,
  - no strategy/paper-trading logic changes.
- Platform ownership split for this step:
  - **GitHub:** runtime code + focused tests + docs/status/backlog/spec updates.
  - **Railway:** no topology/cron/runtime-env/deployment mutation required.

## Step 49 implementation note (delivery semantics follow-up scope refinement)
- Scope is docs-only reassessment/refinement after Step 48; do not implement runtime changes in this step.
- Reassess remaining delivery observability gaps with Step 48 now in place (`correlation_id` + `dedup_check_result`).
- Compare exactly two next-slice candidates with explicit value/risk/scope/complexity/operator-payoff analysis:
  - `dedup_persist_result`,
  - `delivery_phase`.
- Make one single next runtime recommendation only (no parallel implementation tracks).
- Keep all guardrails explicit: no runtime behavior change, no new telemetry field this step, no schema migration, no Telegram send-path refactor, no queue/retry framework, no strategy logic change.
- Keep platform ownership split explicit:
  - **GitHub:** docs/system-of-record updates only.
  - **Railway:** no topology/cron/runtime-env/deployment mutation required.

## Step 50 implementation note (delivery semantics minimal runtime instrumentation v2)
- Scope is a single-field runtime observability increment only; preserve existing best-effort/non-blocking daily-summary delivery behavior.
- Implement exactly one additional telemetry field in daily summary delivery telemetry + `runs.delivery_summary_json` projection:
  - `dedup_persist_result`.
- Keep `dedup_persist_result` semantics bounded and explicit:
  - `persisted`,
  - `persist_failed`,
  - `not_applicable`.
- Keep projection contract explicit for operator triage:
  - `correlation_id`,
  - `dedup_check_result`,
  - `dedup_persist_result`.
- Add focused tests for:
  - normal send + persist success,
  - send success + persist failure,
  - dedup skip (`not_applicable`),
  - delivery summary projection shape includes `dedup_persist_result`.
- Guardrails:
  - no `delivery_phase`,
  - no DB migration,
  - no queue/retry framework introduction,
  - no Telegram send-path refactor,
  - no broad telemetry redesign,
  - no strategy/paper-trading logic changes.
- Platform ownership split for this step:
  - **GitHub:** runtime code + focused tests + docs/system-of-record updates.
  - **Railway:** no topology/cron/runtime-env/deployment mutation required.

## Step 51 implementation note (post-merge dual acceptance workflow formalization; docs-only)
- Scope is docs governance formalization only; no runtime behavior/API/schema/strategy changes.
- Formalize merge-after acceptance as two mandatory checks for every future merged step:
  - **Post-merge QA Check**: verify new output/function works as intended, success/error path wording is clear, and display/docs/tests stay consistent.
  - **Post-merge Domain Check**: verify alignment with AI-assisted HK investing-system mainline, ensure paper-trading/decision-support-only boundary remains intact, and screen for calculation/interpretation risk.
- Define triage discipline:
  - **Blocker:** materially incorrect output/logic, missing critical error handling, domain-boundary breach, or high-risk interpretation/calculation issue.
  - **Backlog follow-up:** non-blocking clarity/readability/docs-maintenance or observability improvements with no immediate correctness/safety breach.
- Define wording discipline between docs:
  - `docs/status.md` records merged/completed state + acceptance outcomes.
  - `docs/backlog.md` records only remaining actionable follow-ups (not merged completion truth).
- Keep platform ownership explicit for this step:
  - **GitHub:** docs-only updates.
  - **Railway:** no topology/cron/runtime-env/deployment mutation required.
