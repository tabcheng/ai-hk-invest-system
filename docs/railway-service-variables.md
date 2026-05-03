# Railway Service Variables

This document is the deployment-facing reference for environment variables used by this repository's Railway runtime services.

Guardrails:
- Current scope is **paper trading + decision support only**.
- No variable in this document authorizes autonomous real-money trade execution.

## Related docs
- Dual-service deployment runbook: `docs/railway-dual-service-deployment.md`
- Telegram webhook setup: `docs/telegram-webhook-setup.md`
- Telegram troubleshooting runbook: `docs/operator-runbook-telegram-troubleshooting.md`
- Operator paper-risk review runbook: `docs/operator-runbook-paper-risk-review.md`
- Current production/status ledger: `docs/status.md`

## 0) Step 35 service topology (same repo, two Railway services)

Both Railway services point to the **same GitHub repository** and differ by start command/runtime responsibility:

- **Service A: `telegram-webhook`**
  - **Start Command:** `python -m src.telegram_webhook_server`
  - **Responsibility:** Long-running ingress service for Telegram webhook requests.
  - **Cron:** **Not configured** on this service.

- **Service B: `paper-daily-runner`**
  - **Start Command:** `python -m src.daily_runner`
  - **Responsibility:** Batch/scheduled daily paper-trading decision-support run.
  - **Business schedule baseline:** Hong Kong Time (HKT).
  - **Current target run time:** 20:00 HKT.
  - **Railway cron timezone:** UTC.
  - **Cron:** `0 12 * * *` configured **only** on this service (maps to 20:00 HKT).

Important:
- Railway cron executes the selected service's start command.
- Runner service should finish daily batch work and exit.
- Runner service should **not** host Telegram webhook ingress.
- Webhook service should **not** own cron.

## 1) Shared variables (both services)

### `SUPABASE_URL`
- **Required/Optional:** Required.
- **Purpose:** Supabase project endpoint used by runtime and webhook command execution paths.
- **Format / Example:** URL, e.g. `https://<project-ref>.supabase.co`.
- **If missing:** Supabase client initialization fails (`Missing SUPABASE_URL or SUPABASE_KEY...`); runtime and webhook command handling cannot complete normally.
- **Security note:** Not secret by itself, but should still be managed in deployment variables (not hardcoded).

### `SUPABASE_KEY`
- **Required/Optional:** Required.
- **Purpose:** Supabase API key used by server-side runtime.
- **Format / Example:** Key string (usually `service_role` key for backend workloads).
- **If missing:** Same failure mode as missing `SUPABASE_URL`; webhook route may return `503 supabase_client_unavailable`.
- **Security note:** Secret with elevated privileges; never expose client-side or in logs.

### `TELEGRAM_BOT_TOKEN`
- **Required/Optional:** Required for Telegram outbound delivery and webhook reply path.
- **Purpose:** Authenticates Telegram Bot API calls (`sendMessage`, `setWebhook`, operator replies).
- **Format / Example:** Telegram bot token string, e.g. `123456789:AA...`.
- **If missing:** Telegram send path returns `missing_telegram_config`; webhook command handling may still run internally but cannot reply to operator chat.
- **Security note:** Secret. Never commit to repo; store only in Railway protected variables.

### `TELEGRAM_CHAT_ID`
- **Required/Optional:** Required.
- **Purpose:** Operator authorization baseline and default delivery destination.
- **Format / Example:** Telegram chat id string (often numeric), e.g. `-1001234567890`.
- **If missing:** Operator commands are treated as unauthorized (`missing_configured_chat_id`); default Telegram delivery is skipped.
- **Security note:** Sensitive operational identifier; avoid exposing in public logs/screenshots.

### `TELEGRAM_OPERATOR_ALLOWED_USER_IDS`
- **Required/Optional:** Optional (recommended for stricter operator control).
- **Purpose:** Adds per-user allowlist on top of chat allowlist for operator commands (`/runs`, `/help`, `/h`, `/risk_review [run_id]`).
- **Format / Example:** Comma-separated Telegram user ids, e.g. `12345678,87654321`.
- **If missing:** Chat-level auth remains active, user-level gate is open inside the allowed chat.
- **Security note:** Treat as sensitive access-control config.

