create table if not exists paper_trades (
  id bigserial primary key,
  trade_date date not null,
  stock text not null,
  action text not null check (action in ('BUY', 'SELL')),
  quantity integer not null check (quantity > 0),
  price numeric not null,
  gross_amount numeric not null,
  fee numeric not null,
  net_amount numeric not null,
  realized_pnl numeric,
  signal_id bigint,
  run_id bigint references runs(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_paper_trades_trade_date on paper_trades(trade_date);
create index if not exists idx_paper_trades_stock_date on paper_trades(stock, trade_date);
create index if not exists idx_paper_trades_run_id on paper_trades(run_id);

create table if not exists paper_daily_snapshots (
  id bigserial primary key,
  snapshot_date date not null,
  cash numeric not null,
  market_value numeric not null,
  total_equity numeric not null,
  open_positions integer not null,
  cumulative_realized_pnl numeric not null,
  cumulative_unrealized_pnl numeric not null,
  run_id bigint references runs(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists idx_paper_daily_snapshots_date on paper_daily_snapshots(snapshot_date);
create index if not exists idx_paper_daily_snapshots_run_id on paper_daily_snapshots(run_id);

create table if not exists paper_events (
  id bigserial primary key,
  event_date date not null,
  stock text not null,
  signal text not null,
  event_type text not null,
  message text not null,
  signal_id bigint,
  run_id bigint references runs(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_paper_events_event_date on paper_events(event_date);
create index if not exists idx_paper_events_run_id on paper_events(run_id);
