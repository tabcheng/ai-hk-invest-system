create table if not exists public.human_decision_journal_entries (
  id bigserial primary key,
  created_at timestamptz not null default timezone('utc', now()),
  scope text not null,
  run_id bigint not null,
  human_action text not null,
  note text not null,
  source_command text not null,
  operator_user_id_hash_or_label text null,
  metadata jsonb null
);

create index if not exists idx_human_decision_journal_entries_run_id
  on public.human_decision_journal_entries(run_id);
