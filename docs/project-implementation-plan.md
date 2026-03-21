# Project Implementation Plan (System-of-Record View)

## Purpose
This document aligns:
- strategic intent (`docs/spec.md`),
- execution truth (`docs/status.md`),
- pending/completed work (`docs/backlog.md`).

It is intentionally concise and optimized for small-step execution.

## Completed implementation steps (aligned)

### Steps 1–12 ✅
Documentation foundation, signal framework, dedup/run observability baseline, runtime modularization, regression tests, and Telegram MVP + initial hardening are complete.

### Steps 13–20 ✅
Traceability hardening, structured observability telemetry, CI test gating, notification schema guardrails, platform baseline docs, Supabase access-model clarification, and decision ledger v1 are complete.

### Steps 21–29 ✅ (repo-confirmed; acceptance may need human confirmation)
- Step 21: paper position/PnL foundation.
- Step 22: paper risk guardrails v1 (+ follow-up fixes).
- Step 23: risk observability / decision-support record v1.
- Step 24: paper-risk review summarizer.
- Step 25: operator-facing paper-risk CLI.
- Step 26: beginner paper-risk runbook.
- Step 27: beginner Telegram troubleshooting runbook.
- Step 28: beginner daily review summary helper.
- Step 29: Telegram outcomes quick-reference.

## Current implementation state
- Runtime behavior is stable and still human-in-the-loop.
- Paper-trading + decision record + risk review surfaces exist in baseline v1 form.
- Operator docs are present for core paper-risk and Telegram troubleshooting tasks.
- Platform hardening execution still includes manual checklist items outside repo code.

## Next small-step candidates (do not over-plan)

### Step 31 candidate set (choose one small slice first)
1. **Docs + operations closure slice (recommended first)**
   - Reconcile open manual platform checklist items with explicit `done/unknown` markers.
   - Acceptance target: no contradiction across `status/backlog/plan`.

2. **Notification clarity + dedup semantics slice**
   - Tighten wording/examples for `sent/skipped/deduped/failed` and stock label clarity (`stock_name + stock_id`).
   - Acceptance target: operator-facing docs read consistently with runtime behavior.

3. **Paper-trading analytics follow-up scoping slice**
   - Define one minimal analytics increment with data dependencies and validation plan (no broad implementation yet).
   - Acceptance target: reviewable Step 32-ready spec.

## Planning guardrails
- Keep each step small, testable, and reviewable.
- Preserve runtime behavior unless a step explicitly approves runtime change.
- Do not introduce autonomous real-money execution.
- Mark uncertain facts as `unknown / needs confirmation`.
