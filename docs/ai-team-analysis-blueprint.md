# AI Team Analysis Blueprint (Step 135A)

## 1) Purpose and Positioning
- This blueprint is the docs-of-record analysis contract for how the AI team analyzes **each stock / specified ticker** inside this system.
- Strategy-research companion docs-of-record: `docs/hk-equity-strategy-research-reference-20260512.md` (horizon policy, HK market characteristics, strategy families, scorecard/risk-gate framework, desk mapping).
- Product定位：這不是專業交易員 dashboard；這是給非專業人類操作員使用的 **AI 香港股票投資團隊工作台**。
- Internal analysis can use professional methods, but first-layer UI must stay simple Traditional Chinese and Cantonese-friendly.
- A non-professional operator should understand the **conclusion + risk + next review action** within ~10 seconds.
- Technical fields must be under `查看技術資料`.
- System boundary remains strict: paper-only, decision-support only.

## 2) Hard Boundaries (must always hold)
- No broker integration.
- No live execution.
- No real-money execution.
- No autonomous execution.
- No real-money order creation.
- No paper order creation in this docs-only step.
- No frontend secrets.
- No raw Telegram initData exposure.
- No vendor token exposure in frontend, browser, client-side code, logs, docs, Telegram messages, or chat.
- Backend-only vendor token usage is allowed only through approved provider abstractions and backend/server environment variables.

## 3) Cross-Desk Shared Vocabulary

### 3.1 Scorecard vocabulary (standard)
- Data Quality: `enough` / `partial` / `insufficient`
- Technical: `positive` / `neutral` / `negative` / `unclear`
- Fundamental: `supportive` / `unclear` / `weak` / `unavailable`
- Catalyst: `positive` / `neutral` / `negative` / `none` / `unavailable`
- Risk: `low` / `medium` / `high` / `unknown`
- Confidence: `low` / `medium` / `high`
- Simulated Direction: `positive observation` / `observe` / `cautious` / `insufficient`

### 3.2 Mandatory safety wording (UI)
- `只供模擬檢視`
- `不建立訂單`
- `不連接券商`
- `不是真實買賣建議`

## 4) Department-by-Department Analysis Contract

## 4.1 Market Data Desk
- **Purpose**: produce bounded, timestamped market snapshots per ticker.
- **Inputs**: monitored ticker list, provider snapshot, timestamp, freshness metadata, normalization rules.
- **Methods / professional techniques**:
  - ticker normalization (HK format consistency)
  - source/time/freshness validation
  - bounded field projection for downstream desks
- **Output contract**:
  - `market_snapshot` with symbol, price-related fields (if available), timestamp, freshness, source label
  - `market_data_status`: `ok` / `partial` / `unavailable`
- **Plain-language UI wording**:
  - `當時資料`、`資料時間`、`資料可能過舊`
- **Must not do**:
  - no recommendation wording
  - no fake value filling
  - no raw vendor payload exposure
- **Evidence / audit fields**:
  - `source`, `as_of_hkt`, `freshness`, `provider_status`, `normalization_note`

## 4.2 Data Quality Desk
- **Purpose**: classify whether data is enough for bounded interpretation.
- **Inputs**: market snapshot, technical inputs, fundamental inputs, catalyst inputs, missing-field map.
- **Methods / professional techniques**:
  - completeness checks
  - consistency checks
  - stale/unknown handling with conservative downgrade
- **Output contract**:
  - `data_quality`: `enough` / `partial` / `insufficient`
  - `missing_context_list`
  - `quality_reason_brief`
- **Plain-language UI wording**:
  - `資料足夠` / `資料部分不足` / `資料不足`
- **Must not do**:
  - must not overstate confidence when fields are missing
  - must not mask uncertainty
- **Evidence / audit fields**:
  - `required_fields_checked`, `missing_fields`, `stale_flags`

## 4.3 Monitoring & Alert Desk
- **Purpose**: detect stale/no-data/run anomalies and generate review alerts.
- **Inputs**: run status, section status, freshness flags, risk warnings.
- **Methods / professional techniques**:
  - health aggregation
  - alert severity classification
  - bounded next-action hints
- **Output contract**:
  - `alerts[]` with severity and short action hint
  - `monitoring_health`: `ok` / `attention_needed` / `unavailable`
- **Plain-language UI wording**:
  - `請留意`、`需要跟進`、`建議下一步`
- **Must not do**:
  - no suppression of risk/stale alerts
  - no execution-implying text
- **Evidence / audit fields**:
  - `alert_type`, `severity`, `generated_at_hkt`, `source_section`

## 4.4 Stock Selection Desk
- **Purpose**: select watchlist candidates for review, not trade action.
- **Inputs**: liquidity/coverage baseline, data quality status, watchlist policy.
- **Methods / professional techniques**:
  - eligibility screening
  - exclusion by insufficient data
  - explainable candidate tagging
