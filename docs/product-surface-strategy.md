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

- Step 131: Journal submit now persists bounded decision context snapshot (including market freshness/acceptance + paper position/PnL/risk context) and reports journal/snapshot save status separately.
- Step 131A: Journal surface wording now explicitly marks `paper_buy`/`paper_sell` as journal labels only (no simulated order, no position mutation, no broker connection).
- Step 131B: Journal save result UX now prioritizes submit-adjacent persistent inline result card (with saved identifiers + paper-only guardrail wording), while optional toast is secondary feedback only.

- Added product slice: Recent Journal Snapshots review surface in Journal tab (read-only list, no edit/delete/order).

- Added Journal Outcome Link surface: Mini App Journal tab now includes read-only "後續結果 / Outcome Link" cards sourced from backend `/miniapp/api/journal-outcomes`; Telegram adds `/journal_outcome` bounded summary command.

## Step 133+ Mini App Outcome Review wording contract (long-term)
- Traditional Chinese is the primary UX language; English is helper-only.
- Main card copy must stay simple/readable for non-technical users (Primary-5-level target).
- Outcome Review primary labels should prefer: `當時資料`, `現在結果`, `盈虧變化`, `資料不足`, `資料可能過舊`, `只供模擬檢視`.
- Raw internal labels must not be first-layer UX text.
- Technical identifiers/statuses may appear only in collapsed `查看技術資料`.
- Maintain explicit UI states:
  - `正在載入後續結果...`
  - `暫時未有已保存的決策紀錄。`
  - `已載入最近 5 條決策結果。`
  - `已有決策紀錄，但資料不足，暫時未能計算結果。`
  - `暫時未能載入，請稍後再試。`
  - `資料可能過舊，請勿用作即時判斷。`
- Safety wording must remain visible in the outcome surface:
  - `只供模擬檢視` / `不建立訂單` / `不連接券商` / `不是真實買賣建議`.
- Do not use execution-implying words (`Buy now`, `Sell now`, `Execute`, `Order`, `Trade action`).

## Step 134A future Mini App surface map (AI Team Workbench)
Planned user-facing surfaces (Chinese primary, English helper):
1. 今日簡報 / Daily Brief
2. AI 觀察名單 / AI Watchlist
3. 股票檢視 / Stock Review
4. 決策日誌 / Journal
5. 回顧 / Review
6. 策略回顧 / Strategy Review
7. AI 團隊 / AI Team

All surfaces remain read/review-first and paper-only unless a later explicit gated step approves bounded write/simulation actions.

- Step 134B Mini App first-layer: 今日頁以「Daily Brief + AI Team role UI」為首層工作台，先回答「今日 AI 團隊發現咩、資料夠唔夠、風險、模擬方向、人類下一步」，技術細節後置於「查看技術資料」。

- Step 134C: Mini App first layer (`今日簡報 / Daily Brief`) should prefer backend bounded `sections.daily_brief` contract; frontend fallback is allowed only when section is unavailable. Keep technical fields in `查看技術資料` and keep paper-only/no-broker wording.


## 2026-05-12 — Step 135A AI Team Analysis Blueprint surface policy
- Mini App/Telegram first-layer analysis wording must stay Traditional Chinese + non-professional friendly, with conclusion/risk/next action understandable within ~10 seconds.
- Professional analysis depth is allowed internally, but technical fields must be placed under `查看技術資料`.
- Stock dossier first-layer should prioritize: `headline_summary`, `data_sufficiency`, `risk_brief`, `simulated_direction`, `operator_next_actions`, and `safety_note`.
- Safety wording remains mandatory: `只供模擬檢視` / `不建立訂單` / `不連接券商` / `不是真實買賣建議`.
- Boundaries unchanged: no broker/live execution, no real-money order creation, no autonomous execution.

## Step 135B Stock Review surface policy
- Add a bounded `股票檢視 / Stock Review` shell for non-professional operators.
- First-layer wording remains simple Traditional Chinese and paper-only (`AI 模擬方向`, `只供模擬檢視`).
- Technical source/status/timestamps/internal fields must stay under `查看技術資料`.
- This surface is read-only and must not imply or enable execution/order behavior.

## Step 135C Stock Review readability polish policy
- Stock Review first-layer must present fixed human-readable labels in Traditional Chinese:
  `一句總結`, `資料夠唔夠`, `技術觀察`, `基本面觀察`, `新聞 / 催化觀察`, `風險提示`, `模擬組合背景`, `AI 模擬方向`, `你下一步要做咩`.
- Empty state wording uses: `暫時未有可檢視的股票簡報。系統會在有 signals / risk / portfolio context 後顯示。`
- If static helper text is shown for simulated direction, use:
  `AI 模擬方向只分為：偏正面觀察、繼續觀察、謹慎、資料不足。只供模擬檢視。`
- Technical/internal/raw fields continue to stay under collapsed `查看技術資料` only.

