-- Step 91 (proposal-only): Supabase/internal table for latest_system_run canonical path.
-- This migration draft defines schema + RLS baseline only.
-- Runtime integration is intentionally deferred (no runtime read/write wiring in Step 91).

create or replace function public.latest_system_runs_limitations_valid(input jsonb)
returns boolean
language plpgsql
immutable
as $$
declare
  elem jsonb;
  item_text text;
begin
  if jsonb_typeof(input) <> 'array' then
    return false;
  end if;

  if jsonb_array_length(input) > 5 then
    return false;
  end if;

  for elem in select value from jsonb_array_elements(input)
  loop
    if jsonb_typeof(elem) <> 'string' then
      return false;
    end if;
  end loop;

  for item_text in select value from jsonb_array_elements_text(input)
  loop
    if char_length(item_text) > 160 then
      return false;
    end if;
  end loop;

  return true;
end;
$$;

create table if not exists public.latest_system_runs (
  id uuid primary key default gen_random_uuid(),
  run_id text not null,
  run_status text not null,
  started_at timestamptz null,
  completed_at timestamptz null,
  data_timestamp timestamptz null,
  summary text null,
  limitations jsonb not null default '[]'::jsonb,
  source text not null default 'paper_daily_runner',
  strategy_version text null,
  data_source text null,
  data_timestamp_source text null,
  created_at timestamptz not null default now(),

  constraint latest_system_runs_run_id_len_chk
    check (char_length(run_id) between 1 and 80),
  constraint latest_system_runs_run_status_chk
    check (run_status in ('success', 'failed', 'partial', 'unknown')),
  constraint latest_system_runs_summary_len_chk
    check (summary is null or char_length(summary) <= 500),
  constraint latest_system_runs_limitations_valid_chk
    check (public.latest_system_runs_limitations_valid(limitations))
);

create index if not exists idx_latest_system_runs_latest_read
  on public.latest_system_runs (completed_at desc nulls last, created_at desc, id desc);

create index if not exists idx_latest_system_runs_source_created_at
  on public.latest_system_runs (source, created_at desc);

alter table public.latest_system_runs enable row level security;

-- Step 91 RLS posture: deny-by-default, backend-only access to be added in future step.
-- No anon/authenticated policy is created in this proposal step.
