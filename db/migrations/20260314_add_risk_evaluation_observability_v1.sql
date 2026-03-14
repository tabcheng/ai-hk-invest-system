alter table if exists paper_events
  add column if not exists risk_evaluation jsonb;

alter table if exists paper_trade_decisions
  add column if not exists risk_evaluation jsonb;
