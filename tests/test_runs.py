from datetime import datetime, timedelta, timezone

from src.runs import list_recent_runs


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client):
        self.client = client
        self.cutoff = None

    def select(self, _columns):
        return self

    def gte(self, column, value):
        assert column == "created_at"
        self.cutoff = value
        return self

    def order(self, _column, desc=False):
        assert desc is True
        return self

    def limit(self, _count):
        return self

    def execute(self):
        cutoff_dt = datetime.fromisoformat(self.cutoff)
        data = [row for row in self.client.rows if datetime.fromisoformat(row["created_at"]) >= cutoff_dt]
        return _Result(data)


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table_name):
        assert table_name == "runs"
        return _FakeQuery(self)


def test_list_recent_runs_filters_by_days_window():
    now = datetime.now(timezone.utc)
    within_window = (now - timedelta(days=2)).isoformat()
    out_of_window = (now - timedelta(days=8)).isoformat()
    fake_client = _FakeClient(
        rows=[
            {"id": 101, "status": "SUCCESS", "created_at": within_window, "updated_at": within_window},
            {"id": 99, "status": "FAILED", "created_at": out_of_window, "updated_at": out_of_window},
        ]
    )

    rows = list_recent_runs(fake_client, days=5)

    assert len(rows) == 1
    assert rows[0]["id"] == 101


def test_list_recent_runs_rejects_invalid_days():
    fake_client = _FakeClient(rows=[])
    try:
        list_recent_runs(fake_client, days=0)
        assert False, "expected ValueError for non-positive days"
    except ValueError as exc:
        assert "days must be a positive integer" in str(exc)
