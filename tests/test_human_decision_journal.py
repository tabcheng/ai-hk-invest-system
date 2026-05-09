from src.human_decision_journal import (
    record_miniapp_human_paper_decision_journal,
    record_stock_level_decision_note,
)


class _FakeExecResult:
    def __init__(self):
        self.data = [{"id": 99}]


class _FakeTable:
    def __init__(self):
        self.payload = None

    def insert(self, payload):
        self.payload = payload
        return self

    def execute(self):
        return _FakeExecResult()


class _FakeClient:
    def __init__(self):
        self.table_name = None
        self.table_obj = _FakeTable()

    def table(self, table_name):
        self.table_name = table_name
        return self.table_obj


def test_record_stock_level_decision_note_payload_includes_stock_metadata():
    client = _FakeClient()
    result = record_stock_level_decision_note(
        client,
        run_id=31,
        stock_id="0700.HK",
        source_command="/daily_review",
        human_action="observe",
        note="QA stock-level smoke test only; no execution.",
        operator_user_id_hash_or_label="u-1",
    )
    payload = client.table_obj.payload
    assert client.table_name == "human_decision_journal_entries"
    assert payload["scope"] == "stock"
    assert payload["run_id"] == 31
    assert payload["human_action"] == "observe"
    assert payload["source_command"] == "/daily_review"
    assert payload["metadata"]["stock_id"] == "0700.HK"
    assert result["id"] == 99


def test_record_miniapp_human_paper_decision_journal_forces_paper_only_fields():
    client = _FakeClient()
    result = record_miniapp_human_paper_decision_journal(
        client,
        business_date="2026-05-09",
        run_id="run-117",
        ticker="0700.HK",
        decision_type="watch",
        rationale_text="Paper-only review note.",
        operator_user_id_hash_or_label="tg_user:42",
        confidence_label="medium",
        quantity_intent=100,
        notional_intent=50000.0,
    )
    payload = client.table_obj.payload
    assert payload["operator_user_id_hash_or_label"] == "tg_user:42"
    assert payload["metadata"]["paper_trade_only"] is True
    assert payload["metadata"]["real_trade_decision"] is False
    assert payload["metadata"]["broker_execution"] is False
    assert payload["metadata"]["no_order_created"] is True
    assert payload["metadata"]["decision_scope"] == "human_paper_decision"
    assert "init_data" not in payload["metadata"]
    assert result["id"] == 99
