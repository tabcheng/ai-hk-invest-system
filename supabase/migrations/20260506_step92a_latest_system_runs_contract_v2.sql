create table if not exists public.latest_system_runs (
  id uuid primary key default gen_random_uuid(),
  run_id text not null,
  business_date date,
  status text,
  source text not null,
  data_timestamp timestamptz,
  summary_json jsonb not null default '{}'::jsonb,
  risk_summary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.latest_system_runs
  add column if not exists business_date date,
  add column if not exists status text,
  add column if not exists data_timestamp timestamptz,
  add column if not exists summary_json jsonb,
  add column if not exists risk_summary_json jsonb,
  add column if not exists updated_at timestamptz default now();

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'latest_system_runs'
      and column_name = 'run_status'
  ) then
    execute 'update public.latest_system_runs set status = coalesce(status, run_status)';
    execute 'alter table public.latest_system_runs alter column run_status drop not null';
  end if;
end $$;

update public.latest_system_runs
set
  business_date = coalesce(business_date, (created_at at time zone 'UTC')::date),
  status = coalesce(status, 'unknown'),
  data_timestamp = coalesce(data_timestamp, created_at),
  summary_json = coalesce(summary_json, jsonb_build_object('paper_trade_only', true)),
  risk_summary_json = coalesce(risk_summary_json, '{}'::jsonb),
  updated_at = coalesce(updated_at, created_at);

alter table public.latest_system_runs
  alter column business_date set not null,
  alter column status set not null,
  alter column data_timestamp set not null,
  alter column summary_json set default '{}'::jsonb,
  alter column summary_json set not null,
  alter column risk_summary_json set default '{}'::jsonb,
  alter column risk_summary_json set not null,
  alter column updated_at set default now(),
  alter column updated_at set not null;

alter table public.latest_system_runs
  drop constraint if exists latest_system_runs_status_chk,
  add constraint latest_system_runs_status_chk check (status in ('success', 'failed', 'partial', 'unknown'));

alter table public.latest_system_runs
  drop constraint if exists latest_system_runs_run_id_len_chk,
  add constraint latest_system_runs_run_id_len_chk check (char_length(run_id) between 1 and 80),
  drop constraint if exists latest_system_runs_source_len_chk,
  add constraint latest_system_runs_source_len_chk check (char_length(source) between 1 and 80);

alter table public.latest_system_runs
  drop constraint if exists latest_system_runs_summary_paper_only_chk,
  add constraint latest_system_runs_summary_paper_only_chk check ((summary_json->>'paper_trade_only')::boolean is true);

with ranked as (
  select
    id,
    row_number() over (
      partition by source
      order by updated_at desc, created_at desc, id desc
    ) as rn
  from public.latest_system_runs
)
delete from public.latest_system_runs l
using ranked r
where l.id = r.id
  and r.rn > 1;

create unique index if not exists idx_latest_system_runs_source_unique
  on public.latest_system_runs (source);

create index if not exists idx_latest_system_runs_latest_read
  on public.latest_system_runs (updated_at desc, created_at desc, id desc);

alter table public.latest_system_runs enable row level security;
