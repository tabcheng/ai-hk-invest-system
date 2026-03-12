from datetime import date

from src.notifications import (
    build_daily_summary_message,
    send_daily_run_summary,
    send_daily_run_summary_with_telemetry,
    send_telegram_message,
)


class _FakeQuery:
    def __init__(self, table_name, client):
        self.table_name = table_name
        self.client = client
        self.filters = {}
        self.ordering = None
        self.insert_payload = None

    def select(self, _columns):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, key, desc=False):
        self.ordering = (key, desc)
        return self

    def limit(self, _count):
        return self

    def upsert(self, payload, **_kwargs):
        self.insert_payload = payload
        return self

    def execute(self):
        class Result:
            def __init__(self, data):
                self.data = data

        if self.insert_payload is not None:
            self.client.inserts.append((self.table_name, self.insert_payload))
            return Result([self.insert_payload])

        if self.table_name == "notification_logs":
            run_date = self.filters.get("notification_date")
            target = self.filters.get("target")
            sent = self.client.sent_logs.get((run_date, target), False)
            return Result([{"id": 1}] if sent else [])

        if self.table_name == "paper_daily_snapshots":
            if "snapshot_date" in self.filters:
                run_date = self.filters["snapshot_date"]
                equity = self.client.equity_by_date.get(run_date)
                return Result([] if equity is None else [{"total_equity": equity}])
            if self.client.latest_equity is None:
                return Result([])
            return Result([{"snapshot_date": "2026-03-10", "total_equity": self.client.latest_equity}])

        return Result([])


class _FakeClient:
    def __init__(self, equity_by_date=None, latest_equity=None, sent_logs=None):
        self.equity_by_date = equity_by_date or {}
        self.latest_equity = latest_equity
        self.sent_logs = sent_logs or {}
        self.inserts = []

    def table(self, table_name):
        return _FakeQuery(table_name, self)


def test_build_daily_summary_message_contains_required_fields_and_stock_names():
    message = build_daily_summary_message(
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK", "0388.HK", "1299.HK"],
        signal_outcomes={"0700.HK": "BUY", "0388.HK": "HOLD", "1299.HK": "SELL"},
        paper_trade_count_today=2,
        total_equity=101234.56,
        equity_source="run_date",
        warning_note=None,
    )

    assert "<b>date:</b> 2026-03-11" in message
    assert "<b>status:</b> SUCCESS" in message
    assert "Tencent Holdings (0700.HK): <b>BUY</b>" in message
    assert "Hong Kong Exchanges and Clearing (0388.HK): <b>HOLD</b>" in message
    assert "AIA Group (1299.HK): <b>SELL</b>" in message
    assert "<b>paper_trades_today:</b> 2" in message
    assert "<b>total_equity (run_date):</b> 101234.56 HKD" in message


def test_build_daily_summary_message_uses_na_equity_and_warning_note():
    message = build_daily_summary_message(
        run_date=date(2026, 3, 11),
        run_status="FAILED",
        tickers=["0700.HK"],
        signal_outcomes={"0700.HK": "ERROR"},
        paper_trade_count_today=0,
        total_equity=None,
        equity_source="none",
        warning_note="paper_trading skipped",
    )

    assert "<b>total_equity:</b> N/A" in message
    assert "<b>note:</b> paper_trading skipped" in message



def test_build_daily_summary_message_unknown_ticker_uses_id_only():
    message = build_daily_summary_message(
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["9999.HK"],
        signal_outcomes={"9999.HK": "HOLD"},
        paper_trade_count_today=0,
        total_equity=None,
        equity_source="none",
    )

    assert "• 9999.HK: <b>HOLD</b>" in message

def test_send_telegram_message_skips_when_env_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    sent = send_telegram_message("hello")

    assert sent is False


