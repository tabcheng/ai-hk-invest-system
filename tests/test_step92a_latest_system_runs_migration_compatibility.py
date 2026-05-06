from pathlib import Path
from datetime import date, datetime

import src.latest_system_runs_repository as repo


MIGRATION_PATH = Path("supabase/migrations/20260506_step92a_latest_system_runs_contract_v2.sql")


def _sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_migration_has_conditional_legacy_run_status_handling() -> None:
    sql = _sql()
    assert "column_name = 'run_status'" in sql
    assert "set status = coalesce(status, run_status)" in sql


def test_migration_drops_legacy_run_status_not_null_conditionally() -> None:
    sql = _sql()
    assert "alter table public.latest_system_runs alter column run_status drop not null" in sql


def test_repository_payload_does_not_require_legacy_run_status() -> None:
    payload = repo.build_latest_system_run_upsert_payload(
        run_id=1,
        business_date=date(2026, 5, 6),
        status="success",
        source="paper_daily_runner",
        data_timestamp=datetime(2026, 5, 6),
        summary_json={"paper_trade_only": True},
    )
    assert "run_status" not in payload


def test_migration_deduplicates_source_before_unique_index() -> None:
    sql = _sql()
    assert "partition by source" in sql
    assert "delete from public.latest_system_runs l" in sql
    assert "r.rn > 1" in sql
    assert "create unique index if not exists idx_latest_system_runs_source_unique" in sql
    assert sql.index("delete from public.latest_system_runs l") < sql.index(
        "create unique index if not exists idx_latest_system_runs_source_unique"
    )
