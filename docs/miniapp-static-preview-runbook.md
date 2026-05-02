# Mini App Static Preview Deployment Runbook (Step 73)

## Goal
Provide an operator-executable runbook to deploy the Phase 1 Mini App read-only preview shell as a dedicated Railway static service.

## Scope and service boundary
- **Service name:** `miniapp-static-preview`
- **Platform:** Railway
- **Source repo:** same GitHub repository (`ai-hk-invest-system`)
- **Root Directory:** `/miniapp`
- **Purpose:** Phase 1 read-only Telegram Mini App / Web UI preview shell

This service is intentionally separate from:
- `telegram-webhook`
- `paper-daily-runner`

Hard boundaries:
- `miniapp-static-preview` **must not** host webhook ingress.
- `miniapp-static-preview` **must not** run daily runner jobs.
- `miniapp-static-preview` **must not** include production data access.

## Phase 1 contract (must remain true)
- Read-only review shell only.
- No production Supabase reads.
- No write action.
- No decision capture.
- No paper order creation.
- No auth enablement in this step.
- No broker/live execution.

## Railway manual execution checklist (post-merge)
1. Open Railway project dashboard.
2. Create a new service named `miniapp-static-preview`.
3. Connect the same GitHub repository used by existing services.
4. Set **Root Directory** to `/miniapp`.
5. Configure deployment as static site/static service.
6. Deploy the service and wait until build/deploy status is healthy.
7. Generate or confirm Railway-provided domain URL.
8. Open preview URL and verify shell page renders.
9. Verify no production Supabase read path exists in browser behavior/code path.
10. Verify no write action controls exist in UI.
11. Verify no secrets appear in browser bundle/source (service role key, vendor secrets, webhook secret, broker keys).
12. Verify `telegram-webhook` service remains unchanged.
13. Verify `paper-daily-runner` service remains unchanged.

## Security and domain guardrails
Must remain explicit and enforced:
- No `SUPABASE_SERVICE_ROLE_KEY` in browser/client code.
- No vendor API secrets in browser/client code.
- No webhook secret in browser/client code.
- No broker key in browser/client code.
- Future data-enabled Mini App must validate Telegram `initData` server-side before granting access.
- `initDataUnsafe` must not be trusted for authorization.
- No autonomous live-money execution.
- Human final real-money decision remains outside this system.

## Validation checklist (acceptance)
- Preview URL serves static shell from `/miniapp` root.
- Shell is read-only and visibly labeled as paper-trading/decision-support context.
- No backend data call wiring in this phase.
- No secret values in page source or browser artifacts.
- No impact to existing webhook ingress and runner schedules.

## Rollback
If preview service is incorrect or violates boundary:
1. Disable/unpublish `miniapp-static-preview` Railway service.
2. Remove Mini App preview URL usage from operator path.
3. Keep in-repo static shell artifact for local/docs review only.
4. Re-open backlog item for corrected redeploy.
