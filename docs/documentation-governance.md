# Documentation Governance (Step 135G-DOC)

## Source of truth
- GitHub docs-of-record are the long-term project source of truth.
- Chat history, Codex prompts/tasks, PR comments, review comments, and informal discussions are working context only.
- Any decision that affects future implementation must be captured in docs-of-record.

## Must document
Any of the following changes/discussion conclusions must be captured in docs:
- product direction
- UI / IA / first-view contract
- backend read/write model
- API contract
- Supabase / Railway / Telegram behavior
- market data / vendor / data freshness
- AI token / LLM behavior / AI team behavior
- security / secrets / auth / authorization
- review gate / PR process
- tests / acceptance / smoke
- domain guardrails / paper-only boundary
- regulatory boundary

## PR documentation requirements
Every PR must state:
- docs read before implementation
- docs updated and why
- docs intentionally not updated and why
- docs/status impact
- docs/backlog impact
- whether new follow-ups were added to backlog
- whether post-deploy smoke is required

## Review gate
Do not approve if:
- code/UI/test behavior changed but relevant docs were not updated
- docs/status or docs/backlog contradict merged reality
- Codex/reviewer comments are unresolved
- outdated unresolved review threads remain
- CI failed or is still running
- domain guardrails are weakened
- runtime/Railway/Supabase changes lack acceptance path

## Post-merge closure
- Every merged PR must update status/backlog when step state changes.
- A merged step must not remain Active P0 / in progress.
- Post-merge QA Check and Post-merge Domain Check must be recorded.
