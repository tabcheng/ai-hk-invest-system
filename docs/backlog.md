# Product + Engineering Backlog

Prioritization:
- **P0** = next implementation-critical
- **P1** = near-term important hardening
- **P2** = valuable follow-up

## Active backlog (pending)

### P0
1. **Step 45 candidate — Dedup/delivery semantics documentation validation**
   - Consolidate operator-facing wording/examples for `sent`, `skipped`, `deduped`, `failed`.
   - Keep scope docs-first; runtime changes only if a concrete defect is proven.

### P1
1. **Platform hardening evidence pass (GitHub / Railway / Supabase)**
   - Refresh manual verification checklist evidence for branch protection, CI checks, scheduler posture, runtime secret hygiene, and Supabase backup/RLS posture.
   - Keep runtime behavior unchanged.

2. **Paper-trading analytics follow-up scoping**
   - Define one minimal analytics increment (metrics + dependencies + validation plan) without broad implementation.

3. **Telegram command registration follow-up (optional)**
   - Decide whether to add bot command registration (`setMyCommands`) for discoverability.
   - Keep this isolated from strategy and paper-trading logic.

### P2
- Expand deterministic replay/integration fixtures for multi-day paper-trading scenarios.
- Improve failure-path coverage for DB/notification/run-finalization edge cases.
- Track lightweight runtime health metrics (duration, per-ticker latency, failure ratio) in a scoped step.

## Completed backlog (archived)

### Recently completed (Steps 40–44)
- **Step 40 completed:** normalized operator response shape for `/runs`, `/runner_status`, `/risk_review` and centralized HTML-safe rendering contract.
- **Step 41 completed:** added read-only paper position/PnL snapshot helper and `/pnl_review` operator command, including input/correctness hardening.
- **Step 42 completed:** added market-data provider boundary (`MARKET_DATA_PROVIDER`) with `yfinance` baseline and deterministic `mock` provider.
- **Step 43 completed:** normalized operator/review human-facing timestamp display to HKT while preserving storage/log timestamp semantics.
- **Step 44 completed:** aligned merged/completed documentation status for Steps 40–43, hardened deployment/config documentation clarity (webhook vs runner topology, HKT schedule baseline, provider/mock policy, GitHub vs Railway responsibilities), and normalized backlog wording/state.

### Earlier completed foundations
- Step 1–12 baseline (documentation foundation, signal framework, dedup, run lifecycle, modularization, tests, Telegram MVP/hardening).
- Steps 13–20 baseline (traceability hardening, observability JSON, CI gating, notification schema guardrails, platform docs, Supabase access model, decision ledger v1).
- Steps 21–39 baseline (paper-trading risk/review surfaces, operator docs/runbooks, webhook ingress, `/risk_review`, dual-service deployment docs, runner observability, `/runner_status`, HTML/timezone hardening follow-ups).

## Notes
- `docs/status.md` is the merge/completion system-of-record for step state.
- This backlog tracks remaining actionable work only; completed items are archived for context.
- No backlog item authorizes autonomous live-money execution.
