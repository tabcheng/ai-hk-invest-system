from datetime import date

from src.db import build_signal_payload


def test_build_signal_payload_uses_given_date_and_fields():
    signal_data = {
        "stock": "1299.HK",
        "signal": "SELL",
        "price": 88.5,
        "reason": "MA50 (80.00) is below MA200 (90.00)",
    }

    payload = build_signal_payload(signal_data, signal_date=date(2026, 3, 10))

    assert payload == {
        "date": "2026-03-10",
        "stock": "1299.HK",
        "signal": "SELL",
        "price": 88.5,
        "reason": "MA50 (80.00) is below MA200 (90.00)",
    }
