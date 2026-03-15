# Operator Runbook: Telegram Notification Troubleshooting (v1)

This guide helps a non-technical operator answer one simple question:

**"Why did I not get a Telegram message for today’s run?"**

Use this checklist in order. Stop when you find the answer.

---

## Quick outcomes (what happened?)

By the end of this runbook, your case should fit into one of these buckets:

1. **No signal**
   - The run did not finish correctly, so no final summary could be delivered.
2. **No notification needed**
   - The run finished, but there was nothing meaningful to send (for example, no qualifying output), or delivery was intentionally skipped/deduplicated.
3. **Delivery failure**
   - The run finished and should have sent a message, but Telegram delivery failed (configuration/reachability/API issue).

---

## Step 1 — Did the run complete?

Start with the run status.

- If status is `FAILED` (or the run never reached a final success state), treat this as **No signal** first.
- If status is `SUCCESS`, continue to Step 2.

Why this matters:
- Telegram summary delivery is best-effort at end-of-run. If the run does not complete correctly, notification behavior can be incomplete.

Operator note:
- If the run failed, escalate the run failure first. Notification troubleshooting comes second.

---

## Step 2 — Was there anything to notify?

If the run completed, check whether there was meaningful output for a summary.

Ask:
1. Did the run produce any signal or summary-worthy results?
2. Is this a day where output is expected to be empty or minimal?

If there was nothing meaningful to send, this is usually **No notification needed**, not a system break.

---

## Step 3 — Are Telegram environment variables configured?

Confirm that required Telegram settings exist in the deployment environment:

- Bot token variable (example: Telegram bot API token)
- Chat target variable (example: destination chat ID)

Common beginner issues:
- Variable name typo
- Extra spaces or quotes in values
- Value pasted into the wrong variable
- Variable set in staging but not in production

If required variables are missing/invalid, classify as **Delivery failure** (configuration).

---

## Step 4 — Is the bot/chat reachable?

Even with variables set, delivery can fail if the bot cannot reach the target.

Simple checks:
1. Has the bot been added to the target chat?
2. If a channel/group is used, does the bot have permission to post?
3. Has the chat ID changed or become invalid?
4. Was the bot token rotated/revoked?

If reachability/permission is broken, classify as **Delivery failure** (reachability/permission).

---

## Step 5 — Was delivery skipped, deduped, or failed?

Check run/notification logs and classify:

- **Skipped intentionally**
  - The system decided not to send for this run path.
  - Outcome: usually **No notification needed**.

- **Deduplicated**
  - Message was intentionally not re-sent because an equivalent summary was already sent.
  - Outcome: **No notification needed** (expected duplicate protection).

- **Failed**
  - Attempt happened, but Telegram send returned an error.
  - Outcome: **Delivery failure**.

Tip:
- “No message received” is not always a bug. Skipped/deduped paths can be healthy behavior.

---

## Decision table (fast triage)

- Run not successful → **No signal**
- Run successful + nothing meaningful to summarize → **No notification needed**
- Run successful + skipped/deduped by design → **No notification needed**
- Run successful + attempted send failed → **Delivery failure**

---

## Escalation checklist

Escalate when any of these are true:

1. Multiple consecutive successful runs have Telegram delivery failures.
2. Environment variables are correct, but send attempts still fail.
3. Bot/chat permissions look correct, but API errors persist.
4. A dedup/skip decision appears incorrect for the run date/target.
5. You cannot determine whether the case is “no notification needed” vs “delivery failure.”

Include this context in escalation:

- Run ID and run date
- Final run status (`SUCCESS`/`FAILED`)
- Whether output existed to notify
- Telegram env-var check result (configured/missing)
- Bot/chat reachability check result
- Log classification (skipped, deduped, failed) and exact error text if failed
- Whether issue is one-off or repeated across runs

---

## Plain-language examples

- **Example A: No signal**
  - Run failed early due to upstream processing issue.
  - Telegram summary missing is expected side-effect.

- **Example B: No notification needed**
  - Run completed but produced no summary-worthy content.
  - No Telegram message is acceptable.

- **Example C: Delivery failure**
  - Run completed and had content, but Telegram API returned unauthorized/forbidden.
  - Fix token/permissions and retry next run.

---

## Guardrail reminder

This system provides decision-support signals. Human oversight remains required for investment decisions.
