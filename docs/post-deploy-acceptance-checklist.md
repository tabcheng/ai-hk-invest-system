# Post-deploy Acceptance Checklist (Step 66)

## Purpose
This checklist is the post-deploy/manual-acceptance gate for PRs that touch runtime, Telegram operator flow, database persistence, paper-trading support surfaces, and related deployment configuration.

After Step 66, every relevant PR must explicitly state which checklist sections apply and provide evidence before acceptance is marked PASS.

## A. All PRs
- [ ] GitHub CI is PASS.
- [ ] PR scope matches the currently approved step scope (no unauthorized scope expansion).
- [ ] `docs/status.md` is updated with current step state and acceptance status wording.
- [ ] `docs/backlog.md` is updated when new non-blocking follow-up work is discovered.
- [ ] No premature post-merge PASS wording is written before actual manual acceptance/review is completed.
- [ ] Docs-only PRs normally require GitHub CI + review only, unless docs changes also modify workflow/runtime expectations.

## B. Telegram / Operator PRs
- [ ] Operator Smoke Test is executed after merge/deploy.
- [ ] Workflow run link is captured in review evidence.
- [ ] Smoke-test artifact/report is reviewed.
- [ ] Overall smoke-test result is PASS.
- [ ] `response_text_verification` limitation is explicitly understood/acknowledged unless a future test-mode echo contract is introduced.

## C. Supabase / Persistence PRs
- [ ] `verify_supabase=true` is required when DB persistence behavior is touched.
- [ ] Supabase verification status is PASS.
- [ ] Matched row count and QA marker are checked where applicable.
- [ ] `SUPABASE_URL` and backend key vars (`SUPABASE_SECRET_KEY` preferred; `SUPABASE_SERVICE_ROLE_KEY` allowed) remain backend secret stores only.
- [ ] `SUPABASE_KEY` is treated as transitional fallback only (not preferred active runtime dependency).
- [ ] No secrets appear in logs, reports, docs, or source code.

## D. Railway / Deployment PRs
- [ ] Railway deployment is completed before production smoke test starts.
- [ ] No unexpected changes in service topology, cron, env vars, or webhook routing.
- [ ] If Railway settings changed, document exact setting changes and rollback notes.
- [ ] Affected backend services are explicitly reviewed (`paper-daily-runner`, `telegram-webhook` when Supabase path applies, and any scheduled/smoke backend service using production Supabase data).
- [ ] `miniapp-static-preview` remains free of `SUPABASE_SECRET_KEY` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_KEY`.
- [ ] No `SUPABASE_KEY` fallback warning appears when `SUPABASE_SECRET_KEY` is configured.

## E. Domain Guardrail
- [ ] No broker integration.
- [ ] No live-money order flow.
- [ ] No autonomous real execution.
- [ ] System remains paper-trading / decision-support only.
- [ ] Human final decision authority is preserved.
- [ ] Strategy or calculation changes receive stricter review before acceptance.

## F. Evidence to paste back for review
- PR link.
- Workflow run link.
- Artifact/report status.
- Railway deployment status (if relevant).
- Supabase verification result (if relevant).

## G. RLS Runtime Acceptance Check (Step 91A)
- [ ] backend key corrected to secret-class before runner test: yes/no
- [ ] Current publishable-class key corrected before Step 92: yes/no
- [ ] Railway redeploy completed after key correction: yes/no
- [ ] paper-daily-runner DB write acceptance passed: yes/no
- [ ] paper-daily-runner latest run completed after RLS enabled: yes/no
- [ ] runs table insert/update observed: yes/no
- [ ] signals upsert/update observed: yes/no
- [ ] decision ledger / paper trading writes observed if applicable: yes/no/not applicable
- [ ] Telegram notification still works: yes/no
- [ ] Mini App API smoke still passes: yes/no
- [ ] no service key exposed in Mini App static preview: yes/no
- [ ] no service key logged: yes/no
- [ ] no anon/publishable key used for backend writes: yes/no
- [ ] issues / errors:

Step 91A recorded result (PR #88):
- platform key correction completed: yes
- RLS runtime acceptance completed: yes

## Step 91C runtime acceptance automation note
- GitHub Step 91C acceptance workflow can reduce manual checks by generating structured smoke evidence artifacts for reviewer validation.
- Full acceptance still requires Railway log evidence or a future Railway API/CLI integration for fallback-warning verification.
- Confirm Mini App frontend/static preview never contains `SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, or `SUPABASE_KEY`.
- Confirm no broker integration and no live-money execution path is introduced.
- Step 91C aggregate pass rule: required gates (`preflight`, key class, operator smoke, miniapp smoke, `runs`, `signals`) must all be `PASS`; stale required rows are `FAIL`.
- Step 91C optional checks policy: optional tables may be `NOT_CONFIGURED`, but optional check `FAIL/INVALID` is blocking and must be resolved before acceptance.

## Step 91C-2 Railway evidence artifact check
- Runtime acceptance now optionally collects read-only Railway log evidence (`railway_step91c_log_evidence_report.{md,json}`).
- Expected fallback warning status: `PASS`/`FAIL` when configured, otherwise `NOT_CONFIGURED` (never fake PASS).
- This evidence step must not mutate Railway variables and must not redeploy services.

- Step 91C-2 note: `staged_changes_check` remains `NOT_CONFIGURED` in this step (no staged-changes automation yet); scope is still read-only evidence only with no variable mutation/redeploy/staged-change commit.
