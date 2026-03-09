# Project Status

## Last reviewed date
2026-03-09

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- No autonomous live-trading execution is enabled.
- The human user remains the final decision-maker for all real trade actions.

## Current progress
- Milestone 1 (Documentation Foundation): completed and validated; required docs remain in place and workflow rules are preserved.
- Milestone 1 task (daily signal deduplication): refined to use single-write idempotency (`upsert` on conflict) and explicit duplicate-trigger logging without a pre-read query.
- Added rerun-safe migration SQL for the `signals_date_stock_unique` constraint to protect `(date, stock)` at the database layer.
- Execution runbook remains in place to enforce small scoped tasks and per-task status updates.

## Next approved task
- Begin Milestone 2 by drafting signal categories, assumptions, and risk constraints for Hong Kong equities.
