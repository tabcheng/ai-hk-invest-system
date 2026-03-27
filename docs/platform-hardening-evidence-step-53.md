# Step 53 — Platform Hardening Evidence Pass (GitHub / Railway / Supabase)

## Scope and guardrails
- Scope is docs-first evidence/checklist refresh only.
- No strategy, paper-trading flow, real-money execution, runtime behavior, deployment topology, or large infra hardening changes are included.
- Classification used throughout:
  - **repo-confirmed**: verifiable from repository files/docs.
  - **manual verification required**: must be checked in platform UI/console; repo cannot prove it.
  - **backlog follow-up**: non-blocking gap to track for later approved step.

## Evidence summary (small, verifiable)

### 1) GitHub

#### repo-confirmed
- CI test workflow exists at `.github/workflows/tests.yml` and runs on `pull_request` and `push` to `main` with `pytest`.
- System-of-record docs explicitly assign GitHub ownership for branch protection, required reviews, and required status checks.

#### manual verification required
- Branch protection state for target branch (for example `main`):
  - require pull request before merge,
  - required number of reviewers,
  - required status checks (`tests`) blocking merge,
  - stale review dismissal / force-push / deletion protections.
- Repository-level merge policy toggles (merge commit / squash / rebase) and whether they match team policy.
- Secret scanning/push protection enablement state.

#### manual check method (UI)
1. GitHub repo → **Settings** → **Branches** → branch protection / rulesets.
2. GitHub repo → **Settings** → **General** → pull request + merge button settings.
3. GitHub repo → **Settings** → **Code security and analysis** → secret scanning/push protection.
4. Capture dated screenshot or operator note as external evidence artifact.

---

### 2) Railway

#### repo-confirmed
- Dual-service split is documented and explicit:
  - `telegram-webhook`: long-running ingress, no cron.
  - `paper-daily-runner`: scheduled runner with cron `0 12 * * *` UTC (20:00 HKT).
- Runtime env/secret variable expectations are documented (Supabase/Telegram/operator allowlists/provider/runtime values).

#### manual verification required
- Railway project actually has exactly the expected service split and start commands in production.
- Cron is attached only to runner service and set to intended UTC schedule.
- Required env vars are injected on correct service(s); sensitive values are present but not leaked in logs.
- Railway deployment and runtime settings (restart policy/health posture/log retention) align with operator expectation.

#### manual check method (UI)
1. Railway project → verify services `telegram-webhook` and `paper-daily-runner` exist.
2. Open each service → confirm **Start Command** and cron posture (runner only).
3. Service **Variables** → confirm required keys exist (without exposing secret values in docs).
4. Service **Deployments/Logs** → confirm latest deploy/run behavior is consistent with docs.

---

### 3) Supabase

#### repo-confirmed
- Repository docs clearly state backend-only runtime access intent and staged RLS hardening plan (table-by-table) rather than one-shot broad changes.
- Supabase project posture (backup, RLS state, key exposure) is explicitly recognized as requiring periodic manual confirmation.

#### manual verification required
- Backup posture:
  - PITR/backup availability by plan,
  - restore drill feasibility and last successful restore test evidence.
- Access posture:
  - active API keys/roles in use,
  - service-role key handling/rotation policy,
  - no unintended anon/client direct table access paths.
- RLS posture:
  - actual per-table RLS enablement state,
  - policy definitions/effectiveness for `runs`, `signals`, `paper_trades`, `paper_positions`, `paper_daily_snapshots`, `paper_events`, `notification_logs`, `paper_trade_decisions`.

#### manual check method (UI/SQL)
1. Supabase dashboard → **Database** → **Backups**: confirm backup/PITR state.
2. Supabase dashboard → **Authentication / API / Project Settings**: review key and access posture.
3. Supabase SQL editor:
   - inspect `pg_tables`/`pg_policies`/`pg_class` for table-level RLS + policy state,
   - record results with timestamp.
4. Store evidence artifact reference outside repo (ops vault/runbook evidence log).

## Backlog follow-up opened from this pass
1. Define a lightweight recurring platform evidence cadence and artifact location policy (docs/process scope first).
2. Keep any future hardening implementation separate from this evidence step and require explicit approval.

## Domain-boundary confirmation
- This pass supports operator workflow and paper-trading decision-support governance.
- It does **not** alter strategy logic, trading execution scope, or deployment runtime behavior.
