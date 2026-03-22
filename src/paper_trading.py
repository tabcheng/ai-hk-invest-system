from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import floor

from supabase import Client

from src.risk_manager import SEVERITY_RANK, build_risk_evaluation_payload, evaluate_paper_trade_risk


@dataclass(frozen=True)
class PaperTradingConfig:
    initial_cash_hkd: float = 100000.0
    target_allocation_per_new_position_hkd: float = 10000.0
    commission_rate: float = 0.001
    min_fee_hkd: float = 18.0
    max_open_positions: int = 5
    # v1 risk guardrails for paper-trade evaluation and human decision support.
    max_single_position_weight: float = 0.40
    max_daily_new_allocation_hkd: float = 30000.0
    max_position_add_allocation_hkd: float = 10000.0
    cash_floor_hkd: float = 5000.0


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


def _evaluate_buy_trade_risk(
    *,
    cash: float,
    positions: dict[str, Position],
    mark_prices: dict[str, float],
    trades: list[dict],
    stock: str,
    quantity: int,
    execution_price: float,
    total_cost: float,
    config: PaperTradingConfig,
) -> dict:
    """Evaluate BUY risk guardrails using explicit, serializable plain-data inputs."""
    gross_amount = quantity * execution_price
    # Concentration guardrail must use mark-based valuation so unrealized
    # gains/losses are reflected in projected portfolio weights.
    position_rows_for_risk = [
        {
            "ticker": ticker,
            "quantity": position.quantity,
            "last_price": float(mark_prices.get(ticker, position.average_entry_price)),
        }
        for ticker, position in positions.items()
    ]
    portfolio_summary_for_risk = {
        "cash": cash,
        "total_equity": cash
        + sum(
            p.quantity * float(mark_prices.get(ticker, p.average_entry_price))
            for ticker, p in positions.items()
        ),
        "daily_new_allocation_used_hkd": sum(
            float(trade["gross_amount"])
            for trade in trades
            if trade["action"] == "BUY"
        ),
    }
    candidate_for_risk = {
        "action": "BUY",
        "stock": stock,
        "quantity": quantity,
        "price": execution_price,
        "gross_amount": gross_amount,
        "total_cost": total_cost,
    }
    risk_config = {
        "max_single_position_weight": config.max_single_position_weight,
        "max_daily_new_allocation_hkd": config.max_daily_new_allocation_hkd,
        "max_position_add_allocation_hkd": config.max_position_add_allocation_hkd,
        "cash_floor_hkd": config.cash_floor_hkd,
    }
    return evaluate_paper_trade_risk(
        portfolio_summary=portfolio_summary_for_risk,
        positions=position_rows_for_risk,
        candidate_trade=candidate_for_risk,
        config=risk_config,
    )


