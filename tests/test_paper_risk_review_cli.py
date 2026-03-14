import json

from src import paper_risk_review_cli


def test_build_deterministic_operator_review_sorts_tickers_and_rows():
    review = {
        "run_id": 321,
        "total_blocked_buys": 1,
        "total_warning_buys": 2,
        "total_executed_buys": 3,
        "per_ticker": {
            "0700.HK": [
                {
                    "event_type": "BUY_EXECUTED",
                    "severity": "warning",
                    "summary_message": "warning path",
                    "compact_rule_summary": "warning=max_daily_new_allocation_hkd",
                },
                {
                    "event_type": "BUY_BLOCKED_RISK_GUARDRAIL",
                    "severity": "blocked",
                    "summary_message": "blocked path",
                    "compact_rule_summary": "failed=cash_floor_and_sufficiency",
                },
            ],
            "0005.HK": [
                {
                    "event_type": "BUY_EXECUTED",
                    "severity": "info",
                    "summary_message": "info path",
                    "compact_rule_summary": "passed=max_single_position_weight",
                }
            ],
        },
    }

    output = paper_risk_review_cli._build_deterministic_operator_review(review, run_id=321)

    assert output["run_id"] == 321
    assert output["total_blocked_buys"] == 1
    assert list(output["per_ticker"].keys()) == ["0005.HK", "0700.HK"]
    assert [row["event_type"] for row in output["per_ticker"]["0700.HK"]] == [
        "BUY_BLOCKED_RISK_GUARDRAIL",
        "BUY_EXECUTED",
    ]


def test_paper_risk_review_cli_main_outputs_compact_deterministic_json(monkeypatch, capsys):
    class FakeClient:
        pass

    def fake_get_supabase_client():
        return FakeClient()

    def fake_get_paper_risk_review_for_run(_client, run_id):
        assert run_id == 777
        return {
            "run_id": 123,
            "total_blocked_buys": 0,
            "total_warning_buys": 1,
            "total_executed_buys": 1,
            "per_ticker": {
                "1299.HK": [
                    {
                        "event_type": "BUY_EXECUTED",
                        "severity": "warning",
                        "summary_message": "warn",
                        "compact_rule_summary": "warning=max_daily_new_allocation_hkd",
                    }
                ]
            },
        }

    monkeypatch.setattr(paper_risk_review_cli, "get_supabase_client", fake_get_supabase_client)
    monkeypatch.setattr(
        paper_risk_review_cli,
        "get_paper_risk_review_for_run",
        fake_get_paper_risk_review_for_run,
    )

    exit_code = paper_risk_review_cli.main(["--run-id", "777"])

    assert exit_code == 0
    printed = capsys.readouterr().out.strip()
    parsed = json.loads(printed)
    assert parsed["run_id"] == 777
    assert parsed["total_warning_buys"] == 1
    assert parsed["per_ticker"]["1299.HK"][0]["event_type"] == "BUY_EXECUTED"
    assert (
        printed
        == '{"per_ticker":{"1299.HK":[{"compact_rule_summary":"warning=max_daily_new_allocation_hkd","event_type":"BUY_EXECUTED","severity":"warning","summary_message":"warn"}]},"run_id":777,"total_blocked_buys":0,"total_executed_buys":1,"total_warning_buys":1}'
    )
