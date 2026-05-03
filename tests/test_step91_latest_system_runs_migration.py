from pathlib import Path


MIGRATION_PATH = Path("supabase/migrations/20260503_step91_create_latest_system_runs.sql")


def _sql() -> str:
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_uses_decoded_limitations_length_validation() -> None:
    sql = _sql()
    assert "jsonb_array_elements_text(input)" in sql
    assert "jsonb_typeof(elem) <> 'string'" in sql
    assert "char_length(item_text) > 160" in sql


def test_migration_has_deterministic_latest_read_index_order() -> None:
    sql = _sql()
    assert "(completed_at desc nulls last, created_at desc, id desc)" in sql


def test_migration_enables_rls_without_public_policy() -> None:
    sql = _sql().lower()
    assert "alter table public.latest_system_runs enable row level security;".lower() in sql
    assert "create policy" not in sql
