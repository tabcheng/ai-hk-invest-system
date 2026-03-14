from __future__ import annotations

"""Pure paper-trading risk guardrails for pre-trade decision support.

This module intentionally contains no database or network interactions so it can
be unit-tested in isolation and reused across runtime surfaces.
"""

SEVERITY_RANK = {"info": 0, "warning": 1, "blocked": 2}


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_result(
    *,
    rule_name: str,
    severity: str,
    passed: bool,
    message: str,
    metrics: dict,
) -> dict:
    return {
        "rule_name": rule_name,
        "severity": severity,
        "passed": passed,
        "message": message,
        "metrics": metrics,
    }


def evaluate_paper_trade_risk(
    portfolio_summary: dict,
    positions: list[dict],
    candidate_trade: dict,
    config: dict,
) -> dict:
    """Evaluate a candidate paper trade against explicit v1 guardrails.

    Expected inputs are dict-like plain values to keep this interface simple and
    serializable for telemetry/audit use.
    """
    action = str(candidate_trade.get("action", "")).upper()
    stock = str(candidate_trade.get("stock", ""))
    quantity = int(candidate_trade.get("quantity") or 0)
    price = _to_float(candidate_trade.get("price"))
    notional = _to_float(candidate_trade.get("gross_amount"), quantity * price)
    total_cost = _to_float(candidate_trade.get("total_cost"), notional)

    cash = _to_float(portfolio_summary.get("cash"))
    total_equity = _to_float(portfolio_summary.get("total_equity"), cash)
    daily_new_allocation_used = _to_float(portfolio_summary.get("daily_new_allocation_used_hkd"))

    max_single_weight = _to_float(config.get("max_single_position_weight"), 1.0)
    max_daily_new_allocation = _to_float(config.get("max_daily_new_allocation_hkd"), float("inf"))
    max_position_add = _to_float(config.get("max_position_add_allocation_hkd"), float("inf"))
    cash_floor = _to_float(config.get("cash_floor_hkd"), 0.0)

    position_value_map: dict[str, float] = {}
    for row in positions:
        ticker = str(row.get("ticker") or row.get("stock") or "")
        row_qty = int(row.get("quantity") or 0)
        row_price = _to_float(row.get("last_price"), _to_float(row.get("price")))
        position_value_map[ticker] = max(row_qty * row_price, 0.0)

    existing_position_value = position_value_map.get(stock, 0.0)
    projected_position_value = existing_position_value + (notional if action == "BUY" else 0.0)
    # Equity should reflect BUY friction cost (fees/slippage) so concentration
    # checks use a realistic post-trade denominator.
    fee_impact = max(total_cost - notional, 0.0) if action == "BUY" else 0.0
    projected_total_equity = max(total_equity - fee_impact, 0.0)
    projected_weight = (
        projected_position_value / projected_total_equity
        if projected_total_equity > 0
        else 0.0
    )

    rule_results: list[dict] = []

    # 1) Single-position concentration.
    concentration_passed = projected_weight <= max_single_weight
    rule_results.append(
        _build_result(
            rule_name="max_single_position_weight",
            severity="info" if concentration_passed else "blocked",
            passed=concentration_passed,
            message=(
                "Projected position weight is within configured limit."
                if concentration_passed
                else "Projected position weight breaches configured limit."
            ),
            metrics={
                "ticker": stock,
                "projected_weight": projected_weight,
                "max_allowed_weight": max_single_weight,
            },
        )
    )

    # 2) Daily allocation budget.
    projected_daily_new_allocation = daily_new_allocation_used + (notional if action == "BUY" else 0.0)
    daily_allocation_passed = projected_daily_new_allocation <= max_daily_new_allocation
    rule_results.append(
        _build_result(
            rule_name="max_daily_new_allocation_hkd",
            severity="info" if daily_allocation_passed else "warning",
            passed=daily_allocation_passed,
            message=(
                "Projected daily allocation remains within configured budget."
                if daily_allocation_passed
                else "Projected daily allocation exceeds configured budget."
            ),
            metrics={
                "projected_daily_new_allocation_hkd": projected_daily_new_allocation,
                "max_daily_new_allocation_hkd": max_daily_new_allocation,
            },
        )
    )

    # 3) Add-to-existing-position guardrail.
    if existing_position_value > 0.0 and action == "BUY":
        add_passed = notional <= max_position_add
        add_severity = "info" if add_passed else "blocked"
        add_message = (
            "Position-add allocation is within configured per-trade add limit."
            if add_passed
            else "Position-add allocation exceeds configured per-trade add limit."
        )
    else:
        add_passed = True
        add_severity = "info"
        add_message = "No existing position add detected; add-limit guardrail not triggered."

    rule_results.append(
        _build_result(
            rule_name="max_position_add_allocation_hkd",
            severity=add_severity,
            passed=add_passed,
            message=add_message,
            metrics={
                "existing_position_value_hkd": existing_position_value,
                "position_add_notional_hkd": notional if action == "BUY" else 0.0,
                "max_position_add_allocation_hkd": max_position_add,
            },
        )
    )

    # 4) Cash sufficiency + cash floor.
    projected_cash = cash - (total_cost if action == "BUY" else 0.0)
    has_enough_cash = projected_cash >= 0
    above_cash_floor = projected_cash >= cash_floor
    cash_passed = has_enough_cash and above_cash_floor
    if not has_enough_cash:
        cash_message = "Trade would consume more cash than available paper cash."
    elif not above_cash_floor:
        cash_message = "Trade would breach configured paper-cash floor."
    else:
        cash_message = "Projected paper cash remains above configured floor."

    rule_results.append(
        _build_result(
            rule_name="cash_floor_and_sufficiency",
            severity="info" if cash_passed else "blocked",
            passed=cash_passed,
            message=cash_message,
            metrics={
                "cash_hkd": cash,
                "projected_cash_hkd": projected_cash,
                "cash_floor_hkd": cash_floor,
            },
        )
    )

    highest = max((row["severity"] for row in rule_results), key=lambda s: SEVERITY_RANK[s])
    allowed = all(row["severity"] != "blocked" for row in rule_results)

    if allowed:
        summary = f"Trade risk-check passed with overall severity={highest}."
    else:
        failed = [row["rule_name"] for row in rule_results if row["severity"] == "blocked"]
        summary = f"Trade risk-check blocked by: {', '.join(failed)}."

    return {
        "allowed": allowed,
        "severity": highest,
        "summary_message": summary,
        "rule_results": rule_results,
    }
