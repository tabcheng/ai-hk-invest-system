# AI Team Operating Model (Step 134A)

## A. Purpose
- Define the official operating model for the **AI Hong Kong equity investing team**.
- This system is a **paper-trading decision-support** system.
- This system is **not** an autonomous trading system.
- Final real-money decisions are made by the **Human Operator** outside this system.
- The system does not connect to brokers, does not create real-money orders, and does not execute live trades.

## B. Team organization

### 1) Data & Monitoring Layer
- Market Data Desk / 市場資料部
- Data Quality Desk / 資料質素部
- Monitoring & Alert Desk / 監察與提示部

### 2) Research Layer
- Stock Selection Desk / 股票篩選部
- Technical Analyst / 技術分析部
- Fundamental Analyst / 基本面研究部
- News & Catalyst Desk / 新聞與事件部

### 3) Strategy & Portfolio Layer
- Strategy Research Desk / 策略研究部
- Paper Portfolio Desk / 模擬組合部
- Risk Desk / 風險管理部

### 4) Decision Layer
- AI Decision Advisor / AI 決策顧問
- Paper Investment Committee / 模擬投資委員會

### 5) Governance Layer
- Model Auditor / 模型稽核部
- Compliance & Boundary Desk / 合規與邊界部

### 6) Human Layer
- Human Operator / 人類操作員

## C. Role contracts (Purpose / Inputs / Outputs / Must not do / UI wording / Boundary)

### Market Data Desk / 市場資料部
- Purpose: maintain bounded market data snapshots for review.
- Inputs: provider feeds, run timestamps, symbol universe.
- Outputs: normalized market snapshots, freshness metadata.
- Must not do: strategy recommendation or order suggestion.
- UI wording style: `當時資料`, `資料時間`, `資料可能過舊`.
- Boundary notes: no raw vendor payload exposure in UI.

### Data Quality Desk / 資料質素部
- Purpose: assess sufficiency/completeness/consistency.
- Inputs: market snapshots, derived indicators, data lineage.
- Outputs: quality labels (`sufficient`, `partial`, `insufficient`), gap notes.
- Must not do: fabricate missing values or overstate confidence.
- UI wording style: simple status first, technical details in `查看技術資料`.
- Boundary notes: must flag `資料不足` before downstream conclusion.

### Monitoring & Alert Desk / 監察與提示部
- Purpose: run-state and risk-signal monitoring.
- Inputs: run lifecycle, review sections, risk snapshots, paper PnL.
- Outputs: alerts for stale data, runner failures, no-data, risk warnings, paper PnL movement, strategy review due.
- Must not do: suppress warning signals for cosmetic reasons.
- UI wording style: concise severity + action hint.
- Boundary notes: severity levels are `info`, `caution`, `warning`, `block`.

### Stock Selection Desk / 股票篩選部
- Purpose: select candidates into **AI Watchlist** only.
- Inputs: liquidity filters, volatility context, sector/watch constraints.
- Outputs: `watchlist_candidate`, `not_enough_data`, `avoid_for_now`, `needs_review`.
- Must not do: call outputs buy recommendations.
- UI wording style: `AI 觀察名單`, `只供模擬檢視`.
- Boundary notes: selection output is upstream research evidence only.

### Technical Analyst / 技術分析部
- Purpose: produce chart/indicator interpretation for review.
- Inputs: OHLCV history, indicator series, timeframe context.
- Outputs: trend/momentum/volatility commentary with evidence.
- Must not do: claim guaranteed outcomes.
- UI wording style: conclusion first, numbers second.
- Boundary notes: uncertain patterns must be labeled uncertain.

### Fundamental Analyst / 基本面研究部
- Purpose: summarize fundamental drivers and risk factors.
- Inputs: financial metrics, valuation context, sector comparables.
- Outputs: explainable assumptions and caveats.
- Must not do: unsupported valuation certainty claims.
- UI wording style: plain Chinese summaries, no jargon-heavy first layer.
- Boundary notes: missing filings/data must be explicit.

### News & Catalyst Desk / 新聞與事件部
- Purpose: track material events and catalysts.
- Inputs: structured news/event feeds, timestamped context.
- Outputs: catalyst summary, uncertainty/conflict markers.
- Must not do: rely on unverified rumors as facts.
- UI wording style: what happened / why relevant / uncertainty.
- Boundary notes: raw payload and secrets are never exposed.

### Strategy Research Desk / 策略研究部
- Purpose: maintain strategy hypotheses and `strategy_version`.
- Inputs: historical outcomes, review findings, audit notes.
- Outputs: strategy-improvement proposals and test plans.
- Must not do: auto-change production strategy.
- UI wording style: proposal + rationale + validation plan.
- Boundary notes: strategy changes require PR + review + tests + deploy.

### Paper Portfolio Desk / 模擬組合部
- Purpose: simulate paper allocation/position review.
- Inputs: paper decisions, risk constraints, paper PnL.
- Outputs: paper exposure summaries and simulation notes.
- Must not do: mutate real positions.
- UI wording style: `模擬`, `只供模擬檢視` prominently shown.
- Boundary notes: no real account linkage.

### Risk Desk / 風險管理部
- Purpose: risk gating for simulated decisions.
- Inputs: concentration, drawdown, volatility, data sufficiency.
- Outputs: risk flags, gating rationale.
- Must not do: bypass risk gates without explicit rationale.
- UI wording style: risk signal + next review action.
- Boundary notes: risk outputs are advisory in paper-only context.

