# Strategy Specification (Current MVP)

## Purpose
Define the exact current production signal semantics so future paper-trading work can be implemented consistently **without** changing runtime behavior.

## Runtime-truth signal model (MA50 / MA200)
The runtime computes two simple moving averages from the `Close` series:
- `MA50 = rolling_mean(Close, 50)`
- `MA200 = rolling_mean(Close, 200)`

Signal decision uses the **latest row where both MA50 and MA200 are non-null**.

Decision rule (exact):
- `BUY` when `MA50 > MA200`
- `SELL` when `MA50 < MA200`
- `HOLD` when `MA50 == MA200`

No other indicator, filter, or regime logic participates in the current decision.

## Canonical signal semantics

### BUY
- Meaning: Latest valid MA pair indicates `MA50 > MA200`.
- Operational implication: Bullish trend signal under the current single-factor rule.
- Governance: Decision support only; not an autonomous real-trade command.

### SELL
- Meaning: Latest valid MA pair indicates `MA50 < MA200`.
- Operational implication: Bearish trend signal under the current single-factor rule.
- Governance: Decision support only; not an autonomous real-trade command.

### HOLD
- Meaning: Latest valid MA pair indicates `MA50 == MA200`.
- Operational implication: Tie state under current MA rule; no directional edge from this strategy alone.

### NO_DATA
Returned when required market data is missing for signal computation, including:
- no market data frame, or
- empty data frame, or
- missing `Close` column.

Operational implication: skip directional action and investigate data quality/pipeline inputs.

### INSUFFICIENT_DATA
Returned when `Close` data exists but there is not enough history to produce at least one row with both MA50 and MA200.

Operational implication: defer directional decision until sufficient history is available.

## Human decision authority (non-negotiable)
- AI-generated signals are decision-support artifacts only.
- The human user remains the final decision-maker for any real-money trade.
- Nothing in this repository authorizes autonomous live-trading execution.

## Decision ledger v1 expectation
- For paper-trading governance, each AI signal should be recorded alongside an explicit human decision state (`PENDING`/approved/rejected/deferred) in a decision ledger record.
- This ledger is for reviewability and process discipline; it is not an automatic execution mechanism.

## Current strategy limitations
1. Single-factor model (only MA50/MA200 relationship).
2. No position/risk management embedded in signal generation.
3. No portfolio-level optimization or concentration control in signal logic.
4. No transaction-cost/slippage optimization in the signal rule.
5. Data availability limitations can reduce actionable coverage (`NO_DATA` / `INSUFFICIENT_DATA`).
6. Limited explainability beyond MA relationship state.

## Change control
Any semantic change to signal definitions must be documented here first and implemented only in a separately approved runtime task.
