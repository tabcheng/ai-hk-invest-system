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
