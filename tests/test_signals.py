import pandas as pd

from src.signals import generate_signal_from_data


def test_generate_signal_buy_when_ma50_above_ma200():
    close_prices = [100.0] * 199 + [300.0]
    df = pd.DataFrame({"Close": close_prices})

    result = generate_signal_from_data("0700.HK", df)

    assert result["stock"] == "0700.HK"
    assert result["signal"] == "BUY"
    assert result["price"] == 300.0
    assert "above MA200" in result["reason"]


def test_generate_signal_insufficient_data_when_history_too_short():
    df = pd.DataFrame({"Close": [10.0, 11.0, 12.0]})

    result = generate_signal_from_data("0388.HK", df)

    assert result == {
        "stock": "0388.HK",
        "signal": "INSUFFICIENT_DATA",
        "price": 12.0,
        "reason": "Not enough historical data to calculate both MA50 and MA200",
    }


def test_generate_signal_returns_no_data_for_empty_frame():
    df = pd.DataFrame()

    result = generate_signal_from_data("1299.HK", df)

    assert result == {
        "stock": "1299.HK",
        "signal": "NO_DATA",
        "price": None,
        "reason": "No market data returned from provider",
    }


def test_generate_signal_returns_hold_when_moving_averages_equal():
    close_prices = [200.0] * 200
    df = pd.DataFrame({"Close": close_prices})

    result = generate_signal_from_data("0700.HK", df)

    assert result["signal"] == "HOLD"
    assert result["price"] == 200.0
    assert "equals MA200" in result["reason"]
