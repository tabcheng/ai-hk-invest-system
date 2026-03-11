# Documentation Maintenance Protocol

## Purpose
Define the recurring process that keeps project documents accurate, synchronized, and usable as a system of record.

## Core documents requiring regular review

### Tier 1 (must-review every completed task)
1. `docs/status.md` — authoritative current state and next approved task.
2. `docs/backlog.md` — prioritized pending work, completed markers, technical debt inventory.
3. `AGENTS.md` — workflow rules and execution guardrails for future Codex work.

### Tier 2 (must-review at milestone transitions)
4. `docs/plans.md` — milestone roadmap and validation expectations.
5. `docs/implement.md` — execution runbook consistency.
6. `docs/project-implementation-plan.md` — completed steps and active roadmap framing.
7. `docs/architecture-v3.md` — architecture truth and layer/module responsibilities.

### Tier 3 (must-review when strategy/evaluation scope changes)
8. `docs/spec.md` — objective/governance foundations.
9. `docs/strategy-spec.md` — strategy semantics and decision rules.
10. `docs/paper-trading-v1.md` — simulation contract and acceptance semantics.

## When maintenance should happen

### Event-driven maintenance (required)
- After each completed task (minimum: status + backlog updates).
- After any merged runtime behavior change (full impacted-doc sweep).
- After schema/migration changes (architecture + status + backlog cross-check).
- After production incident/recovery work (status and backlog remediation updates).

### Scheduled maintenance (recommended)
- Weekly lightweight documentation sync review.
- Milestone-end deep review before selecting next milestone scope.
- Monthly “system-of-record integrity” pass to remove drift and stale backlog items.

## Maintenance review checklist

### A) Reality alignment
- Confirm documented behavior matches current runtime behavior.
- Confirm “next approved task” matches highest-priority pending backlog/roadmap item.
- Confirm completed work is marked complete and no longer presented as active.

### B) Traceability quality
- Ensure status entries identify what changed and why.
- Ensure backlog items are explicit enough to execute without ambiguity.
- Ensure architecture/module mapping still reflects code structure.

### C) Guardrail integrity
- Confirm human-final-decision governance language remains intact.
- Confirm no document implies autonomous live trading.
- Confirm scope boundaries (Railway/Supabase/signal/paper-trading/Telegram behavior) are respected unless explicitly authorized.

### D) Maintainability quality
- Remove duplicate or contradictory statements.
- Keep milestone language concise, deterministic, and testable.
- Add/update implementation notes only where they improve future execution clarity.

## Ownership model
- Every task author is responsible for immediate Tier 1 updates.
- Milestone owner (or acting Codex maintainer) is responsible for Tier 2 coherence.
- Strategy owner/human decision-maker validates Tier 3 intent and governance consistency.

## Acceptance standard for “docs healthy”
Documentation is considered healthy when:
1. status/backlog/architecture are mutually consistent,
2. next work is explicit and prioritized,
3. completed work is clearly separated from pending,
4. no governance drift is present.
