# Implementation Runbook (Codex)

## Purpose
Provide a consistent execution workflow for long-horizon Codex contributions.

## Core rules
- `docs/plans.md` is the source of truth for milestone sequence and scope.
- Work on one milestone at a time.
- Keep diffs small and tightly scoped to the current task.
- Validate outcomes after each milestone before moving forward.
- Do not break Railway production flow.
- Update `docs/status.md` after each completed task.
- If validation fails, stop progression and repair issues before continuing.

## Standard execution loop
1. Read `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, and `docs/status.md`.
2. Select the next approved milestone task from `docs/status.md`.
3. Implement only the scoped change for that task.
4. Run validation checks defined in `docs/plans.md`.
5. If any validation fails, stop and repair before taking new scope.
6. Update `docs/status.md` with what was completed, what was validated, and the next approved task.
7. Commit with a clear milestone/task summary.


## Step 15 implementation note (structured observability JSON)
- Add nullable `runs.error_summary_json` and `runs.delivery_summary_json` via migration.
- Keep legacy text `error_summary` and category text summaries unchanged for backward compatibility.
- Build structured ticker/stage error records and Telegram delivery telemetry in Python, then persist on run finalization in best-effort updates.
- Guardrail: telemetry writes are observability-only and must never block signal generation, dedup persistence, paper-trading, or Telegram delivery attempts.
