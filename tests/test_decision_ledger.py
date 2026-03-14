from pathlib import Path

import pytest

from src.decision_ledger import (
    DecisionRecord,
    build_decision_record_payload,
    create_decision_record_from_signal,
    save_paper_trade_decision_record,
)


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        self.client.insert_calls.append((self.table_name, self.payload))
        return _Result([self.payload])


class _FakeClient:
    def __init__(self):
        self.insert_calls = []

    def table(self, table_name):
        return _FakeQuery(self, table_name)


def test_build_decision_record_payload_validates_required_fields():
    with pytest.raises(ValueError, match="stock_id is required"):
        build_decision_record_payload(
            DecisionRecord(
                run_id=1,
                stock_id=" ",
                stock_name="Tencent Holdings",
                signal_action="BUY",
                signal_score=None,
                rationale_summary=None,
                human_decision="PENDING",
                decision_note="Awaiting review",
                paper_trade_status="PENDING",
            )
        )


def test_build_decision_record_payload_rejects_non_string_required_fields():
    with pytest.raises(ValueError, match="stock_name is required"):
        build_decision_record_payload(
            DecisionRecord(
                run_id=1,
                stock_id="0700.HK",
                stock_name=None,
                signal_action="BUY",
                signal_score=None,
                rationale_summary=None,
                human_decision="PENDING",
                decision_note="Awaiting review",
                paper_trade_status="PENDING",
            )
        )


def test_build_decision_record_payload_rejects_non_finite_signal_score():
    with pytest.raises(ValueError, match="signal_score must be a finite number"):
        build_decision_record_payload(
            DecisionRecord(
                run_id=1,
                stock_id="0700.HK",
                stock_name="Tencent Holdings",
                signal_action="BUY",
                signal_score=float("inf"),
                rationale_summary=None,
                human_decision="PENDING",
                decision_note="Awaiting review",
                paper_trade_status="PENDING",
            )
        )


def test_save_paper_trade_decision_record_happy_path():
    client = _FakeClient()
    record = DecisionRecord(
        run_id=22,
        stock_id="0700.HK",
        stock_name="Tencent Holdings",
        signal_action="BUY",
        signal_score=0.82,
        rationale_summary="MA50 crossed above MA200",
        human_decision="PENDING",
        decision_note="Needs portfolio allocation review",
        paper_trade_status="PENDING",
    )

    save_paper_trade_decision_record(client, record)

    assert len(client.insert_calls) == 1
    table_name, payload = client.insert_calls[0]
    assert table_name == "paper_trade_decisions"
    assert payload["stock_id"] == "0700.HK"
    assert payload["stock_name"] == "Tencent Holdings"
    assert payload["signal_action"] == "BUY"
    assert payload["human_decision"] == "PENDING"


def test_create_decision_record_from_signal_defaults_to_pending_human_review():
    record = create_decision_record_from_signal(
        run_id=99,
        stock_id="0388.HK",
        stock_name="Hong Kong Exchanges and Clearing",
        signal_data={"signal": "HOLD", "reason": "MA50 equals MA200"},
    )

    assert record.run_id == 99
    assert record.signal_action == "HOLD"
    assert record.human_decision == "PENDING"
    assert record.paper_trade_status == "PENDING"


def test_decision_ledger_migration_contains_required_columns():
    migration_sql = Path("db/migrations/20260313_create_paper_trade_decisions_table.sql").read_text()

    for required_column in [
        "id bigserial primary key",
        "run_id bigint",
        "stock_id text not null",
        "stock_name text not null",
        "signal_action text not null",
        "signal_score numeric",
        "rationale_summary text",
        "human_decision text not null",
        "decision_note text not null",
        "paper_trade_status text not null",
        "created_at timestamptz not null",
    ]:
        assert required_column in migration_sql
