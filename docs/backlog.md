# Product + Engineering Backlog

Prioritization:
- **P0** = next implementation-critical
- **P1** = near-term important hardening
- **P2** = valuable follow-up

## Active backlog (pending)

### P0
1. **Step 52 candidate — Platform hardening evidence pass (GitHub / Railway / Supabase)**
   - Refresh manual verification checklist evidence for branch protection, CI checks, scheduler posture, runtime secret hygiene, and Supabase backup/RLS posture.
   - Keep runtime behavior unchanged.

### P1
1. **Paper-trading analytics follow-up scoping**
   - Define one minimal analytics increment (metrics + dependencies + validation plan) without broad implementation.

2. **Telegram command registration follow-up (optional)**
   - Decide whether to add bot command registration (`setMyCommands`) for discoverability.
   - Keep this isolated from strategy and paper-trading logic.

3. **Delivery semantics phase narrative instrumentation (`delivery_phase`)**
   - Re-evaluate whether a compact `delivery_phase` enum still adds enough operator triage value beyond current fields (`correlation_id`, `dedup_check_result`, `dedup_persist_result`).
   - Keep scope bounded and avoid broad telemetry redesign; preserve current best-effort/non-blocking delivery behavior.
   - If approved later, require focused tests and explicit backward-compatible projection semantics.

### P2
- Expand deterministic replay/integration fixtures for multi-day paper-trading scenarios.
- Improve failure-path coverage for DB/notification/run-finalization edge cases.
- Track lightweight runtime health metrics (duration, per-ticker latency, failure ratio) in a scoped step.

## Completed backlog (archived)

### Recently completed (Steps 40–51)
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
