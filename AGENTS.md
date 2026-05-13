# AGENTS.md

## Documentation-first workflow (required)
For any non-trivial task (beyond tiny typo/format edits), read before implementation:
1. `AGENTS.md`
2. `docs/spec.md`
3. `docs/plans.md`
4. `docs/status.md`

## Mission + hard domain guardrails
- Internal **AI Hong Kong equity investing** system.
- Scope is **AI analysis + AI paper/simulated decisions + human review + strategy improvement loop**.
- Must stay **paper-trading / decision-support only**:
  - no broker connection,
  - no live order placement,
  - no autonomous real-money execution.
- Always distinguish and label:
  1. **AI simulated decision**
  2. **Human paper decision**
  3. **Real trade decision outside system**

## Product surfaces
- Telegram Bot (notifications, quick commands, smoke path)
- Telegram Mini App / Web UI (review surfaces)
- Backend + Supabase (system of record, audit trail, paper-trading/decision records)

## Security + access boundaries
- Mini App frontend must never use Supabase service/secret keys.
- Telegram `initData` must be validated server-side before access.
- Backend production writes/reads after RLS must use backend-only elevated key class (`sb_secret_*` or service-role class).
- Do **not** use `sb_publishable_*`, anon, or public keys for backend writes after RLS.
- Never expose secrets/raw sensitive values in docs/logs/chat (including Supabase secrets, Telegram tokens/webhook secrets, vendor/broker secrets, raw Telegram initData, allowlist IDs, Railway token/raw fingerprint/full hash).

## PR requirements (mandatory)
Every PR must state:
- goal
- scope
- changed files
- GitHub impact
- Railway impact
- Supabase impact
- tests run
- acceptance instructions
- risk / limitation
- whether post-deploy smoke is required

## PR review hard gate (mandatory before approval)
Reviewers must check all:
1. PR metadata/scope
2. diff/patch/changed files
3. CI status/jobs/logs
4. PR conversation comments
5. issue/top-level comments
6. review submissions
7. inline review threads / Codex comments
8. unresolved thread count
9. outdated-but-unresolved thread count
10. docs/status wording
11. backlog updates
12. domain guardrails

Do **not** approve if:
- CI failed or still running (unless clearly irrelevant and explicitly explained),
- any non-outdated unresolved reviewer/Codex thread affects correctness, audit trail, security, runtime behavior, domain guardrails, or docs-of-record,
- any outdated-but-unresolved reviewer/Codex thread remains unresolved,
- runtime/Supabase/Railway changes lack an explicit acceptance path.

## Step 91C / PR #98 runtime lesson
- Step 91C Runtime Acceptance passed in GitHub Actions run **25424407687** after PR **#98** merge.
- Railway Public API 403 in GitHub Actions was resolved by explicit `Accept` / `User-Agent` / `Authorization` headers.
- Railway probes/log evidence must remain read-only and secret-safe (no raw logs).

## Post-merge checks (mandatory after every merge)
Record both in docs:
1. **Post-merge QA Check** (output/function, success+error paths, docs/tests/display consistency)
2. **Post-merge Domain Check** (AI HK alignment, paper-only boundary, no broker/live execution, interpretation risk reviewed)

## Documentation alignment (system-of-record set)
Keep these aligned:
- `AGENTS.md`
- `docs/spec.md`
- `docs/architecture-v3.md`
- `docs/project-implementation-plan.md`
- `docs/backlog.md`
- `docs/status.md`
- `docs/product-surface-strategy.md`
- `docs/production-readiness-strategy.md`
- `docs/market-data-strategy.md`
- `docs/miniapp-readonly-data-boundary.md`
- `docs/latest-system-run-storage-topology.md`
- `docs/latest-system-runs-repository-contract.md`
- `docs/railway-service-variables.md`
- `docs/operator-runbook.md`
- `docs/post-deploy-acceptance-checklist.md`

## Mini App UI long-term wording standards (Step 133+)
- Mini App UI must use **Traditional Chinese** as primary language.
- English may be shown only as secondary/helper text.
- Main user-facing copy must be simple enough for approximately Primary 5 readers.
- Technical terms must be hidden behind collapsible `查看技術資料` or explained in simple Chinese.
- Prefer main labels: `當時資料` `現在結果` `盈虧變化` `資料不足` `資料可能過舊` `只供模擬檢視`.
- Do not use raw internal labels as main UX text (for example: `outcome_delta`, `snapshot_json`, `latest_run_id`, `stale_do_not_use_for_intraday`, `normalized payload`).
- If technical IDs/status are needed, place them in collapsed technical details only.

### Required Outcome Review UI states
- Loading: `正在載入後續結果...`
- Empty: `暫時未有已保存的決策紀錄。`
- Success: `已載入最近 5 條決策結果。`
- Partial/insufficient: `已有決策紀錄，但資料不足，暫時未能計算結果。`
- Error: `暫時未能載入，請稍後再試。`
- Stale warning: `資料可能過舊，請勿用作即時判斷。`

### Hard safety wording
- `只供模擬檢視`
- `不建立訂單`
- `不連接券商`
- `不是真實買賣建議`

### Prohibited execution-implying UI labels
- Buy now
- Sell now
- Execute
- Order
- Trade action

## Step 134A AI Team Operating Model summary (mandatory)
- AI team operating model is docs-of-record in `docs/ai-team-operating-model.md`.
- All PRs must preserve role boundaries across data/research/strategy/decision/governance/human layers.
- PRs must not bypass AI team boundaries (especially paper-only, no broker/live/order behavior).
- Reusable Mini App and Telegram UI wording/safety rules remain governed by docs-of-record and must stay aligned.

## Documentation capture cross-reference
- Follow `docs/documentation-governance.md` for source-of-truth and Documentation Capture Check requirements.
- Any decisions affecting product/architecture/UI/security/review process must be captured in docs-of-record before approval.
