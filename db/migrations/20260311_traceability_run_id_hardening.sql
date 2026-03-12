-- Milestone 4 traceability hardening: ensure major run artifacts link back to runs.id
-- and improve run-level failure observability by error category.

alter table if exists public.signals
  add column if not exists run_id bigint references public.runs(id) on delete set null;

create index if not exists idx_signals_run_id on public.signals(run_id);

alter table if exists public.notification_logs
  add column if not exists run_id bigint references public.runs(id) on delete set null;

create index if not exists idx_notification_logs_run_id on public.notification_logs(run_id);

alter table if exists public.runs
  add column if not exists ticker_error_count integer,
  add column if not exists post_process_error_count integer,
  add column if not exists notification_error_count integer,
  add column if not exists ticker_error_summary text,
  add column if not exists post_process_error_summary text,
  add column if not exists notification_error_summary text;
