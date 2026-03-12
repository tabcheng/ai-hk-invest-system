# Project Status

## Last reviewed date
2026-03-11

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py` (Railway entry point), now as a thin entry into modularized runtime code under `src/`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- Run-level observability is preserved via a `runs` table lifecycle (`RUNNING` at start, terminal `SUCCESS`/`FAILED` at finish) without changing ticker processing scope.
- End-to-end run traceability is hardened: `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, and `notification_logs` now persist `run_id` linkage for single-run reconstruction.
- Run observability now separates failure categories (`ticker`, `post-processing`, `notification`) with per-category counts and summaries on `runs`.
- Paper-trading v1 remains deterministic and gated to full ticker-success runs.
- Telegram daily summary remains best-effort and non-blocking.
- Telegram summary formatting is deterministic HTML and includes stock name + stock id labels.
- Daily-summary equity prefers run-date snapshots with explicit fallback labeling to latest snapshot when run-date data is unavailable.
- Daily-summary notifications include minimal cross-run dedup persistence so the same run-date summary is not repeatedly re-sent to the same target.
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

## Current documentation posture
- Core planning, status, architecture, and maintenance docs now form a traceable documentation stack for future Codex execution.
- Backlog clearly separates completed work from pending items and tracks follow-up notification work as active backlog.
- Runtime + docs now align on notification guardrails: best-effort delivery, deterministic formatting, and non-blocking failure posture.
- Traceability docs now align with runtime persistence: major daily artifacts can be audited back to a single run record.

## Next approved task
- Continue Milestone 4 hardening by implementing compact structured `error_summary` schema/versioning and adding project-level pytest configuration + CI test gating.
