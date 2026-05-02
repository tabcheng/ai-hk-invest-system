# Mini App API Smoke Runbook (Step 80 Controlled Railway Acceptance Planning)

## Scope
- Endpoint: `POST /miniapp/api/review-shell`
- Step 80 scope is **controlled Railway smoke decision + acceptance planning docs only**.
- Endpoint remains **mock-only** and **read-only**.
- No Supabase production read, no Mini App frontend fetch wiring, no write/order/execution.

## Service ownership boundary (Railway)
- Endpoint owner service: **`telegram-webhook`**.
- Static preview service **`miniapp-static-preview` must not host backend API**.
- **`paper-daily-runner` must remain unaffected** by this smoke path.

## Required request contract
- Header: `Content-Type: application/json`
- Accepted variant: `application/json; charset=utf-8`
- Body:
```json
{ "init_data": "<Telegram.WebApp.initData raw query string>" }
```

## Controlled Railway pre-smoke checks
1. Confirm latest Railway deployment includes the **Step 79 merge commit** before manual smoke.
2. Confirm endpoint path is exactly `POST /miniapp/api/review-shell`.
3. Confirm request contract still requires `Content-Type: application/json`.
4. Confirm no Mini App frontend fetch is wired to this endpoint.
5. Confirm no Supabase production read is expected for this endpoint.

## Backend env requirements (backend-only secrets/allowlist)
- `TELEGRAM_BOT_TOKEN` must remain backend-only.
- `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` must remain backend-only.
- Do **not** expose either value in browser/client/static Mini App files.
- Do **not** paste real bot token into docs, logs, GitHub comments, or browser tools.
- Allowlist must be Telegram **numeric user id only** (not username).

## Safe smoke expectations before allowlist/env setup
Expected safe failures:
- Missing/invalid `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` => safe `503`.
- Missing/invalid `TELEGRAM_BOT_TOKEN` => safe `503`.
- Non-JSON Content-Type => `415` with `{ "ok": false, "error": "unsupported_media_type" }`.
- Oversized body (>8192 bytes) => `413` with `{ "ok": false, "error": "payload_too_large" }`.
- Invalid `initData` signature/freshness => `401` with `{ "ok": false, "error": "invalid_init_data" }`.

## Authorized mock smoke expectations after env setup
Expected authorized success path:
- Authorized request returns `200`.
- Response remains **mock-only/read-only**.
- Response includes guardrails:
  - `guardrails.read_only=true`
  - `guardrails.paper_trade_only=true`
  - `guardrails.decision_support_only=true`
  - `guardrails.no_broker_execution=true`
  - `guardrails.no_real_money_execution=true`
- Response must not include real Supabase production data.
- Response must not include write/order/execution affordance.

## Evidence template (record after manual smoke)
- Railway service:
- Deployment commit:
- Endpoint URL tested:
- Content-Type 415 tested: yes/no
- Oversized 413 tested: yes/no
- Invalid initData 401 tested: yes/no
- Missing/invalid env 503 tested: yes/no
- Authorized mock 200 tested: yes/no/not run
- Supabase production read observed: yes/no
- Write/order/execution path observed: yes/no
- telegram-webhook existing Telegram command behavior unaffected: yes/no
- paper-daily-runner unaffected: yes/no

## Security reminders
- Do **not** paste real bot token into browser/client.
- Do **not** log raw `init_data`.
- Do **not** expose `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` to frontend.
- Do **not** add Supabase reads in this step.
- Do **not** add write/order/execution in this step.

## Out of scope (Step 80)
- Supabase production data read
- Supabase schema/RLS changes
- Mini App frontend fetch wiring
- decision capture
- paper order creation
- broker/live execution
