# Operator Runbook — Telegram Command Output Interpretation (Step 58)

## Scope
- This runbook aligns operator-facing examples with Step 57 normalized wording for:
  - `/runs`
  - `/runner_status`
  - `/risk_review <run_id>`
  - `/pnl_review`
  - `/outcome_review`
  - `/outcome_review <days>`
  - `/daily_review`
- This is review-only guidance for paper-trading decision support; human remains final decision-maker.

## Global interpretation guardrails
- These commands are **read-only** review surfaces; they do not execute live trades or mutate strategy state.
- No-data responses are normal in some windows and should be interpreted as "nothing matched current filter/snapshot", not system failure.
- Invalid-input responses should be corrected and retried using the displayed `Usage:` format.

## Step 57 stock display policy (must follow exactly)
- If stock name is available, display:
  - `stock_name=<name> | stock_id=<id>`
- If stock name is unavailable, display:
  - `stock_id=<id> | name_unavailable`
- Never imply a stock name exists when source data does not provide one.

---

## `/runs`
**Purpose**
- Quickly review recent run ids/status for follow-up commands.

**Example command**
- `/runs`
- `/runs 7d`

**Interpret normal output**
- Expect recent run rows with run id, status, and timestamps.
- Use the returned run id for `/risk_review <run_id>`.

**Interpret no-data output**
- "no matching records" means no run rows in current lookback window.
- Action: widen lookback (for example from default to `7d`) and retry.

**Handle invalid input / usage output**
- If you see `Invalid input: ...` + `Usage: /runs [days]d`, correct format and retry.
- Accepted pattern is integer + `d` suffix (for example `3d`, `14d`).

**Boundary note**
- Read-only operational lookup; no trading or execution action.

---

## `/runner_status`
**Purpose**
- Check latest runner lifecycle outcome (success/failed/no recent run).

**Example command**
- `/runner_status`

**Interpret normal output**
- Expect latest run summary fields (status, started/finished time, duration, entrypoint/schedule basis).
- `status=success` indicates run flow completed; still pair with review commands for content validation.

**Interpret no-data output**
- "no matching records" indicates no runner record currently queryable.
- Action: verify scheduler/service health and retry later.

**Handle invalid input / usage output**
- Only exact `/runner_status` is supported.
- Malformed variants (for example `/runner_status now`) may be ignored as unrecognized commands, not return explicit usage/invalid-input text.
- Retry using exact `/runner_status`.

**Boundary note**
- Operational health check only; no strategy mutation or execution.

---

## `/risk_review <run_id>`
**Purpose**
- Review paper-trading risk evaluation summary for one run id.

**Example command**
- `/risk_review 12345`

**Interpret normal output**
- Read as per-run risk context to support human decision review.
- Use together with `/runs` to confirm target run exists and is intended.

**Interpret no-data output**
- "no matching records" means the provided `run_id` was not found in current query scope.
- Action: run `/runs` first, pick a valid run id, then retry `/risk_review <run_id>`.
- If a run exists but internal review generation fails, treat it as a failed/internal-error path (not a no-data interpretation path).

**Handle invalid input / usage output**
- If `Invalid input` + `Usage: /risk_review <run_id>` appears, provide one integer run id and retry.

**Boundary note**
- Decision-support review only; does not place orders.

---

## `/pnl_review`
**Purpose**
- Review current paper position/PnL snapshot.

**Example command**
- `/pnl_review`

**Interpret normal output**
- Read totals/open positions and per-symbol lines for paper performance diagnostics.
- Apply Step 57 stock display policy exactly when interpreting symbol rows.

**Interpret no-data output**
- "no matching records" indicates no matching paper snapshot/trade rows in current state.
- Action: verify whether paper trades have been generated for the period.

**Handle invalid input / usage output**
- Command accepts no extra arguments.
- If invalid usage appears, rerun as exact `/pnl_review`.

**Boundary note**
- Paper-trading diagnostic only; no live-money execution.

---

## `/outcome_review`
**Purpose**
- Review closed-trade outcome summary over default available snapshot window.

**Example command**
- `/outcome_review`

**Interpret normal output**
- Focus on `closed_trade_count`, `win/loss/flat`, `win_rate`, holding-period stats, and top realized winners/losers.
- Use as evidence for strategy review discussions, not autonomous action triggers.

