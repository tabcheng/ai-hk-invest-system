# Production Readiness Strategy (Step 69 System-of-Record)

## Positioning update
Project has moved from trial/prototype mode into formal internal product mode for AI-assisted Hong Kong investing workflows (paper-trading decision support only).

## Lightweight environment model
1. **Local dev**
   - Fast developer iteration and targeted checks.
2. **CI test**
   - Deterministic baseline validation and regression detection.
3. **Staging-lite**
   - Optional, bounded pre-production verification lane for integration-risk changes.
4. **Production**
   - Internal operational environment with controlled release discipline and post-deploy acceptance evidence.

UAT-lite may be introduced later as optional follow-up; it is not required in this step.

## When staging-lite is needed
- Cross-surface integration changes (for example new UI-to-backend flows).
- Changes with elevated secrets/auth/routing risk.
- Changes where production-first validation would be too risky for internal operations.

## When production smoke test is required
- Any merged runtime/DB/UI change affecting operator workflows or persistence semantics.
- Any release with changed Telegram command behavior or decision-journal flow.
- Any change explicitly covered by Step 66 post-deploy acceptance checklist governance.

## Secrets and API key handling
- Secrets stay in backend/runtime secret stores only (GitHub Secrets, Railway environment secrets).
- Never expose service-role or vendor keys in client bundles or browser-visible channels.
- No broker keys are introduced because broker/live execution is out of scope.

## GitHub Actions environment strategy
- Keep manual vs automatic workflows explicit by purpose and risk.
- Protect sensitive workflows with environment-scoped secrets and clear evidence artifacts.
- Preserve post-deploy acceptance artifact capture for auditability.

## Railway environment strategy
- Keep webhook/runner topology responsibilities explicit per service.
- Environment separation should remain lightweight and operationally simple unless risk profile requires expansion.
- Do not create new environment tiers in this step; this document is strategy guidance only.

## Supabase project/schema strategy
- Keep system-of-record consistency and migration discipline bounded to approved steps.
- Prefer incremental schema evolution with explicit acceptance evidence when runtime data contracts change.
- No schema/environment creation is performed in this docs-only step.

## Rollback + acceptance evidence principle
- Each release should preserve a clear rollback option and documented acceptance evidence.
- Acceptance evidence should include expected success path and known-failure-path behavior.
- Strategy or simulation-governance changes require stricter review before acceptance closure.


## Step 72 Mini App preview/deployment readiness policy (docs-only)
- Default preview path for Phase 1 shell: **Railway dedicated static site/static service** (separate from Telegram webhook ingress runtime).
- Deployment change class for Step 72: docs-level decision only; no runtime backend/auth/data-path enablement in this step.
- Required guardrails for any static preview deployment:
  - static shell remains read-only and paper-trading decision-support context only;
  - no production Supabase reads;
  - no service-role backend endpoint;
  - no vendor SDK or vendor secret in browser;
  - no write action/strategy change/paper-order creation/live execution.
- Future auth gate requirement stays unchanged: any later data-enabled Mini App flow must validate Telegram `initData` server-side before access.
- Rollback baseline: disable/unpublish static preview service URL and fall back to local-only preview while keeping repo shell unchanged.
- Step 73 execution requirement: use a dedicated Railway static service named `miniapp-static-preview` with Root Directory `/miniapp`; keep this service isolated from `telegram-webhook` ingress and `paper-daily-runner` scheduling responsibilities.
- Step 73 operator runbook source-of-truth: `docs/miniapp-static-preview-runbook.md` for post-merge manual creation/deploy/verification checklist.


## Step 75 Mini App read-only data boundary readiness policy (docs-only)
- Step class: docs-only planning; no runtime/API/auth/Supabase/Railway implementation changes in this step.
- Data-read prerequisite remains mandatory: server-side Telegram `initData` validation + authorization boundary must be implemented before any production Mini App data read.
- Security posture for first data-enabled read-only phase:
  - browser/client must not hold Supabase service-role or vendor/broker secrets;
  - backend-only bounded read API contract;
  - read-only response shape with explicit paper-trading/decision-support wording.
- Operational isolation requirement remains: webhook ingress and daily runner behavior must remain unaffected by future Mini App read-only data surface rollout.

## Step 78 readiness note (Mini App backend auth gate skeleton)
- Step 78 adds backend-only auth-gated mock read-only endpoint `POST /miniapp/api/review-shell`.
- This step does not require Railway manual deployment changes by default and does not introduce Supabase schema/runtime data-read dependencies.
- Production data-enabled Mini App API remains blocked pending explicit bounded read design + acceptance.


