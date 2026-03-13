# Project Spec

## Objective
Build a long-horizon AI-assisted Hong Kong stock investing system with disciplined, repeatable workflows.

## Decision Model
- The final real trading decision always remains with the human user.
- AI-generated signals are used for disciplined decision support and for later paper-trading evaluation before any escalation in live usage.
- Decision records for paper-trading must explicitly separate AI signal output from final human decisions for audit and review.

## Non-Goals (current phase)
- Fully autonomous live trading without human approval.
- Frequent strategy churn without documented rationale.

## Operating Principles
- Emphasize consistency, auditability, and incremental improvement.
- Keep implementation and validation aligned with documented plans and status.
