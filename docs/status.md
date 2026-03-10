# Project Status

## Last reviewed date
2026-03-10

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- Run-level observability is now added via a `runs` table lifecycle (`RUNNING` at start, terminal `SUCCESS`/`FAILED` at finish) without changing ticker processing scope.
- No autonomous live-trading execution is enabled.
- The human user remains the final decision-maker for all real trade actions.

## Current progress
- Milestone 1 (Documentation Foundation): completed and validated; required docs remain in place and workflow rules are preserved.
- Milestone 1 task (daily signal deduplication): refined to use single-write idempotency (`upsert` on conflict) and explicit duplicate-trigger logging without a pre-read query.
- Added rerun-safe migration SQL for the `signals_date_stock_unique` constraint, including deterministic duplicate-row cleanup (prefer `created_at`, then `id`) before constraint creation to protect `(date, stock)` at the database layer.
- Milestone 2 task (basic run-level observability): added `runs` table migration and minimal `main.py` run tracking so each Railway execution creates one run row and finalizes status with counters and optional error summary.
- Milestone 2 follow-up: corrected run counter accounting so terminal `FAILED` updates report `processed_tickers` and `failed_tickers` based on actual loop progress if execution aborts early.
- Execution runbook remains in place to enforce small scoped tasks and per-task status updates.

## Next approved task
- Continue Milestone 2 by documenting signal categories, assumptions, and risk constraints for Hong Kong equities.
