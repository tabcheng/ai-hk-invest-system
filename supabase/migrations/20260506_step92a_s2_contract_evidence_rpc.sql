create or replace function public.step92a_latest_system_runs_contract_evidence()
returns jsonb
language sql
security definer
set search_path = public, pg_catalog
as $$
  select jsonb_build_object(
    'table_exists', exists (
      select 1
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public'
        and c.relname = 'latest_system_runs'
        and c.relkind in ('r', 'p')
    ),
    'rls_enabled', coalesce((
      select c.relrowsecurity
      from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
      where n.nspname = 'public'
        and c.relname = 'latest_system_runs'
        and c.relkind in ('r', 'p')
      limit 1
    ), false),
    'source_unique_index_exists', exists (
      select 1
      from pg_indexes
      where schemaname = 'public'
        and tablename = 'latest_system_runs'
        and indexname = 'idx_latest_system_runs_source_unique'
    ),
    'latest_read_index_exists', exists (
      select 1
      from pg_indexes
      where schemaname = 'public'
        and tablename = 'latest_system_runs'
        and indexname = 'idx_latest_system_runs_latest_read'
    )
  );
$$;

revoke all on function public.step92a_latest_system_runs_contract_evidence() from public;
revoke all on function public.step92a_latest_system_runs_contract_evidence() from anon;
revoke all on function public.step92a_latest_system_runs_contract_evidence() from authenticated;
grant execute on function public.step92a_latest_system_runs_contract_evidence() to service_role;
