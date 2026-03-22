# Product + Engineering Backlog

Prioritization:
- **P0** = next implementation-critical
- **P1** = near-term important hardening
- **P2** = valuable follow-up

## Active backlog (pending)

### P1 — Step 40+ candidates (small, reviewable, verifiable)
1. **Platform hardening follow-up (Step 40A candidate)**
   - Close/verify manual controls documented in Step 19/19B (GitHub branch protection, Railway worker posture, Supabase backup/RLS checklist).
   - Keep repo changes documentation-first unless explicit runtime/platform mutation is approved.

2. **Notification dedup follow-up**
   - Re-validate and document dedup semantics (`sent` vs `skipped` vs `deduped`/`failed`) to reduce operator confusion.
   - Add doc clarifications where ambiguity remains; runtime changes only if explicitly approved.

3. **Paper-trading analytics follow-up (scoping pass)**
   - Define minimal next metrics package (for example drawdown/turnover/risk-adjusted lens) as a scoped Step candidate.
   - Do not introduce large analytics expansion in one step.

4. **Docs maintenance (ongoing discipline)**
   - Continue status/backlog/plan alignment after each completed step.
   - Keep unknowns explicitly marked as `unknown / needs confirmation`.

5. **Telegram command registration follow-up (optional, scoped)**
   - Evaluate whether to add explicit bot-command registration (for example via Telegram `setMyCommands`) for in-app discoverability.
   - Keep scope small; do not couple command registry work with strategy/paper-trading logic.

### P2 — Medium-term quality and reliability
- Expand deterministic replay/integration fixtures for multi-day paper-trading scenarios.
- Improve failure-path coverage for DB/notification/run-finalization edge cases.
- Track lightweight runtime health metrics (duration, per-ticker latency, failure ratio) once Step 31 scope is approved.

## Completed backlog (archived)

- Step 37 completed: dedicated daily-runner entrypoint introduced (`python -m src.daily_runner`), with HKT business schedule baseline formally documented (target 20:00 HKT; Railway UTC cron `0 12 * * *`).
- Step 38 completed: daily runner observability/logging now emits consistent execution summary fields (`started_at`, `finished_at`, `duration_seconds`, `status`, `entrypoint`, `schedule_basis`) for both success and failure paths, with safe failure summary and focused runner tests for summary content + exit codes.
- Step 38 review hotfix completed: failure `error_summary` normalization now collapses multiline/irregular whitespace before truncation so runner failure summaries stay single-line and easier to review in log systems.
- Step 39 completed: Telegram operator `/runner_status` command added with allowlist auth gating, latest persisted run-summary lookup, safe fallback/failure responses, and focused operator/webhook non-crash coverage.
- Step 39 review hotfix completed: `/runner_status` naive timestamp parsing now normalizes to UTC so operator summary times and duration remain deterministic across runtime environments.

### Foundation + runtime hardening
- Step 1–12 baseline (documentation foundation, signal framework, dedup, run lifecycle, modularization, tests, Telegram MVP/hardening).
- End-to-end `run_id` traceability hardening across core persistence surfaces.
- Structured run observability JSON + delivery telemetry persistence.
- Pytest project config + CI test gating.
- Telegram schema versioning + schema evolution guardrails.

### Platform posture + governance docs
- Step 19 operational baseline hardening docs (GitHub/Railway/Supabase).
- Step 19B Supabase access model clarification + staged RLS rollout plan.

### Paper-trading decision/risk surfaces
- Step 20 decision ledger (`paper_trade_decisions`) and post-review hardening.
- Step 21 paper positions/PnL foundation and follow-up rerun/state-sync fixes.
- Step 22 risk guardrails v1 and post-review concentration fixes.
- Step 23 risk observability payload + decision-record alignment and follow-up BUY-executed context.
- Step 24 risk review summarizer and normalization fix.
- Step 25 operator CLI read path and deterministic output-shape follow-up.

### Operator docs (beginner-facing)
- Step 26 paper-risk review runbook.
- Step 27 Telegram troubleshooting runbook.
- Step 28 daily review summary helper (+ completeness fix).
- Step 29 Telegram outcomes quick reference (+ wording tightening).
- Step 31 Telegram message readability improvement (`stock` / `signal/action` / `key_reason/indicator` / `risk_note`, with stock name + stock id clarity and dedup identity unchanged).
- Step 32 Telegram operator run-id lookup command (`/runs` default 5 days, optional day parameter) backed by persistent `runs` metadata with operator access guardrail, plus invalid-parameter usage-response hardening and schema-safe run-field selection hotfix.
- Step 33 Telegram operator help command uplift (`/help` + `/h` alias) with compact bilingual scope/guardrail copy and command usage guidance; discoverability hardening kept handler-only because repo currently has no bot command-registration mechanism.
- Step 34A Telegram inbound webhook integration foundation (`POST /telegram/webhook`) wiring Telegram ingress to existing operator command handler/reply path (`/help`, `/h`, `/runs`) with minimal ingress/auth/send logging, optional transport secret verification hardening, and setup runbook.
- Step 34A docs hotfix completed: fix webhook setup doc so optional secret token is truly optional (split with-secret vs no-secret `setWebhook` examples and add guardrail guidance).
- Step 34A message-format hotfix completed: fix Telegram HTML parse-mode placeholder issue by replacing angle-bracket placeholders in operator help/usage text with HTML-safe bracket placeholders, with follow-up tests covering both `/help` and malformed `/runs` usage output.
- Step 34B completed: Telegram `/risk_review [run_id]` operator command with allowlist/auth guardrail, strict run-id validation, run existence checks, safe failure replies, and observability logs for accepted/failed/completed transitions.
- Step 34B completed: `docs/railway-service-variables.md` deployment reference for Railway service variables across Telegram/webhook, operator allowlist, Supabase, and runtime settings.
- Step 34B review hotfix completed: isolated unexpected operator-handler/run-lookup exceptions so webhook processing remains healthy and Telegram replies stay sanitized, with focused tests for these failure paths.
- Step 34B test hotfix completed: lazy-loaded paper-risk review dependency in Telegram operator path to reduce import-time runtime coupling and keep focused operator/webhook tests runnable in constrained environments.
- Step 35 completed: split Railway deployment topology into two same-repo services (`telegram-webhook` long-running ingress, `paper-daily-runner` cron batch runner), clarified start commands, cron ownership, and service-scoped variable guidance in deployment docs.

## Notes
- This backlog is a planning artifact, not proof of merge approval. For merge/acceptance truth, cross-check `docs/status.md` and human PR history.
- No backlog item authorizes autonomous live-money execution.
