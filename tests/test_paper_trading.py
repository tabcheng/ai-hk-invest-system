from datetime import date
from pathlib import Path

from src.paper_trading import (
    PaperTradingConfig,
    Position,
    _build_compact_rule_summary,
    _build_position_state_from_trade_rows,
    _clear_existing_day_outputs,
    _fetch_prior_state,
    _refresh_paper_positions_from_trades,
    get_paper_daily_review_summary_for_run,
    get_paper_position_pnl_review_snapshot,
    get_paper_risk_review_for_run,
    get_paper_portfolio_summary,
    simulate_day,
)


def test_buy_opens_position():
    result = simulate_day(
        signal_rows=[{"id": 1, "date": "2026-03-11", "stock": "0700.HK", "signal": "BUY", "price": 100.0}],
        run_id=10,
        trade_date=date(2026, 3, 11),
    )

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["action"] == "BUY"
    assert trade["quantity"] == 100
    assert trade["run_id"] == 10
    assert result["snapshot"]["run_id"] == 10
    assert result["ending_positions"]["0700.HK"] == Position(quantity=100, average_entry_price=100.0)


def test_sell_closes_position():
    result = simulate_day(
        signal_rows=[{"id": 2, "date": "2026-03-11", "stock": "0700.HK", "signal": "SELL", "price": 110.0}],
        run_id=11,
        trade_date=date(2026, 3, 11),
        starting_positions={"0700.HK": Position(quantity=100, average_entry_price=100.0)},
        starting_cash=90000.0,
    )

    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["action"] == "SELL"
    assert trade["quantity"] == 100
    assert "0700.HK" not in result["ending_positions"]


def test_hold_produces_event_only():
    result = simulate_day(
        signal_rows=[{"id": 3, "date": "2026-03-11", "stock": "0388.HK", "signal": "HOLD", "price": 200.0}],
        run_id=12,
        trade_date=date(2026, 3, 11),
    )

    assert result["trades"] == []
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "HOLD_EVENT"
    assert result["events"][0]["run_id"] == 12


def test_duplicate_buy_does_not_create_second_position():
    result = simulate_day(
        signal_rows=[{"id": 4, "date": "2026-03-11", "stock": "1299.HK", "signal": "BUY", "price": 50.0}],
        run_id=13,
        trade_date=date(2026, 3, 11),
        starting_positions={"1299.HK": Position(quantity=100, average_entry_price=48.0)},
        config=PaperTradingConfig(),
    )

    assert result["trades"] == []
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "BUY_SKIPPED_ALREADY_HOLDING"
    assert result["ending_positions"]["1299.HK"].quantity == 100




def test_duplicate_buy_includes_add_check_context():
    result = simulate_day(
        signal_rows=[{"id": 41, "date": "2026-03-11", "stock": "1299.HK", "signal": "BUY", "price": 50.0}],
        run_id=131,
        trade_date=date(2026, 3, 11),
        starting_positions={"1299.HK": Position(quantity=100, average_entry_price=48.0)},
        config=PaperTradingConfig(max_position_add_allocation_hkd=2000.0),
    )

    assert result["trades"] == []
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "BUY_SKIPPED_ALREADY_HOLDING"
    assert "Add-check:" in result["events"][0]["message"]
    assert result["events"][0]["risk_evaluation"]["allowed"] is False
    assert result["events"][0]["risk_evaluation"]["severity"] == "blocked"


def test_buy_blocked_by_risk_guardrail_cash_floor():
    result = simulate_day(
        signal_rows=[{"id": 40, "date": "2026-03-11", "stock": "1299.HK", "signal": "BUY", "price": 50.0}],
        run_id=130,
        trade_date=date(2026, 3, 11),
        starting_cash=4000.0,
        config=PaperTradingConfig(cash_floor_hkd=5000.0),
    )

    assert result["trades"] == []
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "BUY_BLOCKED_RISK_GUARDRAIL"
    assert "cash_floor_and_sufficiency" in result["events"][0]["message"]
    risk = result["events"][0]["risk_evaluation"]
    assert sorted(risk.keys()) == ["allowed", "rule_results", "severity", "summary_message"]
    assert risk["allowed"] is False
    assert risk["severity"] == "blocked"




