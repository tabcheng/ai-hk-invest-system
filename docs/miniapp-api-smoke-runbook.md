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

## Pre-env safe failures (before allowlist/env setup)
Expected safe failures:
- Missing/invalid `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` => safe `503`.
- Missing/invalid `TELEGRAM_BOT_TOKEN` => safe `503`.
- Non-JSON Content-Type => `415` with `{ "ok": false, "error": "unsupported_media_type" }`.
- Oversized body (>8192 bytes) => `413` with `{ "ok": false, "error": "payload_too_large" }`.

Note:
- In a **true pre-env** smoke run, `401 invalid_init_data` is not expected because backend env/config checks happen before initData validation.

## Post-env negative auth checks (after env/config is present)
Expected failures:
- Invalid `initData` signature/freshness => `401` with `{ "ok": false, "error": "invalid_init_data" }`.
- Unauthorized operator (valid initData but user id not in allowlist) => `403` with `{ "ok": false, "error": "operator_not_authorized" }`.

## Post-env authorized mock success (after env/config is present)
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
- Content-Type 415 tested: yes/no/result
- Oversized 413 tested: yes/no/result
- Missing/invalid env 503 tested: yes/no/result
- Invalid initData 401 tested: yes/no/not run/result
- Unauthorized operator 403 tested: yes/no/not run/result
- Authorized mock 200 tested: yes/no/not run/result
- Supabase production read observed: yes/no
- Write/order/execution path observed: yes/no
- telegram-webhook existing Telegram command behavior unaffected: yes/no
- paper-daily-runner unaffected: yes/no
- Notes / limitations:

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


## Step 81 execution evidence record (operator-controlled)
- This section records **manual operator-controlled Railway smoke execution evidence** after Step 80 planning.
- Scope remains platform-smoke evidence only for `POST /miniapp/api/review-shell`.
- Do not perform Supabase production reads, Mini App frontend fetch wiring, or any write/order/execution action in Step 81.

### Evidence staging expectation
1. **Pre-env stage** (no backend allowlist/token ready): verify safe bounded failures (`415`, `413`, `503`).
2. **Post-env negative auth stage** (env configured by operator): verify `401` invalid initData and `403` unauthorized operator.
3. **Post-env authorized mock stage** (when operator allowlist and test initData are valid): verify bounded mock-only `200` response and guardrails.

### Step 81 constraints reminder
- Raw Telegram `initData` must not be logged into app logs, browser console, docs, or PR comments.
- `TELEGRAM_BOT_TOKEN` and `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` remain backend-only secrets/allowlist values.
- Step 81 does not authorize or introduce production Supabase data read.


## Step 82 — GitHub Actions automated smoke workflow (manual trigger only)
- Added workflow: `.github/workflows/miniapp-api-smoke.yml`.
- Trigger mode is `workflow_dispatch` only (no `push` / `pull_request` auto run).
- Suggested protected environment: `miniapp-smoke`.
- Required GitHub secrets (environment or repository):
  - `MINIAPP_SMOKE_ENDPOINT_URL`
  - `MINIAPP_SMOKE_BOT_TOKEN`
  - `MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID`
  - `MINIAPP_SMOKE_UNAUTHORIZED_TELEGRAM_USER_ID`
- Added script: `scripts/miniapp_api_smoke.py`.
- Endpoint URL contract: if `MINIAPP_SMOKE_ENDPOINT_URL` already ends with `/miniapp/api/review-shell`, script uses it directly; otherwise script appends `/miniapp/api/review-shell`.
- Script generates Telegram-signed `initData` locally via HMAC and uses current `auth_date`; no Telegram network call required.
- Script validates and checks bounded cases: `415`, `413`, `401`, `403`, `200`.
- Logs are bounded to safe labels + HTTP status + safe error/status fields only.
- Raw `initData`, bot token, allowlist IDs, and full request body must not be printed.
- For `200`, script asserts mock/read-only guardrails and decision-support-only / paper-trade-only / no-broker/no-real-money execution flags.
- Step 82 remains smoke tooling + docs only: no Supabase production read, no frontend fetch wiring, no write/order/execution path.

### Optional local dry-run
```bash
export MINIAPP_SMOKE_ENDPOINT_URL='https://<railway-service-url>'
export MINIAPP_SMOKE_BOT_TOKEN='<bot-token>'
export MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID='<authorized-user-id>'
export MINIAPP_SMOKE_UNAUTHORIZED_TELEGRAM_USER_ID='<unauthorized-user-id>'
python scripts/miniapp_api_smoke.py
```
- Expected safe output: PASS/FAIL per case with status code only.
- Do not paste real secrets into shell history snapshots, screenshots, or GitHub comments.

## Step 84 smoke contract update (bounded runtime runner status)
- Authorized `200` response no longer requires `sections.runner_status.status=mock`.
- Updated accepted runner-status contract:
  - `sections.runner_status.source=railway_runtime_env`
  - `sections.runner_status.status` in `{ "ok", "unknown" }`
- Remaining sections still expected mock-only:
  - `sections.daily_review.status=mock`
  - `sections.pnl_snapshot.status=mock`
  - `sections.outcome_review.status=mock`
- Guardrails remain mandatory and unchanged:
  - `read_only=true`
  - `paper_trade_only=true`
  - `decision_support_only=true`
  - `no_broker_execution=true`
  - `no_real_money_execution=true`
- Security checks remain unchanged:
  - no secret exposure,
  - no write/order/execution affordance,
  - no Supabase production data read.
