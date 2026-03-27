# AGENTS.md

## Documentation-first workflow (required)
For any non-trivial task (anything beyond a tiny typo or formatting-only edit), read these files before doing implementation work:
1. `AGENTS.md`
2. `docs/spec.md`
3. `docs/plans.md`
4. `docs/status.md`

## Execution expectations
- Keep changes scoped to the approved task.
- Prefer small, reviewable diffs.
- After each completed task, update `docs/status.md` to reflect current state and next approved work.
- After every merged step, complete and record dual acceptance checks in docs:
  1. **Post-merge QA Check** (output/function behavior, error/success path clarity, display-docs-tests consistency).
  2. **Post-merge Domain Check** (AI HK investing-system alignment, paper-trading/decision-support boundary, calculation/interpretation risk scan).
- Preserve current runtime behavior unless a task explicitly authorizes runtime changes.
- For future code changes, add clear comments for non-obvious logic, data flow, constraints, and guardrails.

## Strategy guardrails
- The project goal is a long-horizon AI-assisted Hong Kong stock investing system.
- AI outputs are decision-support signals and never a replacement for user responsibility.
