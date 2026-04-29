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
- Operator commands (`/runs`, `/runner_status`, `/risk_review`, `/pnl_review`, `/outcome_review`, `/help`) are read-only review surfaces and do not mutate strategy, paper-trading decisions, or execution state.
- Operator command `/daily_review` provides a short daily operator review packet by aggregating existing read-only surfaces (`/runner_status`, `/pnl_review`, `/outcome_review`) into one compact status view; packet fields include `business_date_hkt`, `latest_run_time_hkt`, `daily_review_health`, `next_action_hint`, and `detail_commands`; partial no-data/internal-error is section-scoped and should not fail the full packet unless command-level processing itself fails.
- `/daily_review` health/hint fields are operator readiness/data-availability signals only (not buy/sell/hold advice), and the command remains read-only within paper-trading decision-support boundaries.
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

## Delivery Semantics Minimal Runtime Instrumentation v2 (Step 50)
### System-of-record separation
- **Implemented minimal runtime scope (this step):**
  - add `dedup_persist_result` into daily summary delivery telemetry and persist into `runs.delivery_summary_json`.
- **Bounded semantics (no behavior mutation):**
  - `dedup_persist_result=persisted` when Telegram summary delivery succeeds and SENT dedup marker persistence succeeds.
  - `dedup_persist_result=persist_failed` when Telegram summary delivery succeeds but SENT dedup marker persistence fails.
  - `dedup_persist_result=not_applicable` when no dedup marker persistence attempt is applicable (for example dedup-skip path, send failure, or no persistence target/client context).
- **Summary projection contract (operator triage baseline):**
  - app-side `runs.delivery_summary_json` projection carries:
    - `correlation_id`,
    - `dedup_check_result`,
    - `dedup_persist_result`.
- **Explicit non-goals preserved:**
  - no `delivery_phase`,
  - no DB migration,
  - no queue/retry framework work,
  - no Telegram send-path refactor,
  - no broad telemetry redesign,
  - no strategy logic change,
  - no paper-trading logic change.

### Platform ownership for this step
- **GitHub (changed in Step 50):** runtime code + focused tests + docs/backlog/status/system-of-record updates for `dedup_persist_result`.
- **Railway (no change in Step 50):** no service topology, cron, runtime env var, webhook, or deployment-process modification is required.

## Paper-trading analytics follow-up scoping (Step 54, docs-only)
### Selected minimal increment
- **Increment chosen:** `win/loss and holding-period summary` for **closed paper trades only**.
- **Reason for selection:** this slice is directly useful for strategy performance review, can be computed from existing persisted paper-trading records, and stays within a minimal docs-first scope without changing runtime behavior.

### Operator/reviewer questions this increment answers
1. For already-closed paper trades, how often did outcomes finish positive vs negative?
2. What is the typical holding period before exits (median/p50, p75, max)?
3. Which symbols contribute the largest realized wins/losses in the review window?
4. Is current observed outcome quality concentrated in a few names or broadly distributed?

### Current-feasible-now data dependencies
Primary dependency (sufficient for the minimal increment):
- `paper_trades`
  - `stock`, `action`, `trade_date`, `quantity`, `price`, `realized_pnl`, `run_id`, `id`.
  - Use BUY/SELL replay pairing per ticker with deterministic ordering (`trade_date`, then `id`) to derive closed-trade outcomes and holding days.

Optional context join (not required for minimal metric computation):
- `paper_trade_decisions`
  - `run_id`, `stock_id`, `signal_action`, `human_decision`, `paper_trade_status`, `created_at`.
  - Can annotate review slices later, but **not required** for Step 54 minimal output.

Already sufficient now:
- Closed-trade realized PnL and action chronology are available from `paper_trades`.
- Deterministic replay ordering contract already exists in current paper-trading review logic.

Insufficient now (explicitly deferred as future follow-up, no scope expansion in this step):
- No explicit benchmark/alpha context (cannot conclude market-relative skill).
- No transaction-cost stress scenarios beyond current deterministic fee model.
- No dedicated lifecycle linkage between specific decision-ledger rows and eventual closed-trade outcomes for full decision-to-outcome attribution.
- No regime labeling (trend/range/high-volatility buckets) for context-specific interpretation.