## 2) Webhook-only variables (`telegram-webhook` service)

### `PORT`
- **Required/Optional:** Required by Railway runtime contract (injected by platform).
- **Purpose:** Primary bind port for webhook server process (`python -m src.telegram_webhook_server`).
- **Format / Example:** Integer string, e.g. `8080`.
- **If missing:** Service falls back to `TELEGRAM_WEBHOOK_PORT` then `8080`; on Railway this should normally be present automatically.
- **Security note:** Not secret.

### `TELEGRAM_WEBHOOK_HOST`
- **Required/Optional:** Optional.
- **Purpose:** Overrides webhook server bind host.
- **Format / Example:** Host/IP string, default `0.0.0.0`.
- **If missing:** Defaults to `0.0.0.0`.
- **Security note:** Not secret.

### `TELEGRAM_WEBHOOK_PORT`
- **Required/Optional:** Optional fallback.
- **Purpose:** Local/dev fallback bind port when `PORT` is absent.
- **Format / Example:** Integer string, e.g. `8080`.
- **If missing:** Final fallback is `8080`.
- **Security note:** Not secret.

### `TELEGRAM_WEBHOOK_SECRET_TOKEN`
- **Required/Optional:** Optional but recommended for production/long-term deployment.
- **Purpose:** Transport-level verification for inbound `POST /telegram/webhook` via header `X-Telegram-Bot-Api-Secret-Token`.
- **Format / Example:** Random high-entropy string, e.g. `tg_whsec_...`.
- **If missing:** Webhook transport auth is open (handler auth guardrails still apply).
- **Security note:** Secret. Must match value passed in Telegram `setWebhook secret_token` when enabled.

## 3) Runner-only variables (`paper-daily-runner` service)

Step 35 does not introduce runner-exclusive environment variables in repo code.

Runner-specific behavior is controlled by service command/schedule:
- Start command: `python -m src.daily_runner`
- Business schedule baseline: HKT
- Current target run time: 20:00 HKT
- Railway cron timezone: UTC
- Cron schedule: `0 12 * * *`

Operational guardrail:
- Do not configure webhook ingress variables solely for runner usage.
- Keep runner service focused on batch execution and completion/exit.

## 4) Deployment notes (Railway)

- Keep both services in one repo, separated by responsibility and start command.
- Cron must be attached only to `paper-daily-runner`; do not attach cron to `telegram-webhook`.
- Keep webhook service running continuously and reachable at your Railway public URL for Telegram delivery.
- Prefer enabling `TELEGRAM_WEBHOOK_SECRET_TOKEN` on webhook service after base connectivity validation.
- Keep Python runtime pinned to repo `.python-version` (`3.12.9`) to avoid known Railpack mismatch issues documented in `docs/status.md`.

## Step 91A naming/boundary cleanup note (no in-step variable rename)
- `SUPABASE_KEY` is currently used by runtime code and is ambiguous.
- Preferred future backend-only explicit names: `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY`.
- Do not rename variables directly in this step.
- Staged migration recommendation:
  1. add runtime support for new explicit key var with fallback to `SUPABASE_KEY`;
  2. update Railway variables;
  3. smoke/acceptance;
  4. remove fallback later.
- `miniapp-static-preview` must not hold Supabase service-role/secret key variables.

## Step 91A operator verification matrix (manual, no value disclosure)
- `paper-daily-runner`
  - verify backend runtime key is elevated backend-only key (`SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY` target path), not anon/publishable key.
- `telegram-webhook`
  - verify service key remains backend runtime only and is not exposed to any frontend/static artifacts.
- `miniapp-static-preview`
  - verify no Supabase service-role/secret key is configured.

Security rule:
- Never paste/print full key values in docs, tickets, PR comments, screenshots, logs, or CI output.

## Step 91A explicit warning after confirmed finding
- `paper-daily-runner` must not use publishable-class key (`sb_publishable_...`) for backend writes when RLS is enabled.
- `miniapp-static-preview` must not receive Supabase service-role/secret keys.
- `telegram-webhook` future Supabase read path (when enabled) must use backend-only elevated key boundary only.
