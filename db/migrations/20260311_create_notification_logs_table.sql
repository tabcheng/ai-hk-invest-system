-- Milestone 4: notification hardening with minimal cross-run daily-summary dedup.
create table if not exists notification_logs (
  id bigserial primary key,
  notification_date date not null,
  target text not null,
  message_type text not null,
  status text not null,
  created_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists idx_notification_logs_daily_target_type_status
  on notification_logs(notification_date, target, message_type, status);

create index if not exists idx_notification_logs_date_target
  on notification_logs(notification_date, target);
