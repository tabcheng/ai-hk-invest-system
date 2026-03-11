from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import floor

from supabase import Client


@dataclass(frozen=True)
class PaperTradingConfig:
    initial_cash_hkd: float = 100000.0
    target_allocation_per_new_position_hkd: float = 10000.0
    commission_rate: float = 0.001
    min_fee_hkd: float = 18.0
    max_open_positions: int = 5


@dataclass
class Position:
    quantity: int
    average_entry_price: float


DEFAULT_PAPER_TRADING_CONFIG = PaperTradingConfig()


def _calculate_fee(notional: float, config: PaperTradingConfig) -> float:
    return max(notional * config.commission_rate, config.min_fee_hkd)


def _normalize_signal_rows(signal_rows: list[dict]) -> list[dict]:
    sorted_rows = sorted(signal_rows, key=lambda row: (row["date"], row["stock"], row.get("id", 0)))
    deduped: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in sorted_rows:
        key = (row["date"], row["stock"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _build_mark_prices(signal_rows: list[dict], positions: dict[str, Position]) -> dict[str, float]:
    price_map: dict[str, float] = {}
    for row in signal_rows:
        price = row.get("price")
        if price is not None:
            price_map[row["stock"]] = float(price)

    for stock, position in positions.items():
        price_map.setdefault(stock, position.average_entry_price)

    return price_map


def simulate_day(
    signal_rows: list[dict],
    run_id: int | None,
    trade_date: date,
    config: PaperTradingConfig = DEFAULT_PAPER_TRADING_CONFIG,
    starting_cash: float | None = None,
    starting_positions: dict[str, Position] | None = None,
    cumulative_realized_pnl: float = 0.0,
) -> dict:
    cash = config.initial_cash_hkd if starting_cash is None else float(starting_cash)
    positions: dict[str, Position] = dict(starting_positions or {})
    realized_pnl_total = float(cumulative_realized_pnl)

    trades: list[dict] = []
    events: list[dict] = []

    ordered_rows = _normalize_signal_rows(signal_rows)

    for row in ordered_rows:
        stock = row["stock"]
        signal = row["signal"]
        signal_id = row.get("id")
        price = row.get("price")
        execution_price = float(price) if price is not None else None

        base_event = {
            "event_date": trade_date.isoformat(),
            "stock": stock,
            "signal": signal,
            "signal_id": signal_id,
            "run_id": run_id,
        }

        if signal == "BUY":
            if stock in positions:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_ALREADY_HOLDING",
                        "message": "BUY skipped because position already exists for ticker.",
                    }
                )
                continue
            if execution_price is None or execution_price <= 0:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_INVALID_PRICE",
                        "message": "BUY skipped because signal price is missing or non-positive.",
                    }
                )
                continue
            if len(positions) >= config.max_open_positions:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_MAX_OPEN_POSITIONS",
                        "message": "BUY skipped because max_open_positions has been reached.",
                    }
                )
                continue

            quantity = floor(config.target_allocation_per_new_position_hkd / execution_price)
            if quantity < 1:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_SIZE_LT_ONE_SHARE",
                        "message": "BUY skipped because computed quantity is less than 1 share.",
                    }
                )
                continue

            gross_amount = quantity * execution_price
            fee = _calculate_fee(gross_amount, config)
            total_cost = gross_amount + fee
            if total_cost > cash:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_INSUFFICIENT_CASH",
                        "message": "BUY skipped because available cash is insufficient.",
                    }
                )
                continue

            cash -= total_cost
            positions[stock] = Position(quantity=quantity, average_entry_price=execution_price)

            trades.append(
                {
                    "trade_date": trade_date.isoformat(),
                    "stock": stock,
                    "action": "BUY",
                    "quantity": quantity,
                    "price": execution_price,
                    "gross_amount": gross_amount,
                    "fee": fee,
                    "net_amount": -total_cost,
                    "realized_pnl": 0.0,
                    "signal_id": signal_id,
                    "run_id": run_id,
                }
            )
            continue

        if signal == "SELL":
            if stock not in positions:
                events.append(
                    {
                        **base_event,
                        "event_type": "SELL_SKIPPED_NOT_HOLDING",
                        "message": "SELL skipped because no open position exists for ticker.",
                    }
                )
                continue
            if execution_price is None or execution_price <= 0:
                events.append(
                    {
                        **base_event,
                        "event_type": "SELL_SKIPPED_INVALID_PRICE",
                        "message": "SELL skipped because signal price is missing or non-positive.",
                    }
                )
                continue

            position = positions[stock]
            quantity = position.quantity
            gross_amount = quantity * execution_price
            fee = _calculate_fee(gross_amount, config)
            net_amount = gross_amount - fee
            realized_pnl = (execution_price - position.average_entry_price) * quantity - fee

            cash += net_amount
            realized_pnl_total += realized_pnl
            del positions[stock]

            trades.append(
                {
                    "trade_date": trade_date.isoformat(),
                    "stock": stock,
                    "action": "SELL",
                    "quantity": quantity,
                    "price": execution_price,
                    "gross_amount": gross_amount,
                    "fee": fee,
                    "net_amount": net_amount,
                    "realized_pnl": realized_pnl,
                    "signal_id": signal_id,
                    "run_id": run_id,
                }
            )
            continue

        if signal == "HOLD":
            events.append(
                {
                    **base_event,
                    "event_type": "HOLD_EVENT",
                    "message": "HOLD signal recorded; no trade executed.",
                }
            )
            continue

        events.append(
            {
                **base_event,
                "event_type": f"{signal}_EVENT",
                "message": f"{signal} signal recorded; no trade executed.",
            }
        )

    mark_prices = _build_mark_prices(ordered_rows, positions)
    market_value = sum(position.quantity * mark_prices[stock] for stock, position in positions.items())
    unrealized_pnl = sum(
        (mark_prices[stock] - position.average_entry_price) * position.quantity
        for stock, position in positions.items()
    )
    total_equity = cash + market_value

    snapshot = {
        "snapshot_date": trade_date.isoformat(),
        "cash": cash,
        "market_value": market_value,
        "total_equity": total_equity,
        "open_positions": len(positions),
        "cumulative_realized_pnl": realized_pnl_total,
        "cumulative_unrealized_pnl": unrealized_pnl,
        "run_id": run_id,
    }

    return {
        "trades": trades,
        "events": events,
        "snapshot": snapshot,
        "ending_cash": cash,
        "ending_positions": positions,
        "cumulative_realized_pnl": realized_pnl_total,
    }


