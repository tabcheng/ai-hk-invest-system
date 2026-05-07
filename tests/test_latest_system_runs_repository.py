from datetime import date, datetime, timezone

import src.latest_system_runs_repository as repo


class _Query:
    def __init__(self, recorder):
        self.recorder = recorder

    def upsert(self, payload, on_conflict=None, returning=None):
        self.recorder["payload"] = payload
        self.recorder["on_conflict"] = on_conflict
        self.recorder["returning"] = returning
        return self

    def select(self, fields):
        self.recorder["fields"] = fields
        return self

    def eq(self, key, value):
        self.recorder.setdefault("eq", []).append((key, value))
        return self

    def order(self, key, desc=False):
        self.recorder.setdefault("order", []).append((key, desc))
        return self

    def limit(self, limit):
        self.recorder["limit"] = limit
        return self

    def execute(self):
        class R:
            data = self.recorder.get("rows", [])

        return R()


class _Client:
    def __init__(self, recorder):
        self.recorder = recorder

    def table(self, name):
        self.recorder["table"] = name
        return _Query(self.recorder)


def test_build_payload_requires_paper_trade_only_true():
    payload = repo.build_latest_system_run_upsert_payload(
        run_id=123,
        business_date=date(2026, 5, 6),
        status="success",
        source="paper_daily_runner",
        data_timestamp=datetime(2026, 5, 6, tzinfo=timezone.utc),
        summary_json={"paper_trade_only": True, "processed_tickers": 3},
        risk_summary_json={},
    )

    assert payload["run_id"] == "123"
    assert payload["status"] == "success"
    assert payload["summary_json"]["paper_trade_only"] is True
    assert payload["updated_at"].endswith("+00:00")


def test_upsert_uses_source_conflict_key():
    recorder = {}
    client = _Client(recorder)

    repo.upsert_latest_system_run(client, {"source": "paper_daily_runner"})

    assert recorder["table"] == "latest_system_runs"
    assert recorder["on_conflict"] == "source"
    assert "updated_at" in recorder["payload"]


def test_upsert_overrides_stale_updated_at_with_fresh_utc_time():
    recorder = {}
    client = _Client(recorder)

    repo.upsert_latest_system_run(client, {"source": "paper_daily_runner", "updated_at": "2000-01-01T00:00:00+00:00"})

    parsed = datetime.fromisoformat(recorder["payload"]["updated_at"])
    assert parsed.tzinfo is not None
    assert recorder["payload"]["updated_at"] != "2000-01-01T00:00:00+00:00"


def test_build_payload_sets_updated_at_from_app_utc_time():
    payload = repo.build_latest_system_run_upsert_payload(
        run_id=123,
        business_date=date(2026, 5, 6),
        status="success",
        source="paper_daily_runner",
        data_timestamp=datetime(2026, 5, 6, tzinfo=timezone.utc),
        summary_json={"paper_trade_only": True, "processed_tickers": 3},
        risk_summary_json={},
    )

    parsed = datetime.fromisoformat(payload["updated_at"])
    assert parsed.tzinfo is not None


def test_read_latest_returns_single_safe_row():
    recorder = {
        "rows": [
            {
                "id": "1",
                "run_id": "123",
                "business_date": "2026-05-06",
                "status": "success",
                "source": "paper_daily_runner",
                "data_timestamp": "2026-05-06T00:00:00+00:00",
                "summary_json": {"paper_trade_only": True},
                "risk_summary_json": {},
                "created_at": "2026-05-06T00:00:00+00:00",
                "updated_at": "2026-05-06T00:00:00+00:00",
            }
        ]
    }
    client = _Client(recorder)

    row = repo.get_latest_system_run(client)

    assert row is not None
    assert row["summary_json"]["paper_trade_only"] is True
    assert recorder["limit"] == 1