**Interpret no-data output**
- If output states no closed trades / no matching records, current snapshot has no closed round-trips for this view.

**Handle invalid input / usage output**
- No argument in this form; remove extra tokens and retry exact command.

**Boundary note**
- Review/diagnostic surface only; human final decision required.

---

## `/outcome_review <days>`
**Purpose**
- Review closed-trade outcomes using a bounded recent window.

**Example command**
- `/outcome_review 30`

**Interpret normal output**
- Same metrics as `/outcome_review`, but limited to valid days-window contract.
- Useful for daily/weekly/monthly trend checks during operator review.

**Interpret no-data output**
- "no closed paper trades in review window" / "no matching records" means nothing matched the selected window.
- Action: expand days window and retry.

**Handle invalid input / usage output**
- If invalid token/range appears, follow usage exactly and keep `<days>` in accepted range `1..365`.
- Example fix: `/outcome_review 7`.

**Boundary note**
- Paper-trading decision-support only; no autonomous live-money behavior.

---

## `/daily_review`
**Purpose**
- 快速生成每日 operator review packet（MVP），用短格式整合核心 read-only review surfaces。

**Example command**
- `/daily_review`

**Handle invalid input / usage output**
- Only exact `/daily_review` is supported.
- Extra-token variants (for example `/daily_review now`) return explicit usage guidance: `Usage: /daily_review`.
- Retry using exact `/daily_review`.

**Interpret normal output**
- `business_date_hkt`: 今日 review packet 的 HKT business date（display-only，不改任何 persisted storage semantics）。
- `runner_status`: latest runner 狀態（`success/failed/no data/internal error`）。
- `latest_run_id`: 最新 run id（若無則 `N/A`）。
- `latest_run_time_hkt`: latest run 的建立時間（HKT）；若無 latest run 則 `N/A`。
- `pnl_snapshot`: 紙上交易持倉/盈虧摘要可用性（`available/no matching records/internal error`）。
- `outcome_summary`: 平倉結果摘要可用性（`available/no closed trades/internal error`）。
- `daily_review_health`: readiness/data-availability health（`ok/attention_needed/internal_error`），不是投資建議或買賣信號。
- `next_action_hint`: 根據 section 狀態給 operator 的 follow-up 提示，不提供 buy/sell/hold 決策。
- `detail_commands`: `/runner_status`, `/runs`, `/pnl_review`, `/outcome_review`；若有 latest run 會包含 `/risk_review <run_id>`。
- 若 `runner_status` 為 `failed` 或 `unknown`，即使 pnl/outcome 可用，`daily_review_health` 仍為 `attention_needed`。

**Interpret partial no-data output**
- 任何單一 section 顯示 `no data` 或 `no matching records` 屬可接受情境，不代表整個 command 失敗。

**Interpret helper internal-error output**
- 單一 helper 失敗時，packet 仍應 `Status: completed.`，該 section 顯示 `internal error`。
- Action: 依建議改跑 `/runner_status`、`/pnl_review`、`/outcome_review` 並查 logs。

**Boundary note**
- `/daily_review` 為 read-only operator review command。
- 僅限 paper-trading decision support；health/hint 欄位只代表 review readiness，不提供自動買賣決策，不涉及 real-money execution。


---

## `/decision_note` runtime MVP (Step 68: run-level + stock-level)
- Step 61 定義 contract；Step 62 提供 run-level runtime；Step 68 擴展為 stock-level runtime。
- Scope: `run` and `stock` (stock scope requires `stock_id`).
- User-supplied required fields: `scope`, `run_id`, `human_action`, `note`, `source_command` (+ `stock_id` when `scope=stock`).
- System-generated required fields: `created_at` (record creation time) and `operator_user_id_hash_or_label` when available/applicable.
- Operator should not manually provide `created_at` in Telegram command text.
- Recommended fields: `system_signal`, `confidence`, `reason_tag`.
- `system_signal` values: `buy_signal`, `sell_signal`, `hold_signal`, `block_signal`, `watch_signal`, `none`.
- `human_action` values: `observe`, `watchlist`, `reject_signal`, `accept_for_paper`, `defer`.
- `confidence`: `low`, `medium`, `high`.
- Guardrails: no broker integration/no market order/no auto real-money execution; `accept_for_paper` is journaling context only; human remains final decision-maker.
- Examples:
  - `/decision_note scope=run run_id=321 source_command=/daily_review human_action=observe confidence=medium note=Daily review checked.`
  - `/decision_note scope=stock run_id=321 stock_id=0700.HK source_command=/daily_review human_action=observe note=Reviewed signal; no action.`

