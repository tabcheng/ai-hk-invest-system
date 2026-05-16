# Post-deploy Acceptance Checklist (Step 66)

## Purpose
This checklist is the post-deploy/manual-acceptance gate for PRs that touch runtime, Telegram operator flow, database persistence, paper-trading support surfaces, and related deployment configuration.

After Step 66, every relevant PR must explicitly state which checklist sections apply and provide evidence before acceptance is marked PASS.

## A. All PRs
- [ ] GitHub CI is PASS.
- [ ] PR scope matches the currently approved step scope (no unauthorized scope expansion).
- [ ] `docs/status.md` is updated with current step state and acceptance status wording.
- [ ] `docs/backlog.md` is updated when new non-blocking follow-up work is discovered.
- [ ] No premature post-merge PASS wording is written before actual manual acceptance/review is completed.
- [ ] Docs-only PRs normally require GitHub CI + review only, unless docs changes also modify workflow/runtime expectations.

## B. Telegram / Operator PRs
- [ ] Operator Smoke Test is executed after merge/deploy.
- [ ] Workflow run link is captured in review evidence.
- [ ] Smoke-test artifact/report is reviewed.
- [ ] Overall smoke-test result is PASS.
- [ ] `response_text_verification` limitation is explicitly understood/acknowledged unless a future test-mode echo contract is introduced.

## C. Supabase / Persistence PRs
- [ ] `verify_supabase=true` is required when DB persistence behavior is touched.
- [ ] Supabase verification status is PASS.
- [ ] Matched row count and QA marker are checked where applicable.
- [ ] `SUPABASE_URL` and backend key vars (`SUPABASE_SECRET_KEY` preferred; `SUPABASE_SERVICE_ROLE_KEY` allowed) remain backend secret stores only.
- [ ] `SUPABASE_KEY` is treated as transitional fallback only (not preferred active runtime dependency).
- [ ] No secrets appear in logs, reports, docs, or source code.

## D. Railway / Deployment PRs
- [ ] Railway deployment is completed before production smoke test starts.
- [ ] No unexpected changes in service topology, cron, env vars, or webhook routing.
- [ ] If Railway settings changed, document exact setting changes and rollback notes.
- [ ] Affected backend services are explicitly reviewed (`paper-daily-runner`, `telegram-webhook` when Supabase path applies, and any scheduled/smoke backend service using production Supabase data).
- [ ] `miniapp-static-preview` remains free of `SUPABASE_SECRET_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_KEY`.
- [ ] No `SUPABASE_KEY` fallback warning appears when `SUPABASE_SECRET_KEY` is configured.

## E. Domain Guardrail
- [ ] No broker integration.
- [ ] No live-money order flow.
- [ ] No autonomous real execution.
- [ ] System remains paper-trading / decision-support only.
- [ ] Human final decision authority is preserved.
- [ ] Strategy or calculation changes receive stricter review before acceptance.

## F. Evidence to paste back for review
- PR link.
- Workflow run link.
- Artifact/report status.
- Railway deployment status (if relevant).
- Supabase verification result (if relevant).

## G. RLS Runtime Acceptance Check (Step 91A)
- [ ] backend key corrected to secret-class before runner test: yes/no
- [ ] Current publishable-class key corrected before Step 92: yes/no
- [ ] Railway redeploy completed after key correction: yes/no
- [ ] paper-daily-runner DB write acceptance passed: yes/no
- [ ] paper-daily-runner latest run completed after RLS enabled: yes/no
- [ ] runs table insert/update observed: yes/no
- [ ] signals upsert/update observed: yes/no
- [ ] decision ledger / paper trading writes observed if applicable: yes/no/not applicable
- [ ] Telegram notification still works: yes/no
- [ ] Mini App API smoke still passes: yes/no
- [ ] no service key exposed in Mini App static preview: yes/no
- [ ] no service key logged: yes/no
- [ ] no anon/publishable key used for backend writes: yes/no
- [ ] issues / errors:

Step 91A recorded result (PR #88):
- platform key correction completed: yes
- RLS runtime acceptance completed: yes

## Step 91C runtime acceptance automation note
- GitHub Step 91C acceptance workflow can reduce manual checks by generating structured smoke evidence artifacts for reviewer validation.
- Full acceptance still requires Railway log evidence or a future Railway API/CLI integration for fallback-warning verification.
- Mini App smoke endpoint URL is read from GitHub Actions environment variable context (`vars.MINIAPP_SMOKE_ENDPOINT_URL`) under `production-smoke`.
- Mini App smoke bot token and Telegram smoke user IDs must remain GitHub Actions environment secrets.
- Confirm Mini App frontend/static preview never contains `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `SUPABASE_KEY`.
- Confirm no broker integration and no live-money execution path is introduced.
- Step 91C aggregate pass rule: required gates (`preflight`, key class, operator smoke, miniapp smoke, `runs`, `signals`) must all be `PASS`; stale required rows are `FAIL`.
- Step 91C optional checks policy: optional tables may be `NOT_CONFIGURED`, but optional check `FAIL/INVALID` is blocking and must be resolved before acceptance.

## Step 91C-2 Railway evidence artifact check
- Runtime acceptance now optionally collects read-only Railway log evidence (`railway_step91c_log_evidence_report.{md,json}`).
- Expected fallback warning status: `PASS`/`FAIL` when configured, otherwise `NOT_CONFIGURED` (never fake PASS).
- Workflow console prints a safe summary line only (`overall_status`, `fallback_warning_check`, `logs_read_count`, `railway_api_http_status`, `railway_api_error_kind`, `limitation`); no raw logs or secrets should be printed.
- This evidence step must not mutate Railway variables and must not redeploy services.
- Optional endpoint override: `RAILWAY_API_URL` (from GitHub Actions vars) can be set when default endpoint is unsuitable.
- HTTPError diagnostics policy:
  - `401/403` likely token scope/workspace mismatch.
  - `400/422` likely GraphQL query/schema mismatch.
  - inspect `railway_api_error_excerpt_redacted` only (redacted, bounded excerpt; no token/raw logs).
- Connectivity probe policy: `me { email }` is account-token only; workspace/project token runs should keep connectivity as `NOT_RUN` with reason (for example `workspace_probe_not_configured`) unless explicitly switched to account probe mode.

- Step 91C-2 note: `staged_changes_check` remains `NOT_CONFIGURED` in this step (no staged-changes automation yet); scope is still read-only evidence only with no variable mutation/redeploy/staged-change commit.


### Step 91C-5 check additions
- Confirm report field `railway_log_query_mode=environment` by default.
- Confirm report field `railway_query_stage=environment_logs` for 4xx diagnostics (`403/400/422`).
- If `logs_read_count > 0` and no fallback-warning matches, accept `fallback_warning_check=PASS`.
- If configured but `logs_read_count=0`, treat Railway evidence as `FAIL` and record limitation explicitly.

- For Step 91C environment mode, `RAILWAY_LOG_SERVICE_IDS` is required; missing IDs must produce Railway evidence `FAIL` (no unfiltered environment scan).
- Treat `RAILWAY_LOG_SERVICE_NAMES` as display-only labels.

- Step 91C-6: 若 Step91C workflow 出現 Railway 403，先檢查 `railway_api_probe_report`：
  - metadata 403 => token/secret/project access 問題；
  - metadata PASS + environmentLogs 403 => logs endpoint/query-specific 權限問題；
  - metadata PASS + ID missing => vars 配置錯誤；
  - environmentLogs PASS + evidence FAIL => log window/fallback-warning 路徑問題。
- Railway diagnostics artifact 必須保持 read-only，不得輸出 token 或 raw logs。


### Step 91C-7A check additions
- 若本機 curl/GraphiQL 成功但 GitHub Actions 失敗，必查 `railway_api_probe_report`：
  - `token_fingerprint_expected_configured` / `token_fingerprint_match`
  - `account_probe_status` (urllib)
  - `curl_account_probe_status`（僅當 `RAILWAY_CURL_PROBE=on`）
- 判讀：
  - fingerprint mismatch => 優先判定為 GitHub runner secret mismatch。
  - urllib FAIL + curl PASS => 偏向 Python urllib/request-shape 差異。
  - urllib FAIL + curl FAIL => 偏向 runner-edge/token-permission 問題。
- 保持 secret-safe：不得在 artifact/chat/docs 粘貼 token 或 raw logs；只使用 redacted/summary fields。


## Step 92A-S1 Manual Post-merge Smoke (latest_system_runs)
- Trigger only via GitHub Actions `workflow_dispatch` (`.github/workflows/step92a-post-merge-smoke.yml`).
- Keep outputs secret-safe and summary-only; do not print raw keys/tokens/initData/allowlist values.
- Validate `latest_system_runs` table/index/RLS/row-contract evidence via service-role-only RPC (`/rest/v1/rpc/step92a_latest_system_runs_contract_evidence`) and capture safe selected fields only.
- Optional `run_paper_daily_runner=true` is best-effort and must not force failed terminal status solely due to write-path best-effort behavior.
- Confirm no Railway topology mutation, no deploy/redeploy, no variable mutation, and no broker/live execution behavior.

## Step 92B Telegram latest-system-run smoke
- [ ] Deploy `telegram-webhook` runtime (if code changed).
- [ ] Trigger `/latest_system_run` from allowlisted operator chat/user.
- [ ] Verify response includes `data_timestamp_hkt` and `updated_at_hkt` (HKT display boundary).
- [ ] Verify raw labels `data_timestamp` and `updated_at` are not shown in operator-facing output.
- [ ] Verify response shows bounded latest row fields only (no secrets/raw errors).
- [ ] Verify `latest_system_runs.updated_at` refreshes after upsert (freshness ambiguity removed).
- [ ] Verify missing-row fallback and safe internal-error fallback behavior.
- [ ] Verify no broker/live execution language or behavior is introduced.
- Step 92C: Mini App now fetches backend POST /miniapp/api/review-shell and displays read-only latest_system_run card from latest_system_runs with server-side initData validation + operator allowlist authorization + HKT display fields only; no frontend Supabase direct read/write, no decision capture/order creation/broker/live execution.
- Step 92C routing note: Mini App static frontend must use non-secret MINIAPP_API_BASE_URL (telegram-webhook public URL) when frontend/backend are different origins; same-origin default is local/dev only.
- Step 92C-1: miniapp-static-preview must provide non-secret `MINIAPP_API_BASE_URL` (telegram-webhook public URL) through runtime `/config.js` injection; Railway variable changes require deploy for effect.
- Step 92C-1: telegram-webhook must set `MINIAPP_ALLOWED_ORIGIN` to exact miniapp-static-preview public origin to allow cross-origin `POST/OPTIONS /miniapp/api/review-shell` while keeping server-side initData validation + operator allowlist and paper-trading/no-broker boundaries unchanged.
- Step 92C-1 deploy-risk reminder: verify Railway `miniapp-static-preview` is configured to build using `miniapp/Dockerfile` (or equivalent Dockerfile path). Adding Dockerfile to repo alone does not enable runtime `/config.js` injection.
- Step 92C-1 deploy-risk reminder: if deployment still uses old static/Caddy path without Dockerfile startup flow, `/config.js` injection will not work.
- Step 92D post-deploy smoke required: verify Mini App still shows Latest System Run card and now shows Daily Review Summary card with HKT-only timestamp labels; confirm `paper_trade_only=true`; confirm no raw `data_timestamp` / `updated_at` labels and no secrets/raw initData/allowlist/chat/user IDs exposed; confirm no write path/decision capture/order creation/broker/live execution.

- Step 92E: Mini App 新增「信號摘要」read-only card，信號僅作 AI 模擬／paper-trading 檢視證據，不構成買賣指示；前端開始統一以繁體中文顯示標籤（後端 snake_case 合約保留）；無 schema/migration、無寫入路徑、無決策提交、無下單、無 broker/live execution。

## Step 92F-UI Post-deploy smoke (required)
- [ ] Deploy `miniapp-static-preview`.
- [ ] Deploy `telegram-webhook` only if backend changed (Step 92F-UI pure frontend normally no backend deploy).
- [ ] Confirm `miniapp-static-preview` build path仍使用 `miniapp/Dockerfile`.
- [ ] Confirm runtime `/config.js` 注入的 `MINIAPP_API_BASE_URL` 指向 telegram-webhook public URL.
- [ ] Telegram 內開啟 Mini App，確認單欄手機介面且無水平捲動。
- [ ] 確認 `今日檢視` 在最上方。
- [ ] 確認 `最新系統運行` / `每日檢視摘要` / `信號摘要` 為清晰分離卡片。
- [ ] 確認 status chip 以繁中顯示（例如 成功/部分完成/暫時未有資料）。
- [ ] 確認指標欄位可讀，且不顯示 raw snake_case 作為前台標籤。
- [ ] 確認 signal `top_items` 為多列項目顯示，不是單段長文。
- [ ] 確認顯示為 HKT 欄位語意，並保留「模擬/非買賣指示」邊界文字。
- [ ] 確認未暴露 secrets、raw initData、allowlist/chat/user IDs。
- [ ] 確認無 write path / decision capture / order creation / broker/live execution。

## Step 116 Post-deploy smoke (required)
- [ ] 確認 `UI build` 與 `Deployed build` 可見，且與本次 merge commit 一致。
- [ ] 確認 `Daily Review Coverage=已準備好` 時顯示 ready copy（不是 partial copy）。
- [ ] 確認 `每日檢視摘要` 在無缺失區塊時不顯示空白 missing chip area（可見 `暫無缺失區塊`）。
- [ ] 確認 PnL 卡有 Paper/模擬語境（非真實戶口語意），且有貨幣/資料時間（如資料提供）。
- [ ] 確認 Risk 卡有 review-only 語境；warnings 空時顯示中性文案 `暫無風險警示`。
- [ ] 確認安全邊界說明仍可見。
- [ ] 確認無 broker/live execution/real-money/order/submit 文案。

## Step 117 post-deploy smoke additions
- Verify journal section visible, guardrail checkbox required, and valid submit returns bounded success or bounded unavailable.

## Step 118 post-deploy smoke (required)
- [ ] Confirm `UI build` and `Deployed build` match merge commit.
- [ ] Confirm journal section title is Chinese-first and field labels are Chinese-first with optional English auxiliary.
- [ ] Confirm ticker picker uses monitored signal tickers (`signals_summary.top_items`) and shows disabled/no-data state when unavailable.
- [ ] Confirm selecting ticker updates Decision Context Pack.
- [ ] Confirm Decision Context Pack includes signal reason + missing-context checklist + insufficient-data warning.
- [ ] Confirm rationale placeholder is Chinese and does not invite real trade instruction.
- [ ] Confirm guardrail checkbox remains required.
- [ ] Confirm submit button text is `記錄人手模擬決策`.
- [ ] Confirm success/error wording remains paper-only/no-order-created.
- [ ] Confirm no broker/live execution/real-money/order creation action wording appears.

- Step 119 add: verify `decision_context_summary` rendered for selected ticker, readiness chip uses `不足/部分/基本`, and no broker/live execution/order wording appears.

## 2026-05-10 — Step 120 Mini App IA redesign
- Step 119 post-deploy smoke passed with build 7f5c5d6 (baseline).
- Mini App shifted from single long scroll to segmented tabs: 今日/信號/Context/Journal.
- Decision Context readiness semantics tightened to conservative labels (insufficient/basic/partial; unknown=>不足) and current no-market-data state is 不足.
- Missing Context now Chinese-first labels; no raw internal English-only keys in UI-facing payload.
- Current system still lacks canonical market data source; market data may remain unavailable/unknown.
- No vendor integration, no broker/live/real-money execution, no order/simulated-order creation, no Supabase schema migration, no Telegram auth change.


### Step 124 post-deploy smoke addendum
- Verify deploy build matches merge commit and Step 123 reference build context `d1df5e8`.
- In `telegram-webhook` service with `MARKET_DATA_PROVIDER=eodhd` and backend-only `EODHD_API_TOKEN`, run smoke for `0700.HK`, `0388.HK`, `1299.HK`.
- Confirm output is sanitized (no token/raw payload) and market status is explicit (`ok/partial/unavailable`).
- Confirm Mini App Context tab updates bounded market fields when available and keeps clear unavailable state when vendor fails.

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


## Step 136C/136D Railway cadence post-deploy evidence fields
For each Railway scheduled service candidate, capture:
- service_name
- run_type
- railway_cron_utc
- intended_hkt_window
- deploy_id_or_timestamp
- run_log_evidence_pointer
- execution_summary.run_type
- smoke_command_or_run_id
- guardrails confirmation (`paper_only=true`, `creates_orders=false`, `broker_connection=false`)
- safety confirmation (no secrets observed, no live/order execution observed)
- operator conclusion (`PASS` / `FAIL` / `BLOCKED`)

## Railway cadence evidence validator usage
- Input: Railway logs JSON export (`--input-json`) and/or plain text logs (`--input-text`).
- Required expected args:
  - `--expected-run-type`
  - `--expected-entrypoint` (default `python -m src.daily_runner`)
  - `--expected-schedule-basis-contains` (recommended)
- Example:
  - `python scripts/railway_cadence_evidence_validate.py --input-json logs.json --expected-run-type midday_market_monitor --expected-schedule-basis-contains "Railway cron UTC: 30 4 * * 1-5" --output-json report.json --output-md report.md`
- Required PASS fields:
  - `status=pass`
  - `execution_status=success`
  - expected/observed run_type match
  - expected entrypoint match
  - completed message present
  - `secrets_observed=false`
  - `broker_live_order_execution_observed=false`
- Redaction rules:
  - Telegram chat id must not appear in report output.
  - Secret-like tokens must not be echoed to report output.
  - Evidence remains manual/operator-provided unless separately marked natural cron evidence.

### Cadence metadata consistency gate (Step 136D-2-FIX)
- `execution_summary.schedule_basis` must match effective `AIHK_RUN_TYPE` cadence mapping.
- Failure classification: `run_type=status success` but `schedule_basis mismatch` = metadata blocker (not platform-success evidence).

## Step 136D accepted manual-equivalent evidence pattern
- `midday_market_monitor`: manual-equivalent smoke pass is acceptable when run metadata, status, entrypoint, schedule basis, and paper result are present and secret-safe.
- `stale_risk_refresh`: manual-equivalent smoke pass is acceptable with the same evidence structure.
- For both cases, duplicate-protection/Telegram dedup behavior in same-date reruns is acceptable if clearly classified as manual-equivalent smoke.

## Natural cron evidence follow-up template
- Record service name, deployment id, run id, UTC start/finish time, run_type, expected UTC cron expression, observed schedule alignment, and secret-safe log summary.

## Step 136H/136I-lite post-deploy smoke additions
- [ ] Confirm `summary_json.ai_team_packet.status=ok` exists in latest `paper_daily_runner` row.
- [ ] Confirm Mini App shows AI Team Packet read-only card with safety labels.
- [ ] Confirm Telegram `/ai_team_packet` returns bounded summary without raw JSON/secrets.
- [ ] Confirm Mini App + Telegram both remain paper-only/decision-support-only/no broker/no live/no real-money/no order creation.


### Step 136J/136K-lite update (2026-05-16)
- AI Team surfaces remain read-only and consume bounded `latest_system_runs.summary_json.ai_team_packet` only.
- Mini App exposes compact `AI 團隊摘要` in Today tab and detailed `AI 團隊摘要 / AI Team Packet` in System tab with deterministic freshness labels (`最新` / `可能過舊` / `未能判斷`) and fail-closed unavailable behavior.
- Telegram `/ai_team_packet` is Chinese-first, bounded, read-only operator summary; no raw JSON, no secret exposure, no journal/order/runner side-effects.
- Guardrails unchanged: paper-only, decision-support-only, no broker connection, no live/real-money execution, no autonomous execution, no order creation; human operator remains final decision-maker outside system.
- Internal MVP Launch Candidate v1 acceptance requires CI green, Railway service success, latest runner row evidence, Mini App AI Team visibility checks, Telegram command checks, and secret-safe outputs.
- LLM/vendor integration remains deferred post-launch unless explicitly approved with backend-only provider abstraction and mock-first acceptance path.