def _fetch_prior_state(client: Client, trade_date: date) -> tuple[float | None, float, dict[str, Position]]:
    snapshot_result = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date,cash,cumulative_realized_pnl")
        .lt("snapshot_date", trade_date.isoformat())
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    starting_cash = None
    realized_pnl = 0.0
    if snapshot_result.data:
        starting_cash = float(snapshot_result.data[0]["cash"])
        realized_pnl = float(snapshot_result.data[0]["cumulative_realized_pnl"])

    trade_rows = (
        client.table("paper_trades")
        .select("stock,action,quantity,price")
        .lt("trade_date", trade_date.isoformat())
        .order("trade_date")
        .order("id")
        .execute()
    ).data or []

    positions: dict[str, Position] = {}
    for row in trade_rows:
        stock = row["stock"]
        action = row["action"]
        quantity = int(row["quantity"])
        price = float(row["price"])

        if action == "BUY":
            positions[stock] = Position(quantity=quantity, average_entry_price=price)
        elif action == "SELL":
            positions.pop(stock, None)

    return starting_cash, realized_pnl, positions


def _clear_existing_day_outputs(client: Client, trade_date: date) -> None:
    day = trade_date.isoformat()
    client.table("paper_trades").delete().eq("trade_date", day).execute()
    client.table("paper_events").delete().eq("event_date", day).execute()
    client.table("paper_daily_snapshots").delete().eq("snapshot_date", day).execute()

def run_paper_trading_for_today(
    client: Client,
    run_id: int | None,
    config: PaperTradingConfig = DEFAULT_PAPER_TRADING_CONFIG,
) -> dict:
    trade_date = datetime.now(timezone.utc).date()

    signal_rows = (
        client.table("signals")
        .select("id,date,stock,signal,price")
        .eq("date", trade_date.isoformat())
        .order("stock")
        .execute()
    ).data or []

    starting_cash, realized_pnl, starting_positions = _fetch_prior_state(client, trade_date)

    _clear_existing_day_outputs(client, trade_date)

    result = simulate_day(
        signal_rows=signal_rows,
        run_id=run_id,
        trade_date=trade_date,
        config=config,
        starting_cash=starting_cash,
        starting_positions=starting_positions,
        cumulative_realized_pnl=realized_pnl,
    )

    if result["trades"]:
        client.table("paper_trades").insert(result["trades"]).execute()

    if result["events"]:
        client.table("paper_events").insert(result["events"]).execute()

    client.table("paper_daily_snapshots").upsert(
        result["snapshot"], on_conflict="snapshot_date", ignore_duplicates=False
    ).execute()

    print(
        "Paper trading completed: "
        f"trades={len(result['trades'])}, events={len(result['events'])}, "
        f"equity={result['snapshot']['total_equity']:.2f}"
    )

    return result
