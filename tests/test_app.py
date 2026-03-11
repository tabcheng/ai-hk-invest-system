import src.app as app


def test_paper_trading_skipped_when_any_ticker_fails(monkeypatch):
    updates = []
    called = {"paper": 0}

    monkeypatch.setattr(app, "TICKERS", ["A.HK", "B.HK"])
    monkeypatch.setattr(app, "get_supabase_client", lambda: object())
    monkeypatch.setattr(app, "create_run", lambda client: 123)

    def fake_signal(ticker):
        if ticker == "A.HK":
            return {"stock": ticker, "signal": "BUY", "price": 10.0, "reason": "ok"}
        raise RuntimeError("fetch failed")

    monkeypatch.setattr(app, "get_signal_for_ticker", fake_signal)
    monkeypatch.setattr(app, "save_signal", lambda client, signal_data: None)

    def fake_paper(client, run_id):
        called["paper"] += 1

    monkeypatch.setattr(app, "run_paper_trading_for_today", fake_paper)
    monkeypatch.setattr(app, "update_run", lambda client, run_id, payload: updates.append(payload))

    app.main()

    assert called["paper"] == 0
    assert len(updates) == 1
    payload = updates[0]
    assert payload["status"] == "FAILED"
    assert payload["failed_tickers"] == 1
    assert "paper_trading skipped" in payload["error_summary"]


def test_paper_trading_runs_when_all_tickers_succeed(monkeypatch):
    updates = []
    called = {"paper": 0}

    monkeypatch.setattr(app, "TICKERS", ["A.HK", "B.HK"])
    monkeypatch.setattr(app, "get_supabase_client", lambda: object())
    monkeypatch.setattr(app, "create_run", lambda client: 124)
    monkeypatch.setattr(
        app,
        "get_signal_for_ticker",
        lambda ticker: {"stock": ticker, "signal": "HOLD", "price": 20.0, "reason": "ok"},
    )
    monkeypatch.setattr(app, "save_signal", lambda client, signal_data: None)

    def fake_paper(client, run_id):
        called["paper"] += 1

    monkeypatch.setattr(app, "run_paper_trading_for_today", fake_paper)
    monkeypatch.setattr(app, "update_run", lambda client, run_id, payload: updates.append(payload))

    app.main()

    assert called["paper"] == 1
    assert len(updates) == 1
    payload = updates[0]
    assert payload["status"] == "SUCCESS"
    assert payload["failed_tickers"] == 0


def test_paper_trading_failure_does_not_change_ticker_failure_counter(monkeypatch):
    updates = []

    monkeypatch.setattr(app, "TICKERS", ["A.HK", "B.HK"])
    monkeypatch.setattr(app, "get_supabase_client", lambda: object())
    monkeypatch.setattr(app, "create_run", lambda client: 125)
    monkeypatch.setattr(
        app,
        "get_signal_for_ticker",
        lambda ticker: {"stock": ticker, "signal": "HOLD", "price": 20.0, "reason": "ok"},
    )
    monkeypatch.setattr(app, "save_signal", lambda client, signal_data: None)

    def failing_paper(client, run_id):
        raise RuntimeError("paper engine failure")

    monkeypatch.setattr(app, "run_paper_trading_for_today", failing_paper)
    monkeypatch.setattr(app, "update_run", lambda client, run_id, payload: updates.append(payload))

    app.main()

    assert len(updates) == 1
    payload = updates[0]
    assert payload["status"] == "FAILED"
    assert payload["failed_tickers"] == 0
    assert "paper_trading: paper engine failure" in payload["error_summary"]
