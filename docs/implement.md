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
5. Update `docs/status.md` with results and next approved task.
6. Commit with a clear milestone/task summary.
