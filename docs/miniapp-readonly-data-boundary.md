# Mini App Read-only Data Surface Boundary Plan (Step 75) + Auth Prerequisite Utility (Step 76)

## Scope and intent
This document defines the **next-step boundary plan** for moving from the current static Mini App shell (Phase 1) to a future **data-enabled but read-only** surface.

This is a docs-only planning step.

## Background context
- Step 73 completed Railway `miniapp-static-preview` static deployment and acceptance.
- Step 74 completed Mini App static shell polish and static-contract test hardening.
- Current Mini App remains static/read-only/framework-free and does not perform production Supabase read, Telegram auth validation, or write actions.

Explicit non-goals in Step 75:
- no runtime API implementation
- no Telegram auth validation code
- no Supabase client/browser production read
- no Supabase schema or RLS policy change
- no Mini App JS data-fetch integration
- no write action, decision capture, or paper order creation
- no broker/live execution path
- no Railway topology or env-var change

## A) Recommended data path (future implementation target)
1. Mini App browser sends Telegram `initData` to backend.
2. Backend validates `initData` **server-side**.
3. Backend enforces operator allowlist / authorization checks.
4. Backend reads bounded data from Supabase/internal services.
5. Backend returns bounded read-only JSON response.
6. Mini App renders read-only review cards.

## B) Explicitly rejected path for now
- No direct browser-to-Supabase production reads.
- No Supabase service-role/secret key in browser/client code.
- No vendor API secret in browser/client code.
- No broker key in browser/client code.
- No use of `initDataUnsafe` for authorization decisions.

## C) First read-only data candidates (definition only)
Candidate sections for first data-enabled read-only surface:
- latest runner status
- recent runs / latest run id
- daily review packet summary
- paper PnL / risk snapshot
- outcome review summary

This section is a planning contract only; no API/data implementation is included in Step 75.

## D) Deferred / excluded data from first read-only surface
Keep out of first read-only data surface:
- strategy mutation
- decision capture
- paper order creation
- broker/live execution
- raw unrestricted Supabase table browsing
- vendor secret-backed market-data calls from browser
- write-capable endpoints

## E) Conceptual read-only response contract (example)
```json
{
  "status": "ok",
  "generated_at_hkt": "2026-05-02T20:00:00+08:00",
  "sections": {
    "runner_status": {},
    "daily_review": {},
    "pnl_snapshot": {},
    "outcome_review": {}
  },
  "guardrails": {
    "read_only": true,
    "paper_trade_only": true,
    "no_broker_execution": true
  }
}
```

Notes:
- `generated_at_hkt` is for review readability and should be explicit about timezone semantics.
- Response must stay bounded to review fields; no write semantics or execution intents.

## F) Acceptance criteria for future implementation step
Any future runtime implementation for Mini App read-only data must prove:
1. server-side `initData` validation exists;
2. authorization is enforced;
3. no secrets are exposed to browser/client bundles;
4. no write path exists;
5. response remains bounded/read-only;
6. output retains paper-trading/decision-support wording;
7. webhook and daily runner services remain unaffected.

## Domain boundary reminder
The AI HK Invest system remains paper-trading/decision-support only:
- AI simulated decision
- human paper decision
- real trade decision outside system

No broker integration or autonomous real-money execution is authorized by this plan.

## Step 76 implementation update (backend-only auth utility)
- Added `src/miniapp_auth.py` backend-only Telegram Mini App `initData` validation helper with bounded failure reasons and freshness checks.
- Added focused deterministic tests in `tests/test_miniapp_auth.py` using fake bot token fixtures only; no Telegram network calls, no Supabase dependency, and no Railway dependency.
- This step does **not** add HTTP endpoint/API route, Mini App frontend fetch integration, Supabase read path, or Railway deployment/config changes.
- Production Mini App data read remains blocked until all of the following are implemented and accepted:
  1. validation helper is wired into an actual backend endpoint;
  2. operator authorization boundary is enforced;
  3. bounded read-only response contract is implemented and accepted.

## Step 77 implementation update (backend-only operator authorization boundary helper)
- Added backend-only operator authorization boundary helper in `src/miniapp_auth.py` that accepts validated context from `validate_telegram_init_data(...)` and authorizes only by stable Telegram numeric `user.id`.
- The helper returns a bounded authorized context only (`telegram_user_id`, optional `username`, `authorization_status=authorized`) and rejects bounded failures for:
  - `missing_user`
  - `missing_user_id`
  - `invalid_user_id_type`
  - `empty_operator_allowlist`
  - `unauthorized_user_id`
