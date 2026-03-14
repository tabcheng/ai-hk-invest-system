# Product + Engineering Backlog

Prioritization scale:
- **P0** = next implementation-critical
- **P1** = important near-term hardening
- **P2** = valuable follow-up

## Recently completed (moved out of active backlog)

1. **Paper-trading v1 implementation** ✅ completed
   - Deterministic simulator and persistence outputs are in place.

2. **Telegram daily summary notification MVP** ✅ completed
   - End-of-run best-effort Telegram summary delivery is active.

3. **Telegram deterministic run-date + startup-failure attempt** ✅ completed
   - Hardening completed to improve summary consistency and fatal-startup visibility.

4. **Telegram notification hardening + first docs maintenance review** ✅ completed
   - Summaries now include stock name + stock id using deterministic HTML formatting.
   - Summary equity prefers run-date snapshot with clear fallback labeling.
   - Cross-run daily-summary dedup persistence added (`notification_logs`) for same run-date + target.
   - Delivery remains best-effort/non-blocking.
   - Documentation system-of-record refreshed (`status`/`backlog`).

5. **End-to-end `run_id` traceability hardening** ✅ completed
   - Added run linkage persistence for `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, and `notification_logs`.
   - Added migration-level FK-style links/indexes where practical.
   - Run records now persist separated ticker/post-processing/notification failure summaries.


6. **Structured run observability JSON + delivery telemetry** ✅ completed
   - Added `runs.error_summary_json` and `runs.delivery_summary_json` schema support.
   - Added structured ticker/stage error records and Telegram delivery telemetry persistence in run finalization.
   - Preserved legacy text summary fields and best-effort/non-blocking observability guardrails.

7. **Basic pytest project config + CI test gating** ✅ completed
   - Added a conservative root `pytest.ini` for stable repository-root discovery.
   - Added `.github/workflows/tests.yml` to run `pytest` on pull requests and pushes to `main`, pinned to Python 3.10 with pip caching.

8. **Telegram follow-up: summary schema versioning** ✅ completed
   - Added a compact versioned daily-summary payload contract (`schema_version: 1`) with run metadata, totals, and stock rows (`stock_id` + optional `stock_name`).
   - Separated payload construction from Telegram message rendering via schema-dispatched renderer.
   - Added delivery telemetry context for `summary_schema_version` and tests for payload/renderer empty + multi-stock paths.

9. **Step 18: schema evolution guardrails + contract hardening** ✅ completed
   - Added explicit schema evolution guardrails: current schema version constant, supported-version allowlist, centralized renderer dispatch map, consistency validation between supported versions and renderer keys, and fail-fast unsupported/misconfigured-version errors.
   - Expanded tests for current-version dispatch, supported-version mapping, unsupported-version handling, renderer entrypoint stability, and telemetry schema-version propagation.


10. **Step 19: operational baseline hardening (GitHub/Railway/Supabase)** ✅ completed
   - Documented platform baseline controls and explicit manual verification checklist for GitHub branch protection/security settings, Railway worker healthcheck posture + env/logging hygiene, and Supabase backup/RLS/free-tier production risks.


11. **Step 19B: Supabase access model clarification + safe RLS hardening plan** ✅ completed
   - Documented current Supabase runtime access model as backend-only and inventory of core runtime tables (`runs`, `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, `notification_logs`).
   - Captured current posture from manual review: core tables are in `public`, and RLS is not enabled.
   - Added a low-risk staged hardening plan: start with single-table RLS rollout (`public.runs`) + explicit backend policy + verification/rollback notes, then expand table-by-table.
   - Deferred broad schema/private-schema migration to follow-up planning to avoid one-shot production risk.
   - Preserved runtime behavior and trading logic (documentation + low-risk governance pass only).


12. **Step 20: paper-trading decision ledger / decision record v1** ✅ completed
   - Added `paper_trade_decisions` schema for run-linked AI signal and human decision records.
   - Added minimal application helper + best-effort insert integration at signal persistence time.
   - Added tests for schema presence, required-field validation, and happy-path insert behavior.

13. **Post-review Step 20 hardening** ✅ completed
   - Refactored app integration to a dedicated best-effort decision-ledger helper for clearer guardrails.
   - Tightened decision payload validation for non-string required fields and invalid/non-finite `signal_score` values.
   - Added app-level tests for stock metadata mapping and non-blocking behavior when ledger writes fail.

14. **Step 21: paper position / PnL snapshot foundation** ✅ completed
   - Added `paper_positions` schema for ticker-level quantity, average cost, mark price, and realized/unrealized PnL state.
   - Added long-only position-state refresh after simulated trade writes (including weighted-average cost updates across repeated buys and clean zero-quantity handling on sells).
   - Added a compact `get_paper_portfolio_summary` helper to support future Telegram/dashboard read paths.

