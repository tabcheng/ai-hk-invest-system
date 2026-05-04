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
