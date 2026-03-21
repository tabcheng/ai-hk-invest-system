# Railway Service Variables

This document is the deployment-facing reference for environment variables used by this repository's runtime services on Railway.

Guardrails:
- Current scope is **paper trading + decision support only**.
- No variable in this document authorizes autonomous real-money trade execution.

## Related docs
- Telegram webhook setup: `docs/telegram-webhook-setup.md`
- Telegram troubleshooting runbook: `docs/operator-runbook-telegram-troubleshooting.md`
- Operator paper-risk review runbook: `docs/operator-runbook-paper-risk-review.md`
- Current production/status ledger: `docs/status.md`

## 1) Telegram / webhook

### `TELEGRAM_BOT_TOKEN`
- **Required/Optional:** Required for Telegram outbound delivery and webhook reply path.
- **Purpose:** Authenticates Bot API calls to `sendMessage` and `setWebhook`.
- **Format / Example:** Telegram bot token string, e.g. `123456789:AA...`.
- **If missing:** Telegram send path returns `missing_telegram_config`; webhook command handling may still run internally but cannot reply to operator chat.
- **Security note:** Secret. Never commit to repo; store only in Railway protected variables.

### `TELEGRAM_CHAT_ID`
- **Required/Optional:** Required for operator authorization baseline and default notification target.
- **Purpose:** Restricts operator command usage to configured chat and defines default delivery destination for summary notifications.
- **Format / Example:** Telegram chat id string (often numeric), e.g. `-1001234567890`.
- **If missing:** Operator commands are treated as unauthorized (`missing_configured_chat_id`); default Telegram delivery is skipped.
- **Security note:** Sensitive operational identifier; avoid exposing in public logs/screenshots.

### `TELEGRAM_OPERATOR_ALLOWED_USER_IDS`
- **Required/Optional:** Optional (recommended for stricter control).
- **Purpose:** Adds per-user allowlist on top of chat allowlist for operator commands (`/runs`, `/help`, `/h`, `/risk_review [run_id]`).
- **Format / Example:** Comma-separated Telegram user ids, e.g. `12345678,87654321`.
- **If missing:** Chat-level auth remains active, user-level gate is open inside the allowed chat.
- **Security note:** Treat as sensitive access-control config.

### `TELEGRAM_WEBHOOK_SECRET_TOKEN`
- **Required/Optional:** Optional but recommended for production/long-term deployment.
- **Purpose:** Transport-level verification for inbound `POST /telegram/webhook` via header `X-Telegram-Bot-Api-Secret-Token`.
- **Format / Example:** Random high-entropy string, e.g. `tg_whsec_...`.
- **If missing:** Webhook transport auth is open (handler auth guardrails still apply).
- **Security note:** Secret. Must match the value passed to Telegram `setWebhook secret_token` when enabled.

## 2) Operator allowlist / access control

> Note: these variables also appear in Telegram sections because access control is enforced during Telegram command handling.

### `TELEGRAM_CHAT_ID`
- **Required/Optional:** Required.
- **Purpose:** Primary operator chat boundary.
- **Format / Example:** `-1001234567890`.
- **If missing:** All operator commands denied.
- **Security note:** Keep private; this value maps directly to operator surface.

### `TELEGRAM_OPERATOR_ALLOWED_USER_IDS`
- **Required/Optional:** Optional.
- **Purpose:** Secondary operator user boundary.
- **Format / Example:** `12345678,87654321`.
- **If missing:** Only chat-level gate enforced.
- **Security note:** Access control data; restrict visibility.

## 3) Supabase / database

### `SUPABASE_URL`
- **Required/Optional:** Required.
- **Purpose:** Supabase project endpoint used by runtime and webhook command execution path.
- **Format / Example:** URL, e.g. `https://<project-ref>.supabase.co`.
- **If missing:** Supabase client initialization fails (`Missing SUPABASE_URL or SUPABASE_KEY...`); main runtime and webhook processing cannot complete normally.
- **Security note:** Not secret by itself, but should still be managed in deployment variables (not hardcoded).

### `SUPABASE_KEY`
- **Required/Optional:** Required.
- **Purpose:** Supabase API key used by server-side runtime.
- **Format / Example:** Key string (usually `service_role` key for backend workloads).
- **If missing:** Same failure mode as missing `SUPABASE_URL`; webhook route may return `503 supabase_client_unavailable`.
- **Security note:** Secret with elevated privileges; never expose client-side or in logs.

## 4) Runtime / environment

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

## 5) Deployment notes (Railway)

- Keep webhook service and batch runtime behavior aligned with current guardrails: paper-trading review/support only, no real-money auto execution.
- Prefer enabling `TELEGRAM_WEBHOOK_SECRET_TOKEN` in production after base webhook connectivity is confirmed.
- Keep Python runtime pinned to repo `.python-version` (`3.12.9`) to avoid known Railpack mismatch issues documented in `docs/status.md`.
