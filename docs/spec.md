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
- Market data access must pass through a replaceable provider boundary so sources can evolve without strategy/orchestration rewrites.

## Telegram / Operator Delivery Semantics (current reality)
- Telegram daily summary delivery is **best-effort** and **non-blocking**. Delivery outcomes must never block signal generation, persistence, or paper-trading evaluation.
- Daily-summary dedup identity is fixed to `(notification_date, target, message_type, status)`; readability/text updates do not change dedup identity.
- Retry/rerun behavior is expected to be mixed:
  - **No prior SENT marker:** a rerun can deliver another summary message for the same date.
  - **Prior SENT marker present:** later rerun is expected to be dedup-skipped (`skip_reason=dedup_already_sent`).
  - **Dedup check/persist failure:** system degrades gracefully to send-attempt path (possible duplicate delivery), then records observability for follow-up.
- Operator commands (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/help`) are read-only review surfaces and do not mutate strategy, paper-trading decisions, or execution state.
- This phase remains paper-trading/decision-support only. No autonomous real-money execution is authorized.

## Operator Expectation Baseline
- Normal expectation for one run date: operators usually see one daily run summary message plus command replies when they request review data.
- Expected/acceptable duplicate cases:
  - rerun before dedup marker is persisted;
  - near-simultaneous reruns racing on dedup marker persistence;
  - transport uncertainty where Telegram accepted delivery but dedup persistence failed.
- Suspicious/follow-up cases (should be reviewed with logs + `runs.delivery_summary_json`):
  - repeated duplicates across many runs/days with no corresponding rerun/retry context;
  - command replies repeatedly failing while webhook ingress remains healthy;
  - frequent `failed` delivery outcomes without infra/config changes.
