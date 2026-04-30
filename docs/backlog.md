# Product + Engineering Backlog

Prioritization:
- **P0** = next implementation-critical
- **P1** = near-term important hardening
- **P2** = valuable follow-up

## Active backlog (pending)

### P0
1. **Step 67 future plan — scheduled daily health check**
   - Keep as future plan only; do not implement schedule in Step 63.

2. **Step 65 candidate — optional Supabase verification for operator smoke harness**
   - Keep default harness behavior non-blocking and safe (`verify_supabase=false` by default).
   - Add row-level verification only if it remains bounded/read-only.
   - No schema migration and no runtime execution-path change.

### P1
1. **Telegram command registration follow-up (optional)**
   - Decide whether to add bot command registration (`setMyCommands`) for discoverability.
   - Keep this isolated from strategy and paper-trading logic.

2. **Delivery semantics phase narrative instrumentation (`delivery_phase`)**
   - Re-evaluate whether a compact `delivery_phase` enum still adds enough operator triage value beyond current fields (`correlation_id`, `dedup_check_result`, `dedup_persist_result`).
   - Keep scope bounded and avoid broad telemetry redesign; preserve current best-effort/non-blocking delivery behavior.
   - If approved later, require focused tests and explicit backward-compatible projection semantics.

3. **Platform evidence cadence + artifact capture follow-up (GitHub / Railway / Supabase)**
   - Define a lightweight recurring manual verification cadence (for example monthly/after critical config changes) and where to store dated evidence snapshots/screenshots.
   - Keep this as documentation/process hardening first; do not trigger infra refactor or runtime topology changes without a separate approved step.

4. **Decision-to-outcome attribution linkage follow-up (analytics)**
   - Evaluate a bounded linkage model between `paper_trade_decisions` records and subsequent closed-trade outcomes.
   - Keep this as a follow-up design/implementation candidate only after Step 55 confirms baseline utility.
   - Preserve decision-support guardrails; do not introduce autonomous execution semantics.

5. **Telegram output language option (future)**
   - Add configurable Telegram output language support, initially `zh-HK` and `en`.
   - Suggested rollout: apply first to `/daily_review`, then expand to other commands.
   - Not in Step 60 scope: no localization implementation in this step.

### P2
- Expand deterministic replay/integration fixtures for multi-day paper-trading scenarios.
- Improve failure-path coverage for DB/notification/run-finalization edge cases.
- Track lightweight runtime health metrics (duration, per-ticker latency, failure ratio) in a scoped step.
- Add market-relative/context overlays for analytics interpretation (for example benchmark comparison or regime tags) only after baseline outcome summary is stable.

## Completed backlog (archived)

