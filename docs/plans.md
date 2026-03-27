# Project Plans

`plans.md` is the source-of-truth roadmap for milestone execution.

## Milestone 1: Documentation Foundation
Define and maintain core execution docs (`spec`, `plans`, `status`, `implement`) so future Codex work remains consistent and traceable.

### Validation
- Confirm required docs exist: `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, `docs/status.md`, and `docs/implement.md`.
- Confirm `AGENTS.md` requires pre-work reading of `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, and `docs/status.md` for non-trivial work.
- Confirm `AGENTS.md` requires updating `docs/status.md` after each completed task.
- Confirm every merged step is followed by documented dual acceptance checks:
  - **Post-merge QA Check** (output/function behavior, error/success paths, display/docs/tests consistency).
  - **Post-merge Domain Check** (AI HK investing-system alignment, paper-trading/decision-support boundary, calculation/interpretation risk review).
- Confirm no runtime behavior files (for example `main.py`) are modified during documentation-only tasks.

## Milestone 2: Signal Framework Definition
Document candidate signal categories, data assumptions, and risk constraints for Hong Kong equities.

### Validation
- Verify each signal category has explicit assumptions and intended use.
- Verify constraints and caveats are documented for human review.
- Verify language remains consistent with human-final-decision governance in `docs/spec.md`.

## Milestone 3: Paper-Trading Evaluation Loop
Define a paper-trading protocol for measuring signal quality and operational discipline.

### Validation
- Verify evaluation metrics and review cadence are documented.
- Verify no live-trading automation is introduced without explicit approval.
- Verify paper-trading outcomes can be reviewed and traced in a repeatable way.

## Milestone 4: Controlled Production Hardening
Improve reliability and observability while keeping human-in-the-loop decision authority.

### Validation
- Verify production flow remains stable and reproducible.
- Verify rollout and rollback procedures are documented.
- Verify controls continue to prevent autonomous real-trade execution.