### Minimal metric definitions (for future implementation contract)
- **Review scope:** closed trades only (open positions are excluded from win/loss and holding-period denominator).
- **Closed-trade unit:** one completed round-trip derived from deterministic BUY->SELL pairing in replay order (`trade_date`, then `id`) within each ticker stream.
- **Core metrics:**
  - `closed_trade_count`: number of paired closed trades in window.
  - `win_count`: number of closed trades with `realized_pnl > 0`.
  - `loss_count`: number of closed trades with `realized_pnl < 0`.
  - `flat_count`: number of closed trades with `realized_pnl == 0` (must be shown explicitly to avoid denominator ambiguity).
  - `win_rate`: `win_count / closed_trade_count` (when `closed_trade_count > 0`; else report `N/A`).
  - `median_holding_days`: median calendar-day span from entry BUY date to exit SELL date for each closed trade.
  - `p75_holding_days`, `max_holding_days`: distribution context for tail risk/readability.
- **Top contributors view (bounded):**
  - Top realized winners/losers are ranked by cumulative realized PnL contribution in the selected window, with explicit count limit (for example top 5 each side).

### Validation rubric (docs-only acceptance target for future implementation step)
Usefulness validation:
1. Operator can answer win/loss ratio and median holding period for a selected review window without manual ledger reconstruction.
2. Output includes at least: `closed_trade_count`, `win_count`, `loss_count`, `win_rate`, `median_holding_days`, and top realized winners/losers.
3. Results are deterministic for the same database snapshot (stable ordering + stable pairing contract).

Output clarity validation:
- All percentages and counts use explicit denominator labels (for example `win_rate = win_count / closed_trade_count`).
- Empty-window behavior is explicit (`closed_trade_count=0` with clear “no closed trades in window” wording).
- Date window/timezone basis is explicitly stated in output docs (storage UTC semantics, review display semantics noted).
- Output includes explicit note that `flat_count` exists and why `win_count + loss_count` may be smaller than `closed_trade_count`.
- Top winners/losers section states ranking basis (`realized_pnl`) and tie-break policy (stable deterministic ordering).

Interpretation-risk reminders required in operator-facing docs:
- Win rate alone is insufficient; must be read together with payoff magnitude and holding-period distribution.
- Small sample windows are unstable and can be misleading.
- Results are paper-trading evidence, not proof of live-trading profitability.
- Concentrated gains/losses in a few symbols can distort aggregate conclusions.

Required limitation statements in docs:
- This increment is review/diagnostic only and must not alter strategy decisions or execution behavior.
- No real-money execution or recommendation automation is introduced.
- No causal claim is made between AI signal quality and realized outcomes without broader attribution controls.
- Round-trip pairing is a simplified review model and should not be interpreted as tax/accounting-grade lot matching.

### Step 54 non-goals (explicit)
- No strategy rule changes.
- No real-money execution path changes.
- No large analytics implementation in this step.
- No deployment topology/runtime behavior changes.
- No Telegram wording backlog changes mixed into this scope.

## Paper-trade outcome summary implementation (Step 55, bounded runtime slice)
### Implemented review surface (single minimal surface)
- Added one read-only Telegram operator command: `/outcome_review`.
- Command returns deterministic closed-trade outcome summary from persisted `paper_trades` only.
- This is a bounded review/diagnostic surface; it does not mutate strategy, ledger, or execution state.

### Deterministic implementation contract
- **Closed paper trades only:** open inventory is excluded from all outcome denominators.
- **Pairing order:** BUY/SELL replay is deterministic by `trade_date`, then `id`, with FIFO lot matching within ticker.
- **Stable ordering + tie-break:**
  - Top winners: cumulative realized PnL desc, then ticker asc.
  - Top losers: cumulative realized PnL asc, then ticker asc.
- **Empty-window behavior:** explicit `closed_trade_count=0`, `win_rate=N/A`, and clear no-closed-trades note.
- **Denominator-safe wording:** output carries explicit formula label `win_count / closed_trade_count`.

### Minimum metric output contract (implemented)
- `closed_trade_count`
- `win_count`
- `loss_count`
- `flat_count`
- `win_rate` (or `N/A` when denominator is zero)
- `median_holding_days`
- `p75_holding_days`
- `max_holding_days`
- `top_realized_winners`
- `top_realized_losers`