- **Output contract**:
  - `selection_status`: `watchlist_candidate` / `not_enough_data` / `avoid_for_now` / `needs_review`
  - `selection_reason_brief`
- **Plain-language UI wording**:
  - `AI 觀察名單`、`先觀察`、`資料不足先不處理`
- **Must not do**:
  - no buy/sell instruction
- **Evidence / audit fields**:
  - `selection_rule_version`, `screening_notes`

## 4.5 Technical Analyst
- **Purpose**: provide bounded technical observation per ticker.
- **Inputs**: OHLCV series, technical indicators, timeframe context.
- **Methods / professional techniques**:
  - trend/momentum structure reading
  - volatility/range assessment
  - pattern ambiguity handling
- **Output contract**:
  - `technical_label`: `positive` / `neutral` / `negative` / `unclear`
  - `technical_observation_brief`
  - `technical_evidence_points[]`
- **Plain-language UI wording**:
  - `技術走勢偏正面/中性/偏弱/未明`
- **Must not do**:
  - no certainty claims
  - no hidden assumptions
- **Evidence / audit fields**:
  - `timeframe`, `indicators_used`, `as_of_hkt`

## 4.6 Fundamental Analyst
- **Purpose**: provide bounded business/fundamental context.
- **Inputs**: financial metrics, profitability/valuation context, sector notes.
- **Methods / professional techniques**:
  - driver-and-risk summary
  - comparative sanity check
  - explicit unavailable handling
- **Output contract**:
  - `fundamental_label`: `supportive` / `unclear` / `weak` / `unavailable`
  - `fundamental_observation_brief`
- **Plain-language UI wording**:
  - `基本面支持/未清楚/偏弱/未有資料`
- **Must not do**:
  - no hard target-price promises
- **Evidence / audit fields**:
  - `data_window`, `key_metrics_used`, `availability_state`

## 4.7 News & Catalyst Desk
- **Purpose**: summarize material events and potential catalysts.
- **Inputs**: timestamped news/event signals and relevance tags.
- **Methods / professional techniques**:
  - event relevance triage
  - conflict/uncertainty tagging
  - recency awareness
- **Output contract**:
  - `catalyst_label`: `positive` / `neutral` / `negative` / `none` / `unavailable`
  - `catalyst_observation_brief`
- **Plain-language UI wording**:
  - `近期消息偏正面/中性/偏負面/暫無`
- **Must not do**:
  - no rumor-as-fact
- **Evidence / audit fields**:
  - `event_time_hkt`, `relevance_reason`, `confidence_note`

## 4.8 Strategy Research Desk
- **Purpose**: maintain hypothesis and interpretation framework.
- **Inputs**: historical simulated outcomes, desk outputs, audit findings.
- **Methods / professional techniques**:
  - hypothesis lifecycle management
  - versioned strategy notes
  - retrospective refinement proposals
- **Output contract**:
  - `strategy_context_brief`
  - `strategy_review_flag` (if review due)
- **Plain-language UI wording**:
  - `策略角度：目前重點`、`後續檢討方向`
- **Must not do**:
  - no automatic production strategy mutation
- **Evidence / audit fields**:
  - `strategy_version`, `review_due_flag`, `change_proposal_ref`

## 4.9 Paper Portfolio Desk
- **Purpose**: situate ticker within paper portfolio context.
- **Inputs**: paper positions, exposure summary, paper PnL snapshots.
- **Methods / professional techniques**:
  - concentration review
  - exposure balance review
  - paper-only context annotation
- **Output contract**:
  - `portfolio_context_brief`
  - `exposure_signal` (bounded descriptive tag)
- **Plain-language UI wording**:
  - `模擬組合現況`、`倉位風險提示`
- **Must not do**:
  - no real position linkage
- **Evidence / audit fields**:
  - `paper_trade_only=true`, `position_snapshot_time_hkt`

## 4.10 Risk Desk
- **Purpose**: provide conservative risk interpretation.
- **Inputs**: volatility, concentration context, data quality status, catalyst uncertainty.
- **Methods / professional techniques**:
  - scenario-based risk grading
  - missing-data penalty
  - override caution policy
- **Output contract**:
  - `risk_label`: `low` / `medium` / `high` / `unknown`
  - `risk_brief`
- **Plain-language UI wording**:
  - `風險較低/中等/較高/未明`
- **Must not do**:
  - no bypass of missing-data caution
- **Evidence / audit fields**:
  - `risk_factors[]`, `risk_reason`, `data_penalty_applied`

## 4.11 AI Decision Advisor
- **Purpose**: synthesize all desk outputs into one simulated-direction statement.
- **Inputs**: outputs from desks 1–10 and active monitoring/audit signals.
- **Methods / professional techniques**:
  - cross-signal conflict resolution
  - confidence gating by data quality
  - concise recommendation framing for non-professional operator
