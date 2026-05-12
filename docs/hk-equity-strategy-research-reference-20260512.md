# HK Equity Strategy Research Reference (2026-05-12)

Source: 「港股 AI Team Analysis Blueprint 落地研究報告 20260512」  
Type: Long-term internal research reference (docs-of-record)  
Scope: AI team analysis + paper-only decision-support product design

## 1) Positioning and non-advice boundary
- This document is a **research reference**, not trading advice.
- It guides internal AI team analysis design, strategy design, and product-surface wording.
- The human operator remains the final real-money decision maker **outside** this system.
- The system remains **paper-only / decision-support only**.
- Always separate:
  1. AI simulated decision
  2. Human paper decision
  3. Real trade decision outside system

## 2) Strategy horizon policy
### Short-term horizon
- Requires fresher/intraday data and timing awareness.
- Sensitive to slippage, spread, queue position, and liquidity shocks.
- Current project phase stance: **monitoring / alert / observation only**.
- No short-term paper decision engine in current phase.

### Medium-term horizon
- Suitable for the current phase.
- Uses daily/weekly data, signals, risk context, paper portfolio context, and outcome review.
- Best fit for Stock Dossier + AI Decision Advisor v1 deterministic synthesis.

### Long-term horizon
- Suitable for the current phase.
- Requires fundamentals + valuation + earnings + cash flow + balance-sheet quality + sector/cycle context.
- Does not need tick-level execution data, but still needs freshness for announcements, earnings, suspensions, dividends, and policy/news changes.

### Recommended project stance
- Phase 1 focus: medium/long-term review.
- Short-term remains monitoring/alert/observation until data freshness, liquidity/slippage evidence, and execution-boundary controls mature.

## 3) Hong Kong equity market characteristics (strategy implications)
- High index/sector concentration can create crowding and correlated drawdowns.
- China/HK policy sensitivity can dominate short-window price behavior.
- Northbound/southbound flow matters for pressure and sentiment context.
- A-share/US linkage can transmit shocks across sessions.
- Liquidity dispersion is large across blue chips vs small caps.
- Announcement/event risk can reset valuation quickly.
- Gap risk and suspended-trading risk are material.
- HKD peg/rate and macro sensitivity influence valuation regimes.
- Sector rotation can be fast (internet/financials/property/consumption/healthcare/energy).

## 4) Data requirements by horizon
| Horizon | Required data | Nice-to-have | Freshness requirement | Data quality risk | Suitable now |
|---|---|---|---|---|---|
| Short-term | intraday bars/order-book proxy, spread/liquidity proxy, event calendar, halt/suspension flags | depth-of-book quality tiers, execution benchmark proxies | near-real-time/intraday | stale intraday or missing liquidity fields can invert decision meaning | No (observation only) |
| Medium-term | daily OHLCV + turnover, corporate actions, sector classification, paper portfolio/PnL/exposure, outcome review labels, strategy version + data timestamp | weekly flow proxy, catalyst summaries | daily close + latest available announcements | stale close labels, symbol mapping drift, action-adjustment errors | Yes |
| Long-term | earnings/financial statements, valuation ratios, cash flow, balance sheet quality, dividend history, HKEX announcement metadata | management quality proxy, cycle regime tags | report-cycle freshness + announcement monitoring | reporting lag, restatement drift, missing disclosure normalization | Yes |

Minimum evidence fields across all horizons:
- `strategy_version`
- `data_timestamp`
- `data_quality_state`
- explicit horizon tag
- outcome review linkage fields

## 5) Strategy families (HK equity applicability)
| Family | Why it may work | Main risks | Useful indicators | Suitable horizon | AI desk owner | Required guardrails |
|---|---|---|---|---|---|---|
| Trend / momentum | persistent repricing and sector leadership cycles | reversal/gap risk, crowded exits | relative strength, moving trend state, turnover trend | short/medium | Technical Analyst + Strategy Research Desk | liquidity/risk gate, no execution wording |
| Mean reversion (cautious) | overshoot after panic/forced de-risk | value trap, regime break | deviation bands, breadth, volatility state | short/medium | Technical Analyst | only with catalyst/risk confirmation |
| Value | valuation mean re-anchoring over longer windows | structural decline, policy shocks | P/E, P/B, FCF yield, earnings quality flags | medium/long | Fundamental Analyst + Stock Selection Desk | data freshness + governance check |
| Quality | durable business quality under uncertainty | overpaying for quality, style rotation | ROE stability, leverage quality, margin resilience | medium/long | Fundamental Analyst | concentration limits |
| Growth | earnings expansion and structural demand | valuation compression/rate sensitivity | revenue/earnings growth trend, reinvestment profile | medium/long | Fundamental + News/Catalyst Desk | valuation + risk-level gate |
| Low-vol / defensive | downside resilience in risk-off windows | lag in sharp risk-on rebound | beta/volatility, drawdown profile, stability buckets | medium/long | Risk Desk + Paper Portfolio Desk | avoid hidden illiquidity |
| Dividend / income | yield carry with cash-return discipline | dividend cuts, value traps | payout sustainability, cash flow cover, dividend history | medium/long | Fundamental Analyst | suspension/dividend-event checks |
| Event / catalyst | repricing around announcements/policy | headline whipsaw, binary outcomes | event calendar, earnings surprise context, policy-watch tags | short/medium | News & Catalyst Desk | mandatory uncertainty labeling |
| Risk-off / cash-preservation | avoids forced risk during unstable regimes | opportunity cost | market stress regime flags, drawdown monitor | all horizons | Risk Desk | can downgrade/block positive simulated direction |

