from src.risk_manager import evaluate_paper_trade_risk


BASE_CONFIG = {
    "max_single_position_weight": 0.40,
    "max_daily_new_allocation_hkd": 30000.0,
    "max_position_add_allocation_hkd": 10000.0,
    "cash_floor_hkd": 5000.0,
}


def test_evaluate_paper_trade_risk_allowed_case():
    result = evaluate_paper_trade_risk(
        portfolio_summary={"cash": 80000.0, "total_equity": 100000.0, "daily_new_allocation_used_hkd": 5000.0},
        positions=[{"ticker": "0700.HK", "quantity": 100, "last_price": 100.0}],
        candidate_trade={
            "action": "BUY",
            "stock": "0388.HK",
            "quantity": 50,
            "price": 100.0,
            "gross_amount": 5000.0,
            "total_cost": 5020.0,
        },
        config=BASE_CONFIG,
    )

    assert result["allowed"] is True
    assert result["severity"] == "info"


def test_evaluate_paper_trade_risk_warning_for_daily_budget_breach_only():
    result = evaluate_paper_trade_risk(
        portfolio_summary={"cash": 80000.0, "total_equity": 100000.0, "daily_new_allocation_used_hkd": 28000.0},
        positions=[{"ticker": "0700.HK", "quantity": 100, "last_price": 100.0}],
        candidate_trade={
            "action": "BUY",
            "stock": "0388.HK",
            "quantity": 50,
            "price": 50.0,
            "gross_amount": 2500.0,
            "total_cost": 2518.0,
        },
        config=BASE_CONFIG,
    )

    assert result["allowed"] is True
    assert result["severity"] == "warning"
    assert any(
        row["rule_name"] == "max_daily_new_allocation_hkd" and row["severity"] == "warning"
        for row in result["rule_results"]
    )


def test_evaluate_paper_trade_risk_blocked_for_cash_floor_and_insufficient_cash():
    result = evaluate_paper_trade_risk(
        portfolio_summary={"cash": 4000.0, "total_equity": 60000.0, "daily_new_allocation_used_hkd": 0.0},
        positions=[],
        candidate_trade={
            "action": "BUY",
            "stock": "0005.HK",
            "quantity": 100,
            "price": 50.0,
            "gross_amount": 5000.0,
            "total_cost": 5018.0,
        },
        config=BASE_CONFIG,
    )

    assert result["allowed"] is False
    assert result["severity"] == "blocked"
    assert any(
        row["rule_name"] == "cash_floor_and_sufficiency" and row["severity"] == "blocked"
        for row in result["rule_results"]
    )


def test_evaluate_paper_trade_risk_blocked_for_existing_position_add_limit():
    result = evaluate_paper_trade_risk(
        portfolio_summary={"cash": 90000.0, "total_equity": 100000.0, "daily_new_allocation_used_hkd": 0.0},
        positions=[{"ticker": "0700.HK", "quantity": 100, "last_price": 100.0}],
        candidate_trade={
            "action": "BUY",
            "stock": "0700.HK",
            "quantity": 200,
            "price": 100.0,
            "gross_amount": 20000.0,
            "total_cost": 20020.0,
        },
        config=BASE_CONFIG,
    )

    assert result["allowed"] is False
    assert result["severity"] == "blocked"
    assert any(
        row["rule_name"] == "max_position_add_allocation_hkd" and row["severity"] == "blocked"
        for row in result["rule_results"]
    )