- /decision_note scope=run run_id=123 source_command=/daily_review human_action=observe note=Daily review checked. : Record run-level human decision journal entry only; no execution.
- /decision_note scope=stock run_id=123 stock_id=0700.HK source_command=/daily_review human_action=observe note=Reviewed signal; no action. : Record stock-level human decision journal entry only; no execution.

## Step 65 manual Operator QA harness (GitHub Actions + optional Supabase verification)
- Scope: manual QA harness only; not trading logic, not strategy changes, not paper-trading calculation changes.
- Workflow: `.github/workflows/operator-smoke-test.yml` (manual `workflow_dispatch` only; no schedule/push/PR trigger).
- Script: `scripts/operator_smoke_test.py` builds mock Telegram updates and POSTs to webhook test endpoint, then writes:
  - `operator_smoke_report.md`
  - `operator_smoke_report.json`
- Required GitHub secrets/variables:
  - Secret: `OPERATOR_WEBHOOK_TEST_URL`
  - Variable: `OPERATOR_TEST_CHAT_ID`
  - Variable: `OPERATOR_TEST_USER_ID`
  - Secret (optional if webhook auth enabled): `OPERATOR_WEBHOOK_SECRET`
  - Secret (required only when `verify_supabase=true`): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Step 65 smoke cases:
  - Existing: `/help`, `/daily_review`, `/decision_note` run-level success, `/decision_note` stock-level success, invalid `/decision_note`.
  - Expanded: `/runs`, `/runner_status`, `/risk_review <test_run_id>`, `/pnl_review`, `/outcome_review`.
- Guardrails:
  - Harness validates command responses only; no broker/live-money execution is allowed.
  - Verification focus is transport/delivery contract (`HTTP 200`, `ok=true`, `handled=true`, `replied=true`, `send_result.delivered=true` when available).
  - Response text verification is explicitly `SKIPPED_current_webhook_contract` under current webhook payload contract.
  - `--test-run-id` must be a positive integer (numeric only, e.g. `31`).
  - Harness generates a unique `qa_marker` and appends it into `/decision_note ... note=... marker=<qa_marker>` for this run.
  - When `verify_supabase=true`, harness performs read-only query on `human_decision_journal_entries` and requires at least one matching row (`scope=run`, `run_id=<test_run_id>`, `source_command=/daily_review`, `human_action=observe`, `note` contains `qa_marker`).
  - `SUPABASE_SERVICE_ROLE_KEY` is sensitive and must not be pasted in chat/source/log/report.
  - Step 65 does not implement stock-level decision journal runtime.
  - Step 66 post-deploy acceptance checklist remains deferred scope.
  - Step 67 scheduled daily health check remains future plan only (not implemented in Step 65).
  - QA harness is not trading logic and must not trigger broker/live-money execution.
- Future governance note:
  - After Step 66, runtime/Telegram/DB project changes should include operator QA-harness consideration in acceptance flow.


## Post-merge acceptance flow (Step 66)
1. If runtime/deployment-relevant change exists, first wait for Railway deploy completion before production smoke validation.
2. Run Operator Smoke Test via GitHub Actions manual workflow (`workflow_dispatch`).
3. Use `verify_supabase=true` only when DB persistence was touched by the merged PR; otherwise keep default skipped mode.
4. Paste workflow run link in review thread and confirm artifact/report status.
5. After reviewer confirmation, record final acceptance result in `docs/status.md` (do not pre-mark PASS before manual review completion).

## Step 91A RLS runtime acceptance execution template
Use together with `docs/post-deploy-acceptance-checklist.md` section **G**.

- backend key corrected to secret-class before runner test: yes/no
- Current publishable-class key corrected before Step 92: yes/no
- Railway redeploy completed after key correction: yes/no
- paper-daily-runner DB write acceptance passed: yes/no
- paper-daily-runner latest run completed after RLS enabled: yes/no
- runs table insert/update observed: yes/no
- signals upsert/update observed: yes/no
- decision ledger / paper trading writes observed if applicable: yes/no/not applicable
- Telegram notification still works: yes/no
- Mini App API smoke still passes: yes/no
- no service key exposed in Mini App static preview: yes/no
- no service key logged: yes/no
- no anon/publishable key used for backend writes: yes/no
- issues / errors:

Recorded Step 91A operator result:
- platform key correction completed: yes
- RLS runtime acceptance completed: yes

## Step 91C Railway backend Supabase key migration (manual acceptance template)
Use together with `docs/railway-service-variables.md` Step 91C and `docs/post-deploy-acceptance-checklist.md` sections **C/D**.

- Railway staged env review completed for affected backend services (`paper-daily-runner`, `telegram-webhook` if Supabase path enabled, other backend scheduled/smoke services): yes/no
- backend target key set to `SUPABASE_SECRET_KEY` (`sb_secret_...`) on affected backend services: yes/no
- explicit fallback-only posture confirmed (`SUPABASE_KEY` present only for transitional rollback/backward compatibility): yes/no
- Railway deploy completed for all affected backend services: yes/no
- post-deploy `paper-daily-runner` execution completed: yes/no
- DB writes verified (`runs`, `signals`, decision-ledger / paper-trading where applicable): yes/no
- `latest_system_runs` path unaffected if configured: yes/no/not applicable
- Telegram webhook/smoke path still works: yes/no
- Mini App API read-only smoke still works: yes/no
- `miniapp-static-preview` confirms no Supabase secret/service-role/fallback backend key vars configured: yes/no
- no secret/service key values exposed in logs/artifacts/screenshots: yes/no
- no fallback warning for `SUPABASE_KEY` observed when `SUPABASE_SECRET_KEY` is configured: yes/no
- issues / errors:

## Step 91C-1 GitHub automated runtime acceptance smoke
- Use GitHub Actions workflow `Step 91C Runtime Acceptance` (`.github/workflows/step91c-runtime-acceptance.yml`) to produce reviewer artifacts with reduced manual handling.
- Artifacts include: `operator_smoke_report.{md,json}`, `miniapp_api_smoke_report.{md,json}`, `step91c_runtime_acceptance_report.{md,json}`.
- `MINIAPP_SMOKE_ENDPOINT_URL` is expected from GitHub Actions environment variable `production-smoke` via `vars.MINIAPP_SMOKE_ENDPOINT_URL` (not secret context by default).
- Mini App sensitive values remain environment secrets: `MINIAPP_SMOKE_BOT_TOKEN`, `MINIAPP_SMOKE_ALLOWED_TELEGRAM_USER_ID`, `MINIAPP_SMOKE_UNAUTHORIZED_TELEGRAM_USER_ID`.
- If endpoint URL is treated as sensitive in your org, store it as an environment secret and update workflow context usage accordingly.
- Guardrail remains unchanged: paper-trading / decision-support only, no broker integration, no real-money execution.
- Limitation: until Railway token/log integration is added, Railway env/fallback-warning evidence remains partial (`fallback_warning_check=NOT_CHECKED`).
- Step 91C aggregate evidence gate classification: required Supabase checks are `runs` and `signals`; optional checks are `latest_system_runs`, `decision_ledger`, and `paper_trades` (optional may return `NOT_CONFIGURED` without auto-failing the optional section).
- Step 91C preflight accepts backend key fallback: `SUPABASE_SECRET_KEY` is preferred and must be `sb_secret_...` when present; if absent, `SUPABASE_SERVICE_ROLE_KEY` is accepted as explicit backend alternative.
- Optional table checks (`latest_system_runs`, `decision_ledger`, `paper_trades`) allow `NOT_CONFIGURED` but any optional `FAIL/INVALID` still fails aggregate `overall_status`.

## Step 91C-2 Railway evidence automation (read-only)
- Adds optional read-only Railway log evidence script `scripts/railway_step91c_log_evidence.py` for fallback-warning verification artifacts.
- No Railway variable mutation, no deploy/redeploy, no staged-change commit, and no secret/raw-log output.
- `RAILWAY_TOKEN` must stay in GitHub Actions environment secrets only; when token/IDs are absent, report is `NOT_CONFIGURED`.
- Workflow accepts optional `RAILWAY_API_URL` override (default remains Railway backboard GraphQL v2); evidence only prints host-level endpoint context.
- Workflow console now includes safe one-line diagnostics summary (`overall_status`, `fallback_warning_check`, `logs_read_count`, `railway_api_http_status`, `railway_api_error_kind`, `limitation`) while detailed evidence remains in artifact files.
- If Railway evidence fails with `HTTPError`, inspect:
  - `railway_api_http_status` (401/403 usually token scope/workspace mismatch; 400/422 usually GraphQL query/schema mismatch),
  - `railway_api_error_excerpt_redacted` (safe redacted excerpt only, no token/raw log payload).