def test_send_daily_run_summary_supports_missing_client(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    sent = send_daily_run_summary(
        client=None,
        run_id=None,
        run_date=date(2026, 3, 11),
        run_status="FAILED",
        tickers=["0700.HK"],
        signal_outcomes={},
        paper_trade_count_today=0,
        warning_note="startup failure",
    )

    assert sent is False


def test_send_daily_run_summary_skips_when_already_sent(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-1")

    fake_client = _FakeClient(sent_logs={("2026-03-11", "chat-1"): True})

    sent = send_daily_run_summary(
        client=fake_client,
        run_id=301,
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK"],
        signal_outcomes={"0700.HK": "HOLD"},
        paper_trade_count_today=0,
    )

    assert sent is True
    assert fake_client.inserts == []


def test_send_daily_run_summary_prefers_run_date_equity_and_records_dedup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-2")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")

    captured = {"message": None}

    def fake_send(text):
        captured["message"] = text
        return {
            "delivered": True,
            "channel": "telegram",
            "telegram_message_id": 999,
            "failure_reason": None,
        }

    monkeypatch.setattr("src.notifications.send_telegram_message_with_result", fake_send)

    fake_client = _FakeClient(equity_by_date={"2026-03-11": 123456.78}, latest_equity=99999.0)

    sent = send_daily_run_summary(
        client=fake_client,
        run_id=302,
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK"],
        signal_outcomes={"0700.HK": "BUY"},
        paper_trade_count_today=1,
    )

    assert sent is True
    assert "<b>total_equity (run_date):</b> 123456.78 HKD" in captured["message"]
    assert fake_client.inserts
    table_name, payload = fake_client.inserts[0]
    assert table_name == "notification_logs"
    assert payload["notification_date"] == "2026-03-11"
    assert payload["target"] == "chat-2"
    assert payload["run_id"] == 302


def test_send_daily_run_summary_with_telemetry_models_single_attempt(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-telemetry")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")

    def fake_send(_text):
        return {
            "delivered": False,
            "channel": "telegram",
            "telegram_message_id": None,
            "failure_reason": "http_500",
        }

    monkeypatch.setattr("src.notifications.send_telegram_message_with_result", fake_send)

    telemetry = send_daily_run_summary_with_telemetry(
        client=None,
        run_id=None,
        run_date=date(2026, 3, 11),
        run_status="FAILED",
        tickers=["0700.HK"],
        signal_outcomes={"0700.HK": "ERROR"},
        paper_trade_count_today=0,
    )

    assert telemetry["schema_version"] == 1
    assert telemetry["attempted"] is True
    assert telemetry["success"] is False
    assert telemetry["channel"] == "telegram"
    assert telemetry["message_type"] == "DAILY_SUMMARY"
    assert telemetry["telegram_message_id"] is None
    assert telemetry["failure_reason"] == "http_500"
    assert telemetry["skip_reason"] is None
    assert "messages" not in telemetry
    assert telemetry["counts"]["attempts"] == 1
    assert telemetry["counts"]["delivered"] == 0
    assert telemetry["counts"]["failed"] == 1
    assert telemetry["counts"]["skipped"] == 0
    assert telemetry["context"]["ticker_count"] == 1


def test_send_daily_run_summary_with_telemetry_dedup_skip_is_not_failure(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-dedup")

    fake_client = _FakeClient(sent_logs={("2026-03-11", "chat-dedup"): True})

    telemetry = send_daily_run_summary_with_telemetry(
        client=fake_client,
        run_id=401,
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK", "0388.HK"],
        signal_outcomes={"0700.HK": "BUY", "0388.HK": "HOLD"},
        paper_trade_count_today=1,
    )

    assert telemetry["attempted"] is False
    assert telemetry["success"] is True
    assert telemetry["skip_reason"] == "dedup_already_sent"
    assert telemetry["failure_reason"] is None
    assert telemetry["counts"]["attempts"] == 0
    assert telemetry["counts"]["delivered"] == 0
    assert telemetry["counts"]["failed"] == 0
    assert telemetry["counts"]["skipped"] == 1
    assert telemetry["context"]["ticker_count"] == 2


def test_send_daily_run_summary_with_telemetry_success_counts(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-success")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")

    def fake_send(_text):
        return {
            "delivered": True,
            "channel": "telegram",
            "telegram_message_id": 1234,
            "failure_reason": None,
        }

    monkeypatch.setattr("src.notifications.send_telegram_message_with_result", fake_send)

    telemetry = send_daily_run_summary_with_telemetry(
        client=None,
        run_id=None,
        run_date=date(2026, 3, 11),
        run_status="SUCCESS",
        tickers=["0700.HK", "0388.HK"],
        signal_outcomes={"0700.HK": "BUY", "0388.HK": "HOLD"},
        paper_trade_count_today=1,
    )

    assert telemetry["attempted"] is True
    assert telemetry["success"] is True
    assert telemetry["counts"]["attempts"] == 1
    assert telemetry["counts"]["delivered"] == 1
    assert telemetry["counts"]["failed"] == 0
    assert telemetry["counts"]["skipped"] == 0
    assert telemetry["telegram_message_id"] == 1234
    assert telemetry["context"]["ticker_count"] == 2