- **Output contract**:
  - `simulated_direction`: `positive observation` / `observe` / `cautious` / `insufficient`
  - `confidence`: `low` / `medium` / `high`
  - `headline_summary`
  - `operator_next_actions[]`
- **Plain-language UI wording**:
  - `AI 模擬方向：偏正面觀察 / 繼續觀察 / 謹慎 / 資料不足`
- **Must not do**:
  - no real-money instruction
  - no execution language
- **Evidence / audit fields**:
  - `synthesis_inputs_ref`, `conflict_flags`, `confidence_reason`

## 4.12 Paper Investment Committee
- **Purpose**: second-layer committee review for paper-only decision framing.
- **Inputs**: AI Decision Advisor output, risk output, portfolio context.
- **Methods / professional techniques**:
  - committee-style challenge and consistency checks
  - conservative escalation discipline
- **Output contract**:
  - `paper_committee_view` (bounded simulated view)
  - `committee_reason_brief`
- **Plain-language UI wording**:
  - `模擬投資委員會意見`
- **Must not do**:
  - no order creation
  - no execution implication
- **Evidence / audit fields**:
  - `review_timestamp_hkt`, `review_notes_ref`

## 4.13 Model Auditor
- **Purpose**: audit quality, consistency, and hallucination/overclaim risks.
- **Inputs**: full analysis chain, confidence labels, missing-context handling.
- **Methods / professional techniques**:
  - trace review
  - overconfidence detection
  - unsupported-claim detection
- **Output contract**:
  - `audit_status`: `pass` / `needs_attention`
  - `audit_findings[]`
- **Plain-language UI wording**:
  - `模型稽核提示`、`需要人工覆核`
- **Must not do**:
  - no hiding critical finding
- **Evidence / audit fields**:
  - `finding_code`, `severity`, `evidence_ref`

## 4.14 Compliance & Boundary Desk
- **Purpose**: enforce product boundary and wording safety.
- **Inputs**: UI copy, API fields, alerts, committee/advisor phrasing.
- **Methods / professional techniques**:
  - boundary phrase scan
  - prohibited wording checks
  - secret exposure checks
- **Output contract**:
  - `boundary_status`: `pass` / `blocked`
  - `boundary_findings[]`
- **Plain-language UI wording**:
  - `安全邊界檢查`
- **Must not do**:
  - no relaxation of guardrails
- **Evidence / audit fields**:
  - `boundary_rule_version`, `blocked_reason`, `safety_wording_present`

## 4.15 Human Operator
- **Purpose**: final human reviewer and owner of any real trade decision outside this system.
- **Inputs**: first-layer dossier summary + technical details + audit/compliance flags.
- **Methods / professional techniques**:
  - human judgment check
  - interpretation sanity check
  - next-review scheduling
- **Output contract**:
  - `human_paper_decision_note` (future bounded journal context)
  - `next_review_plan`
- **Plain-language UI wording**:
  - `你下一步要睇乜`、`幾時再檢查`
- **Must not do**:
  - must not treat AI output as auto-trade instruction
- **Evidence / audit fields**:
  - `operator_review_time_hkt`, `operator_note_ref`

## 5) Stock Dossier v1 (required contract)
Per ticker, the first-layer dossier output uses:
- `headline_summary`
- `data_sufficiency`
- `technical_observation`
- `fundamental_observation`
- `catalyst_observation`
- `risk_brief`
- `portfolio_context`
- `simulated_direction`
- `operator_next_actions`
- `technical_details`
- `safety_note`

### First-layer display principle
- One-screen summary should let non-professional operator understand:
  1. 結論（而家係偏正面觀察 / 繼續觀察 / 謹慎 / 資料不足）
  2. 風險（低 / 中 / 高 / 未明）
  3. 下一步（要再睇咩、幾時再睇）
- Technical values/IDs remain inside `查看技術資料`.

## 6) Implementation Phases

### Phase 1
- deterministic read models first.

### Phase 2
- backend-only AI synthesis, if justified.

### Phase 3
- DB persistence for audit/outcome learning.

### Phase 4
- strategy review / team learning.

## 7) Explicit Non-Goals for Step 135A
- This step is docs-only.
- No runtime code changes.
- No Railway changes.
- No Supabase changes.
- No new vendor / AI token integration in this docs-only step.
- Existing backend-only vendor-token policy remains unchanged.
- No DB writes.
\n- Step 135E: Strategy Horizon Policy in Stock Dossier added deterministic horizon fields (recommended_review_horizon, short/medium/long policies, data states, data gaps, confidence notes, paper_decision_scope) and Stock Review "策略週期判斷" UI section; short-term remains monitoring/observation-only; no broker/order/live/real-money path.