### Recently completed (Steps 40–60)
- **Step 40 completed:** normalized operator response shape for `/runs`, `/runner_status`, `/risk_review` and centralized HTML-safe rendering contract.
- **Step 41 completed:** added read-only paper position/PnL snapshot helper and `/pnl_review` operator command, including input/correctness hardening.
- **Step 42 completed:** added market-data provider boundary (`MARKET_DATA_PROVIDER`) with `yfinance` baseline and deterministic `mock` provider.
- **Step 43 completed:** normalized operator/review human-facing timestamp display to HKT while preserving storage/log timestamp semantics.
- **Step 44 completed:** aligned merged/completed documentation status for Steps 40–43, hardened deployment/config documentation clarity (webhook vs runner topology, HKT schedule baseline, provider/mock policy, GitHub vs Railway responsibilities), and normalized backlog wording/state.
- **Step 45 completed:** validated and documented current Telegram/operator-facing dedup + delivery semantics reality (command replies, runner summaries, review responses, retry/rerun/duplicate expectations), clarified operator expectation baseline, and refreshed backlog follow-ups without runtime behavior changes.
- **Step 46 completed:** added delivery semantics observability evidence checklist, operator validation guidance, and explicit observability gap analysis (known behavior vs verifiable evidence vs unresolved gaps vs future follow-up), with docs-only scope and no runtime behavior changes.
- **Step 47 completed:** documented delivery semantics runtime instrumentation scoping proposal, prioritized observability gaps, classified candidate fields by value/risk/priority, and codified explicit no-implementation/no-migration/no-refactor guardrails (GitHub docs-only; Railway unchanged).
- **Step 48 completed:** implemented minimal runtime delivery instrumentation (`correlation_id`, `dedup_check_result`) with bounded semantics (`send_path`, `dedup_skip`, `dedup_check_fallback`), added focused tests for normal-send/dedup-skip/fallback + delivery summary projection, and updated docs/system-of-record artifacts (GitHub changed; Railway unchanged).
- **Step 49 completed:** performed post-Step-48 delivery observability gap reassessment, compared `dedup_persist_result` vs `delivery_phase` (value/risk/scope/complexity/operator payoff), selected one single next slice recommendation (`dedup_persist_result`), and synchronized docs/implement/backlog/status with explicit GitHub-vs-Railway ownership split (docs-only, Railway unchanged).
- **Step 50 completed:** implemented minimal runtime delivery instrumentation v2 by adding `dedup_persist_result` (`persisted` / `persist_failed` / `not_applicable`) in summary telemetry and `runs.delivery_summary_json` projection, added focused tests for persist success/failure and dedup-skip N/A semantics, and updated docs/system-of-record artifacts (GitHub changed; Railway unchanged).
- **Step 50 review hotfix completed:** test harness now injects local stubs for optional runtime packages (`requests`, `supabase`, `pandas`, `yfinance`) in `tests/conftest.py` so focused test execution is not blocked by sandbox package-install restrictions (runtime behavior unchanged).
- **Step 51 completed (docs-only):** formalized mandatory post-merge dual acceptance workflow (`Post-merge QA Check` + `Post-merge Domain Check`), codified blocker vs backlog-follow-up triage, and normalized wording discipline so `docs/status.md` is merge/acceptance truth while `docs/backlog.md` tracks only pending follow-ups.
- **Step 52 completed:** fixed test-harness pandas stub coverage so market-data/signals tests have required fallback API surface only when pandas is unavailable.
- **Step 53 completed (docs-only):** delivered a minimal platform hardening evidence pass summary/checklist for GitHub/Railway/Supabase with explicit `repo-confirmed` vs `manual verification required` vs `backlog follow-up` separation, and synced status/project-plan records without runtime/deployment topology changes.
- **Step 54 completed (docs-only):** scoped one minimal paper-trading analytics increment (`win/loss and holding-period summary` for closed paper trades), documented operator questions/data dependencies/sufficiency gaps, and defined validation rubric + interpretation-risk/limitation guardrails without implementation/runtime changes.
- **Step 54 review hardening completed (docs-only):** tightened metric-definition precision (`flat_count`, `win_rate` denominator/N/A handling, deterministic ranking basis/tie-break, simplified pairing limitation wording) so Step 55 implementation can stay bounded and less ambiguous.
- **Step 55 completed:** implemented bounded closed-trade outcome summary helper + `/outcome_review` operator surface with deterministic BUY/SELL pairing (`trade_date`, `id`), denominator-safe wording, explicit empty-window behavior, stable top-contributor tie-break, focused tests, and docs sync (GitHub changed; Railway unchanged).
- **Step 55 review hotfix completed:** hardened outcome review robustness by skipping malformed `trade_date` rows (instead of failing review output), clarified nearest-rank percentile math via `ceil(...)`, and added focused malformed-date coverage.
- **Step 56 completed:** added bounded optional review window grammar (`/outcome_review <days>`), deterministic exit-`trade_date` window filtering anchored to latest available snapshot `trade_date`, explicit invalid/out-of-range usage errors, and focused tests/docs alignment (GitHub changed; Railway unchanged).
- **Step 57 completed:** performed bounded operator-surface consistency/wording normalization for `/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review`, including stock-display fallback policy (`stock_name + stock_id` preferred; `stock_id=<id> | name_unavailable` fallback), normalized usage/invalid-input wording, normalized no-data phrasing, focused tests, and docs sync (GitHub changed; Railway unchanged).
- **Step 58 completed (docs-only):** added `docs/operator-runbook.md` with compact normal/no-data/invalid-input interpretation examples for `/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review`, `/outcome_review <days>`, and explicitly documented Step 57 stock-display fallback policy; runtime behavior unchanged (GitHub changed; Railway unchanged).
- **Step 59 completed:** added read-only `/daily_review` Telegram operator command as a compact daily operator review packet MVP that aggregates section-level status from existing review surfaces (`runner_status`, latest run id, pnl snapshot availability, outcome summary availability), with partial no-data/internal-error tolerance, focused tests (success/partial-no-data/helper-error/unauthorized/help inclusion), and docs sync across runbook/spec/status/backlog (GitHub changed; Railway unchanged).
- **Step 60 completed:** upgraded read-only `/daily_review` usability by adding `business_date_hkt`, `latest_run_time_hkt`, `daily_review_health`, `next_action_hint`, and `detail_commands` (including `/risk_review <run_id>` when available), while preserving section-scoped no-data/internal-error tolerance and command-level completion behavior; added focused tests and docs synchronization (GitHub changed; Railway unchanged).
- **Step 62 completed:** implemented `/decision_note` runtime MVP (run-level journaling only), including validation/authorization-focused tests and explicit non-execution boundary messaging.
- **Step 63 completed:** added manual Telegram operator smoke-test QA harness (`scripts/operator_smoke_test.py`) + manual GitHub Actions workflow (`workflow_dispatch`) with report artifacts (`operator_smoke_report.md/json`) and 7-day retention; no strategy/paper-trading calculation/live-money execution changes.

### Earlier completed foundations
- Step 1–12 baseline (documentation foundation, signal framework, dedup, run lifecycle, modularization, tests, Telegram MVP/hardening).
- Steps 13–20 baseline (traceability hardening, observability JSON, CI gating, notification schema guardrails, platform docs, Supabase access model, decision ledger v1).
- Steps 21–39 baseline (paper-trading risk/review surfaces, operator docs/runbooks, webhook ingress, `/risk_review`, dual-service deployment docs, runner observability, `/runner_status`, HTML/timezone hardening follow-ups).

## Notes
- `docs/status.md` is the merge/completion + acceptance system-of-record for step state.
- This backlog tracks remaining actionable follow-ups only; completed items are archived for context and must not be treated as the canonical merge-state record.
- Wording guideline:
  - Use `repo merge completed` and `manual platform acceptance completed` in `docs/status.md`.
  - Use `docs maintenance follow-up` only when opening a pending backlog item (not when declaring merge completion).
- No backlog item authorizes autonomous live-money execution.

- Step 62 runtime MVP is complete (run-level only); stock-level decision journal runtime remains intentionally not implemented.