def _build_event_payload(
    *,
    base_event: dict,
    event_type: str,
    message: str,
    risk_evaluation: dict | None = None,
) -> dict:
    """Build a paper-event row with optional structured risk context."""
    event = {
        **base_event,
        "event_type": event_type,
        "message": message,
    }
    risk_payload = build_risk_evaluation_payload(risk_evaluation)
    if risk_payload is not None:
        # Traceability guardrail: keep risk context compact and consistent so
        # blocked/warning/info outcomes are reviewable without log parsing.
        event["risk_evaluation"] = risk_payload
    return event


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
    mark_prices = _build_mark_prices(ordered_rows, positions)

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
            if execution_price is None or execution_price <= 0:
                events.append(
                    {
                        **base_event,
                        "event_type": "BUY_SKIPPED_INVALID_PRICE",
                        "message": "BUY skipped because signal price is missing or non-positive.",
                    }
                )
                continue

            if stock in positions:
                # Existing positions are still non-additive in v1 simulation behavior,
                # but run the dedicated add-exposure risk check for decision support
                # so this path surfaces guardrail posture explicitly.
                quantity = floor(config.target_allocation_per_new_position_hkd / execution_price)
                if quantity < 1:
                    events.append(
                        {
                            **base_event,
                            "event_type": "BUY_SKIPPED_ALREADY_HOLDING",
                            "message": "BUY skipped because position already exists for ticker.",
                        }
                    )
                    continue

                gross_amount = quantity * execution_price
                fee = _calculate_fee(gross_amount, config)
                risk_evaluation = _evaluate_buy_trade_risk(
                    cash=cash,
                    positions=positions,
                    mark_prices=mark_prices,
                    trades=trades,
                    stock=stock,
                    quantity=quantity,
                    execution_price=execution_price,
                    total_cost=gross_amount + fee,
                    config=config,
                )
                events.append(
                    _build_event_payload(
                        base_event=base_event,
                        event_type="BUY_SKIPPED_ALREADY_HOLDING",
                        message=(
                            "BUY skipped because position already exists for ticker. "
                            f"Add-check: {risk_evaluation['summary_message']}"
                        ),
                        risk_evaluation=risk_evaluation,
                    )
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

            risk_evaluation = _evaluate_buy_trade_risk(
                cash=cash,
                positions=positions,
                mark_prices=mark_prices,
                trades=trades,
                stock=stock,
                quantity=quantity,
                execution_price=execution_price,
                total_cost=total_cost,
                config=config,
            )

            if not risk_evaluation["allowed"]:
                events.append(
                    _build_event_payload(
                        base_event=base_event,
                        event_type="BUY_BLOCKED_RISK_GUARDRAIL",
                        message=risk_evaluation["summary_message"],
                        risk_evaluation=risk_evaluation,
                    )
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
            events.append(
                _build_event_payload(
                    base_event=base_event,
                    event_type="BUY_EXECUTED",
                    message="BUY executed in paper trading simulation.",
                    risk_evaluation=risk_evaluation,
                )
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

    # Historical-correct bootstrap for reruns/backfills: only include trades
    # strictly before the target trade_date.
    trade_rows = (
        client.table("paper_trades")
        .select("stock,action,quantity,price")
        .lt("trade_date", trade_date.isoformat())
        .order("trade_date")
        .order("id")
        .execute()
    ).data or []

    rebuilt = _build_position_state_from_trade_rows(trade_rows)
    positions: dict[str, Position] = {}
    for ticker, row in rebuilt.items():
        qty = int(row["quantity"])
        if qty <= 0:
            continue
        positions[ticker] = Position(quantity=qty, average_entry_price=float(row["avg_cost"]))

    return starting_cash, realized_pnl, positions


def _clear_existing_day_outputs(client: Client, trade_date: date) -> None:
    day = trade_date.isoformat()
    client.table("paper_trades").delete().eq("trade_date", day).execute()
    client.table("paper_events").delete().eq("event_date", day).execute()
    client.table("paper_daily_snapshots").delete().eq("snapshot_date", day).execute()


def _build_position_state_from_trade_rows(trade_rows: list[dict]) -> dict[str, dict[str, float | int]]:
    positions: dict[str, dict[str, float | int]] = {}

    for row in trade_rows:
        ticker = row["stock"]
        action = row["action"]
        quantity = int(row["quantity"])
        price = float(row["price"])
        realized_pnl = float(row.get("realized_pnl") or 0.0)

        existing = positions.get(
            ticker,
            {
                "ticker": ticker,
                "quantity": 0,
                "avg_cost": 0.0,
                "last_price": 0.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
            },
        )

        current_qty = int(existing["quantity"])
        current_avg = float(existing["avg_cost"])

        if action == "BUY":
            # Weighted-average entry price is intentionally explicit and long-only:
            # every BUY grows the position and updates avg_cost by notional weighting.
            new_qty = current_qty + quantity
            if new_qty > 0:
                existing["avg_cost"] = ((current_avg * current_qty) + (price * quantity)) / new_qty
            existing["quantity"] = new_qty
            existing["last_price"] = price

        elif action == "SELL":
            # Long-only guardrail: a SELL cannot create a short position. If a
            # trade row is inconsistent (sell > holdings), clamp to zero.
            new_qty = max(current_qty - quantity, 0)
            existing["quantity"] = new_qty
            existing["last_price"] = price
            existing["realized_pnl"] = float(existing["realized_pnl"]) + realized_pnl
            if new_qty == 0:
                existing["avg_cost"] = 0.0

        existing["unrealized_pnl"] = (
            (float(existing["last_price"]) - float(existing["avg_cost"])) * int(existing["quantity"])
        )
        positions[ticker] = existing

    return positions


def _refresh_paper_positions_from_trades(client: Client, trade_date: date) -> list[dict]:
    trade_rows = (
        client.table("paper_trades")
        .select("stock,action,quantity,price,realized_pnl,trade_date,id")
        .lte("trade_date", trade_date.isoformat())
        .order("trade_date")
        .order("id")
        .execute()
    ).data or []

    position_map = _build_position_state_from_trade_rows(trade_rows)
    position_rows: list[dict] = []
    for ticker in sorted(position_map.keys()):
        row = position_map[ticker]
        position_rows.append(
            {
                "ticker": ticker,
                "quantity": int(row["quantity"]),
                "avg_cost": float(row["avg_cost"]),
                "last_price": float(row["last_price"]),
                "unrealized_pnl": float(row["unrealized_pnl"]),
                "realized_pnl": float(row["realized_pnl"]),
                # Explicitly refresh updated_at on each write so read surfaces
                # can reliably detect fresh position-state updates.
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    existing_rows = (
        client.table("paper_positions")
        .select("ticker")
        .execute()
    ).data or []
    existing_tickers = {row["ticker"] for row in existing_rows}
    next_tickers = {row["ticker"] for row in position_rows}

    if position_rows:
        client.table("paper_positions").upsert(
            position_rows, on_conflict="ticker", ignore_duplicates=False
        ).execute()

    stale_tickers = sorted(existing_tickers - next_tickers)
    if stale_tickers:
        client.table("paper_positions").delete().in_("ticker", stale_tickers).execute()

    return position_rows


def get_paper_portfolio_summary(client: Client) -> dict:
    positions = (
        client.table("paper_positions")
        .select("ticker,quantity,avg_cost,last_price,unrealized_pnl,realized_pnl")
        .order("ticker")
        .execute()
    ).data or []

    latest_snapshot = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date,cash,total_equity,cumulative_realized_pnl,cumulative_unrealized_pnl")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    ).data or []

    cash = float(latest_snapshot[0]["cash"]) if latest_snapshot else 0.0
    total_equity = float(latest_snapshot[0]["total_equity"]) if latest_snapshot else 0.0
    market_value = sum(float(row["last_price"]) * int(row["quantity"]) for row in positions)

    return {
        "snapshot_date": latest_snapshot[0]["snapshot_date"] if latest_snapshot else None,
        "cash": cash,
        "market_value": market_value,
        "total_equity": total_equity,
        "open_positions": sum(1 for row in positions if int(row["quantity"]) > 0),
        "positions": positions,
    }


def get_paper_position_pnl_review_snapshot(client: Client) -> dict:
    """
    Build a read-only paper-trading position/PnL review snapshot.

    Data-flow and guardrail notes:
    - Reads from persisted `paper_trades`, `paper_positions`, and latest
      `paper_daily_snapshots` rows only; this function performs no writes.
    - Closed-position count is derived from full trade-ledger reconstruction:
      tickers with net quantity `0` after replay are treated as currently closed.
    - Per-symbol summary prioritizes `paper_positions` values for open positions
      and falls back to trade-ledger reconstruction for closed symbols.
    - Stock-name traceability is currently limited by available schema in this
      read path; output keeps `stock_name=None` until a dedicated name source is
      approved/documented.
    """
    trade_rows = (
        client.table("paper_trades")
        .select("stock,action,quantity,price,realized_pnl,id")
        .order("id")
        .execute()
    ).data or []
    rebuilt_positions = _build_position_state_from_trade_rows(trade_rows)

    persisted_open_rows = (
        client.table("paper_positions")
        .select("ticker,quantity,avg_cost,last_price,unrealized_pnl,realized_pnl,updated_at")
        .order("ticker")
        .execute()
    ).data or []
    open_by_ticker = {
        str(row.get("ticker")): row
        for row in persisted_open_rows
        if row.get("ticker") is not None
    }

    latest_snapshot_rows = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    ).data or []
    snapshot_date = latest_snapshot_rows[0].get("snapshot_date") if latest_snapshot_rows else None

    symbol_rows: list[dict] = []
    total_realized = 0.0
    total_unrealized = 0.0
    for ticker in sorted(rebuilt_positions.keys()):
        rebuilt = rebuilt_positions[ticker]
        open_row = open_by_ticker.get(ticker)
        quantity = int(open_row.get("quantity") if open_row is not None else rebuilt.get("quantity") or 0)
        avg_cost = float(open_row.get("avg_cost") if open_row is not None else rebuilt.get("avg_cost") or 0.0)
        last_price = float(
            open_row.get("last_price") if open_row is not None else rebuilt.get("last_price") or avg_cost
        )
        realized_pnl = float(
            open_row.get("realized_pnl") if open_row is not None else rebuilt.get("realized_pnl") or 0.0
        )
        unrealized_pnl = float(
            open_row.get("unrealized_pnl") if open_row is not None else rebuilt.get("unrealized_pnl") or 0.0
        )

        total_realized += realized_pnl
        total_unrealized += unrealized_pnl
        symbol_rows.append(
            {
                "stock": ticker,
                "stock_name": None,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "last_price": last_price,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "position_status": "OPEN" if quantity > 0 else "CLOSED",
                "valuation_timestamp": (
                    open_row.get("updated_at")
                    if open_row is not None and open_row.get("updated_at")
                    else snapshot_date
                ),
            }
        )

    return {
        "open_positions_count": sum(1 for row in symbol_rows if row["position_status"] == "OPEN"),
        "closed_positions_count": sum(1 for row in symbol_rows if row["position_status"] == "CLOSED"),
        "total_realized_pnl": total_realized,
        "total_unrealized_pnl": total_unrealized,
        "valuation_timestamp": snapshot_date,
        "per_symbol": symbol_rows,
    }


def _build_compact_rule_summary(risk_evaluation: dict) -> str:
    """Return a compact, stable one-line rule summary for review surfaces."""
    rule_rows = risk_evaluation.get("rule_results")
    if not isinstance(rule_rows, list) or not rule_rows:
        return "rules=none"

    failed_rules: list[str] = []
    warning_rules: list[str] = []
    passed_rules: list[str] = []

    for row in rule_rows:
        if not isinstance(row, dict):
            continue
        rule_name = str(row.get("rule_name") or "unknown_rule")
        if row.get("passed") is False:
            failed_rules.append(rule_name)
            continue
        if str(row.get("severity", "info")) == "warning":
            warning_rules.append(rule_name)
            continue
        passed_rules.append(rule_name)

    parts: list[str] = []
    if failed_rules:
        parts.append(f"failed={','.join(sorted(set(failed_rules)))}")
    if warning_rules:
        parts.append(f"warning={','.join(sorted(set(warning_rules)))}")
    if passed_rules:
        parts.append(f"passed={','.join(sorted(set(passed_rules)))}")

    return " | ".join(parts) if parts else "rules=none"


def get_paper_risk_review_for_run(client: Client, run_id: int) -> dict:
    """Build a compact human-readable risk review for one paper-trading run.

    This read surface is intentionally observability-only and derives review
    output from persisted `paper_events.risk_evaluation` payloads.
    """
    event_rows = (
        client.table("paper_events")
        .select("id,stock,event_type,risk_evaluation")
        .eq("run_id", run_id)
        .order("id")
        .execute()
    ).data or []

    review_by_ticker: dict[str, list[dict]] = {}
    total_blocked_buys = 0
    total_warning_buys = 0
    total_executed_buys = 0

    for row in event_rows:
        event_type = str(row.get("event_type") or "")
        if not event_type.startswith("BUY_"):
            continue

        risk_evaluation = build_risk_evaluation_payload(row.get("risk_evaluation"))
        if risk_evaluation is None:
            continue

        severity = str(risk_evaluation.get("severity") or "info")
        if severity not in SEVERITY_RANK:
            severity = "info"
        summary_message = str(risk_evaluation.get("summary_message") or "")

        if severity == "blocked":
            total_blocked_buys += 1
        if severity == "warning":
            total_warning_buys += 1
        if event_type == "BUY_EXECUTED":
            total_executed_buys += 1

        ticker = str(row.get("stock") or "UNKNOWN")
        review_by_ticker.setdefault(ticker, []).append(
            {
                "event_type": event_type,
                "severity": severity,
                "summary_message": summary_message,
                "compact_rule_summary": _build_compact_rule_summary(risk_evaluation),
            }
        )

    return {
        "run_id": run_id,
        "total_blocked_buys": total_blocked_buys,
        "total_warning_buys": total_warning_buys,
        "total_executed_buys": total_executed_buys,
        "per_ticker": review_by_ticker,
    }


def get_paper_daily_review_summary_for_run(client: Client, run_id: int) -> dict:
    """Return a compact beginner-friendly daily review for one paper-trading run.

    The output intentionally uses short plain-language fields so operators can
    understand one run quickly without reading raw event JSON.
    """
    risk_review = get_paper_risk_review_for_run(client, run_id)

    trade_rows = (
        client.table("paper_trades")
        .select("stock,action")
        .eq("run_id", run_id)
        .order("id")
        .execute()
    ).data or []

    event_rows = (
        client.table("paper_events")
        .select("stock")
        .eq("run_id", run_id)
        .order("id")
        .execute()
    ).data or []

    snapshot_rows = (
        client.table("paper_daily_snapshots")
        .select("snapshot_date,cash,total_equity,open_positions")
        .eq("run_id", run_id)
        .order("id")
        .limit(1)
        .execute()
    ).data or []

    snapshot = snapshot_rows[0] if snapshot_rows else None
    previous_snapshot_rows: list[dict] = []
    if snapshot and snapshot.get("snapshot_date"):
        previous_snapshot_rows = (
            client.table("paper_daily_snapshots")
            .select("snapshot_date,cash,total_equity")
            .lt("snapshot_date", str(snapshot["snapshot_date"]))
            .order("snapshot_date", desc=True)
            .limit(1)
            .execute()
        ).data or []

    tickers_with_activity = {str(ticker) for ticker in risk_review["per_ticker"].keys()}
    # Activity should include all event rows (for example HOLD or non-risk BUY skip
    # paths) so operators get a complete ticker count for the run.
    for row in event_rows + trade_rows:
        stock = row.get("stock")
        if stock is not None:
            tickers_with_activity.add(str(stock))

    sell_count = sum(1 for row in trade_rows if str(row.get("action") or "") == "SELL")

    notable_items: list[str] = []
    blocked_count = int(risk_review["total_blocked_buys"])
    warning_count = int(risk_review["total_warning_buys"])
    executed_count = int(risk_review["total_executed_buys"])
    if blocked_count > 0:
        notable_items.append(f"{blocked_count} BUY signal(s) were blocked by risk guardrails.")
    if warning_count > 0:
        notable_items.append(f"{warning_count} BUY execution(s) had warning-level risk notes.")
    if executed_count == 0:
        notable_items.append("No BUY trades were executed in this run.")
    if sell_count > 0:
        notable_items.append(f"{sell_count} SELL trade(s) were executed.")

    portfolio_change_summary = None
    if snapshot:
        equity_now = float(snapshot.get("total_equity") or 0.0)
        cash_now = float(snapshot.get("cash") or 0.0)
        open_positions_now = int(snapshot.get("open_positions") or 0)

        if previous_snapshot_rows:
            prev = previous_snapshot_rows[0]
            equity_change = equity_now - float(prev.get("total_equity") or 0.0)
            cash_change = cash_now - float(prev.get("cash") or 0.0)
            portfolio_change_summary = (
                "Portfolio vs previous snapshot: "
                f"equity {equity_change:+.2f} HKD, cash {cash_change:+.2f} HKD, "
                f"open positions now {open_positions_now}."
            )
        else:
            portfolio_change_summary = (
                "Portfolio snapshot recorded: "
                f"total equity {equity_now:.2f} HKD, cash {cash_now:.2f} HKD, "
                f"open positions {open_positions_now}."
            )

    return {
        "run_id": run_id,
        "total_executed_buys": executed_count,
        "total_blocked_buys": blocked_count,
        "total_warning_buys": warning_count,
        "number_of_tickers_with_activity": len(tickers_with_activity),
        "notable_items": notable_items,
        "portfolio_change_summary": portfolio_change_summary,
    }


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

    try:
        _refresh_paper_positions_from_trades(client, trade_date)
    except Exception as e:
        # Best-effort observability-only layer: position snapshots should not
        # change the existing run success/failure semantics for paper trading.
        print(f"paper_positions refresh failed (non-blocking): {e}")

    print(
        "Paper trading completed: "
        f"trades={len(result['trades'])}, events={len(result['events'])}, "
        f"equity={result['snapshot']['total_equity']:.2f}"
    )

    return result