## Step 79 readiness note (Mini App API skeleton hardening)
- `POST /miniapp/api/review-shell` now enforces explicit JSON Content-Type and bounded request size cap before auth processing.
- Endpoint remains bounded mock-only/read-only and does not read Supabase production data.
- No Mini App frontend fetch wiring is introduced in this step.
- No Railway manual env/config change is required in-step unless separately approved.
- Production data-enabled Mini App remains blocked until a separately designed/accepted bounded read implementation is approved.


## Step 80 readiness note (controlled Railway Mini App API smoke acceptance planning)
- Live API smoke for `POST /miniapp/api/review-shell` requires backend-only secrets (`TELEGRAM_BOT_TOKEN`, `MINIAPP_ALLOWED_TELEGRAM_USER_IDS`) and must not expose secrets to browser/client/static Mini App.
- Raw Telegram `initData` must not be logged.
- Smoke acceptance must preserve bounded mock/read-only response contract and explicit guardrails.
- Step 80 smoke scope remains no Supabase production read.
- Step 80 smoke scope remains no write/order/execution.


## Step 81 controlled Railway smoke evidence requirement
- Live smoke evidence for `POST /miniapp/api/review-shell` must record `415`, `413`, and `503` checks.
- If backend env is configured by operator, evidence should also record `401` (invalid initData), `403` (unauthorized operator), and authorized mock `200`.
- Raw Telegram `initData` must not be logged or copied into evidence artifacts.
- `TELEGRAM_BOT_TOKEN` and `MINIAPP_ALLOWED_TELEGRAM_USER_IDS` must remain backend-only and never exposed to browser/client assets.
- Step 81 remains platform smoke evidence only and must not perform Supabase production read.


## Step 82 readiness note (GitHub Actions automated Mini App API smoke)
- Added manual-trigger-only workflow for live Railway smoke of `POST /miniapp/api/review-shell`.
- Workflow is not auto-triggered by `push`/`pull_request`.
- Secrets must be configured in GitHub environment/repository secrets only; never committed to repo.
- Raw `initData`, bot token, and allowlist IDs must not be printed in workflow logs.
- Railway precondition: `telegram-webhook` already deployed/configured with matching backend allowlist for authorized `200` smoke path.
- Scope remains no Supabase production read, no frontend fetch wiring, no write/order/execution.

## Step 84 readiness note (first bounded runtime status source)
- `POST /miniapp/api/review-shell` now exposes first bounded read-only runtime status metadata under `sections.runner_status`.
- This is Railway/backend runtime metadata only and remains within read-only decision-support boundaries.
- No Supabase production read, no market-data read, no paper-PnL read, no decision capture, no paper order creation, and no broker/live execution are introduced.
- Mini App frontend remains not wired to fetch this endpoint in Step 84.
- `miniapp-static-preview` remains static-only and `paper-daily-runner` operational path remains unaffected.

## Step 89 readiness clarification (helper-only)
- Added bounded backend artifact writer helper for `latest_system_run` contract generation only.
- This step does not validate cross-service filesystem readability and does not assume Railway shared filesystem between `paper-daily-runner` and `telegram-webhook`.
- No Railway topology change and no Railway volume creation are included.
- No Supabase production read/write, no Mini App frontend fetch, and no write/order/execution path are included.
- Step 90 must first decide storage + topology before enabling any live runner-to-miniapp artifact flow.


## Step 90 readiness decision (storage/topology, docs-only)
- Runner-to-miniapp `latest_system_run` path is now decisioned at topology level: future canonical path = Supabase/internal table (`latest_system_runs`).
- Security boundary remains backend-only for Supabase access; no browser/client exposure of service-role keys or secrets.
- Step 90 introduces no schema migration, no runtime Supabase read/write, no Railway topology/volume change, and no Mini App frontend fetch wiring.
- Local artifact provider/writer remains valid as fallback/dev/smoke/single-service path.

## Step 91 readiness state (proposal-only)
- Supabase/internal canonical path now has concrete schema/migration draft + repository contract proposal for `latest_system_runs`.
- This step introduces **no** runtime read/write enablement and no Railway topology change; manual Supabase apply/review is deferred pending acceptance.
- Next runtime candidate (Step 92): implement backend repository/provider wiring after schema acceptance, keeping backend-only secret boundary.

## Step 91A readiness update — RLS runtime impact + key-boundary audit
- Trigger: operator manually enabled RLS on all Supabase tables.
- Step 91A scope: docs/runbook/safe-check updates only.
- Required readiness checks:
  - verify backend writer service (`paper-daily-runner`) uses backend-only elevated key;
  - verify no Supabase service key is exposed to Mini App/browser/static preview;
  - verify no service key appears in logs/artifacts.
- Naming cleanup recommendation: migrate ambiguous `SUPABASE_KEY` toward explicit backend env naming (`SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY`) via staged fallback-first migration.
- Non-goal in this step: no Railway variable mutation, no schema/policy code mutation, no runtime repository integration.
