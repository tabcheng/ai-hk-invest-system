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


def test_market_data_acceptance_mapping_rules_and_boundaries():
    from src.market_data.smoke import build_market_data_acceptance_summary

    fresh = build_market_data_acceptance_summary(freshness_status_display="fresh")
    assert fresh["accepted_for_daily_review"] is True
    assert fresh["market_data_acceptance_status"] == "acceptable_for_paper_review"

    delayed = build_market_data_acceptance_summary(freshness_status_display="delayed")
    assert delayed["accepted_for_daily_review"] is True

    last_close = build_market_data_acceptance_summary(freshness_status_display="last_available_close")
    assert last_close["accepted_for_daily_review"] is True
    assert "last available close" in last_close["market_data_acceptance_label_en"]

    stale = build_market_data_acceptance_summary(freshness_status_display="stale")
    assert stale["accepted_for_daily_review"] is False
    assert "盤中" in stale["market_data_acceptance_warning"] or "intraday" in stale["market_data_acceptance_warning"].lower()

    unknown = build_market_data_acceptance_summary(freshness_status_display="unknown")
    assert unknown["accepted_for_daily_review"] is False
    assert "未能驗證" in unknown["market_data_acceptance_warning"] or "cannot be verified" in unknown["market_data_acceptance_warning"].lower()

    text = " ".join(str(v) for v in {**fresh, **stale, **unknown}.values())
    assert "token" not in text.lower()
    assert "payload" not in text.lower()
    assert "broker" not in text.lower()
    assert "real-money" not in text.lower()

def test_build_market_acceptance_by_ticker_partial_failure_only_falls_back_failed_ticker(monkeypatch):
    from src.market_data.smoke import build_market_acceptance_by_ticker

    def _smoke(ticker, env):
        if ticker == "0388.HK":
            raise RuntimeError("single ticker failed")
        return {
            "data_timestamp_hkt": "2026-05-10T16:10:00+08:00",
            "freshness_status": "last_available_close",
            "delay_minutes": 15,
        }

    monkeypatch.setattr("src.market_data.smoke.build_market_smoke_summary", _smoke)
    monkeypatch.setattr(
        "src.market_data.smoke.classify_market_data_freshness",
        lambda **kwargs: {"freshness_status_display": "last_available_close"},
    )
    acceptance = build_market_acceptance_by_ticker(["0700.HK", "0388.HK", "1299.HK"], env={})
    assert acceptance["0700.HK"]["market_data_acceptance_status"] == "caution_last_available_close"
    assert acceptance["1299.HK"]["market_data_acceptance_status"] == "caution_last_available_close"
    assert acceptance["0388.HK"]["market_data_acceptance_status"] == "unknown"
