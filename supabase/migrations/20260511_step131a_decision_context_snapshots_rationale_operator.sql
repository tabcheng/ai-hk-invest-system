alter table if exists public.decision_context_snapshots
  add column if not exists rationale_text text,
  add column if not exists operator_user_id_hash_or_label text;
