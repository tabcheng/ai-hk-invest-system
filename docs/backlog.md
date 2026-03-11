# Product + Engineering Backlog

Prioritization scale:
- **P0** = next implementation-critical
- **P1** = important near-term hardening
- **P2** = valuable follow-up

## P0 — Next implementation-critical items

### 1) Implement paper-trading v1 engine from documented contract
- Build deterministic simulation using `docs/paper-trading-v1.md` rules.
- Ensure no change to production signal-generation runtime behavior.
- Produce auditable trade and portfolio logs.

### 2) Link simulation artifacts to run-level observability (`run_id` linkage)
- Carry `run_id` (or equivalent execution identifier) through generated signal rows and paper-trading outputs for traceability.
- Ensure one execution can be reconstructed across runs, signals, and simulation outputs.

### 3) Standardize `error_summary` structure
- Replace ad hoc/truncated free-text with a lightweight structured schema (e.g., category + message + affected ticker count).
- Preserve compact storage while improving post-run analysis.

### 4) Add basic pytest configuration (project-level)
- Introduce minimal pytest config (`pytest.ini` or equivalent) for stable discovery/markers and predictable local/CI execution.
- Keep configuration intentionally small.

## P1 — PR review reminders (recent) and follow-ups

### Recent PR review reminders (carry-over)
1. **Extract repeated runtime helper logic** into focused helper functions/modules to reduce duplication and simplify future tests.
2. **Improve run-trace coherence** by ensuring identifiers and status updates are consistently connected across layers.
3. **Harden failure reporting quality** so errors are grouped and actionable rather than opaque string blobs.

### Additional near-term follow-up
- Expand automated tests beyond current minimal path coverage (more edge cases for signal and run lifecycle behavior).
- Add CI workflow for lint/test gating on pull requests.

## P2 — Medium-term quality and performance work

### Testing and reliability
- Increase test depth for data edge cases, DB write failure modes, and run finalization corner cases.
- Add fixtures/utilities for deterministic replay-style tests.

### Metrics and performance
- Define performance metrics (runtime duration, per-ticker processing latency, failure ratio, data coverage ratio).
- Track trend metrics over time for regression detection.

### Strategy and analytics extensions
- Add richer evaluation metrics for paper trading (risk-adjusted returns, drawdown episodes, turnover efficiency).
- Document candidate signal extensions only after baseline paper-trading evidence is available.

## Technical debt register (known)
- Runtime flow currently contains logic that can be further decomposed for readability and testability.
- Error summaries are constrained by coarse string truncation behavior.
- Traceability across execution layers is incomplete without explicit linkage keys.
- Test harness exists but remains minimal without central pytest configuration and CI enforcement.

## Backlog maintenance note
After each completed task, update this backlog and `docs/status.md` so next approved work remains explicit and prioritized.
