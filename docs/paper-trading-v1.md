# Paper Trading v1 Definition (MVP)

## Objective
Provide a minimal, deterministic paper-trading protocol to evaluate current MA50/MA200 decision-support signals before any future live-trading automation discussions.

## Scope (in)
- Simulate trades from existing daily signal outputs.
- Track virtual cash, holdings, and basic P&L over time.
- Support one portfolio ledger per simulation run.
- Keep execution deterministic and reproducible from stored inputs.
- Preserve current runtime signal generation behavior (no strategy change in this phase).

## Scope (out)
- Real broker integration or real order routing.
- Intraday execution modeling.
- Margin, short selling, options, leverage.
- Advanced slippage model or market impact modeling.
- Tax modeling and corporate action complexity beyond simple assumptions.
- Autonomous live trading.

## Simulation cadence and universe assumptions
- **Cadence**: once per trading day after signal availability.
- **Price basis**: use a single consistent daily reference price (implementation to choose and document, e.g., close).
- **Universe**: tickers already covered by the existing MVP signal loop.

## Signal-to-trade conversion rules
Signals are interpreted per ticker on each simulation date:

1. `BUY`
   - If no current position: open a new long position per sizing rule.
   - If already long: no additional pyramid in v1 (treat as hold/no-op).
2. `SELL`
   - If long position exists: fully close position in v1.
   - If no position: no-op.
3. `HOLD`
   - No trade.
4. `NO_DATA` or `INSUFFICIENT_DATA`
   - No trade, with explicit event logging for audit.

## Entry and exit rules (v1)
- **Entry**: first eligible `BUY` event when ticker has no active position.
- **Exit**: first eligible `SELL` event when ticker has active position.
- **Partial fills/exits**: unsupported in v1.
- **Same-day buy+sell for one ticker**: unsupported under daily single-signal cadence; at most one state transition per ticker per date.

## Position sizing assumptions
- Use **fixed-fraction sizing** based on available cash (e.g., target percent per new position) as a configurable parameter.
- Enforce a **minimum cash check**: skip trade when cash is insufficient for at least one board-lot-equivalent unit under chosen simplification.
- Enforce optional **max concurrent positions** cap (configurable).
- v1 default behavior should prefer simple integer share quantities and deterministic rounding rules.

## Cash and holdings model
- Portfolio state tracks:
  - `cash_balance`
  - per-ticker `quantity`
  - per-ticker `average_entry_price`
  - realized P&L from closed positions
  - unrealized P&L from open positions (mark-to-market by chosen daily price basis)
- On buy:
  - decrement cash by `trade_notional + fees`
  - increase holdings quantity and recompute average entry price
- On sell:
  - increment cash by `trade_notional - fees`
  - realize P&L against average entry price
  - set position quantity to zero in full-exit v1 rule

## Fee assumptions (v1)
- Include a simple fee model for realism with deterministic computation:
  - configurable bps commission on notional
  - optional minimum fee per trade
- Fees apply to both buy and sell trades.
- Stamp duty / exchange fees can be approximated by a single blended rate in v1 and refined later.

## Required outputs for evaluation
Each simulation run should produce:
- portfolio equity curve by date
- trade log with signal source and execution reason
- per-ticker closed-trade summary
- high-level metrics (total return, hit rate, max drawdown approximation, turnover count)

## Governance constraints
- Paper trading is an evaluation mechanism, not permission for live automation.
- Human review remains mandatory for any real-money action.

## Implementation readiness criteria for next task
A future implementation task should be considered ready when it can unambiguously map:
1. signal rows -> simulation events,
2. events -> trade/no-trade actions,
3. actions -> deterministic ledger updates,
4. ledger states -> reviewable metrics and logs.
