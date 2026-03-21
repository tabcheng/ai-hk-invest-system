# Project Status

## Last reviewed date
2026-03-21

## Current production behavior (repo-confirmed)
- Runtime entrypoint remains `main.py`, delegating orchestration to modular runtime code in `src/`.
- Daily signal persistence remains idempotent on `(date, stock)` and supports rerun-safe behavior.
- Run lifecycle observability remains in `runs` with terminal status + structured summaries (`error_summary_json`, `delivery_summary_json`).
- Paper-trading remains deterministic and paper-only, with run-linked persistence across trades/snapshots/events.
- Decision record separation is implemented via `paper_trade_decisions` (AI signal vs human decision state).
- Telegram delivery remains best-effort/non-blocking with deterministic summary formatting and run-date dedup tracking.
- No autonomous live-money execution is enabled; human remains final decision-maker.
- Deploy/config stability note: Railway/Railpack build previously failed when defaulting to Python `3.13.12` (mise install failure path); repository now pins Python to `3.12.9` via `.python-version` as a deploy stability guardrail (no strategy/paper-trading/signal-flow logic change).

## Milestone status
- Milestone 1 (Documentation Foundation): completed.
- Milestone 2 (Signal framework + modularization/test baseline): completed.
- Milestone 3 (Paper-trading v1): completed.
- Milestone 4 (Controlled production hardening): in-progress, with Steps 19–30 completed and follow-up hardening still pending.

## Step 21–29 status ledger (Step 30 maintenance refresh)

| Step | Goal | Primary deliverable(s) | Merge / acceptance status |
|---|---|---|---|
| 21 | Add paper position + PnL foundation | `paper_positions` schema/state refresh + portfolio summary helper | **Repo evidence:** completed in current code/docs. **Manual acceptance:** unknown / needs confirmation. |
| 22 | Add paper risk guardrails v1 for BUY path | Concentration/allocation/add/cash checks with blocking only for high-risk breaches | **Repo evidence:** completed (plus documented post-review fixes). **Manual acceptance:** unknown / needs confirmation. |
| 23 | Persist risk observability / decision-support record v1 | Structured `risk_evaluation` payload in events + decision ledger fields | **Repo evidence:** completed (including BUY executed context follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 24 | Add paper-risk run review read surface | Aggregated per-run risk review helper + normalization | **Repo evidence:** completed (including normalization follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 25 | Expose operator CLI for paper-risk review | `python -m src.paper_risk_review_cli --run-id <id>` deterministic JSON output | **Repo evidence:** completed (including output-shape follow-up). **Manual acceptance:** unknown / needs confirmation. |
| 26 | Add beginner paper-risk operator runbook | `docs/operator-runbook-paper-risk-review.md` | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 27 | Add beginner Telegram troubleshooting runbook | `docs/operator-runbook-telegram-troubleshooting.md` | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 28 | Add beginner daily review summary helper | `get_paper_daily_review_summary_for_run(...)` + focused tests/fix | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 29 | Add Telegram outcome quick reference | `docs/operator-quick-reference-telegram-outcomes.md` (+ doc tightening follow-up) | **Repo evidence:** completed. **Manual acceptance:** unknown / needs confirmation. |
| 30 | Docs maintenance + project state alignment | Refreshed `docs/status.md`, `docs/backlog.md`, `docs/project-implementation-plan.md`, and runtime/data-flow alignment in architecture docs | **Repo evidence:** completed in this branch. **Merge:** pending PR merge. **Manual acceptance:** unknown / needs confirmation. |

## Known unknowns / needs confirmation
- Exact PR numbers and explicit human acceptance timestamps for Steps 21–29 are not derivable from repository files alone and need manual confirmation.
- Production platform settings (GitHub/Railway/Supabase) still require periodic manual verification outside repo state.

## Next approved task candidate
- Step 31 candidate: platform/documentation hardening follow-up focused on small, reviewable items from active backlog (notification clarity/dedup validation, platform hardening checklist closure, and paper-trading analytics follow-up scoping) without runtime behavior changes unless explicitly approved.
