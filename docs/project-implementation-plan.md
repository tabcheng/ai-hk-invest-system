# Project Implementation Plan (System-of-Record View)

## Purpose
This document is the maintainable implementation-plan layer that bridges:
- strategic intent (`docs/spec.md`, `docs/strategy-spec.md`),
- execution truth (`docs/status.md`), and
- queued work (`docs/backlog.md`).

It clarifies what is already complete, what is active, and what remains backlog-only.

## Completed implementation steps (1–12)

### Step 1 — Documentation foundation ✅
Established core operating docs and workflow discipline (`AGENTS`, spec/plans/status/implement alignment).

### Step 2 — Signal framework definition ✅
Documented strategy semantics and output classes for disciplined human decision support.

### Step 3 — Signal persistence dedup hardening ✅
Implemented idempotent signal persistence with `(date, stock)` uniqueness protection and rerun-safe migration logic.

### Step 4 — Run lifecycle observability baseline ✅
Added `runs` lifecycle tracking (`RUNNING` to terminal status) with core counters and error summary fields.

### Step 5 — Observability robustness fixes ✅
Improved failed-run counters for early aborts and made run tracking best-effort to avoid interrupting core signal generation.

### Step 6 — Runtime modularization ✅
Refactored monolithic flow into focused runtime modules under `src/` while preserving Railway entrypoint behavior.

### Step 7 — Minimal regression test layer ✅
Added focused pytest coverage for signal logic and payload behavior; expanded for preserved `HOLD` and `NO_DATA` semantics.

### Step 8 — Product-definition docs for strategy + paper trading ✅
Added and refined `docs/strategy-spec.md`, `docs/paper-trading-v1.md`, and backlog documentation for implementation readiness.

### Step 9 — Paper-trading v1 implementation ✅
Implemented deterministic paper-trading engine and persistence tables (`paper_trades`, `paper_daily_snapshots`, `paper_events`).

### Step 10 — Paper-trading execution hardening ✅
Added rerun-safe daily replacement writes, execution gating on full ticker success, and app-level tests for post-processing failure behavior.

### Step 11 — Telegram summary delivery MVP + hardening ✅
Added best-effort end-of-run Telegram summaries, deterministic run-date handling, and startup-failure notification attempt.


### Step 12 — Telegram notification hardening + docs maintenance review ✅
Upgraded summary readability (stock name + id, deterministic HTML), added run-date-first equity selection with fallback labels, and introduced minimal cross-run daily-summary dedup persistence while keeping delivery best-effort/non-blocking.

## Current state
- Production behavior is stable with modular runtime architecture and deterministic paper-trading pipeline.
- Signal generation remains unchanged in strategic semantics.
- Observability and notification pathways are present but still have known hardening opportunities (trace linkage, structured failure summaries).
- Documentation set now includes architecture and maintenance layers to improve continuity across future Codex tasks.

## Active roadmap (near-term execution)
These are expected next milestones for active implementation sequencing:
1. **Traceability milestone:** unify `run_id` linkage across run metadata, signals, and paper-trading outputs.
2. **Failure-intelligence milestone:** introduce structured `error_summary` schema and bounded categorization.
3. **Quality-gate milestone:** add project-level pytest config and CI lint/test enforcement.
4. **Notification hardening milestone:** ensure delivery-layer reliability and consistent summary semantics.

## Backlog vs active roadmap policy

### Active roadmap
- Items explicitly listed as “next approved task” in `docs/status.md`.
- P0 items in `docs/backlog.md` that are dependencies for reliability/traceability.

### Backlog (not yet active)
- P1/P2 improvements, exploratory analytics extensions, and non-blocking optimizations.
- Any item lacking explicit “next approved task” status remains queued, not in active execution.

## Planning boundaries
- Do not alter Railway/Supabase/signal-generation/paper-trading/Telegram runtime behavior without explicit approval.
- Keep changes small, reviewable, and milestone-scoped.
- Update status/backlog after every completed task so this plan remains true to delivered state.