def test_buy_executed_event_includes_info_risk_context():
    result = simulate_day(
        signal_rows=[{"id": 60, "date": "2026-03-11", "stock": "0005.HK", "signal": "BUY", "price": 100.0}],
        run_id=140,
        trade_date=date(2026, 3, 11),
    )

    executed_events = [e for e in result["events"] if e["event_type"] == "BUY_EXECUTED"]
    assert len(executed_events) == 1
    assert executed_events[0]["risk_evaluation"]["allowed"] is True
    assert executed_events[0]["risk_evaluation"]["severity"] == "info"


def test_buy_executed_event_includes_warning_risk_context():
    result = simulate_day(
        signal_rows=[{"id": 61, "date": "2026-03-11", "stock": "0388.HK", "signal": "BUY", "price": 100.0}],
        run_id=141,
        trade_date=date(2026, 3, 11),
        config=PaperTradingConfig(max_daily_new_allocation_hkd=5000.0),
    )

    assert len(result["trades"]) == 1
    executed_events = [e for e in result["events"] if e["event_type"] == "BUY_EXECUTED"]
    assert len(executed_events) == 1
    risk = executed_events[0]["risk_evaluation"]
    assert risk["allowed"] is True
    assert risk["severity"] == "warning"

def test_concentration_uses_mark_valuation_with_unrealized_gain_allows_buy():
    result = simulate_day(
        signal_rows=[
            {"id": 50, "date": "2026-03-11", "stock": "0001.HK", "signal": "HOLD", "price": 200.0},
            {"id": 51, "date": "2026-03-11", "stock": "0002.HK", "signal": "BUY", "price": 100.0},
        ],
        run_id=132,
        trade_date=date(2026, 3, 11),
        starting_cash=50000.0,
        starting_positions={"0001.HK": Position(quantity=100, average_entry_price=100.0)},
        config=PaperTradingConfig(max_single_position_weight=0.155),
    )

    assert len(result["trades"]) == 1
    assert result["trades"][0]["stock"] == "0002.HK"


def test_concentration_uses_mark_valuation_with_unrealized_loss_blocks_buy():
    result = simulate_day(
        signal_rows=[
            {"id": 52, "date": "2026-03-11", "stock": "0001.HK", "signal": "HOLD", "price": 50.0},
            {"id": 53, "date": "2026-03-11", "stock": "0002.HK", "signal": "BUY", "price": 100.0},
        ],
        run_id=133,
        trade_date=date(2026, 3, 11),
        starting_cash=50000.0,
        starting_positions={"0001.HK": Position(quantity=100, average_entry_price=100.0)},
        config=PaperTradingConfig(max_single_position_weight=0.17),
    )

    assert result["trades"] == []
    assert any(event["event_type"] == "BUY_BLOCKED_RISK_GUARDRAIL" for event in result["events"])


def test_clear_existing_day_outputs_deletes_all_daily_tables():
    calls = []

    class FakeQuery:
        def __init__(self, table_name):
            self.table_name = table_name

        def delete(self):
            calls.append((self.table_name, "delete"))
            return self

        def eq(self, column, value):
            calls.append((self.table_name, "eq", column, value))
            return self

        def execute(self):
            calls.append((self.table_name, "execute"))
            return self

    class FakeClient:
        def table(self, name):
            calls.append((name, "table"))
            return FakeQuery(name)

    _clear_existing_day_outputs(FakeClient(), date(2026, 3, 11))

    assert calls == [
        ("paper_trades", "table"),
        ("paper_trades", "delete"),
        ("paper_trades", "eq", "trade_date", "2026-03-11"),
        ("paper_trades", "execute"),
        ("paper_events", "table"),
        ("paper_events", "delete"),
        ("paper_events", "eq", "event_date", "2026-03-11"),
        ("paper_events", "execute"),
        ("paper_daily_snapshots", "table"),
        ("paper_daily_snapshots", "delete"),
        ("paper_daily_snapshots", "eq", "snapshot_date", "2026-03-11"),
        ("paper_daily_snapshots", "execute"),
    ]


