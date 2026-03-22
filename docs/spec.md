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

## Delivery Semantics Observability Evidence (Step 46 baseline)
### System-of-record separation
- **Known current behavior:** Telegram daily summary remains best-effort/non-blocking with dedup-aware send-attempt semantics; operator commands remain synchronous read-only replies over webhook.
- **Verifiable evidence surfaces:** Telegram observed messages, `runs.delivery_summary_json`, runner lifecycle logs (`started`/`completed`/`failed` + `execution_summary`), and relevant `runs` records.
- **Evidence detail caveat:** `delivery_summary_json` currently provides generic attempt/success/failure/skip outcomes; explicit dedup read/write fallback activation is currently log-only evidence.
- **Unresolved gaps:** cross-surface correlation still depends on manual operator review and timestamp/run-id matching.
- **Future follow-up:** runtime instrumentation/trace-correlation improvements are deferred to a later approved runtime step (not this docs-only step).

### Operator evidence checklist (executable review flow)
1. **Normal daily summary delivery**
   - Confirm one expected summary message is visible in operator Telegram chat for the run date.
   - Confirm the matching run record exists and `delivery_summary_json` includes a summary-attempt outcome consistent with sent success path.
   - Confirm runner logs show run completion with `execution_summary.status=success` (or equivalent successful completion context).
2. **Rerun scenario**
   - Trigger/inspect a same-date rerun context.
   - Confirm either (a) a second summary appears when no prior SENT marker existed yet, or (b) dedup-skip evidence appears when prior SENT marker existed.
   - Confirm `runs.delivery_summary_json` and runner logs align with the observed rerun outcome.
3. **Duplicate skipped scenario**
   - For rerun with persisted SENT marker, confirm no additional summary appears in Telegram.
   - Confirm `delivery_summary_json` includes dedup-skip semantics (`skip_reason=dedup_already_sent`).
   - Confirm run record/lifecycle remains successful even when delivery is skipped.
4. **Dedup persistence failure scenario**
   - Confirm runner logs indicate dedup read/write failure fallback was activated.
   - Confirm system still attempts delivery (non-blocking degradation) and run lifecycle remains reviewable.
   - Treat possible duplicate message as expected-under-failure only when fallback evidence is present.
5. **Operator command reply vs summary delivery distinction**
   - Verify command replies (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/help`) are webhook-triggered read-only responses and can succeed/fail independently from daily summary send path.
   - Verify summary-delivery evidence is reviewed per run, while command-reply evidence is reviewed per inbound command event/log line.
