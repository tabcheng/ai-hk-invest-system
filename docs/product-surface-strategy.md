# Product Surface Strategy (Step 69 System-of-Record)

## Purpose
Define role boundaries between Telegram Bot and upcoming Mini App / Web UI surfaces while preserving paper-trading decision-support governance.

## Telegram Bot responsibilities
- Deliver run notifications and concise summary alerts.
- Provide quick operator command actions and smoke-test verification path.
- Support fast operational checks when users are mobile or in low-context situations.

## Mini App / Web UI responsibilities
- Provide richer daily review surface (multi-run, multi-stock, and journal context inspection).
- Improve readability and audit navigation as command count and data density grow.
- Serve as product-review surface for AI team paper decisions and outcome follow-up.

## Why Telegram-only is insufficient (at current growth stage)
- Command-by-command chat flow becomes high-friction as review breadth increases.
- Multi-entity comparison in chat output is harder to scan and validate consistently.
- Structured governance artifacts (decision journal, risk gates, outcome reviews) need denser visual review surfaces.

## Phased release roadmap
### Phase 1 — Read-only Review Shell
- Scope: read-only review only; must not alter strategy settings or paper orders.
- Required labeling: explicit paper/simulation status on relevant views.
- Acceptance: post-deploy acceptance evidence is mandatory before phase closure.
- Step 71 MVP baseline: static/mock Mini App-compatible review shell is allowed for low-risk rollout, with no production Supabase read, no write controls, and explicit security/auth TODOs (`initData` server-side validation required; no service-role/vendor secrets in browser).
- Step 72 deployment-path decision: adopt Railway static-site/service as the default preview path for Phase 1 shell exposure (separate from webhook ingress service), keep shell static/read-only, and keep all data/auth/write/vendor integration out of scope.
- Step 73 execution runbook: add operator runbook (`docs/miniapp-static-preview-runbook.md`) to execute dedicated Railway static preview deployment (`miniapp-static-preview`) with explicit `/miniapp` Root Directory and strict separation from `telegram-webhook` and `paper-daily-runner` service responsibilities.

### Step 72 decision record — Mini App preview/deployment path
- **Recommended option (default):** Railway dedicated static site/static service with independent preview URL for operator access.
- **Not recommended as long-term default:** existing webhook service static serving (only acceptable as short-term preview fallback due to ingress coupling and routing ambiguity risk).
- **Alternative viable option:** external static host (low setup cost but adds extra platform governance and deployment/access-policy overhead).
- **Deferred option:** local-only preview (safest for platform change, but insufficient for Telegram Mini App URL rehearsal and operator URL access).
- **Step 72 explicit non-goals:** no data access, no production Supabase read, no service-role backend endpoint, no vendor SDK integration, no write action, no strategy change, no paper order creation, no broker/live execution.
- **Security/auth guardrails:** browser/client must never hold `SUPABASE_SERVICE_ROLE_KEY` or vendor secrets; future data-enabled Mini App must validate Telegram `initData` server-side before any access grant.
- **GitHub impact:** docs-only decision synchronization; no runtime/test/dependency/workflow behavior change.
- **Railway impact:** decision is to add a separate static service in a later execution step; this step does not create/modify running services.
- **Supabase impact:** no schema/policy/data-path/runtime query changes in Step 72.
- **Acceptance checklist (for deployment execution follow-up):**
  1) preview URL opens `miniapp/index.html` read-only shell;
  2) no write controls/actions are exposed;
  3) no production Supabase read path exists;
  4) no service-role/vendor secret appears in browser artifacts;
  5) paper-trading/decision-support-only labeling remains explicit.
- **Rollback plan:** unpublish/disable static preview service and revert Mini App entry URL to local-only/internal preview path while keeping shell artifact unchanged.
- **Future path to Telegram Mini App URL:** after static preview stabilization, bind Telegram Mini App URL to the dedicated static service URL, then introduce server-side `initData` validation before any data/API enablement.


### Phase 2 — Decision Capture
- Add bounded decision-capture forms for human paper decisions/journals only.
- Preserve no-execution boundary and human-final-decision governance.
- Require post-deploy acceptance before rollout completion.

### Phase 3 — AI Team Paper Decision Review
- Add dedicated review workflows for AI team simulated decisions, outcomes, and discussion context.
- Keep outputs as decision-support evidence only; no broker/live execution path.
- Require post-deploy acceptance before rollout completion.

### Phase 4 — Controlled Simulated Order Creation
- Allow controlled simulated-order creation only after risk-gate checks and full metadata capture.
- Required metadata: `strategy_version`, `data_source`, `data_timestamp`, `risk_check`, `paper_trade_only=true`.
- Require post-deploy acceptance before rollout completion.

## Global UI governance rules
- Every phase requires explicit post-deploy acceptance.
- UI must clearly label paper/simulation status to avoid live-trading interpretation risk.
- No UI phase may introduce broker integration or real-money autonomous execution.
