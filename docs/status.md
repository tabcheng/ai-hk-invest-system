# Project Status

## Last reviewed date
2026-03-11

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py` (Railway entry point), now as a thin entry into modularized runtime code under `src/`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- Run-level observability is preserved via a `runs` table lifecycle (`RUNNING` at start, terminal `SUCCESS`/`FAILED` at finish) without changing ticker processing scope.
- No autonomous live-trading execution is enabled.
- The human user remains the final decision-maker for all real trade actions.

## Current progress
- Milestone 1 (Documentation Foundation): completed and validated; required docs remain in place and workflow rules are preserved.
- Milestone 1 task (daily signal deduplication): refined to use single-write idempotency (`upsert` on conflict) and explicit duplicate-trigger logging without a pre-read query.
- Added rerun-safe migration SQL for the `signals_date_stock_unique` constraint, including deterministic duplicate-row cleanup (prefer `created_at`, then `id`) before constraint creation to protect `(date, stock)` at the database layer.
- Milestone 2 task (basic run-level observability): added `runs` table migration and minimal run tracking so each Railway execution creates one run row and finalizes status with counters and optional error summary.
- Milestone 2 follow-up: corrected run counter accounting so terminal `FAILED` updates report `processed_tickers` and `failed_tickers` based on actual loop progress if execution aborts early.
- Milestone 2 follow-up: made run observability best-effort so `create_run`/`update_run` failures are logged without interrupting signal generation or forcing post-processing failure.
- Milestone 2 implementation task (modular MVP refactor): split the single-file runtime into `src/config.py`, `src/data.py`, `src/signals.py`, `src/db.py`, `src/runs.py`, and `src/app.py`, while keeping `main.py` as the unchanged process entrypoint role.
- Milestone 2 implementation task (minimal test layer): added initial pytest coverage for signal generation behavior and signal payload building in `tests/test_signals.py` and `tests/test_payloads.py`.
- Milestone 2 follow-up (review fixes): expanded minimal signal tests to cover additional preserved MVP outcomes (`NO_DATA` and `HOLD`) to strengthen refactor regression safety without changing runtime strategy logic.
- Milestone 2 documentation layer: added product-definition docs for strategy semantics (`docs/strategy-spec.md`), paper-trading MVP rules (`docs/paper-trading-v1.md`), and prioritized follow-up backlog (`docs/backlog.md`) without runtime or infrastructure behavior changes.
- Milestone 2 documentation follow-up (review pass): tightened docs to match runtime-truth signal semantics exactly, made paper-trading v1 rules deterministic (input contract, ordering, ledger updates), and clarified prioritized backlog wording for implementation readiness.
- Milestone 3 implementation task (paper-trading v1 MVP): added deterministic paper-trading tables (`paper_trades`, `paper_daily_snapshots`, `paper_events`), implemented a minimal simulator under `src/paper_trading.py`, and wired execution to run after daily signal generation in `src/app.py` without changing signal-generation logic or Railway cron flow.
- Milestone 3 validation layer: added focused unit tests for BUY open, SELL close, HOLD event-only behavior, and duplicate-BUY skip behavior.
- Milestone 3 follow-up (review fixes): made daily paper-trading persistence rerun-safe by clearing same-day paper outputs before writing deterministic replacements, and separated ticker failure counting from post-processing failures in run finalization status payloads.
- Milestone 3 follow-up (execution gating): paper trading now runs only when all ticker signals succeed; runs with ticker-level failures skip paper trading with a clear logged reason while preserving separate ticker failure counters.

- Milestone 3 follow-up (test hardening): added app-level coverage to assert post-processing paper-trading failures do not change ticker failure counters and still surface in run `error_summary`.

## Next approved task
- Continue Milestone 3 hardening with end-to-end traceability improvements and structured `error_summary` schema work from `docs/backlog.md` P0.
