# Product + Engineering Backlog

Prioritization scale:
- **P0** = next implementation-critical
- **P1** = important near-term hardening
- **P2** = valuable follow-up

## Recently completed (moved out of active backlog)

1. **Paper-trading v1 implementation** ✅ completed
   - Deterministic simulator and persistence outputs are in place.

2. **Telegram daily summary notification MVP** ✅ completed
   - End-of-run best-effort Telegram summary delivery is active.

3. **Telegram deterministic run-date + startup-failure attempt** ✅ completed
   - Hardening completed to improve summary consistency and fatal-startup visibility.

4. **Telegram notification hardening + first docs maintenance review** ✅ completed
   - Summaries now include stock name + stock id using deterministic HTML formatting.
   - Summary equity prefers run-date snapshot with clear fallback labeling.
   - Cross-run daily-summary dedup persistence added (`notification_logs`) for same run-date + target.
   - Delivery remains best-effort/non-blocking.
   - Documentation system-of-record refreshed (`status`/`backlog`).

## Active backlog (pending)

## P0 — Next implementation-critical

### 1) End-to-end traceability via `run_id` linkage
- Link run metadata, signal rows, and paper-trading outputs with one execution identifier.
- Make single-run reconstruction deterministic for audit and debugging.

### 2) Structured `error_summary`
- Replace free-form truncated text with compact structured schema (category, sample message, affected ticker count).
- Keep storage bounded while improving debugging analytics.

### 3) Add basic pytest project configuration
- Add minimal `pytest.ini` (or equivalent) for stable test discovery and consistent local/CI behavior.

### 4) Telegram follow-up: delivery observability expansion
- Extend notification logging from sent-dedup marker to full attempt telemetry (attempted/sent/failed + reason + run_id linkage).
- Keep notification behavior best-effort (non-blocking) while improving post-run diagnosability.

### 5) Telegram follow-up: summary schema versioning
- Introduce explicit message schema version for summary payload formatting.
- Prevent drift when adding/removing summary fields over time.

## P1 — Near-term hardening and review reminders

### Carry-over reminders
1. **Helper extraction:** pull repeated runtime logic into focused helpers to reduce duplication.
2. **Trace coherence:** ensure status/identifier consistency across run + signal + downstream layers.
3. **Failure reporting quality:** improve error grouping/actionability over opaque string blobs.

### Additional hardening
- Add CI pipeline for lint/test gating on pull requests.
- Expand tests for NO_DATA / INSUFFICIENT_DATA propagation, run finalization, DB failure paths, and notification failure pathways.
- Add runbook entry for Telegram environment misconfiguration triage.

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
- Notification layer now has minimal sent-dedup persistence but lacks full delivery-attempt telemetry and schema version governance.

## Maintenance rule
After each completed task, update both this backlog and `docs/status.md` to keep next approved work explicit.