## Step 135D strategy research reference alignment (docs-only)
- Added long-term research reference: `docs/hk-equity-strategy-research-reference-20260512.md`.
- Canonical implementation phase numbering remains defined in `docs/ai-team-analysis-blueprint.md`; Step 135D reference provides strategy workstreams only.
- Product surface interpretation now follows explicit horizon policy: short-term=observation/alert only, medium/long-term=primary review scope in current phase.
- Stock Dossier / AI Decision Advisor copy must remain multi-dimensional (data quality, technical, fundamental, catalyst, risk, liquidity, exposure, confidence, simulated direction) and avoid one magic total score.
- Safety boundary unchanged: paper-only decision support (`只供模擬檢視`, `不建立訂單`, `不連接券商`, `不是真實買賣建議`), no broker/live-order semantics.

## Step 135E next increment note (Stock Review)
- Next Stock Review product increment candidate is **Step 135E — Strategy Horizon Policy in Stock Dossier**.
- UI/policy direction for this increment:
  - strategy horizon policy display in Stock Review read-only layer,
  - short-term horizon remains monitoring/alert/observation only,
  - medium/long-term horizons remain current review focus,
  - first-layer UI remains compact and non-technical for operators.
- Existing rules remain unchanged:
  - Mini App main wording stays Traditional Chinese first (English only secondary/helper),
  - paper-only / decision-support boundary remains explicit,
  - no broker connection, no live order placement, no autonomous real-money execution.

- Step 135E: Strategy Horizon Policy in Stock Dossier added deterministic horizon fields (recommended_review_horizon, short/medium/long policies, data states, data gaps, confidence notes, paper_decision_scope) and Stock Review "策略週期判斷" UI section; short-term remains monitoring/observation-only; no broker/order/live/real-money path.
- Step 135F: Stock Review first-layer is calibrated to fixed order:
  1) 一句總結 2) 資料夠唔夠 3) 策略週期判斷 4) 風險提示 5) AI 模擬方向 6) 你下一步要做咩 7) 查看技術資料。
- Step 135F horizon wording policy:
  - short-term stays observation-only (`短線只供監察 / 提示 / 觀察，不建立任何模擬或真實訂單`);
  - medium-term sufficiency cannot be inferred from global status alone and must keep ticker-context-aware missing-gap summary;
  - long-term first-layer uses compact human summary (`長線資料不足：缺少基本面 / 估值 / 現金流等資料`), with detailed fields under technical details.

## 2026-05-13 — Step 135G first-view IA contract
- Today (今日) default first-screen keeps one primary hero summary card only.
- Hero must include: 今日狀態/一句總結/資料夠唔夠/主要風險/AI 模擬方向/你下一步要做咩 + short safety boundary.
- Secondary responsibility split:
  - 股票檢視: Stock Review first-layer contract from Step 135F.
  - 模擬組合: full paper PnL + risk breakdown.
  - 日誌: human paper decision journal/outcome review surfaces.
  - 系統: Latest System Run, Daily Review Summary, signals/context diagnostics, build metadata visibility.
- Boundary unchanged: read-only/paper-only decision support; no broker/live/order/real-money execution.


## Mini App First-View Contract (Step 135G-DOC)
- Mini App is an AI HK equity review workspace, not a dense dashboard, broker dashboard, trading terminal, or execution console.
- Default first screen must show one primary operator decision-support summary before secondary/technical cards:
  1. 今日狀態
  2. 一句總結
  3. 資料夠唔夠
  4. 主要風險
  5. AI 模擬方向
  6. 你下一步要做咩
  7. short paper-only boundary
- Secondary data may exist but must be moved to secondary tabs or collapsed details:
  - Latest System Run
  - build metadata
  - market smoke diagnostics
  - raw source/timestamps
  - detailed PnL/risk breakdown
  - long AI team explanation
  - technical/internal fields
- First-view must be Traditional Chinese first and understandable for non-technical operators.
- Technical/internal/raw fields belong under 查看技術資料 / 系統資料 / secondary tabs.
- Advice/data/details can remain accessible; they must not dominate the first image / first screen.

## Forbidden UI direction
Do not let Mini App become:
- dense dashboard
- broker dashboard
- live trading terminal
- autonomous AI execution console

Forbidden or restricted wording:
- Buy now
- Sell now
- Execute
- Order
- Trade action
- AI final decision
- Autonomous trading
- 真實落盤
- 立即買入 / 立即賣出

Allowed safer wording:
- AI 模擬方向
- 只供模擬檢視
- 人手覆核
- 你下一步要做咩
- 暫時只觀察
- 不建立訂單
- 不連接券商
- 不是真實買賣建議

## 2026-05-13 — Step 135I Mini App Operator workflow final contract
- Each tab has one primary job: Today=今日先看什麼；Stock Review=單一股票是否繼續檢視；Portfolio/Risk=paper exposure/risk interpretation；Journal=新增人手模擬決策；System=診斷/技術/完整安全說明。
- First layer is summary-first; historical/raw/technical/outcome content must be collapsed or moved to System/secondary sections.
- Stock Review first layer must remain compact: `檢視結論` `策略週期` `主要缺口` `風險提示` `AI 模擬方向` `下一步`.
- Journal default is create-first: form expanded; `決策參考資料` `最近紀錄` `後續結果` collapsed/de-emphasized by default.
- Loaded-state and sufficiency must stay separated: `已載入` does not mean `可安全判斷`.
- Full safety details belong to System/collapsed area; short safety boundary stays globally visible.
- This step defines final operator workflow baseline to avoid repeated micro-fix UI cycles on the same first-view issue set.
