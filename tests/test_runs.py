from datetime import datetime, timedelta, timezone

from src.runs import get_latest_run_execution_summary, list_recent_runs


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, client):
        self.client = client
        self.cutoff = None
        self.selected_columns = None

    def select(self, columns):
        self.selected_columns = columns
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


class _LatestSummaryQuery:
    def __init__(self, client):
        self.client = client
        self.selected_columns = None

    def select(self, columns):
        self.selected_columns = columns
        return self

    def order(self, _column, desc=False):
        assert desc is True
        return self

    def limit(self, _count):
        return self

    def execute(self):
        return _Result(self.client.rows[:1])


class _FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def table(self, table_name):
        assert table_name == "runs"
        self.last_query = _FakeQuery(self)
        return self.last_query


class _LatestSummaryClient:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def table(self, table_name):
        assert table_name == "runs"
        self.last_query = _LatestSummaryQuery(self)
        return self.last_query


def test_list_recent_runs_filters_by_days_window():
    now = datetime.now(timezone.utc)
    within_window = (now - timedelta(days=2)).isoformat()
    out_of_window = (now - timedelta(days=8)).isoformat()
    fake_client = _FakeClient(
        rows=[
            {"id": 101, "status": "SUCCESS", "created_at": within_window},
            {"id": 99, "status": "FAILED", "created_at": out_of_window},
        ]
    )

    rows = list_recent_runs(fake_client, days=5)

    assert len(rows) == 1
    assert rows[0]["id"] == 101
    assert fake_client.last_query.selected_columns == "id,status,created_at"


def test_list_recent_runs_rejects_invalid_days():
    fake_client = _FakeClient(rows=[])
    try:
        list_recent_runs(fake_client, days=0)
        assert False, "expected ValueError for non-positive days"
    except ValueError as exc:
        assert "days must be a positive integer" in str(exc)


def test_list_recent_runs_selects_schema_safe_columns_only():
    fake_client = _FakeClient(rows=[])
    list_recent_runs(fake_client, days=5)
    assert fake_client.last_query.selected_columns == "id,status,created_at"
    assert "updated_at" not in fake_client.last_query.selected_columns


def test_get_latest_run_execution_summary_reads_traceable_fields():
    fake_client = _LatestSummaryClient(
        rows=[
            {
                "id": 501,
                "status": "SUCCESS",
                "created_at": "2026-03-21T12:00:00+00:00",
                "finished_at": "2026-03-21T12:00:08+00:00",
                "error_summary": None,
            }
        ]
    )
    row = get_latest_run_execution_summary(fake_client)
    assert row["id"] == 501
    assert fake_client.last_query.selected_columns == "id,status,created_at,finished_at,error_summary"