- Optional lightweight connectivity check is reported as `connectivity_check` + `connectivity_http_status` to separate auth/connectivity issues from log-query shape issues.
- `me { email }` connectivity probe is **account-token only** per Railway docs. Default probe mode is workspace-safe `NOT_RUN` (`connectivity_reason=workspace_probe_not_configured`) unless `RAILWAY_CONNECTIVITY_PROBE=account` is explicitly set.


## Step 91C-5 Railway environmentLogs evidence (read-only)
- Default mode is `RAILWAY_LOG_QUERY_MODE=environment`.
- The script queries Railway `environmentLogs(environmentId, filter, beforeLimit)` instead of guessed nested deployment log path.
- Set `RAILWAY_LOG_SERVICE_IDS` from Railway Cmd/Ctrl+K service UUIDs to scope filter (`@service:<id>` OR-joined).
- Keep `RAILWAY_LOG_SERVICE_NAMES` for display/compatibility labels only.
- Safety guardrails unchanged: no raw log lines in artifacts, no secret output, no Railway mutations/deploy/redeploy.

- Step 91C scoped environmentLogs evidence requires `RAILWAY_LOG_SERVICE_IDS`; missing IDs must fail evidence instead of scanning full environment logs.
- `RAILWAY_LOG_SERVICE_NAMES` are display labels only in Step 91C environment mode.

## Step 91C-6 Railway runner-side API probe
- 若本機 `curl` 對同一 Railway endpoint / project / environment / services 成功，但 GitHub Actions 仍是 403，先看 artifact：`railway_api_probe_report.md` / `.json`。
- 判讀規則：
  - `project_metadata_status=FAIL` 且 `project_metadata_http_status=403`：優先排查 runner token / GitHub environment secret / project access。
  - `project_metadata_status=PASS` 但 `environment_logs_probe_status=FAIL` 且 `environment_logs_http_status=403`：偏向 Railway logs endpoint/query-specific 權限或 query 路徑問題。
  - metadata PASS 但 `configured_environment_id_found=false` 或 `missing_service_ids` 非空：環境/服務 ID 配置錯誤。
  - `environment_logs_probe_status=PASS` 但主 evidence 仍 FAIL：優先排查 log window 或 fallback warning 命中。
- 探針維持 read-only，且不得在 chat/docs/logs 貼出 token 或原始 log message。


## Step 91C-7A Railway request-shape + token-fingerprint diagnostics (read-only)
- `scripts/railway_api_probe.py` / `scripts/railway_step91c_log_evidence.py` now send explicit API headers aligned with local successful request shape: `Content-Type`, `Accept`, `User-Agent`, `Authorization: Bearer`.
- 新增 `RAILWAY_TOKEN_SHA256_PREFIX`（可選）用於 GitHub runner token 指紋比對；只回報 `token_fingerprint_expected_configured` / `token_fingerprint_match`，不輸出 token、prefix/suffix、完整 hash、raw token length。
- 若 `token_fingerprint_match=false`，視為 fail-safe（避免在錯 token 上誤判 request-shape 問題）。
- 新增可選 `RAILWAY_CURL_PROBE=on`（預設 off）：在 `RAILWAY_CONNECTIVITY_PROBE=account` 時，同 runner 內額外做 curl account probe，僅記錄 `curl_account_probe_status` / `curl_account_probe_http_status`，不輸出 response body。
- 排查順序：
  1) 先看 fingerprint 是否一致（token/secret mismatch）。
  2) 再比對 `account_probe_status`（urllib）與 `curl_account_probe_status`（curl）是否分歧（request-shape/urllib 問題）。
  3) 若兩者都 403，偏向 GitHub runner/Railway edge 或 token權限問題。
- 安全提醒：不要把 token 貼到 chat/docs/logs；Step 91C Railway evidence 維持 read-only，禁止 mutation/deploy/redeploy。
