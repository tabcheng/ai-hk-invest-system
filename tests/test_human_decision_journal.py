from src.human_decision_journal import record_stock_level_decision_note


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
