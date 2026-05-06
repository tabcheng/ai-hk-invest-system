from scripts.step92a_post_merge_smoke import _safe_latest_row


def test_safe_latest_row_only_safe_fields() -> None:
    row = {
        "run_id": 123,
        "business_date": "2026-05-06",
        "status": "success",
        "source": "paper_daily_runner",
        "data_timestamp": "2026-05-06T00:00:00Z",
        "summary_json": {"paper_trade_only": True, "processed_tickers": 10, "successful_tickers": 9, "failed_tickers": 1, "secret": "x"},
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:01:00Z",
        "service_role_key": "must_not_leak",
    }
    safe = _safe_latest_row(row)
    assert safe == {
        "run_id": 123,
        "business_date": "2026-05-06",
        "status": "success",
        "source": "paper_daily_runner",
        "data_timestamp": "2026-05-06T00:00:00Z",
        "paper_trade_only": True,
        "processed_tickers": 10,
        "successful_tickers": 9,
        "failed_tickers": 1,
        "created_at": "2026-05-06T00:00:00Z",
        "updated_at": "2026-05-06T00:01:00Z",
    }


def test_safe_latest_row_none() -> None:
    assert _safe_latest_row(None) is None
