# Paper Trading v1 Definition (MVP)

## Objective
Provide a deterministic, implementation-ready paper-trading protocol to evaluate current MA50/MA200 signals before any live-trading escalation.

## Scope (in)
- Daily end-of-day simulation from existing signal outputs.
- Long-only portfolio simulation (cash + equity holdings).
- Deterministic trade ledger and daily equity snapshots.
- Reproducible results from the same ordered input data.
- No runtime strategy changes in current production signal generation.

## Scope (out)
- Real broker/API order routing.
- Intraday execution logic.
- Shorting, leverage, margin, derivatives.
- Complex slippage/impact models.
- Tax/corporate-action completeness.
- Autonomous live trading.

## Input contract
Each signal row used by simulation should minimally include:
- `date`
- `stock` (ticker)
- `signal` in `{BUY, SELL, HOLD, NO_DATA, INSUFFICIENT_DATA}`
- `price` (signal reference price; may be null for NO_DATA)

If multiple rows exist for the same `(date, stock)`, input must be deduplicated before simulation (implementation should reject or pre-clean deterministically).

## Processing order (determinism)
For each simulation date, process rows sorted by:
1. `date` ascending,
2. `stock` ascending.

At most one action per `(date, stock)` row.

## Signal → trade conversion
1. `BUY`
   - If no open position in ticker: submit simulated buy using sizing rule.
   - If already long: no-op in v1 (no pyramiding).
2. `SELL`
   - If open position exists: submit full-exit simulated sell.
   - If no open position: no-op.
3. `HOLD`
   - No trade.
4. `NO_DATA` / `INSUFFICIENT_DATA`
   - No trade; log a non-trade event reason.

## Entry/exit rules
- Entry trigger: first eligible `BUY` when flat in ticker.
- Exit trigger: first eligible `SELL` when long in ticker.
- Position mode: one long position per ticker.
- Partial exits: out of scope for v1.

## Position sizing assumptions
- Config: `target_allocation_per_new_position` (fixed fraction of current cash).
- Quantity rule: integer shares only, floor rounding.
- Guardrail: skip buy if computed quantity < 1 share.
- Optional cap: `max_open_positions` (if reached, skip additional buys deterministically).

## Cash and holdings ledger model
State fields:
- `cash_balance`
- per-ticker `quantity`
- per-ticker `average_entry_price`
- cumulative `realized_pnl`
- daily `unrealized_pnl`
- daily `portfolio_equity = cash + market_value(holdings)`

Ledger updates:
- Buy:
  - `trade_notional = quantity * execution_price`
  - `cash -= trade_notional + fees`
  - update position quantity and weighted average entry price
- Sell (full exit):
  - `trade_notional = quantity * execution_price`
  - `cash += trade_notional - fees`
  - `realized_pnl += (execution_price - average_entry_price) * quantity - sell_fees`
  - set position quantity to zero

## Fee assumptions (v1)
Use deterministic fee model with config:
- `commission_bps` on notional
- optional `min_fee_per_trade`

Per-trade fee formula:
- `fee = max(notional * commission_bps / 10000, min_fee_per_trade)`

Apply fees on both buy and sell.

## Price assumptions
- Default execution price for simulation is the signal row `price`.
- If `price` is null for a tradeable signal (`BUY`/`SELL`), skip trade and log data-quality exception.

## Required outputs
Simulation run must emit:
1. Trade ledger (`date, stock, action, quantity, price, notional, fees, reason`).
2. Daily portfolio snapshot (`date, cash, holdings_value, equity, realized_pnl, unrealized_pnl`).
3. Non-trade event log (e.g., HOLD/NO_DATA/INSUFFICIENT_DATA/cash constraint/cap reached).
4. Summary metrics (total return, win rate on closed trades, max drawdown, turnover count).

## Position / PnL review snapshot v1 (operator read-only surface)
- A read-only review snapshot is available for operator inspection of paper-trading state.
- Current operator surface: Telegram `/pnl_review`.
- This path is observability-only and must not mutate simulated orders, positions, or decision records.

Minimum summary fields:
- `open_positions_count`
- `closed_positions_count`
- `total_realized_pnl`
- `total_unrealized_pnl`
- per-symbol summary (`stock`, optional `stock_name` when source is available)
- Data-quality fallback: malformed SELL-only history may appear as per-symbol `position_status=FLAT` and is excluded from closed-position count.

Current calculation/assumption definitions:
- Average cost (`avg_cost`): weighted average BUY cost reconstructed from `paper_trades`.
- Realized PnL: cumulative sum of persisted SELL-side `realized_pnl` in trade ledger replay.
- Unrealized PnL: `(last_price - avg_cost) * quantity` for symbols with open quantity.
- Price source / valuation timestamp:
  - Open symbols: `paper_positions.last_price` (latest refreshed state).
  - Closed symbols fallback: last replayed trade price when no open position exists.
  - Snapshot-level `valuation_timestamp`: latest `paper_daily_snapshots.snapshot_date`.

Traceability limitation (current v1):
- `stock_name` is not guaranteed in current read path schema and may be `null`/`N/A`.

## Governance constraints
- Paper trading is evaluation infrastructure, not permission for live automation.
- Human review remains mandatory for all real-money decisions.

## Implementation-ready acceptance for next coding task
A future implementation is ready when it can map, deterministically:
1. validated signal input rows,
2. ordered row processing,
3. signal-to-action decisions,
4. ledger state transitions,
5. reproducible outputs and summary metrics.