15. **Post-review Step 21 state-sync hardening** ✅ completed
   - Prior-day state bootstrap is date-correct for reruns/backfills by rebuilding from `paper_trades` strictly before `trade_date` (no dependency on current `paper_positions` state).
   - `paper_positions` refresh now upserts by ticker, deletes stale tickers, and explicitly refreshes `updated_at` on each state write.

16. **Post-review Step 21 test guardrail hardening** ✅ completed
   - Added focused tests that assert strict `< trade_date` query filtering for prior-state reconstruction and stale ticker deletion behavior during `paper_positions` refresh.


17. **Post-review Step 22 concentration valuation fix** ✅ completed
   - Corrected concentration-risk inputs to use mark-based valuation for existing positions and portfolio equity (unrealized PnL aware) instead of cost-basis valuation.
   - Added simulation tests proving gain/loss-sensitive concentration behavior remains correct under BUY guardrail blocking rules.


18. **Post-review Step 22 fee-denominator concentration fix** ✅ completed
   - Updated concentration projected-weight denominator to use post-trade equity (accounting for BUY fee impact) for tighter risk accuracy under non-trivial fee assumptions.
   - Added pure risk-module test coverage locking this denominator behavior.

19. **Step 23: risk observability / decision-support record v1** ✅ completed
   - Added a compact risk-evaluation payload helper for stable review schema (`allowed`, `severity`, `summary_message`, `rule_results`).
   - Attached structured risk metadata to relevant paper-trading events (blocked BUY guardrail and already-holding add-check paths) to keep blocked/warning/info outcomes traceable.
   - Extended decision-ledger payload/schema support for optional `risk_evaluation` JSON and added focused migration + serialization/integration tests.

## Active backlog (pending)

## P1 — Near-term hardening and review reminders

### Carry-over reminders
1. **Helper extraction:** pull repeated runtime logic into focused helpers to reduce duplication.
2. **Trace coherence:** ensure status/identifier consistency across run + signal + downstream layers.
3. **Failure reporting quality:** improve error grouping/actionability over opaque string blobs.

### Additional hardening
- Expand tests for NO_DATA / INSUFFICIENT_DATA propagation, run finalization, DB failure paths, and notification failure pathways.
- Add runbook entry for Telegram environment misconfiguration triage.

### Manual platform actions (cannot be enforced in repo code)
- Configure GitHub branch protection for `main`: require pull request + review, dismiss stale approvals, require passing `tests` status check, and restrict force-push/delete.
- Enable/verify GitHub Dependabot security updates and version updates.
- Enable/verify GitHub secret scanning and push protection.
- Configure Railway service as a worker-style deployment (no HTTP `/health` requirement for current runtime entrypoint) and verify healthcheck settings do not expect an HTTP path.
- Verify Railway production secrets hygiene (managed env vars only, rotation cadence documented).
- Verify Supabase production backup/PITR posture and RLS exposure review for all runtime tables.
- Manage free-plan pause risk explicitly (wake-up runbook, missed-run catch-up expectations, and alerting/visibility expectations).
- Plan future private-schema migration for backend-only operational tables after staged RLS rollout validation (scope, sequencing, and rollback path).

### Code/documentation follow-ups (repo changes)
- Evolve paper-trade risk guardrails from v1 to v2 (config source, richer sell-path checks, and decision-ledger linkage) after observing paper-run outcomes.
- Define a formal notification schema evolution policy for future daily-summary schema v2+ (change classes, compatibility expectations, rollout and rollback rules).
- Normalize pytest/tooling conventions further (if still relevant) to keep local and CI invocation parity explicit.
- Derive delivery telemetry schema version from the actual summary payload object at send-time (single source of truth), instead of relying on independently-provided context fields.

## P2 — Medium-term quality and performance

### Reliability and test depth
- Add deterministic replay fixtures for multi-day simulation scenarios.
- Increase integration-style coverage for persistence + run lifecycle behavior.

### Metrics and performance
- Track processing duration and per-ticker latency.
- Add failure ratio and data-coverage metrics.
- Monitor performance regressions over time.

### Strategy analytics extensions
- Add richer paper-trading analytics (risk-adjusted return, drawdown episodes, turnover efficiency).
- Evaluate signal extensions only after baseline paper-trading evidence is established.

## Technical debt register
- Runtime flow still has extractable helper opportunities.
- Structured JSON observability is now present with versioned daily-summary payload contracts; continue disciplined schema evolution for future versions.
- Test harness now has project-level pytest config and CI enforcement; continue expanding depth and failure-path coverage.
- Notification layer now has sent-dedup persistence, run-level delivery telemetry, and summary schema-version governance v1; future revisions should evolve the schema with explicit version bumps.
- Telemetry metadata currently relies on explicit context shaping; future hardening should derive schema-version telemetry directly from the rendered payload contract to reduce drift risk.

## Maintenance rule
After each completed task, update both this backlog and `docs/status.md` to keep next approved work explicit.
