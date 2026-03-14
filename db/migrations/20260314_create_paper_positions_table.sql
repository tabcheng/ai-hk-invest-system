create table if not exists paper_positions (
  id bigserial primary key,
  ticker text not null,
  quantity integer not null default 0 check (quantity >= 0),
  avg_cost numeric not null default 0,
  last_price numeric not null default 0,
  unrealized_pnl numeric not null default 0,
  realized_pnl numeric not null default 0,
  updated_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists idx_paper_positions_ticker on paper_positions(ticker);
create index if not exists idx_paper_positions_updated_at on paper_positions(updated_at);
