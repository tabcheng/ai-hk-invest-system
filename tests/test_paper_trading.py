from datetime import date
from pathlib import Path

from src.paper_trading import (
    PaperTradingConfig,
    Position,
    _build_position_state_from_trade_rows,
    _clear_existing_day_outputs,
    _fetch_prior_state,
    _refresh_paper_positions_from_trades,
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
