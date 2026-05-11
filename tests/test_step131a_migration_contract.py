from pathlib import Path


def test_step131a_db_migration_has_required_columns() -> None:
    sql = Path("db/migrations/20260511_step131a_decision_context_snapshots_rationale_operator.sql").read_text(encoding="utf-8").lower()
    assert "alter table if exists public.decision_context_snapshots" in sql
    assert "add column if not exists rationale_text text" in sql
    assert "add column if not exists operator_user_id_hash_or_label text" in sql


def test_step131a_supabase_copy_matches_db_migration() -> None:
    db_sql = Path("db/migrations/20260511_step131a_decision_context_snapshots_rationale_operator.sql").read_text(encoding="utf-8").strip()
    supabase_sql = Path("supabase/migrations/20260511_step131a_decision_context_snapshots_rationale_operator.sql").read_text(encoding="utf-8").strip()
    assert db_sql == supabase_sql