- Security boundary remains explicit:
  - do not read allowlist from browser/client;
  - do not use username as authorization key;
  - do not log raw `initData`;
  - do not log bot token or expose secrets.
- Focused tests now cover authorized/unauthorized and missing/invalid-context failures, including username-only non-authorization behavior.
- No HTTP route/API endpoint is added in this step.
- No Supabase read/schema/RLS change is added in this step.
- No Mini App frontend fetch/change is added in this step.
- No Railway topology/env/runtime change is added in this step.
- Production data read remains blocked until both helper layers are wired into a backend endpoint and a bounded read-only response contract is implemented/accepted.

## Step 78 implementation update (backend-only auth-gated read-only API skeleton)
- Added backend WSGI route `POST /miniapp/api/review-shell` with JSON-only request contract and required `init_data` field.
- Route enforces dual gate: `validate_telegram_init_data(...)` + `authorize_telegram_operator(...)`.
- Added backend-only allowlist env parsing for `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` (comma-separated numeric Telegram user IDs only).
- Success response is bounded mock JSON only (`status=mock` sections + explicit read-only/paper-trade guardrails).
- No Supabase production read, no Mini App frontend fetch wiring, no write action, no decision capture, no paper order creation, and no broker/live execution path in this step.
- Railway manual deployment/env configuration is not required for this PR unless explicitly approved in a later step.
- Production data-enabled Mini App remains blocked until a bounded Supabase/internal read implementation is separately designed and accepted.


## Step 79 implementation update (API skeleton hardening + smoke runbook)
- Hardened `POST /miniapp/api/review-shell` request contract in backend ingress:
  - explicit JSON Content-Type requirement (`application/json` with optional charset variant),
  - bounded reject for unsupported type (`415 unsupported_media_type`),
  - bounded request body cap (`MINIAPP_REVIEW_SHELL_MAX_BODY_BYTES=8192`) with `413 payload_too_large`.
- Existing auth/authorization behavior is preserved (`400/401/403/503` contracts unchanged), with no raw `init_data` echo/log exposure introduced.
- Added smoke validation runbook `docs/miniapp-api-smoke-runbook.md` for controlled later Railway/manual verification.
- Endpoint remains mock-only/read-only; no Supabase production read, no Mini App frontend fetch wiring, and no write/order/execution path in this step.


## Step 80 controlled Railway smoke planning update (docs-only)
- Service ownership is explicit for smoke/acceptance: `telegram-webhook` owns backend API route, `miniapp-static-preview` remains static-only frontend, and `paper-daily-runner` remains unaffected.
- Controlled smoke acceptance is split into pre-env safe failure checks and post-env authorized mock-only success checks.
- Production Supabase data read remains blocked in Step 80 and requires separately designed/accepted bounded read contract in a future step.
- No Mini App frontend fetch integration and no write/order/execution path are introduced in Step 80.


## Step 81 clarification (platform smoke evidence only)
- Step 81 records controlled Railway smoke execution evidence only for backend route `POST /miniapp/api/review-shell`.
- Step 81 does not introduce production Supabase data read and does not change read-only data contract scope.
- Backend smoke route remains owned by `telegram-webhook`; `miniapp-static-preview` remains static-only.
- `paper-daily-runner` remains unaffected.


## Step 82 tooling update (manual automated smoke only)
- Added manual GitHub Actions automated smoke tooling for `POST /miniapp/api/review-shell` via `.github/workflows/miniapp-api-smoke.yml` and `scripts/miniapp_api_smoke.py`.
- Workflow is manual-trigger only and intended for controlled smoke evidence capture.
- Script uses backend secrets/env vars, locally signs Telegram `initData`, and asserts bounded 415/413/401/403/200 contracts.
- Security/logging policy: do not print raw `initData`, bot token, allowlist IDs, or full request body.
- Data boundary remains unchanged: no Supabase production read, no Mini App frontend fetch wiring, and no write/order/execution path.

## Step 84 implementation update (first bounded read-only runtime status source)
- `POST /miniapp/api/review-shell` now uses a dedicated read-model helper (`src/miniapp_read_model.py`) and promotes `sections.runner_status` from pure mock to bounded runtime metadata.
- Runtime section source is bounded to safe Railway/backend runtime metadata only:
  - `RAILWAY_SERVICE_NAME`
  - `RAILWAY_ENVIRONMENT_NAME`
  - `RAILWAY_GIT_BRANCH`
  - `RAILWAY_GIT_COMMIT_SHA` (shortened output only)
  - `RAILWAY_DEPLOYMENT_ID` (presence boolean only)
  - optional `RAILWAY_PROJECT_NAME` is not required by current contract.
