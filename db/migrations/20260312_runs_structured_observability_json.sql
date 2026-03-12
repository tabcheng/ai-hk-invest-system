-- Step 15: add structured observability payloads on runs while keeping legacy text summaries.
alter table if exists public.runs
  add column if not exists error_summary_json jsonb,
  add column if not exists delivery_summary_json jsonb;
