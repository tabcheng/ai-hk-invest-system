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
