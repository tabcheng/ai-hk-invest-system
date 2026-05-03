# AGENTS.md

## Documentation-first workflow (required)
For any non-trivial task (anything beyond a tiny typo or formatting-only edit), read these files before doing implementation work:
1. `AGENTS.md`
2. `docs/spec.md`
3. `docs/plans.md`
4. `docs/status.md`

## Project mission
- This repository is an **internal AI Hong Kong equity investing system**.
- Mainline model: **AI analysis team + AI team paper trading + human final decision + strategy improvement loop**.
- The product supports analysis, AI simulated decisions, human paper decisions, simulated orders/positions/PnL, decision journal, outcome review, strategy review, risk control, and operator review surfaces.
- The system must **not** connect to brokers, place live orders, or perform autonomous real-money execution.

## Decision boundaries (must stay explicit)
Always separate and label:
1. **AI simulated decision**
2. **Human paper decision**
3. **Real trade decision outside system**

All real-money decisions are made and executed outside this system by the human operator.

## Product surfaces
### Telegram Bot
- Notifications
- Quick commands
- Smoke-test path

### Telegram Mini App / Web UI
- Daily review surface
- Multi-stock review
- Decision journal review
- Paper PnL / risk / outcome review

### Backend + Supabase
- System of record
- Audit trail
- Paper-trading records
- Decision records

## UI release phases
1. **Phase 1: Read-only Review Shell**
   - No write action
   - No strategy change
   - No paper order creation
2. **Phase 2: Decision Capture**
   - Bounded journal writes only
   - No execution
3. **Phase 3: AI Team Paper Decision Review**
   - Review AI simulated decisions
   - No broker/live execution
4. **Phase 4: Controlled Simulated Order Creation**
   - Only after risk gate
   - Requires `strategy_version`, `data_source`, `data_timestamp`, `risk_check`, `paper_trade_only=true`

## Market data guardrails
- Introduce/keep a `MarketDataProvider` abstraction before vendor integration.
- Strategy logic must not call vendor SDKs directly.
- Track data source, timestamp, freshness, adjustment policy, and confidence/limitations.
- Vendors may be used with justification, but avoid vendor lock-in.

## Secrets + access guardrails
Never expose these in browser/client/logs/docs:
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_SECRET_KEY`
- vendor API secrets
- webhook secrets
- broker keys

Mini App auth must validate Telegram `initData` server-side before granting access.

## Environment strategy
Use a lightweight formal path:
- local dev
- CI test
- staging-lite when integration risk justifies it
- production with post-deploy acceptance

Do not overbuild full enterprise SDLC too early.

## PR requirements
Every PR must state:
- goal
- scope
- changed files
- GitHub impact
- Railway impact
- Supabase impact
- tests run
- acceptance instructions
- risk/limitation
- whether post-deploy smoke is required

Runtime/DB/Telegram/UI/market-data/paper-trading PRs require stronger review.
Docs-only PRs do not require runtime tests unless repository policy explicitly requires them, but must keep system-of-record docs consistent.

## Review checklist (mandatory before approval)
Inspect all of the following:
- PR metadata
- diff/patch
- CI status
- PR conversation comments
- inline review threads / Codex comments
- review submissions
- docs/status wording
- backlog updates
- domain guardrails

Do not approve when unresolved Codex comments affect correctness, audit trail, security, runtime behavior, or domain guardrails.

## Post-merge checks (mandatory after every merge)
Record both checks in docs:
1. **Post-merge QA Check**
   - output/function works
   - success/error paths are clear
   - docs/tests/display are consistent
2. **Post-merge Domain Check**
   - aligns with AI HK investing system
   - paper trading / decision-support only
   - no broker/live execution
   - calculation/interpretation risk reviewed

## Documentation alignment
Keep the following aligned:
- `AGENTS.md`
- `docs/spec.md`
- `docs/architecture-v3.md`
- `docs/project-implementation-plan.md`
- `docs/backlog.md`
- `docs/status.md`
- `docs/product-surface-strategy.md`
- `docs/production-readiness-strategy.md`
- `docs/market-data-strategy.md`
