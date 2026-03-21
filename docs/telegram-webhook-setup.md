# Telegram Webhook Setup (Step 34A Foundation)

## Scope
This document describes the minimal **Telegram inbound ingress foundation** for operator commands:
- `/help`
- `/h`
- `/runs`
- `/risk_review [run_id]`

Guardrail:
- This webhook path only bridges inbound Telegram commands to existing operator command handlers.
- It does **not** change strategy logic.
- It does **not** add any real-money execution path.

## Inbound integration status (repo-confirmed)
Before Step 34A:
- The repo had Telegram outbound delivery (`sendMessage`) for daily run summaries.
- Operator command handling existed in code (`handle_telegram_operator_command(...)`) but did not have an HTTP ingress route wired to Telegram updates.
- No webhook endpoint and no polling loop for Telegram inbound updates were present.

After Step 34A:
- New ingress route: `POST /telegram/webhook`.
- Telegram update payloads are parsed and passed into `handle_telegram_operator_command(...)`.
- Handler response text (if any) is sent back to the originating Telegram chat via Bot API `sendMessage`.

## Runtime entrypoint for webhook server
Run the dedicated webhook server process:

Deployment topology note (Step 35):
- Keep this webhook process in dedicated Railway service `telegram-webhook`.
- Do **not** configure cron on webhook service.
- Daily cron batch run belongs to separate `paper-daily-runner` service (`python main.py`, `0 12 * * *`).
- See `docs/railway-dual-service-deployment.md` for full two-service runbook.


```bash
python -m src.telegram_webhook_server
```

Defaults:
- Host: `0.0.0.0` (override with `TELEGRAM_WEBHOOK_HOST`)
- Port: `PORT` (or `TELEGRAM_WEBHOOK_PORT`, default `8080`)
- Route: `POST /telegram/webhook`

## Environment variables
Required for reply path:
- `TELEGRAM_BOT_TOKEN`

Required for operator authorization guardrail:
- `TELEGRAM_CHAT_ID`

Optional stricter guardrail:
- `TELEGRAM_OPERATOR_ALLOWED_USER_IDS` (comma-separated Telegram user ids)
- `TELEGRAM_WEBHOOK_SECRET_TOKEN` (transport-level secret checked against Telegram header `X-Telegram-Bot-Api-Secret-Token`)

## Set webhook
Assume your Railway public domain is:
- `https://<your-service>.up.railway.app`

### A) If `TELEGRAM_WEBHOOK_SECRET_TOKEN` is set (recommended for production/long-term)
Use the same secret value in both:
- your service env var: `TELEGRAM_WEBHOOK_SECRET_TOKEN`
- Telegram `setWebhook` parameter: `secret_token`

Telegram will then include the same value in request header `X-Telegram-Bot-Api-Secret-Token`,
which the webhook uses for source verification.

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  --data-urlencode "url=https://<your-service>.up.railway.app/telegram/webhook" \
  --data-urlencode "secret_token=${TELEGRAM_WEBHOOK_SECRET_TOKEN}"
```

### B) If `TELEGRAM_WEBHOOK_SECRET_TOKEN` is NOT set (allowed for early setup/testing)
Do **not** pass `secret_token` when calling `setWebhook`.

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  --data-urlencode "url=https://<your-service>.up.railway.app/telegram/webhook"
```

Expected success payload includes `"ok": true`.

## Secret-token guardrail (operational recommendation)
- `TELEGRAM_WEBHOOK_SECRET_TOKEN` is **optional**, not required for initial testing.
- For production / long-term deployment, enable it to reduce webhook-source spoofing risk.
- For first-time setup, you may skip it temporarily to avoid setup confusion; enable it once
  base webhook connectivity is verified.

## Validate webhook registration
Use Telegram `getWebhookInfo`:

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

Check:
- `url` matches your `/telegram/webhook` URL
- `has_custom_certificate` / `pending_update_count` look healthy for your setup
- `last_error_date` / `last_error_message` indicate no active delivery issue
- `pending_update_count` is not continuously growing

## Railway log checks
In Railway service logs, verify these events when a command is received:
1. `Telegram webhook request received.`
2. `Telegram webhook command text: ...`
3. `Telegram operator auth decision: ...`
4. `Telegram /risk_review requested: ...` / `... completed` / `... failed` (for risk-review commands)
5. `Telegram sendMessage success: ...` (or failure reason)
6. (if enabled) `Telegram webhook transport auth decision: ...`

This confirms ingress → command handler → reply path is connected.
