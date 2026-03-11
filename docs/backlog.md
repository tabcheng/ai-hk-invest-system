# Product + Engineering Backlog

Prioritization scale:
- **P0** = next implementation-critical
- **P1** = important near-term hardening
- **P2** = valuable follow-up

## P0 — Next implementation-critical

### 1) Implement paper-trading v1 exactly from docs contract ✅ completed
- Implemented deterministic simulator from `docs/paper-trading-v1.md` input/order/ledger rules.
- Preserved runtime signal-generation behavior and existing Railway entry/cron flow.
- Added persisted deterministic trade/snapshot/event outputs with new paper-trading tables.

### 2) End-to-end traceability via `run_id` linkage
- Link run metadata, signal rows, and paper-trading outputs with one execution identifier.
- Make single-run reconstruction possible from persisted artifacts.

### 3) Structured `error_summary`
- Replace free-form truncated text with compact structured schema (category, sample message, affected ticker count).
- Keep storage bounded while improving debugging and analytics.

### 4) Add basic pytest project configuration
- Add minimal `pytest.ini` (or equivalent) for stable test discovery and consistent local/CI behavior.

### 5) Telegram daily summary notification MVP ✅ completed
- Added end-of-run Telegram summary delivery for success/failure runs using `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
- Notification delivery is best-effort and does not fail the core job when Telegram is unavailable/misconfigured.
- Included concise deterministic summary fields: run date/status, per-ticker signals, paper trade count, latest total equity, and warning note.

- Follow-up hardening completed: deterministic single run-date usage and startup-failure notification attempt before Supabase client initialization.

## P1 — Review reminders + near-term hardening

### Three recent PR review reminders (carry-over)
1. **Helper extraction:** pull repeated runtime logic into focused helpers to reduce duplication.
2. **Trace coherence:** ensure status/identifier consistency across run + signal + downstream layers.
3. **Failure reporting quality:** improve error grouping/actionability over opaque string blobs.

### Near-term hardening follow-ups
- Add CI pipeline for lint/test gating on pull requests.
- Expand tests for edge cases: NO_DATA / INSUFFICIENT_DATA propagation, run finalization, DB failure paths.

## P2 — Medium-term quality and performance

### Reliability and test depth
- Add deterministic replay fixtures for multi-day simulation scenarios.
- Increase integration-style coverage for persistence + run lifecycle behavior.

### Metrics and performance
- Track processing duration and per-ticker latency.
- Add failure ratio and data-coverage metrics.
- Monitor performance regressions over time.

### Strategy analytics extensions
- Add richer paper-trading analytics (risk-adjusted return, drawdown episodes, turnover efficiency).
- Evaluate signal extensions only after baseline paper-trading evidence is established.

## Technical debt register
- Runtime flow still has extractable helper opportunities.
- `error_summary` remains coarse and truncation-based.
- Execution traceability is incomplete without explicit linkage keys.
- Test harness exists but is minimal without project-level pytest config + CI enforcement.

## Maintenance rule
After each completed task, update both this backlog and `docs/status.md` to keep next approved work explicit.