### Step 55 explicit non-goals preserved
- No strategy rule change.
- No real-money execution behavior.
- No attribution redesign.
- No benchmark/regime overlays.
- No DB schema migration.
- No deployment topology change.

### Platform ownership for this step
- **GitHub (changed in Step 55):** bounded helper/service logic, focused tests, operator command wiring, and docs synchronization.
- **Railway (no change in Step 55):** no service split, cron, env-variable contract, webhook topology, or deployment-process change required.

## Outcome review windowing + runbook alignment (Step 56, bounded runtime slice)
### Implemented review-surface increment (minimal grammar)
- `/outcome_review` keeps existing default behavior (all available rows in current snapshot).
- `/outcome_review <days>` adds an optional bounded integer review window.

### Window contract (deterministic, read-only)
- Window anchor is the latest available `paper_trades.trade_date` in the fetched snapshot.
- Closed-trade inclusion basis is paired exit `trade_date` (`SELL` side of each deterministic closed trade).
- When `<days>` is provided, include closed trades where `exit trade_date >= anchor - (days - 1)`.
- Pairing contract remains unchanged: deterministic BUY/SELL replay by `trade_date`, then `id`, with FIFO lot matching per ticker.

### Input validation contract
- Accepted `<days>` range: `1..365` (inclusive).
- Non-integer token returns explicit usage error.
- Out-of-range integer returns explicit bounded-range usage error.

### Output wording continuity requirements
- Keep denominator-safe wording (`win_count / closed_trade_count`) unchanged.
- Keep explicit empty-window wording (`no closed paper trades in review window`) unchanged under window filter.
- Keep review boundary note (`review/diagnostic only; paper-trading decision support only`) unchanged.

### Step 56 explicit non-goals preserved
- No analytics-type expansion.
- No attribution redesign.
- No benchmark/regime overlays.
- No DB schema migration.
- No Telegram command-registration changes.
- No Railway deployment topology changes.

### Platform ownership for this step
- **GitHub (changed in Step 56):** bounded command parsing, read-only window filter wiring, focused tests, and docs wording alignment.
- **Railway (no change in Step 56):** no service split/cron/env/webhook/deployment-process mutation required.

## Operator surface consistency + wording normalization (Step 57, bounded runtime slice)
### Scope boundary (existing commands only)
- Reviewed and minimally normalized wording/output consistency for:
  - `/runs`
  - `/runner_status`
  - `/risk_review`
  - `/pnl_review`
  - `/outcome_review`
- No new command, no analytics expansion, no strategy/paper-trading logic mutation, no DB schema change, and no Telegram command-registration change.

### Stock display policy (operator-facing contract)
- Prefer `stock_name + stock_id` when both are available.
- Explicit fallback when stock name is unavailable: `stock_id=<id> | name_unavailable`.
- Never imply stock name exists when source data does not provide it.
- Keep implementation bounded to existing response rendering paths (no market metadata integration work in this step).

### Wording normalization contract
- **Usage/invalid input:** normalize to explicit `Usage: ...` plus bounded `Invalid input: ...` reason where applicable.
- **No-data/empty-window:** normalize around `no matching records ...` phrasing while preserving command-specific context.
- **Review boundary/denominator safety:** preserve existing outcome-review denominator-safe formula wording and review-boundary statement.

### Platform ownership for this step
- **GitHub (changed in Step 57):** bounded Telegram operator rendering/parsing wording updates, focused tests, and docs synchronization.
- **Railway (no change in Step 57):** no topology, cron, env-var contract, webhook routing, or deployment-process change required.


## Operator runbook examples baseline (Step 58, docs-only)
- Operator runbook examples are now explicitly aligned with Step 57 normalized wording for normal/no-data/invalid-input paths.
- `/pnl_review` command-output examples must follow stock-display fallback policy exactly:
  - when available: `stock_name=<name> | stock_id=<id>`
  - fallback: `stock_id=<id> | name_unavailable`
- Runbook examples remain read-only interpretation guidance and do not authorize runtime behavior changes, Telegram command behavior changes, or real-money execution.
