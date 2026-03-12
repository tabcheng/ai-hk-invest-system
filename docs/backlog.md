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

5. **End-to-end `run_id` traceability hardening** ✅ completed
   - Added run linkage persistence for `signals`, `paper_trades`, `paper_daily_snapshots`, `paper_events`, and `notification_logs`.
   - Added migration-level FK-style links/indexes where practical.
   - Run records now persist separated ticker/post-processing/notification failure summaries.


6. **Structured run observability JSON + delivery telemetry** ✅ completed
   - Added `runs.error_summary_json` and `runs.delivery_summary_json` schema support.
   - Added structured ticker/stage error records and Telegram delivery telemetry persistence in run finalization.
   - Preserved legacy text summary fields and best-effort/non-blocking observability guardrails.

7. **Basic pytest project config + CI test gating** ✅ completed
   - Added a conservative root `pytest.ini` for stable repository-root discovery.
   - Added `.github/workflows/tests.yml` to run `pytest` on pull requests and pushes to `main`.

## Active backlog (pending)

## P0 — Next implementation-critical

### 1) Telegram follow-up: summary schema versioning
- Introduce explicit message schema version for summary payload formatting.
- Prevent drift when adding/removing summary fields over time.

## P1 — Near-term hardening and review reminders

### Carry-over reminders
1. **Helper extraction:** pull repeated runtime logic into focused helpers to reduce duplication.
2. **Trace coherence:** ensure status/identifier consistency across run + signal + downstream layers.
3. **Failure reporting quality:** improve error grouping/actionability over opaque string blobs.

### Additional hardening
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
- Structured JSON observability is now present, but schema/version governance should be expanded over time.
- Test harness now has project-level pytest config and CI enforcement; continue expanding depth and failure-path coverage.
- Notification layer now has sent-dedup persistence and run-level delivery telemetry, but summary schema-version governance still needs formalization.

## Maintenance rule
After each completed task, update both this backlog and `docs/status.md` to keep next approved work explicit.
