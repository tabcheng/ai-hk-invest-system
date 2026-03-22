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

## Delivery Semantics Runtime Instrumentation Scoping (Step 47 proposal, docs-only)
### System-of-record separation
- **Current known gap (baseline reality):**
  - dedup fallback activation (for example dedup check/persist failure -> send-attempt degradation) is primarily log-only evidence and is not consistently represented as first-class structured run-level fields.
  - `runs.delivery_summary_json` has useful high-level outcome fields, but currently lacks phase-level and correlation-level detail needed for low-friction rerun/retry forensic review.
  - Telegram observed outcome (message seen or not seen) and run record evidence still require manual correlation by date/run id/timestamp context.
- **Scoping proposal (this step):**
  - define a minimal future instrumentation candidate set that improves dedup/rerun/retry/fallback traceability without changing send-path semantics.
  - prioritize candidates by observability value vs implementation risk and keep scope tightly bounded.
- **Not-yet-approved runtime change:**
  - no runtime implementation is approved in this step; all items below are proposal-only and require a dedicated future runtime step before code/schema changes.
- **Future follow-up:**
  - after explicit approval, implement only P0/P1 candidates first with focused validation against Telegram observed outcomes + `runs.delivery_summary_json` + runner logs.

## Delivery Semantics Minimal Runtime Instrumentation v1 (Step 48)
### System-of-record separation
- **Implemented minimal runtime scope (this step):**
  - add `correlation_id` into daily summary delivery telemetry and persist into `runs.delivery_summary_json`.
  - add `dedup_check_result` into daily summary delivery telemetry and persist into `runs.delivery_summary_json`.
- **Bounded semantics (no behavior mutation):**
  - `dedup_check_result=send_path` for normal send-attempt flow.
  - `dedup_check_result=dedup_skip` when dedup marker indicates already sent and send is skipped.
  - `dedup_check_result=dedup_check_fallback` when dedup check path fails and runtime degrades to best-effort send-attempt flow.
- **Cross-surface traceability intent:**
  - `correlation_id` is designed to align runner logs, `runs.delivery_summary_json`, and operator-observed Telegram outcomes during review/troubleshooting.
- **Explicit non-goals preserved:**
  - no DB migration,
  - no queue/retry framework work,
  - no Telegram send-path refactor,
  - no broad `delivery_summary_json` redesign,
  - no strategy logic change,
  - no paper-trading logic change.

## Delivery Semantics Follow-up Scope Refinement (Step 49, docs-only)
### Post-Step-48 gap reassessment
1. **Correlation gap is narrowed but not eliminated.**
   - `correlation_id` now improves run/log/summary joins, but root-cause attribution for duplicate-risk windows still depends on whether dedup marker persistence succeeded.
2. **Dedup write-path evidence remains the highest-confidence missing signal.**
   - `dedup_check_result` explains read/check outcomes, but operators still infer dedup-persist success/failure indirectly from mixed logs + observed Telegram outcomes.
3. **Phase-level progression remains useful but currently secondary.**
   - richer phase telemetry can improve narrative readability, yet the highest triage friction after Step 48 is still SENT-marker write certainty.

### Candidate comparison: `dedup_persist_result` vs `delivery_phase`
| Candidate | Value | Risk | Scope | Implementation complexity | Operator usability payoff |
|---|---|---|---|---|---|
| `dedup_persist_result` | Adds direct evidence for SENT-marker write success/failure and clarifies expected duplicate-under-failure windows. | Low-to-medium risk: semantics must stay bounded (for example `persist_ok`, `persist_failed`, `persist_skipped`) and should avoid overlap with existing fields. | Single-field telemetry increment in existing delivery summary context; no send-path semantics change. | **Lower**: small enum + projection wiring + focused tests; no broad phase contract design required. | **High immediate payoff** for on-call/operator triage because duplicate suspicion can be quickly separated into expected-under-failure vs anomalous behavior. |
| `delivery_phase` | Improves narrative traceability by exposing progression stages (`dedup_check`, `send_attempt`, `dedup_persist`, etc.). | Medium risk: phase taxonomy drift, backward-compat expectations, and potential over-expansion pressure in later steps. | Requires phase vocabulary/ordering contract decisions and careful docs/test alignment to keep stability. | **Medium**: needs schema vocabulary decisions + multi-phase emission coverage + compatibility policy. | **Medium payoff**: helpful for deeper diagnostics but less decisive than persist-result for immediate duplicate triage. |

### Single next-slice recommendation
- **Recommend next implementation slice: `dedup_persist_result` only.**
  - Rationale: highest signal-to-scope ratio after Step 48, directly addresses remaining dedup observability ambiguity, and keeps implementation bounded.
- **Defer `delivery_phase` as a subsequent candidate (not parallelized with next slice).**
  - Revisit only after `dedup_persist_result` evidence proves insufficient for operator workflows.

### Step 49 guardrails (unchanged)
- This step is docs/spec/refinement only; **no runtime implementation**.
- **No new telemetry field is added in this step** (recommendation only).
- **No schema change** and **no DB migration**.
- **No Telegram send-path refactor**.
- **No queue/retry framework introduction**.
- **No strategy or paper-trading logic change**.
- Continue paper-trading / decision-support governance only; no autonomous real-money execution.

### Platform ownership for this step
- **GitHub (changed in Step 49):** docs-only updates for post-Step-48 gap reassessment, candidate comparison, and single-slice recommendation.
- **Railway (no change in Step 49):** no service topology, cron, runtime env var, webhook, or deployment-process modification is required.
