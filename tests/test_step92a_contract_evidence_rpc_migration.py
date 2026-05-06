from pathlib import Path


MIGRATION_PATH = Path("supabase/migrations/20260506_step92a_s2_contract_evidence_rpc.sql")


def _sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8").lower()


def test_rpc_function_has_expected_security_shape() -> None:
    sql = _sql()
    assert "create or replace function public.step92a_latest_system_runs_contract_evidence()" in sql
    assert "returns jsonb" in sql
    assert "security definer" not in sql
    assert "security invoker" in sql
    assert "set search_path = pg_catalog, public, pg_temp" in sql


def test_rpc_function_only_granted_to_service_role() -> None:
    sql = _sql()
    assert "revoke all on function public.step92a_latest_system_runs_contract_evidence() from public;" in sql
    assert "revoke all on function public.step92a_latest_system_runs_contract_evidence() from anon;" in sql
    assert "revoke all on function public.step92a_latest_system_runs_contract_evidence() from authenticated;" in sql
    assert "grant execute on function public.step92a_latest_system_runs_contract_evidence() to service_role;" in sql


def test_rpc_function_returns_boolean_contract_fields() -> None:
    sql = _sql()
    for key in (
        "'table_exists'",
        "'rls_enabled'",
        "'source_unique_index_exists'",
        "'latest_read_index_exists'",
    ):
        assert key in sql
