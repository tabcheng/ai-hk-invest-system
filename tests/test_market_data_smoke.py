import json

from scripts import market_data_smoke


def test_smoke_token_absent_unavailable(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["market_data_smoke", "--ticker", "0700.HK", "--provider", "eodhd"]) 
    rc = market_data_smoke.main()
    out = capsys.readouterr()
    assert rc == 0
    payload = json.loads(out.out.strip())
    assert payload["status"] == "unavailable"
    assert "token" not in out.out.lower()
    assert "token" not in out.err.lower()


def test_smoke_fake_provider_ok_pretty(capsys, monkeypatch):
    class StubProvider:
        def get_ticker_market_snapshot(self, ticker, business_date=None):
            from src.market_data.review_provider import MarketTickerSnapshot

            return MarketTickerSnapshot(
                ticker=ticker,
                status="ok",
                reference_price=320.0,
                previous_close=319.0,
                change=1.0,
                change_pct=0.31,
                volume=100,
                turnover=None,
                currency="HKD",
                market="HKEX",
                data_source="eodhd",
                data_timestamp_hkt="2026-05-10T16:00:00+08:00",
                freshness_status="unknown",
                delay_minutes=None,
                adjustment_policy="vendor_default",
                confidence="unknown",
                limitations=[],
            )

    monkeypatch.setattr(market_data_smoke, "build_review_shell_market_data_provider", lambda env: StubProvider())
    monkeypatch.setattr("sys.argv", ["market_data_smoke", "--ticker", "0700.HK", "--provider", "eodhd", "--pretty"]) 
    rc = market_data_smoke.main()
    out = capsys.readouterr()
    assert rc == 0
    payload = json.loads(out.out)
    assert payload["status"] == "ok"
    assert payload["data_source"] == "eodhd"
    assert "token" not in out.out.lower()
