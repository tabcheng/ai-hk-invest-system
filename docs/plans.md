# Project Plans

`plans.md` is the source-of-truth roadmap for milestone execution.

## Milestone 1: Documentation Foundation
Define and maintain core execution docs (`spec`, `plans`, `status`, `implement`) so future Codex work remains consistent and traceable.

### Validation
- Confirm required docs exist: `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, `docs/status.md`, and `docs/implement.md`.
- Confirm `AGENTS.md` requires pre-work reading of `AGENTS.md`, `docs/spec.md`, `docs/plans.md`, and `docs/status.md` for non-trivial work.
- Confirm `AGENTS.md` requires updating `docs/status.md` after each completed task.
- Confirm every merged step is followed by documented dual acceptance checks:
  - **Post-merge QA Check** (output/function behavior, error/success paths, display/docs/tests consistency).
  - **Post-merge Domain Check** (AI HK investing-system alignment, paper-trading/decision-support boundary, calculation/interpretation risk review).
- Confirm no runtime behavior files (for example `main.py`) are modified during documentation-only tasks.

## Milestone 2: Signal Framework Definition
Document candidate signal categories, data assumptions, and risk constraints for Hong Kong equities.

### Validation
- Verify each signal category has explicit assumptions and intended use.
- Verify constraints and caveats are documented for human review.
- Verify language remains consistent with human-final-decision governance in `docs/spec.md`.

## Milestone 3: Paper-Trading Evaluation Loop
Define a paper-trading protocol for measuring signal quality and operational discipline.

### Validation
- Verify evaluation metrics and review cadence are documented.
- Verify no live-trading automation is introduced without explicit approval.
- Verify paper-trading outcomes can be reviewed and traced in a repeatable way.

## Milestone 4: Controlled Production Hardening
Improve reliability and observability while keeping human-in-the-loop decision authority.

### Validation
- Verify production flow remains stable and reproducible.
- Verify rollout and rollback procedures are documented.
- Verify controls continue to prevent autonomous real-trade execution.


### Current roadmap checkpoint as of Step 135D
- Current product track is **AI Team Workbench + Daily Brief + Stock Dossier / Stock Review**.
- Repo history reflects recent completion of Step 135B (Stock Dossier v1 shell/read model), Step 135C (Stock Review first-layer UX polish), and Step 135D (HK strategy research reference docs-of-record).
- Immediate next implementation candidate is **Step 135E — Strategy Horizon Policy in Stock Dossier**.
- Legacy Step 91C / `latest_system_runs` path remains important baseline history, but is not the immediate next implementation slice for current product increment planning.

### Current roadmap checkpoint (post Step 91C)
#### Completed
- Step 91A/91B/91C runtime acceptance path completed.
- PR #98 merged with Railway request-shape fix.
- GitHub Actions workflow run `25424407687` passed as Step 91C acceptance evidence.

#### Immediate cleanup (next small follow-up)
- Step 91C-7B: wire optional Railway diagnostics into Step 91C workflow env:
  - `RAILWAY_TOKEN_SHA256_PREFIX`
  - `RAILWAY_CURL_PROBE`

#### Next product sequence
1. Implement `latest_system_runs` backend repository/provider.
2. Make `paper-daily-runner` write `latest_system_runs`.
3. Make `telegram-webhook` read latest bounded row.
4. Deploy + smoke.
5. Add Mini App frontend read-only fetch.

#### Validation/guardrails for upcoming runtime changes
- Any runtime/Railway/Supabase change must include an explicit acceptance path.
- Mini App remains read-only until bounded decision-capture phase is explicitly approved.
- No live-money execution path is introduced.
