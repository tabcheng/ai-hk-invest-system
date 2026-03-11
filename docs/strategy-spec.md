# Strategy Specification (Current MVP)

## Purpose
Define the current production signal semantics so future paper-trading work can be implemented consistently without changing live runtime behavior.

## Current signal model (MA50 / MA200)
The MVP strategy uses two moving averages per ticker:
- **MA50**: short/medium trend proxy.
- **MA200**: long-term trend proxy.

Current interpretation:
- **Bullish trend bias** when `MA50 > MA200`.
- **Bearish trend bias** when `MA50 < MA200`.
- **No crossover edge** when values are equal or effectively flat relative to data granularity.

This model is intentionally simple and trend-following; it is not a full portfolio strategy.

## Canonical signal semantics
The following signal labels are the product-definition contract for the current MVP logic layer.

### BUY
- Meaning: Data supports a positive trend condition under current MA rules.
- Intended user action: Consider a buy candidate, subject to human review (position limits, diversification, risk, and context checks).
- Constraint: Not an instruction for automatic real trading.

### SELL
- Meaning: Data supports a negative trend condition under current MA rules.
- Intended user action: Consider reducing or exiting an existing paper/live position after human review.
- Constraint: Not an instruction for automatic real trading.

### HOLD
- Meaning: Data is sufficient, but current MA relationship does not justify a new directional action versus prior state.
- Intended user action: Maintain current stance unless external factors justify override.

### NO_DATA
- Meaning: Required market data for the ticker/date window is unavailable.
- Intended user action: Do not infer trend direction; skip execution decision and inspect data pipeline health.

### INSUFFICIENT_DATA
- Meaning: Data exists but does not include enough history to compute reliable MA50/MA200 values.
- Intended user action: Defer decision until sufficient history is available.

## Human decision authority (non-negotiable)
- AI-generated signals are **decision-support artifacts only**.
- The human user remains the **final decision-maker** for any real-money trade.
- No document in this repository authorizes autonomous live trading.

## Current strategy limitations
1. **Single-factor trend signal**: only MA50/MA200 relationship is considered.
2. **No regime detection**: does not adapt to range-bound vs. trending market regimes.
3. **No risk model integration**: no stop-loss, max drawdown guardrail, or volatility targeting in signal generation.
4. **No portfolio-aware optimization**: signal is ticker-local and does not account for cross-position concentration.
5. **No transaction-cost-aware optimization in signal layer**: fees/slippage are not part of current signal computation.
6. **Data fragility exposure**: NO_DATA / INSUFFICIENT_DATA states can materially reduce actionable coverage.
7. **No causal attribution**: MA crossover logic provides limited explainability beyond trend direction.

## Change control note
Any strategy-semantics changes must be documented here first, then implemented in a separately approved runtime task.