def test_build_position_state_from_trade_rows_updates_avg_cost_and_partial_sell():
    rows = [
        {"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 100.0, "realized_pnl": 0.0},
        {"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 120.0, "realized_pnl": 0.0},
        {"stock": "0700.HK", "action": "SELL", "quantity": 50, "price": 130.0, "realized_pnl": 740.0},
    ]

    positions = _build_position_state_from_trade_rows(rows)

    assert positions["0700.HK"]["quantity"] == 150
    assert positions["0700.HK"]["avg_cost"] == 110.0
    assert positions["0700.HK"]["last_price"] == 130.0
    assert positions["0700.HK"]["unrealized_pnl"] == 3000.0
    assert positions["0700.HK"]["realized_pnl"] == 740.0


def test_get_paper_portfolio_summary_reads_positions_and_latest_snapshot():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_positions":
                return Result(
                    [
                        {
                            "ticker": "0700.HK",
                            "quantity": 150,
                            "avg_cost": 110.0,
                            "last_price": 130.0,
                            "unrealized_pnl": 3000.0,
                            "realized_pnl": 740.0,
                        }
                    ]
                )
            return Result(
                [
                    {
                        "snapshot_date": "2026-03-14",
                        "cash": 80000.0,
                        "total_equity": 99500.0,
                        "cumulative_realized_pnl": 740.0,
                        "cumulative_unrealized_pnl": 3000.0,
                    }
                ]
            )

    class Client:
        def table(self, table_name):
            return Query(table_name)

    summary = get_paper_portfolio_summary(Client())

    assert summary["snapshot_date"] == "2026-03-14"
    assert summary["cash"] == 80000.0
    assert summary["market_value"] == 19500.0
    assert summary["total_equity"] == 99500.0
    assert summary["open_positions"] == 1


def test_paper_positions_migration_contains_required_columns():
    migration_sql = Path("db/migrations/20260314_create_paper_positions_table.sql").read_text()

    for required_column in [
        "create table if not exists paper_positions",
        "ticker text not null",
        "quantity integer not null default 0",
        "avg_cost numeric not null default 0",
        "last_price numeric not null default 0",
        "unrealized_pnl numeric not null default 0",
        "realized_pnl numeric not null default 0",
        "updated_at timestamptz not null",
    ]:
        assert required_column in migration_sql


def test_fetch_prior_state_rebuilds_only_from_trades_before_trade_date():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def lt(self, *_args):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_daily_snapshots":
                return Result([])
            if self.table_name == "paper_trades":
                return Result([
                    {"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 100.0},
                    {"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 120.0},
                    {"stock": "0700.HK", "action": "SELL", "quantity": 50, "price": 130.0},
                ])
            raise AssertionError(f"unexpected table {self.table_name}")

    class Client:
        def table(self, table_name):
            return Query(table_name)

    cash, realized, positions = _fetch_prior_state(Client(), date(2026, 3, 14))

    assert cash is None
    assert realized == 0.0
    assert positions["0700.HK"] == Position(quantity=150, average_entry_price=110.0)


def test_refresh_paper_positions_sets_updated_at_on_upsert_rows():
    upsert_payload = {"rows": None}

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name
            self._delete = False

        def select(self, _columns):
            return self

        def lte(self, *_args):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def delete(self):
            self._delete = True
            return self

        def in_(self, *_args):
            return self

        def upsert(self, rows, **_kwargs):
            upsert_payload["rows"] = rows
            return self

        def execute(self):
            if self.table_name == "paper_trades":
                return Result([{"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 100.0, "realized_pnl": 0.0, "trade_date": "2026-03-14", "id": 1}])
            if self.table_name == "paper_positions" and not self._delete:
                return Result([])
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    rows = _refresh_paper_positions_from_trades(Client(), date(2026, 3, 14))

    assert len(rows) == 1
    assert "updated_at" in rows[0]
    assert isinstance(rows[0]["updated_at"], str)
    assert upsert_payload["rows"] is not None
    assert "updated_at" in upsert_payload["rows"][0]


def test_fetch_prior_state_uses_strict_lt_trade_date_filter():
    calls = []

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def lt(self, column, value):
            calls.append((self.table_name, "lt", column, value))
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_daily_snapshots":
                return Result([])
            if self.table_name == "paper_trades":
                return Result([])
            raise AssertionError(f"unexpected table {self.table_name}")

    class Client:
        def table(self, table_name):
            return Query(table_name)

    _fetch_prior_state(Client(), date(2026, 3, 14))

    assert ("paper_trades", "lt", "trade_date", "2026-03-14") in calls


def test_refresh_paper_positions_deletes_stale_tickers():
    delete_calls = []

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name
            self._delete_mode = False

        def select(self, _columns):
            return self

        def lte(self, *_args):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def upsert(self, *_args, **_kwargs):
            return self

        def delete(self):
            self._delete_mode = True
            return self

        def in_(self, column, values):
            delete_calls.append((column, values))
            return self

        def execute(self):
            if self.table_name == "paper_trades":
                return Result([])
            if self.table_name == "paper_positions" and not self._delete_mode:
                return Result([{"ticker": "0700.HK"}])
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    _refresh_paper_positions_from_trades(Client(), date(2026, 3, 14))

    assert delete_calls == [("ticker", ["0700.HK"])]


def test_risk_observability_migration_adds_jsonb_columns():
    migration_sql = Path("db/migrations/20260314_add_risk_evaluation_observability_v1.sql").read_text()

    assert "alter table if exists paper_events" in migration_sql
    assert "add column if not exists risk_evaluation jsonb" in migration_sql
    assert "alter table if exists paper_trade_decisions" in migration_sql


def test_build_compact_rule_summary_groups_failed_warning_and_passed_rules():
    summary = _build_compact_rule_summary(
        {
            "rule_results": [
                {"rule_name": "cash_floor_and_sufficiency", "passed": False, "severity": "blocked"},
                {"rule_name": "max_daily_new_allocation_hkd", "passed": True, "severity": "warning"},
                {"rule_name": "max_single_position_weight", "passed": True, "severity": "info"},
            ]
        }
    )

    assert summary == (
        "failed=cash_floor_and_sufficiency"
        " | warning=max_daily_new_allocation_hkd"
        " | passed=max_single_position_weight"
    )


def test_get_paper_risk_review_for_run_summarizes_buy_risk_outcomes():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def order(self, _column):
            return self

        def execute(self):
            return Result(
                [
                    {
                        "id": 1,
                        "stock": "0005.HK",
                        "event_type": "BUY_BLOCKED_RISK_GUARDRAIL",
                        "risk_evaluation": {
                            "severity": "blocked",
                            "summary_message": "Trade risk-check blocked by: cash_floor_and_sufficiency.",
                            "rule_results": [
                                {"rule_name": "cash_floor_and_sufficiency", "passed": False, "severity": "blocked"}
                            ],
                        },
                    },
                    {
                        "id": 2,
                        "stock": "0388.HK",
                        "event_type": "BUY_EXECUTED",
                        "risk_evaluation": {
                            "severity": "warning",
                            "summary_message": "Trade risk-check passed with overall severity=warning.",
                            "rule_results": [
                                {"rule_name": "max_daily_new_allocation_hkd", "passed": True, "severity": "warning"}
                            ],
                        },
                    },
                    {
                        "id": 3,
                        "stock": "0700.HK",
                        "event_type": "BUY_EXECUTED",
                        "risk_evaluation": {
                            "severity": "info",
                            "summary_message": "Trade risk-check passed with overall severity=info.",
                            "rule_results": [
                                {"rule_name": "max_single_position_weight", "passed": True, "severity": "info"}
                            ],
                        },
                    },
                    {
                        "id": 4,
                        "stock": "0700.HK",
                        "event_type": "HOLD_EVENT",
                        "risk_evaluation": {
                            "severity": "blocked",
                            "summary_message": "Should be ignored.",
                            "rule_results": [],
                        },
                    },
                    {
                        "id": 5,
                        "stock": "1299.HK",
                        "event_type": "BUY_SKIPPED_ALREADY_HOLDING",
                        "risk_evaluation": None,
                    },
                ]
            )

    class Client:
        def table(self, _table_name):
            return Query()

    review = get_paper_risk_review_for_run(Client(), run_id=200)

    assert review["run_id"] == 200
    assert review["total_blocked_buys"] == 1
    assert review["total_warning_buys"] == 1
    assert review["total_executed_buys"] == 2
    assert sorted(review["per_ticker"].keys()) == ["0005.HK", "0388.HK", "0700.HK"]
    assert review["per_ticker"]["0005.HK"][0]["event_type"] == "BUY_BLOCKED_RISK_GUARDRAIL"
    assert review["per_ticker"]["0005.HK"][0]["severity"] == "blocked"
    assert review["per_ticker"]["0005.HK"][0]["compact_rule_summary"] == "failed=cash_floor_and_sufficiency"
    assert review["per_ticker"]["0388.HK"][0]["compact_rule_summary"] == "warning=max_daily_new_allocation_hkd"


def test_get_paper_risk_review_for_run_normalizes_unknown_severity_to_info():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def order(self, _column):
            return self

        def execute(self):
            return Result(
                [
                    {
                        "id": 1,
                        "stock": "0001.HK",
                        "event_type": "BUY_EXECUTED",
                        "risk_evaluation": {
                            "allowed": True,
                            "severity": "urgent",
                            "summary_message": "risk payload with unknown severity",
                            "rule_results": [],
                        },
                    }
                ]
            )

    class Client:
        def table(self, _table_name):
            return Query()

    review = get_paper_risk_review_for_run(Client(), run_id=201)

    assert review["total_warning_buys"] == 0
    assert review["total_blocked_buys"] == 0
    assert review["total_executed_buys"] == 1
    assert review["per_ticker"]["0001.HK"][0]["severity"] == "info"


def test_get_paper_daily_review_summary_for_run_returns_beginner_friendly_shape():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name
            self._snapshot_lt_value = None

        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def lt(self, _column, value):
            self._snapshot_lt_value = value
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_events":
                return Result(
                    [
                        {
                            "id": 1,
                            "stock": "0005.HK",
                            "event_type": "BUY_BLOCKED_RISK_GUARDRAIL",
                            "risk_evaluation": {
                                "severity": "blocked",
                                "summary_message": "blocked",
                                "rule_results": [],
                            },
                        },
                        {
                            "id": 2,
                            "stock": "0700.HK",
                            "event_type": "BUY_EXECUTED",
                            "risk_evaluation": {
                                "severity": "warning",
                                "summary_message": "warning",
                                "rule_results": [],
                            },
                        },
                        {
                            "id": 3,
                            "stock": "0011.HK",
                            "event_type": "HOLD_EVENT",
                            "risk_evaluation": None,
                        },
                    ]
                )
            if self.table_name == "paper_trades":
                return Result(
                    [
                        {"stock": "0700.HK", "action": "BUY"},
                        {"stock": "0388.HK", "action": "SELL"},
                    ]
                )
            if self.table_name == "paper_daily_snapshots" and self._snapshot_lt_value is None:
                return Result(
                    [
                        {
                            "snapshot_date": "2026-03-15",
                            "cash": 90000.0,
                            "total_equity": 101000.0,
                            "open_positions": 2,
                        }
                    ]
                )
            if self.table_name == "paper_daily_snapshots" and self._snapshot_lt_value is not None:
                return Result([{"snapshot_date": "2026-03-14", "cash": 95000.0, "total_equity": 100000.0}])
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    summary = get_paper_daily_review_summary_for_run(Client(), run_id=300)

    assert summary["run_id"] == 300
    assert summary["total_executed_buys"] == 1
    assert summary["total_blocked_buys"] == 1
    assert summary["total_warning_buys"] == 1
    assert summary["number_of_tickers_with_activity"] == 4
    assert summary["notable_items"] == [
        "1 BUY signal(s) were blocked by risk guardrails.",
        "1 BUY execution(s) had warning-level risk notes.",
        "1 SELL trade(s) were executed.",
    ]
    assert summary["portfolio_change_summary"] == (
        "Portfolio vs previous snapshot: equity +1000.00 HKD, cash -5000.00 HKD, open positions now 2."
    )


def test_get_paper_daily_review_summary_for_run_handles_missing_snapshot_and_no_executed_buys():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def lt(self, _column, _value):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_events":
                return Result(
                    [
                        {
                            "id": 1,
                            "stock": "1299.HK",
                            "event_type": "BUY_BLOCKED_RISK_GUARDRAIL",
                            "risk_evaluation": {
                                "severity": "blocked",
                                "summary_message": "blocked",
                                "rule_results": [],
                            },
                        }
                    ]
                )
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    summary = get_paper_daily_review_summary_for_run(Client(), run_id=301)

    assert summary["run_id"] == 301
    assert summary["total_executed_buys"] == 0
    assert summary["number_of_tickers_with_activity"] == 1
    assert summary["notable_items"] == [
        "1 BUY signal(s) were blocked by risk guardrails.",
        "No BUY trades were executed in this run.",
    ]
    assert summary["portfolio_change_summary"] is None


def test_get_paper_position_pnl_review_snapshot_builds_open_closed_and_totals():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_trades":
                return Result(
                    [
                        {"stock": "0700.HK", "action": "BUY", "quantity": 100, "price": 100.0, "realized_pnl": 0.0},
                        {"stock": "0011.HK", "action": "BUY", "quantity": 50, "price": 80.0, "realized_pnl": 0.0},
                        {"stock": "0011.HK", "action": "SELL", "quantity": 50, "price": 88.0, "realized_pnl": 382.0},
                    ]
                )
            if self.table_name == "paper_positions":
                return Result(
                    [
                        {
                            "ticker": "0700.HK",
                            "quantity": 100,
                            "avg_cost": 100.0,
                            "last_price": 110.0,
                            "unrealized_pnl": 1000.0,
                            "realized_pnl": 0.0,
                            "updated_at": "2026-03-22T12:00:00+00:00",
                        }
                    ]
                )
            if self.table_name == "paper_daily_snapshots":
                return Result([{"snapshot_date": "2026-03-22"}])
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    snapshot = get_paper_position_pnl_review_snapshot(Client())

    assert snapshot["open_positions_count"] == 1
    assert snapshot["closed_positions_count"] == 1
    assert snapshot["total_realized_pnl"] == 382.0
    assert snapshot["total_unrealized_pnl"] == 1000.0
    assert snapshot["valuation_timestamp"] == "2026-03-22"
    assert [row["stock"] for row in snapshot["per_symbol"]] == ["0011.HK", "0700.HK"]
    assert snapshot["per_symbol"][0]["position_status"] == "CLOSED"
    assert snapshot["per_symbol"][0]["stock_name"] is None
    assert snapshot["per_symbol"][1]["position_status"] == "OPEN"


def test_get_paper_position_pnl_review_snapshot_is_read_only_query_path():
    calls: list[tuple[str, str]] = []

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            calls.append((self.table_name, "select"))
            return self

        def order(self, *_args, **_kwargs):
            calls.append((self.table_name, "order"))
            return self

        def limit(self, _n):
            calls.append((self.table_name, "limit"))
            return self

        def execute(self):
            calls.append((self.table_name, "execute"))
            return Result([])

    class Client:
        def table(self, table_name):
            calls.append((table_name, "table"))
            return Query(table_name)

    snapshot = get_paper_position_pnl_review_snapshot(Client())

    assert snapshot["open_positions_count"] == 0
    assert snapshot["closed_positions_count"] == 0
    assert snapshot["per_symbol"] == []
    assert all(method not in {"insert", "update", "upsert", "delete"} for _, method in calls)


def test_get_paper_position_pnl_review_snapshot_sell_only_row_not_counted_as_closed():
    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_trades":
                return Result(
                    [
                        {"stock": "9999.HK", "action": "SELL", "quantity": 10, "price": 50.0, "realized_pnl": 0.0}
                    ]
                )
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    snapshot = get_paper_position_pnl_review_snapshot(Client())

    assert snapshot["open_positions_count"] == 0
    assert snapshot["closed_positions_count"] == 0
    assert len(snapshot["per_symbol"]) == 1
    assert snapshot["per_symbol"][0]["position_status"] == "FLAT"


def test_get_paper_position_pnl_review_snapshot_replays_by_trade_date_then_id():
    order_calls: list[tuple[str, str]] = []

    class Result:
        def __init__(self, data):
            self.data = data

    class Query:
        def __init__(self, table_name):
            self.table_name = table_name

        def select(self, _columns):
            return self

        def order(self, column, **_kwargs):
            order_calls.append((self.table_name, column))
            return self

        def limit(self, _n):
            return self

        def execute(self):
            if self.table_name == "paper_trades":
                # Simulate rerun/backfill case: older trade_date has newer id.
                return Result(
                    [
                        {
                            "stock": "0700.HK",
                            "action": "BUY",
                            "quantity": 50,
                            "price": 80.0,
                            "realized_pnl": 0.0,
                            "trade_date": "2026-03-20",
                            "id": 99,
                        },
                        {
                            "stock": "0700.HK",
                            "action": "BUY",
                            "quantity": 100,
                            "price": 100.0,
                            "realized_pnl": 0.0,
                            "trade_date": "2026-03-21",
                            "id": 10,
                        },
                        {
                            "stock": "0700.HK",
                            "action": "SELL",
                            "quantity": 100,
                            "price": 110.0,
                            "realized_pnl": 1600.0,
                            "trade_date": "2026-03-22",
                            "id": 11,
                        },
                    ]
                )
            if self.table_name == "paper_daily_snapshots":
                return Result([{"snapshot_date": "2026-03-22"}])
            return Result([])

    class Client:
        def table(self, table_name):
            return Query(table_name)

    snapshot = get_paper_position_pnl_review_snapshot(Client())

    assert ("paper_trades", "trade_date") in order_calls
    assert ("paper_trades", "id") in order_calls
    assert snapshot["open_positions_count"] == 1
    assert snapshot["closed_positions_count"] == 0
    assert snapshot["total_realized_pnl"] == 1600.0
    assert len(snapshot["per_symbol"]) == 1
    symbol = snapshot["per_symbol"][0]
    assert symbol["stock"] == "0700.HK"
    assert symbol["quantity"] == 50
    assert round(symbol["avg_cost"], 6) == round((50 * 80.0 + 100 * 100.0) / 150, 6)
    assert symbol["position_status"] == "OPEN"
