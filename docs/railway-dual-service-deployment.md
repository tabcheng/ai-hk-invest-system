# Railway Dual-Service Deployment Runbook (Step 35)

## Goal
Split Railway deployment responsibilities into two services while keeping one GitHub repository:

- Long-running Telegram ingress service (webhook)
- Scheduled batch runner service (daily paper run)

Guardrails:
- Scope remains **paper trading / decision support only**.
- No autonomous real-money execution is introduced.

## Target topology

- **Same GitHub repo:** this repository
- **Service A:** `telegram-webhook`
  - Start Command: `python -m src.telegram_webhook_server`
  - Responsibility: long-running webhook ingress (`POST /telegram/webhook`) and operator reply path
  - Cron: **none**
- **Service B:** `paper-daily-runner`
  - Start Command: `python -m src.daily_runner`
  - Responsibility: scheduled batch paper-trading decision-support run
  - Business schedule baseline: **Hong Kong Time (HKT)**
  - Current target run time: **20:00 HKT**
  - Railway cron timezone: **UTC**
  - Cron (UTC) for current target: `0 12 * * *`

Why this split:
- Railway cron executes the service start command directly.
- Webhook service must stay alive to receive Telegram events.
- Runner service should run daily batch work and then exit.

## Railway setup steps

### 1) Keep existing webhook service
In current `telegram-webhook` service:
1. Verify service is connected to this repo/branch.
2. Verify Start Command is:
   - `python -m src.telegram_webhook_server`
3. Verify cron is **not configured**.

### 2) Create runner service from same repo
Create a new Railway service:
1. Source: same GitHub repository.
2. Service name: `paper-daily-runner`.
3. Start Command:
   - `python -m src.daily_runner`
4. Configure cron schedule (Railway cron uses UTC):
   - `0 12 * * *` (maps to 20:00 HKT)

### 3) Confirm service responsibility boundaries
- `telegram-webhook`:
  - Keeps ingress alive and handles operator commands.
  - Must not run cron.
- `paper-daily-runner`:
  - Executes scheduled run and exits.
  - Must not attempt to serve webhook ingress.

## Variables by service scope

Use `docs/railway-service-variables.md` as the canonical variable dictionary.

### Shared variables (both services)
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_OPERATOR_ALLOWED_USER_IDS` (optional)

### Webhook-only variables
- `PORT` (Railway-provided)
- `TELEGRAM_WEBHOOK_HOST` (optional)
- `TELEGRAM_WEBHOOK_PORT` (optional fallback)
- `TELEGRAM_WEBHOOK_SECRET_TOKEN` (optional but recommended)

### Runner-only variables
- No new runner-exclusive variable is required in Step 35.
- Runner behavior is defined by start command + cron schedule.

## Validation checklist

1. Webhook service health
   - Service deploys with `python -m src.telegram_webhook_server`.
   - Telegram `getWebhookInfo` points to webhook service URL.
2. Runner schedule health
   - Runner service has cron `0 12 * * *` (UTC), targeting 20:00 HKT.
   - Manual run and scheduled run both execute `python -m src.daily_runner` and exit.
3. Responsibility isolation
   - No cron on webhook service.
   - No webhook server start command on runner service.
4. Guardrail confirmation
   - Runtime remains paper-trading / decision-support.
   - No real-money auto execution path is configured.

## Rollback / recovery

If split deployment behaves unexpectedly:
1. Temporarily disable runner cron.
2. Keep webhook service active to preserve operator command path.
3. Verify runner start command and variable set, then re-enable cron.
4. Re-check `docs/status.md` and update operational notes before next change step.
