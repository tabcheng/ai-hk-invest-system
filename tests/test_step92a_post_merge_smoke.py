import json
from urllib.error import HTTPError

import scripts.step92a_post_merge_smoke as smoke
from scripts.step92a_post_merge_smoke import _compute_overall_status, _contract_evidence_check, _safe_latest_row


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


def test_contract_evidence_rpc_pass_mapping(monkeypatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "table_exists": True,
                    "rls_enabled": True,
                    "source_unique_index_exists": True,
                    "latest_read_index_exists": True,
                }
            ).encode("utf-8")

    captured: dict[str, object] = {}

    def _fake_urlopen(req, timeout=30):
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["content_type"] = req.get_header("Content-type")
        captured["body"] = req.data
        return _Resp()

    monkeypatch.setattr(smoke.request, "urlopen", _fake_urlopen)
    mapped, reason = _contract_evidence_check("https://x.supabase.co", "k")
    assert mapped == {
        "table_exists": "PASS",
        "rls_enabled": "PASS",
        "source_unique_index_exists": "PASS",
        "latest_read_index_exists": "PASS",
    }
    assert reason == "ok"
    assert captured["method"] == "POST"
    assert str(captured["url"]).endswith("/rest/v1/rpc/step92a_latest_system_runs_contract_evidence")
    assert captured["content_type"] == "application/json"
    assert captured["body"] == b"{}"


def test_contract_evidence_rpc_404_fails(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise HTTPError("https://x", 404, "not found", hdrs=None, fp=None)

    monkeypatch.setattr(smoke, "_post_rpc", _boom)
    mapped, reason = _contract_evidence_check("https://x.supabase.co", "k")
    assert all(value == "FAIL" for value in mapped.values())
    assert reason == "contract_evidence_rpc_not_configured_http_404"


def _base_report() -> dict:
    return {
        "preflight": "PASS",
        "table_exists": "PASS",
        "rls_enabled": "PASS",
        "source_unique_index_exists": "PASS",
        "latest_read_index_exists": "PASS",
        "paper_daily_runner_row_count_lte_1": "PASS",
        "latest_row_readable": "NOT_CONFIGURED",
        "paper_trade_only_true_if_row_exists": "NOT_CONFIGURED",
        "status_allowed_if_row_exists": "NOT_CONFIGURED",
        "run_paper_daily_runner": False,
        "runner_execution": {"status": "SKIPPED"},
    }


def test_runner_toggle_failure_forces_overall_fail() -> None:
    report = _base_report()
    report["run_paper_daily_runner"] = True
    report["runner_execution"] = {"status": "FAIL"}
    assert _compute_overall_status(report) == "FAIL"


def test_rls_or_index_not_configured_cannot_pass() -> None:
    report = _base_report()
    report["rls_enabled"] = "FAIL"
    assert _compute_overall_status(report) == "FAIL"
    report = _base_report()
    report["source_unique_index_exists"] = "FAIL"
    assert _compute_overall_status(report) == "FAIL"
