# Operator Runbook — Telegram Command Output Interpretation (Step 58)

## Scope
- This runbook aligns operator-facing examples with Step 57 normalized wording for:
  - `/runs`
  - `/runner_status`
  - `/risk_review <run_id>`
  - `/pnl_review`
  - `/outcome_review`
  - `/outcome_review <days>`
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
- Command takes no extra token.
- If extra text is provided and usage/invalid message appears, rerun as exact `/runner_status`.

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
- "no matching records" can mean run id exists but has no matching review rows in current data view.
- Action: confirm run id from `/runs`; if still empty, treat as data-availability follow-up.

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
