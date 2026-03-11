from datetime import date

from src.paper_trading import (
    PaperTradingConfig,
    Position,
    _clear_existing_day_outputs,
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
