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


## Step 112 UX bundle update (Daily Overview operator clarity)
- Daily Overview now separates `System Run Status` and `Daily Review Coverage` to avoid interpretation conflict.
- Availability display uses explicit labels (`已載入`, `未有資料`, `部分完成`) and does not treat missing PnL/risk as run failure.
- Signal section keeps simulated stock-level detail while warning that unknown confidence/risk/PnL means incomplete decision context.
- Safety boundary is layered: short top banner + detailed bottom guardrail section; no broker/live execution wording introduced.

## Step 113 consistency patch (Daily Overview availability + render acceptance)
- Daily Summary availability chips must align with actually rendered sections in the same payload context.
- If `signals_summary.status=ok`, Daily Summary must not simultaneously show `信號摘要` inside `未有資料`.
- Missing `paper_pnl` / `risk` remains explicit `未有資料` and must not be interpreted as system failure.
- Mobile-first polish keeps status labels/chips visually tighter and reduces `HKT` orphan wrapping risk in timestamp rows.

## Step 114 Mini App freshness visibility policy
- Mini App review surface includes low-profile non-secret build metadata (`UI build`, `Deployed build`) for deploy freshness validation during Telegram/WebView smoke.

## Step 115 read-only bundle update
- Daily Overview now extends read-only review coverage to include **Paper PnL / 模擬盈虧** and **Risk Summary / 風險摘要** cards.
- `未有資料` for PnL/risk means source not available yet (not runtime failure), and must not be interpreted as latest run failure.
- Risk/PnL display remains review-only paper-trading context; no order placement, no broker integration, no live-money execution semantics.
- Runtime config injection remains frontend read-only (`/config.js`) and must not include secrets/initData/allowlist identifiers.
- Static hosting cache posture for `index.html` and `config.js` is revalidation-oriented to reduce stale shell/config risk after deploy.

## Step 116 Daily Review dashboard completion (read-only UX polish)
- `Daily Review Coverage` copy policy:
  - `ready`: `今日主要檢視區塊已載入；內容只供模擬交易檢視及決策支援。`
  - `partial`: keep existing non-failure interpretation copy.
  - `unavailable`: `每日檢視暫時未完整載入；請先檢查最新系統運行狀態。`
- `每日檢視摘要` missing section policy:
  - if no missing sections, do not render empty `未有資料` chip area; show neutral `暫無缺失區塊`.
  - if missing sections exist, render bounded chips.
- PnL/Risk cards remain read-only paper-review evidence surfaces only; wording must not imply real-money execution or trade instruction.

## Step 117 product surface update
- Mini App adds bounded Human Paper Decision Journal form with non-execution submit wording.

## Step 118 Mini App journal UX policy update
- Journal interaction is Chinese-first with explicit paper-only guardrail copy and no execution wording.
- Ticker path is monitored signal picker first, not manual free-text-first.
- Decision Context Pack is bounded and must show explicit missing-context checklist to prevent over-interpretation as full investment recommendation.

- Step 119: selected ticker Decision Context Pack now includes grouped Signal / Market Data / Paper Position-PnL / Risk / Missing Context with explicit completeness wording (not trade readiness).

## 2026-05-10 — Step 120 Mini App IA redesign
- Step 119 post-deploy smoke passed with build 7f5c5d6 (baseline).
- Mini App shifted from single long scroll to segmented tabs: 今日/信號/Context/Journal.
- Decision Context readiness semantics tightened to conservative labels (insufficient/basic/partial; unknown=>不足) and current no-market-data state is 不足.
- Missing Context now Chinese-first labels; no raw internal English-only keys in UI-facing payload.
- Current system still lacks canonical market data source; market data may remain unavailable/unknown.
- No vendor integration, no broker/live/real-money execution, no order/simulated-order creation, no Supabase schema migration, no Telegram auth change.


### Step 124 product-surface impact
- Mini App Decision Context remains read-only and paper-review-only; market section now may show bounded vendor-backed fields when provider is enabled.
- Unavailable-safe behavior remains default when provider/token is absent or vendor call fails.
- No broker integration, no live/real-money execution, no order/simulated-order creation, no autonomous execution.

## 2026-05-10 — Step 125 Mobile Operator Market Data Smoke
- Step 124 merged; Android operator cannot run CLI smoke locally.
- Added /market_smoke (0700.HK/0388.HK/1299.HK) as allowlist-protected, read-only diagnostics command with sanitized bounded snapshot output only.
- Mini App Context tab now shows market smoke diagnostics status/source/timestamp/freshness/delay/limitations from backend review-shell payload only.
- Security/domain boundary preserved: no frontend vendor key, no raw EODHD token/payload exposure, no broker/live/real-money execution, no order/simulated-order creation.
- EODHD remains first vendor candidate, not final production vendor commitment.


## Step 126 — Market Data Freshness + Operator Formatting Bundle (2026-05-10)
- Step 125 post-deploy smoke passed for 0700.HK / 0388.HK / 1299.HK; EODHD backend-only path returned status=ok with bounded fields and timestamp evidence.
- EODHD remains first vendor candidate only, not final production-grade commitment.
- Step 126 adds conservative freshness semantics (`fresh`, `delayed`, `last_available_close`, `stale`, `unknown`) and operator-facing warnings so delayed/last-available data is not interpreted as live data.
- Telegram `/market_smoke` now formats price/percent/volume/timestamp/freshness for readability with Chinese-first freshness labeling and caution wording.
- Mini App Context market section now displays formatted values and freshness warnings for `last_available_close`/`stale`/`unknown` using backend payload only.
- Boundaries unchanged: read-only diagnostics + decision support, paper trading only, no broker/live execution, no real-money execution, no order or simulated-order creation, no frontend vendor key, no token/raw vendor payload exposure, no fake data.

## Step 127 product-surface increment
- Mini App Context/Daily Review semantics now expose market-data acceptance in Chinese-first wording so operator can quickly judge if ticker market data is acceptable for daily paper review.
- Telegram `/daily_review` now adds bounded acceptance summary fields without creating a new large command surface.
- No change to paper-only boundary: no broker/live execution/real-money order semantics.

- Step 129 update (in progress): operator surfaces are expanding with ticker-level paper portfolio review (read-only) to support per-stock exposure/PnL scan without adding any order or broker action.