## 6) AI team mapping (desk-by-desk impact)
- **Market Data Desk**: maintain horizon-tagged market/fundamental/catalyst feeds; publish freshness + timestamp evidence.
- **Data Quality Desk**: compute `data_quality_state`; enforce missing/lag/symbol-mapping checks.
- **Monitoring & Alert Desk**: generate short-term observation alerts only (no decision direction).
- **Stock Selection Desk**: create candidate universe + exclusions with sector/liquidity/risk context.
- **Technical Analyst**: produce technical_state and regime-aware signal notes.
- **Fundamental Analyst**: produce fundamental_state with valuation/quality context and lag caveats.
- **News & Catalyst Desk**: tag catalyst_state and uncertainty windows.
- **Strategy Research Desk**: evaluate which strategy family/horizon fits each ticker context.
- **Paper Portfolio Desk**: produce portfolio_exposure_state and diversification context.
- **Risk Desk**: assign risk_level/liquidity_state and block/downgrade gates when needed.
- **AI Decision Advisor**: synthesize multidimensional states into one bounded simulated direction proposal.
- **Paper Investment Committee**: review evidence consistency + risk gate outputs before paper direction acceptance.
- **Model Auditor**: verify wording, traceability, and feature/audit field completeness.
- **Compliance & Boundary Desk**: enforce no-broker/no-live/no-secret boundaries.
- **Human Operator**: final reviewer; real-money action stays outside system.

For each desk output, include evidence/audit fields:
- input source snapshot id or reference
- `strategy_version`
- `data_timestamp`
- horizon tag
- risk check outcome
- confidence band
- safety wording marker

## 7) Practical v1 scoring / feature framework
Use multi-dimensional scorecard fields (no single magic score):
- `data_quality_state`
- `technical_state`
- `fundamental_state`
- `catalyst_state`
- `risk_level`
- `liquidity_state`
- `portfolio_exposure_state`
- `confidence_level`
- `simulated_direction`

Decision contract:
- No total score as final truth.
- Apply risk gate before any positive simulated direction statement.
- Human review remains mandatory.

## 8) Risk management principles
- Position sizing logic remains paper-only in future steps.
- Watch concentration risk by single stock and sector.
- Treat liquidity risk as first-class blocker in small/mid-cap names.
- Explicitly track event/gap/suspension risk.
- Separate stop-loss discussion from review-trigger governance.
- Maintain drawdown-awareness and avoid overtrading.
- Avoid theme chasing without evidence.
- Risk Desk may downgrade confidence or block positive paper-only simulated direction.

## 9) Implementation phases
1. **Phase 1**: deterministic read models + Stock Dossier + Daily Brief.
2. **Phase 2**: Strategy Research Desk outcome-review loop and horizon tagging.
3. **Phase 3**: News/Catalyst + Fundamental source planning and data contracts.
4. **Phase 4**: AI Decision Advisor deterministic synthesis.
5. **Phase 5**: backend-only AI vendor synthesis (only if justified) with strict audit/prompt/version controls.
6. **Phase 6**: DB persistence extension for audit/outcome learning only if needed.

## 10) Hard boundaries (reaffirmed)
- No broker integration.
- No live execution.
- No real-money execution.
- No autonomous execution.
- No real-money order creation.
- No frontend secrets.
- No raw Telegram initData exposure.
- Vendor tokens allowed only through approved backend provider abstractions.
- No token exposure in frontend/browser/client/logs/docs/chat.

## 11) Operator interpretation guidance (from this reference)
- Treat simulated direction as research output only.
- Validate data freshness, risk level, and horizon fit before interpretation.
- If data quality is weak or stale, prefer `資料不足` / `資料可能過舊` framing and defer action.
- Always keep paper-only safety wording visible: `只供模擬檢視 / 不建立訂單 / 不連接券商 / 不是真實買賣建議`.
