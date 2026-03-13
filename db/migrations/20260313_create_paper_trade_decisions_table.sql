create table if not exists paper_trade_decisions (
  id bigserial primary key,
  run_id bigint references runs(id) on delete set null,
  stock_id text not null,
  stock_name text not null,
  signal_action text not null check (signal_action in ('BUY', 'SELL', 'HOLD', 'NO_DATA', 'INSUFFICIENT_DATA', 'ERROR')),
  signal_score numeric,
  rationale_summary text,
  human_decision text not null check (human_decision in ('PENDING', 'APPROVE', 'REJECT', 'DEFER')),
  decision_note text not null,
  paper_trade_status text not null check (paper_trade_status in ('PENDING', 'SIMULATED', 'SKIPPED', 'CANCELLED')),
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_paper_trade_decisions_run_id on paper_trade_decisions(run_id);
create index if not exists idx_paper_trade_decisions_stock_id on paper_trade_decisions(stock_id);
create index if not exists idx_paper_trade_decisions_created_at on paper_trade_decisions(created_at desc);
