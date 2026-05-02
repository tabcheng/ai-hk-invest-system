# Mini App API Smoke Runbook (Step 79)

## Scope
- Endpoint: `POST /miniapp/api/review-shell`
- Step 79 scope is **hardening + smoke runbook only**.
- Endpoint remains **mock-only** and **read-only**.
- No Supabase production read, no Mini App frontend fetch wiring, no write/order/execution.

## Required request contract
- Header: `Content-Type: application/json`
- Accepted variant: `application/json; charset=utf-8`
- Body:
```json
{ "init_data": "<Telegram.WebApp.initData raw query string>" }
```

## Failure expectations (safe defaults)
- Missing/invalid `Content-Type` => `415` with `{ "ok": false, "error": "unsupported_media_type" }`
- Oversized body (>8192 bytes) => `413` with `{ "ok": false, "error": "payload_too_large" }`
- Invalid JSON => `400` with `{ "ok": false, "error": "invalid_json" }`
- Missing `init_data` => `400` with `{ "ok": false, "error": "missing_init_data" }`
- Invalid `initData` signature/freshness => `401` with `{ "ok": false, "error": "invalid_init_data" }`
- Unauthorized operator => `403` with `{ "ok": false, "error": "operator_not_authorized" }`
- Missing bot token or invalid allowlist env => safe `503`

## Before Railway env setup
Expected safe failure is `503` when:
- `TELEGRAM_BOT_TOKEN` missing/invalid, or
- `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` missing/invalid.

## After backend env setup (authorized happy path)
Expected response is bounded mock read-only JSON (example fields):
- `status=ok`
- `sections.*.status=mock`
- `guardrails.read_only=true`
- `guardrails.paper_trade_only=true`
- `guardrails.no_broker_execution=true`
- `guardrails.no_real_money_execution=true`

## Security reminders
- Do **not** paste real bot token into browser/client.
- Do **not** log raw `init_data`.
- Do **not** expose `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` to frontend.
- Do **not** add Supabase reads in this step.
- Do **not** add write/order/execution in this step.

## Out of scope (Step 79)
- Supabase production data read
- Supabase schema/RLS changes
- Mini App frontend fetch wiring
- decision capture
- paper order creation
- broker/live execution
