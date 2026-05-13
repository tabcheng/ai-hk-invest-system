# AI Risk Register Baseline (Step 135G-DOC)

## Current AI boundary
- AI generates analysis and paper/simulated decision-support only.
- Human operator makes all final real-money decisions outside the system.
- No broker connection.
- No live execution.
- No autonomous execution.
- No real-money order instruction.

## Risk categories
1. Hallucinated or unsupported analysis.
2. Stale / incomplete market data.
3. Overconfident simulated direction.
4. Prompt injection (if LLM/vendor integration is added).
5. Sensitive information disclosure.
6. Improper output handling.
7. Excessive agency / accidental execution semantics.
8. Overreliance on AI output.
9. Misleading UI wording.
10. Regulatory boundary drift.

## Required controls
- data source and timestamp display
- data freshness and limitation visibility
- data gap visibility
- risk gate
- human review requirement
- paper-only wording
- no broker/order/live execution wording
- technical details separation
- safe DOM output handling
- no secret exposure
- outcome review loop
- PR review/comment gate

## Before AI token / LLM provider integration
Before any AI token, LLM provider, RAG, embedding, or autonomous agent capability:
- update this risk register
- define prompt injection controls
- define sensitive disclosure controls
- define output validation/sanitization controls
- define excessive agency controls
- define rate/cost/unbounded-consumption controls
- define logging/redaction policy
- define human-review gate
- confirm no broker/live execution path
- update docs/status + docs/backlog + relevant spec/docs

## Reference basis
- OWASP LLM Top 10 includes Prompt Injection, Insecure Output Handling, Sensitive Information Disclosure, Excessive Agency, Overreliance, and related GenAI security risks.
- This is an internal project control document, not a security/regulatory certification claim.
