# Product Surface Strategy (Step 92D-UX System-of-Record)

## Goal
Document the current Telegram + Mini App product-surface strategy before Step 92E expansion, with explicit UI wording and paper-trading boundary guardrails.

## Current state summary (Step 92C / 92C-1 / 92D completed)
- Telegram command `/latest_system_run` is available for quick operator read-only checks.
- Mini App has backend-authenticated read-only cards for:
  - Latest System Run
  - Daily Review Summary
- Step 92C / 92C-1 / 92D post-deploy smoke path is already completed and passed.
- Product direction is now beyond Telegram-only and uses split surfaces by responsibility.

## Surface responsibility split

### Telegram Bot (short, fast, operational)
Use Telegram for:
- short alerts
- quick commands
- deploy/runtime smoke checks
- short summaries
- link-out to Mini App

Telegram should **not** carry:
- dense multi-stock tables
- long-form review content
- complex multi-section analysis that is better reviewed in structured UI

### Mini App (structured review surface by phase)
Currently available (completed):
- Latest System Run
- Daily Review Summary

Planned read-only next (Step 92E+ sequence):
- Signals Summary
- Risk Summary
- Paper PnL
- Outcome Review

Future phase (not yet implemented):
- AI Team Review
- Decision Journal
- Decision capture
- Controlled simulated order creation

Mini App should **not**:
- replace Telegram alerting
- expose secrets/raw Telegram `initData`
- use direct frontend Supabase privileged access

## Surface responsibility matrix
| Capability | Telegram | Mini App |
|---|---|---|
| Short alert / quick status ping | Primary | Secondary |
| Quick command interaction | Primary | Secondary |
| Deploy/runtime smoke path | Primary | Secondary |
| Structured daily review (Latest System Run / Daily Review Summary) | Link-out only | Primary (current) |
| Multi-section read-only review | Not recommended | Primary (expands in Step 92E+) |
| Dense multi-stock comparison | Not recommended | Primary |
| Decision journal review surface | Secondary (shortcut only) | Future phase |

## Mini App information architecture

### Option A — Card List Layout (adopt now)
- Phase: current read-only Phase 1.
- Pattern: vertically stacked cards.
- Reason: best fit for Telegram Mini App mobile viewport and low cognitive load.

### Option B — Dashboard + Tabs (prepare for medium-term)
- Introduce after section count increases.
- Proposed tabs:
  - 總覽
  - 信號
  - 風險
  - 模擬倉
  - 回顧

### Option C — Guided Review Flow (defer)
- Use later in decision-capture phase.
- Step-by-step review flow for operator decision journaling.

### Current decision
- Adopt **Option A** now.
- Prepare docs and transition path for **Option B**.
- Defer **Option C** until decision-capture phase is explicitly approved.

## Standard Mini App home card order
1. 今日總覽 / Daily Overview
2. Latest System Run / 系統運行狀態
3. Daily Review Summary / 每日檢視摘要
4. Signals Summary / 信號摘要
5. Risk Summary / 風險摘要
6. Paper PnL / 模擬盈虧
7. Decision Journal / 決策紀錄
8. Outcome Review / 結果回顧

## Mini App UI/UX wording principles
- User-facing display language must be primarily **Traditional Chinese**.
- English may be used only for widely understood technical labels (for example `HKT`, `Paper Trading`).
- UI text must be understandable for non-technical operators.
- Prefer user-facing labels over raw backend keys.

### Label translation examples
- `paper_trade_only` -> `交易模式：只限模擬（Paper Trading）`
- `review_readiness=partial` -> `檢視狀態：部分完成`
- `data_timestamp_hkt` -> `資料時間（香港時間）`
- `updated_at_hkt` -> `更新時間（香港時間）`

### Card-level readability rule (every card must answer)
1. Current status
2. What it means
3. What the operator should review next

### Domain boundary wording rule (every page/card)
- Must explicitly preserve paper-trading / decision-support-only boundary.
- Must not imply broker connection, live order placement, or autonomous real-money behavior.

## Standard status wording map (backend value -> display)
- `ready` -> `已準備好`
- `partial` -> `部分完成`
- `unavailable` -> `暫時未有資料`
- `success` -> `成功`
- `failed` -> `失敗`
- `unknown` -> `未知`
- `true` -> `是`
- `false` -> `否`


## Phased release roadmap (aligned with responsibility split)
### Phase 1 — Read-only review shell (current)
- Keep review surfaces read-only and paper-trading labeled.
- No decision write path, no order creation, no broker/live execution.

### Phase 2 — Decision capture (future, bounded)
- Add bounded human paper decision journal capture only.
- Keep execution boundary explicit: no broker/live execution.

### Phase 3 — AI team paper decision review (future)
- Add richer review and discussion surfaces for simulated decision quality.
- Keep outputs as decision-support evidence only.

### Phase 4 — Controlled simulated order creation (future, gated)
- Allow only controlled simulated-order creation after risk-gate + metadata completeness checks.
- Required fields remain: `strategy_version`, `data_source`, `data_timestamp`, `risk_check`, `paper_trade_only=true`.

## Security and boundary reminders
- Mini App frontend must never hold Supabase service/secret keys.
- Telegram `initData` validation must remain backend-side before data access.
- Backend writes/privileged reads after RLS must use backend secret/service-role key class only.
- No product surface may introduce broker/live execution semantics.

## Step 92F-UI surface update (Mini App read-only UX)
- Mini App current read-only surface is now mobile-first professional card dashboard with Traditional Chinese primary wording.
- Card sequence follows current strategy: 今日檢視 -> 最新系統運行 -> 每日檢視摘要 -> 信號摘要 -> 安全與邊界說明.
- This step is presentation-only: no new product capability, no decision capture, no write/order/execution semantics.