- Runner status contract now includes:
  - `status` (`ok` or `unknown`)
  - `source=railway_runtime_env`
  - bounded service/environment/branch/short-commit/deployment-presence fields
  - `generated_at_hkt`
- Explicit non-goals preserved in this step:
  - no Supabase production data read,
  - no market-data read,
  - no paper PnL data read,
  - no decision capture,
  - no paper order creation,
  - no broker/live execution,
  - no Mini App frontend fetch wiring.
- Other response sections remain mock-only (`daily_review`, `pnl_snapshot`, `outcome_review`).
- `miniapp-static-preview` remains static-only and `paper-daily-runner` remains unaffected.
- Future Supabase/internal data reads remain separate work requiring explicit bounded data contracts and acceptance.

## Step 86 implementation update (first bounded internal/business read contract + adapter boundary)
- Added a bounded Mini App read-data provider boundary in backend code:
  - `MiniAppReadDataProvider` protocol now separates two bounded reads: `get_runtime_status_summary()` and `get_latest_system_run_summary()`.
  - `RailwayRuntimeEnvMiniAppReadDataProvider` remains the first adapter implementation, using only bounded Railway runtime env metadata for runtime status and a default `latest_system_run` unavailable contract (`status=unavailable`, `source=not_configured`).
- `src/miniapp_read_model.py` consumes the provider boundary (with optional injection for tests) and now returns both `sections.runner_status` and `sections.latest_system_run` from provider methods.
- Scope remains strictly read-only and backend-only:
  - no Supabase production data reads,
  - no Mini App frontend fetch wiring,
  - no write/order/execution path.

## Step 87 implementation update (first real latest-system-run provider via bounded local artifact)
- Added `LocalArtifactMiniAppReadDataProvider` in `src/miniapp_data_provider.py` as the first concrete `latest_system_run` read provider beyond default unavailable contract.
- Provider reads a **backend-local bounded JSON artifact** from `MINIAPP_LATEST_SYSTEM_RUN_ARTIFACT_PATH` and maps only bounded summary fields into `sections.latest_system_run`.
- Default/failure behavior remains explicit and bounded:
  - missing/invalid artifact => `status=unavailable`, `source=local_artifact`, bounded limitation message;
  - valid artifact with required fields => `status=ok`, `source=local_artifact`.
- `src/miniapp_read_model.py` now resolves default provider by env:
  - artifact path configured => local-artifact provider;
  - otherwise => existing `RailwayRuntimeEnvMiniAppReadDataProvider` with Step 86 unavailable fallback.
- Scope stays strict:
  - no Supabase production reads,
  - no Mini App frontend fetch wiring,
  - no write/order/execution path.

## Step 89 implementation update (artifact writer helper only)
- Added bounded backend helper `src/miniapp_artifact_writer.py` to build/write `latest_system_run` artifacts for future runner usage.
- This is helper-only and does **not** establish runtime data flow between Railway services.
- Explicit guardrails preserved in this step:
  - does **not** prove `telegram-webhook` can read `paper-daily-runner` filesystem output,
  - does **not** assume Railway cross-service filesystem sharing,
  - no Railway topology change,
  - no Railway volume creation,
  - no Supabase production read/write,
  - no Mini App frontend fetch wiring,
  - no write/order/execution path.
- Step 90 must decide storage/topology path before any live runner-to-miniapp data flow is enabled.


## Step 90 decision update (storage/topology only, docs-first)
- New decision doc: `docs/latest-system-run-storage-topology.md`.
- Decision outcome: future canonical runner-to-miniapp `latest_system_run` flow should use Supabase/internal-table topology (option C) instead of assuming cross-service filesystem handoff.
- Step 90 is design/contract only: no Supabase migration, no runtime read/write path, no Railway topology or volume change, and no Mini App frontend fetch addition.
- Step 87 local artifact provider and Step 89 artifact writer remain accepted bounded fallback for local/dev/smoke/single-service usage.

## Step 91 boundary update (schema/proposal only)
- Step 91 introduces proposal artifacts only: Supabase `latest_system_runs` migration draft + backend repository contract proposal.
- API/runtime behavior remains unchanged: no Supabase runtime read/write in miniapp route or runner, no frontend Supabase fetch, no write/order/execution.
- Local artifact provider remains valid fallback for local/dev/smoke until Step 92 runtime provider integration.

## Step 91A boundary reaffirmation
- Mini App static preview remains static/read-only and must not receive any Supabase service-role/secret key.
- Step 91A introduces no Mini App frontend Supabase fetch and no new Mini App production Supabase read path.
- Backend service keys remain backend runtime only.
