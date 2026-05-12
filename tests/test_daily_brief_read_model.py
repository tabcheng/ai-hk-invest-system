import pytest

from src.miniapp_read_model import build_daily_brief_section


def _daily(readiness: str = "partial") -> dict:
    return {"status": "ok", "review_readiness": readiness}


def _signals(pos: int, neu: int, neg: int, status: str = "ok") -> dict:
    return {
        "status": status,
        "shown_positive_signals": pos,
        "shown_neutral_signals": neu,
        "shown_negative_signals": neg,
    }


def _risk(level: str, status: str = "ok") -> dict:
    return {"status": status, "risk_level": level}


@pytest.mark.parametrize(
    ("signals", "risk", "daily", "expected_direction"),
    [
        (_signals(3, 1, 0), _risk("low"), _daily("ready"), "偏正面"),
        (_signals(1, 4, 0), _risk("low"), _daily("ready"), "偏觀望"),
        (_signals(0, 1, 4), _risk("high"), _daily("ready"), "偏審慎"),
        (_signals(2, 2, 1), _risk("medium"), _daily("ready"), "偏觀望"),
        (_signals(0, 0, 0), _risk("low"), _daily("ready"), "只可觀察"),
        (_signals(2, 1, 0, status="unavailable"), _risk("low"), _daily("ready"), "只可觀察"),
        (_signals(2, 1, 0), _risk("unknown", status="unavailable"), _daily("ready"), "只可觀察"),
        (_signals(2, 1, 0), _risk("low"), _daily("insufficient"), "只可觀察"),
    ],
)
def test_daily_brief_direction_matrix(signals: dict, risk: dict, daily: dict, expected_direction: str) -> None:
    section = build_daily_brief_section(daily, signals, risk)
    assert expected_direction in section["simulated_direction"]


def test_daily_brief_risk_wording_matrix() -> None:
    assert "偏高" in build_daily_brief_section(_daily("ready"), _signals(1, 1, 1), _risk("high"))["risk_brief"]
    assert "中等風險提示" in build_daily_brief_section(_daily("ready"), _signals(1, 1, 1), _risk("medium"))["risk_brief"]
    assert "重大風險警示" in build_daily_brief_section(_daily("ready"), _signals(1, 1, 1), _risk("low"))["risk_brief"]
    assert "足夠資訊" in build_daily_brief_section(
        _daily("ready"), _signals(1, 1, 1), _risk("unknown", status="unavailable")
    )["risk_brief"]


def test_daily_brief_data_sufficiency_and_safety_note() -> None:
    enough = build_daily_brief_section(_daily("ready"), _signals(1, 0, 0), _risk("low"))
    partial = build_daily_brief_section(_daily("partial"), _signals(1, 0, 0), _risk("low"))
    insufficient = build_daily_brief_section(_daily("unavailable"), _signals(1, 0, 0), _risk("low"))

    assert enough["data_sufficiency"]["state"] == "enough"
    assert partial["data_sufficiency"]["state"] == "partial"
    assert insufficient["data_sufficiency"]["state"] == "insufficient"
    assert "只供模擬檢視" in enough["safety_note"]
