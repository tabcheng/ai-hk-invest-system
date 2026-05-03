# RLS Runtime Impact Audit (Step 91A)

## Scope
Step 91A is a **docs/runbook/readiness** step triggered after operator manually enabled RLS on all Supabase tables.

This step does **not**:
- implement `latest_system_runs` runtime repository;
- add runner runtime write for `latest_system_runs`;
- add Mini App frontend Supabase fetch;
- add Telegram/Mini App runtime Supabase read switch;
- change Supabase schema/RLS policies in code;
- change Railway variables in this PR.

## Current RLS state
- Operator manually enabled RLS on all Supabase tables.
- This is security-positive.
- Runtime impact risk: backend reads/writes can fail if low-privilege (anon/publishable) keys are used for server-side persistence paths.

## Known current finding (confirmed)
- Current Railway `SUPABASE_KEY` is confirmed publishable-class (`sb_publishable_...`), not backend elevated key class.
- Because RLS is enabled on all tables, backend DB write paths are P0 risk under current key boundary.
- Step 91A manual platform acceptance is **blocked** until `paper-daily-runner` uses backend-only elevated Supabase key class.
- Do not paste or log actual key values.

## Platform correction recorded
- Operator confirmed `paper-daily-runner` backend `SUPABASE_KEY` key class has been corrected from publishable-class to secret-class (`sb_secret_...`).
- Actual key value must not be pasted or logged.
- Railway staged changes deployed and post-redeploy runtime checks completed.
- Step 91A platform key correction completed: yes.
- Step 91A RLS runtime acceptance completed: yes.

At-risk until corrected:
- `paper-daily-runner` writes to existing Supabase tables (for example `runs`, `signals`, decision-ledger-related rows, paper-trading outputs) are treated as at-risk until Railway key boundary is corrected.

Post-correction pending checks:
- Completed acceptance evidence:
  - `paper-daily-runner` run completed after redeploy;
  - `runs` insert/update observed;
  - `signals` upsert/update observed;
  - decision ledger / paper-trading writes observed;
  - Telegram notification still works;
  - Mini App API smoke rerun completed;
  - no service key observed in logs;
  - `miniapp-static-preview` remains free of Supabase service/secret key;
  - issues/errors: no.

## Existing Supabase touchpoints (current repo behavior)
- `paper-daily-runner` uses backend Supabase client and writes existing system-of-record tables.
- Existing writes may include `runs`, `signals`, decision-ledger-related records, and paper-trading outputs depending on current run path.
- Telegram webhook command flows depend on backend runtime access boundaries and must keep secrets backend-only.
- Mini App review-shell currently has no production Supabase runtime read.
- Mini App static preview does not use Supabase.

## Required Railway service checks
1. `paper-daily-runner`
   - Must use backend-only elevated Supabase key.
   - Preferred explicit naming target: `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY`.
   - Must not use anon/publishable key for backend writes.
2. `telegram-webhook`
   - Must not expose Supabase service key to frontend/browser/static assets.
   - Keep key in backend runtime variables only.
3. `miniapp-static-preview`
   - Must have no Supabase service key configured.
   - Must remain static/read-only preview surface.

## Key-handling guardrails
- Operator must never paste actual keys into docs, tickets, PR comments, chat, or screenshots.
- Operator must never log full key values in workflow logs or runtime logs.
- Browser/client bundles must never receive service-role/secret keys.

## `SUPABASE_KEY` ambiguity and staged cleanup recommendation
Current env naming `SUPABASE_KEY` is ambiguous.

Step 91A recommendation:
- Prefer explicit backend-only naming in future runtime-safe migration:
  - `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY`.
- Do **not** rename runtime env in this step.

Staged migration plan (future implementation step):
1. Add runtime support for explicit new env var with safe fallback to existing `SUPABASE_KEY`.
2. Update Railway service variables.
3. Run post-deploy smoke/acceptance.
4. Remove ambiguous fallback later after stable verification.

## Acceptance dependency for next step
- Step 92 (`latest_system_runs` runtime integration) should proceed only after Step 91A RLS runtime acceptance checklist evidence is recorded.
- Additional gate status: complete. Step 92 may proceed after PR #88 merge.

## Domain boundary reminder
- System remains paper-trading / decision-support only.
- No broker integration.
- No autonomous real-money execution.
- Human executes any real trade decision outside this system.
