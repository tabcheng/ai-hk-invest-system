# Implementation Runbook (Codex)

## Purpose
Provide a consistent execution workflow for long-horizon Codex contributions.

## Core rules
- `docs/plans.md` is the source of truth for milestone sequence and scope.
- Work on one milestone at a time.
- Keep diffs small and tightly scoped to the current task.
- Validate outcomes after each milestone before moving forward.
- Do not break Railway production flow.
- Update `docs/status.md` after each completed task.
- If validation fails, stop progression and repair issues before continuing.

## Standard execution loop
1. Read `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, and `docs/status.md`.
2. Select the next approved milestone task from `docs/status.md`.
3. Implement only the scoped change for that task.
4. Run validation checks defined in `docs/plans.md`.
5. If any validation fails, stop and repair before taking new scope.
6. Update `docs/status.md` with what was completed, what was validated, and the next approved task.
7. Commit with a clear milestone/task summary.


## Step 15 implementation note (structured observability JSON)
- Add nullable `runs.error_summary_json` and `runs.delivery_summary_json` via migration.
- Keep legacy text `error_summary` and category text summaries unchanged for backward compatibility.
- Build structured ticker/stage error records and message-level Telegram delivery telemetry (single daily-summary attempt per run, with explicit dedup-skip semantics) in Python, then persist on run finalization in best-effort updates.
- Guardrail: telemetry writes are observability-only and must never block signal generation, dedup persistence, paper-trading, or Telegram delivery attempts.

## Step 16 implementation note (pytest config + CI test gating)
- Add a conservative root `pytest.ini` (`minversion`, `testpaths`, `addopts`) to stabilize test discovery from repository root across local and CI runs.
- Add GitHub Actions test workflow at `.github/workflows/tests.yml` that runs on `pull_request` and `push` to `main` using `ubuntu-latest` + `actions/setup-python`.
- Reuse existing dependency flow (`pip install -r requirements.txt`) and run `pytest` directly, avoiding extra tooling or runtime-path behavior changes.


## Step 17 implementation note (versioned daily summary payload + renderer separation)
- Introduce a compact internal `build_daily_summary_payload_v1(...)` contract with `schema_version`, run identity/date, market, summary type, totals, and per-stock rows (`stock_id`, `stock_name`, `signal`).
- Render Telegram text via `render_daily_summary_message(payload)` with schema-version dispatch (v1 renderer), so message formatting can evolve without changing aggregation inputs.
- Keep send path ordering explicit and stable: fetch equity -> build payload -> render message -> send -> dedup marker write.
- Include `context.summary_schema_version` in delivery telemetry so run-level observability records the payload schema used for each attempt.
- Guardrail: preserve existing best-effort/non-blocking delivery semantics and dedup/retry/transport behavior.

## Step 18 implementation note (schema evolution guardrails + summary contract hardening)
- Define explicit notification schema constants in `src/notifications.py`: `CURRENT_DAILY_SUMMARY_SCHEMA_VERSION` and `SUPPORTED_DAILY_SUMMARY_SCHEMA_VERSIONS` (currently `{1}`), while preserving v1 runtime behavior.
- Keep renderer dispatch centralized through a single schema->renderer mapping so future version additions remain reviewable and testable.
- Validate guardrail consistency before dispatch (`current` version must be in the supported set, and supported versions must match renderer-map keys).
- Fail fast for unsupported schema versions with explicit supported-version context so schema drift is surfaced early in tests/CI.
- Keep telemetry `context.summary_schema_version` aligned to the payload schema used at send-time for stable run-level observability.
- Expand tests to cover current-version dispatch, supported-version mapping guarantees, unsupported-version handling, telemetry version propagation, and renderer entrypoint stability.

## Step 19 implementation note (operational baseline hardening)
- Document platform baseline controls across GitHub, Railway, and Supabase with explicit separation between code-enforceable and manual settings.
- Keep runtime behavior unchanged: no trading-logic changes and no new web server path for the worker runtime.
- For Railway healthchecks, document worker-appropriate settings (no HTTP `/health` dependency for current script execution model).
- Capture environment-variable hygiene, log/observability expectations, and Supabase backup/RLS/free-tier risk checks as explicit operational guardrails.
- Record manual follow-ups in `docs/backlog.md` and reflect completion + next approved task in `docs/status.md`.