### AI Decision Advisor / AI 決策顧問
- Purpose: synthesize all desk outputs into one advisory summary.
- Inputs: all layer outputs, alerts, quality flags.
- Outputs: one-line conclusion, can/cannot conclude, missing data, conflicts, learning notes, recommended next data/strategy improvements.
- Must not do: place orders, connect brokers, issue real-money instructions, autonomously change strategies.
- UI wording style: first-layer answer should be short and human-readable.
- Boundary notes: learning notes are proposals only.

### Paper Investment Committee / 模擬投資委員會
- Purpose: second review after AI Decision Advisor.
- Inputs: advisor summary, risk desk gates, portfolio context.
- Outputs: AI simulated decision only (`paper_watch`, `paper_skip`, `paper_hold`, `paper_buy_intent`, `paper_sell_intent`) and paper sizing suggestion only (`0%`, `very small`, `small`, `normal`, `reduce`).
- Must not do: create real orders, mutate real positions, imply real-money advice.
- UI wording style: must display `不建立訂單`, `不是真實買賣建議`.
- Boundary notes: sizing must be explainable and risk-gated.

### Model Auditor / 模型稽核部
- Purpose: audit model behavior quality and safety.
- Inputs: decision traces, model outputs, outcomes, boundary checks.
- Outputs: audit warnings on overconfidence, data sufficiency, unsupported conclusions, team-learning claims, hallucination risk, boundary violations.
- Must not do: hide critical audit findings.
- UI wording style: explicit warning with clear reason.
- Boundary notes: audit warnings feed governance review backlog.

### Compliance & Boundary Desk / 合規與邊界部
- Purpose: enforce product/domain safety boundaries.
- Inputs: UI text, Telegram outputs, Mini App payloads, logs.
- Outputs: compliance findings and boundary fixes.
- Must not do: allow broker/live/order wording drift.
- UI wording style: hard-boundary reminders always visible.
- Boundary notes: no raw initData/secrets/vendor payload exposure.

### Human Operator / 人類操作員
- Purpose: final reviewer and only real-money decision owner.
- Inputs: AI team outputs, journals, outcomes, risk/compliance notes.
- Outputs: human paper decision journal, and separate real trade decision outside system.
- Must not do: treat AI output as autonomous execution.
- UI wording style: direct action checklist for human review.
- Boundary notes: final live trade decisions are outside this system.

## D. Stock Selection Desk output contract
- `watchlist_candidate`
- `not_enough_data`
- `avoid_for_now`
- `needs_review`

## E. Strategy Research Desk contract
- Maintains strategy hypotheses and `strategy_version`.
- May propose strategy improvements.
- Must not auto-change production strategy.
- Any strategy change requires PR, review, tests, and deployment acceptance.

## F. Monitoring & Alert Desk contract
- Alert categories:
  - stale data alerts
  - runner failure alerts
  - no-data alerts
  - risk warnings
  - paper PnL movement alerts
  - strategy review due alerts
- Severity levels:
  - `info`
  - `caution`
  - `warning`
  - `block`

## G. AI Decision Advisor contract
- Produces:
  - one-line conclusion
  - can/cannot conclude
  - missing data
  - conflicts
  - learning notes
  - recommended next data/strategy improvements
- Must not:
  - place orders
  - connect brokers
  - issue real-money instructions
  - autonomously change strategies
- Learning notes are proposal-only.

## H. Paper Investment Committee contract
- Produces AI simulated decision only:
  - `paper_watch`
  - `paper_skip`
  - `paper_hold`
  - `paper_buy_intent`
  - `paper_sell_intent`
- May produce paper sizing suggestion only:
  - `0%`
  - `very small`
  - `small`
  - `normal`
  - `reduce`
- Sizing must be explainable and risk-gated.
- Must not create real orders.
- Must not mutate real positions.
- Must not imply real-money advice.

## I. Model Auditor checks
- overconfidence
- data sufficiency
- unsupported conclusions
- team-learning claims
- model hallucination risk
- boundary violations

## J. Compliance & Boundary Desk checks
- no broker/live/real-money wording
- no order-creation wording
- no raw initData/secrets/vendor payload
- paper-only boundary always visible
- Mini App / Telegram outputs remain safe

## K. Decision chain
Stock Selection
→ Market Data / Technical / Fundamental / News
→ Risk / Portfolio
→ AI Decision Advisor
→ Paper Investment Committee
→ AI simulated decision
→ Human Paper Decision Journal
→ Outcome Review
→ Strategy Review
→ Team Learning
→ Human final real-money decision outside system

## L. UI information hierarchy
1. User conclusion
2. Reason
3. Numbers
4. Technical details

First-layer UI must answer:
- What did the AI team find?
- Can we review this?
- Is data enough?
- What is the paper-only decision direction?
- What should the human operator review next?

Raw status / IDs / timestamps belong in `查看技術資料`.

## M. Hard boundaries (repeated)
- No broker integration.
- No live execution.
- No real-money execution.
- No autonomous execution.
- No real-money order creation.
- No simulated order creation unless explicitly designed as controlled paper-only flow in later step.
- No paper position mutation unless explicitly designed as paper-only flow in later step.
- No raw vendor payload.
- No frontend secrets.
- No raw Telegram initData.
