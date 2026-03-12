# Project Status

## Last reviewed date
2026-03-12

## Current production behavior
- Runtime behavior remains the existing MVP script in `main.py` (Railway entry point), now as a thin entry into modularized runtime code under `src/`.
- Daily signal writes include database-backed deduplication on `(date, stock)` with idempotent write behavior.
- Run-level observability is preserved via a `runs` table lifecycle (`RUNNING` at start, terminal `SUCCESS`/`FAILED` at finish) without changing ticker processing scope.
- End-to-end run traceability is hardened: `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, and `notification_logs` now persist `run_id` linkage for single-run reconstruction.
- Run observability now separates failure categories (`ticker`, `post-processing`, `notification`) with per-category counts and summaries on `runs`.
- Run observability now also persists structured JSON payloads for categorized errors and Telegram delivery telemetry (`error_summary_json`, `delivery_summary_json`) while preserving legacy text summaries for compatibility.
- Delivery telemetry now models one daily-summary message attempt per run (not per ticker), and dedup skips are tracked as `skipped` rather than failed sends.
- Paper-trading v1 remains deterministic and gated to full ticker-success runs.
- Telegram daily summary remains best-effort and non-blocking.
- Telegram summary formatting is deterministic HTML and includes stock name + stock id labels.
- Telegram daily summary now uses a versioned internal payload schema (`schema_version: 1`) with renderer separation (payload build -> render -> send).
- Notification schema evolution now has explicit runtime guardrails: a current version constant, supported-version allowlist, centralized renderer dispatch map, guardrail consistency validation, and fail-fast unsupported handling.
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
- Post-review fix applied: notification delivery failures now enrich run observability fields without changing terminal run status semantics for core processing outcomes.
- Post-review fix applied: same-day rerun signal dedup now re-links existing `(date, stock)` signal rows to the current `run_id`, and intentionally disabled Telegram delivery no longer contributes notification failure counts.
- Follow-up traceability guardrail added: rerun signal relink path updates `run_id` only (not signal values), with test coverage for duplicate rows when `run_id` is absent.
- Step 15 completed: structured run observability JSON and delivery telemetry are now written best-effort during run finalization without changing signal/dedup/runtime semantics.
- Post-review Step 15 fix: run finalization now always persists delivery telemetry in the terminal run update (including successful notifications) while preserving non-blocking observability semantics.
- Post-review Step 15 fix: delivery telemetry schema is now explicitly message-attempt based in both notification output and run payload normalization (no ticker-level message list), with dedup skips counted as `skipped` not `failed`.
- Step 16 completed: added a conservative root `pytest.ini` for stable discovery and a GitHub Actions `tests` workflow that gates `pull_request` and `push` to `main` with `pytest`.
- Step 17 completed: introduced daily summary payload schema v1, schema-versioned renderer dispatch, and delivery telemetry context field `summary_schema_version` while preserving existing notification runtime semantics.
- Step 18 completed: codified schema evolution guardrails (current/supported version constants + centralized dispatch + fail-fast unsupported/misconfigured versions) and expanded tests/docs coverage without changing v1 send behavior.
- Post-review Step 17 fix: strengthened notification test guardrails with unsupported-schema renderer coverage and low-risk test cleanup (spacing/readability) without runtime behavior changes.
- Post-review Step 16 fix: CI now pins Python 3.10 (matching current repo test runtime) and enables pip caching for faster, more stable dependency installs without changing test behavior.

## Current documentation posture
- Core planning, status, architecture, and maintenance docs now form a traceable documentation stack for future Codex execution.
- Backlog clearly separates completed work from pending items and tracks follow-up notification work as active backlog.
- Runtime + docs now align on notification guardrails: best-effort delivery, deterministic formatting, and non-blocking failure posture.
- Traceability docs now align with runtime persistence: major daily artifacts can be audited back to a single run record.

## Next approved task
- Continue Milestone 4 hardening with operational governance follow-ups (notification schema v2+ policy, branch protection required checks verification, and remaining pytest/tooling normalization work if needed).
