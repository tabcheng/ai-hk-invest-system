# Operator Quick Reference: Telegram Notification Outcomes

This page is a simple cheat sheet for what to do when you see a Telegram notification outcome.

Use this when you need a **first action** quickly.

## Quick map

| Outcome | What it usually means | First thing to check | Escalate when |
| --- | --- | --- | --- |
| `sent` | The message was delivered successfully. | Confirm the message content looks correct for the run/date. | The message content looks wrong or incomplete. |
| `skipped` | The system decided no message should be sent (for example, nothing important to notify). | Check run output to confirm there was no notify-worthy result to send. | You expected a notification, but skip keeps happening for multiple runs. |
| `deduped` | A similar message was already sent, so this one was intentionally not sent again. | Check whether a message for the same run/date already exists in Telegram logs/chat history. | You see frequent deduping but cannot find any earlier message to match it. |
| `failed` | The system tried to send a message, but delivery failed. | Check Telegram bot token/chat ID configuration and basic bot reachability first. | Failure repeats after config/reachability checks, or failures continue for 2+ runs. |

## Outcome details (beginner-friendly)

### 1) `sent`

**What it means in plain language**
- Good news: the notification was delivered.

**What to check first**
- Open the message and make sure the date, totals, and ticker labels look reasonable.
- If the content looks normal, no further action is needed.

**When to escalate**
- Escalate if the message format is broken, values look clearly wrong, or key expected sections are missing.

---

### 2) `skipped`

**What it means in plain language**
- The system intentionally did not send a message.
- This is often normal when there is nothing useful to notify.

**What to check first**
- Confirm the run finished.
- Confirm whether that run had any notify-worthy outcome.
- If there was nothing important to send, `skipped` is expected.

**When to escalate**
- Escalate if you expected a message and still get `skipped` across multiple runs/days.

---

### 3) `deduped`

**What it means in plain language**
- The system avoided sending a duplicate notification.
- This is usually normal during reruns or repeat attempts.

**What to check first**
- Check whether a similar message for the same run date was already sent.
- If yes, `deduped` is expected.

**When to escalate**
- Escalate if `deduped` appears often but no earlier matching message can be found.

---

### 4) `failed`

**What it means in plain language**
- A delivery attempt happened, but Telegram did not accept/send it.

**What to check first**
- Verify Telegram configuration values (bot token and chat ID).
- Verify the bot can still reach the chat/channel.
- Check for obvious environment/config mistakes first.

**When to escalate**
- Escalate immediately for production-critical runs.
- Otherwise escalate after repeated failures (for example, 2 or more runs in a row).

## Simple escalation rule of thumb

If you are unsure:
1. Start with the first check in the table.
2. If the same issue repeats, escalate with run IDs and timestamps.
3. Include the exact outcome value (`sent`, `skipped`, `deduped`, or `failed`) in your escalation note.
