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

### Observability gap prioritization (current state)
1. **P0 — Correlation gap across surfaces**
   - Operators cannot reliably join Telegram outcome evidence to a specific delivery attempt/run-level lifecycle without manual timestamp matching.
2. **P1 — Dedup fallback evidence gap**
   - dedup check/persist fallback activation is not consistently queryable in one structured field and therefore increases incident triage effort.
3. **P1 — Delivery phase progression visibility gap**
   - current summary evidence emphasizes final outcome but under-represents intermediate phase transitions (prepare/check/persist/send/finalize) that explain why duplicates or skips occurred.
4. **P2 — Attempt granularity gap**
   - repeated attempts inside one run/rerun context lack a stable attempt identity surface that operators can quickly reference in docs/runbooks.

### Minimal instrumentation candidates (proposal-only; no implementation here)
| Candidate | Value | Risk / cost | Proposed priority | Scope notes |
|---|---|---|---|---|
| `correlation_id` | Creates one stable join key across run logs, delivery summary context, and Telegram observed troubleshooting notes; reduces manual matching overhead. | Low-to-medium risk (ID generation/propagation consistency). | **P0 recommend** | Start with per-run/per-delivery correlation, avoid global tracing framework in first increment. |
| `message_delivery_attempt_id` | Distinguishes multiple attempts in rerun/retry context and supports deterministic incident references. | Medium risk (attempt lifecycle definition drift if over-scoped). | **P1 recommend** | Keep local to delivery path only; do not extend to full queue/retry architecture. |
| `delivery_phase` | Makes phase progression explicit for auditability (`dedup_check`, `send_attempt`, `dedup_persist`, etc.). | Medium risk (phase vocabulary stability + backward compatibility expectations). | **P1 recommend** | Use small fixed enum set; avoid high-cardinality free-text stages. |
| `dedup_check_result` | Converts dedup-read outcome from inference/log-only to structured evidence (hit/miss/error). | Low risk if represented as bounded values. | **P1 recommend** | Keep values compact and semantically stable. |
| `dedup_persist_result` | Exposes whether SENT marker write succeeded/failed and clarifies duplicate-risk windows. | Low risk if bounded and optional. | **P1 recommend** | Critical for distinguishing expected duplicate-under-failure cases. |
| `fallback_activated` | Binary signal to quickly separate normal path vs degraded path incidents. | Low risk, but semantics must be precise to avoid noisy false positives. | **P2 conditional** | Consider only if value cannot be fully inferred from `dedup_*_result`; avoid redundant fields. |

### Candidates not currently recommended for first runtime increment
- full queue/retry orchestration metadata expansion (out-of-scope for minimal increment).
- Telegram send-path refactor to enforce exactly-once semantics (not required for current best-effort policy).
- broad delivery summary schema redesign (higher migration/compatibility risk than needed for first observability step).

### Explicit guardrails (Step 47)
- Do **not** implement runtime instrumentation in this step.
- Do **not** add DB migrations in this step.
- Do **not** modify `delivery_summary_json` schema in this step.
- Do **not** refactor Telegram send path in this step.
- Do **not** introduce queue/retry framework changes in this step.
- Do **not** change strategy logic in this step.
- Continue paper-trading / decision-support governance only; no autonomous real-money execution.

### Platform ownership for this step
- **GitHub (changed in Step 47):** docs-only system-of-record updates for gaps, prioritization, candidate instrumentation scope, and guardrails.
- **Railway (no change in Step 47):** no service topology, cron, runtime env var, webhook, or deployment-process modification is required.
