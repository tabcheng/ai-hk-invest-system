# Operator Quick Reference: Telegram Notification Outcomes

Use this page when you need a quick, first action.

## One-minute map

| Outcome | What it usually means | First action (do this first) | Escalate when |
| --- | --- | --- | --- |
| `sent` | Message delivery worked. | Open the message and quickly confirm the run date and content look correct. | Content looks wrong or incomplete. |
| `skipped` | System intentionally did not send a message. | Check whether the run had anything important to notify. | You expected a message, but `skipped` repeats across runs. |
| `deduped` | System blocked a duplicate message. | Check whether the same run-date message was already sent earlier. | You cannot find any earlier matching message. |
| `failed` | System tried to send, but delivery failed. | Check bot token/chat ID and basic bot-to-chat reachability. | Failure repeats after checks, or it affects 2+ runs in a row. |

## Simple definitions

### `sent`
- **Usually means:** success.
- **First action:** verify message content looks reasonable.
- **Escalate:** if content is clearly wrong.

### `skipped`
- **Usually means:** no notification was needed for that run.
- **First action:** confirm there was no notify-worthy output.
- **Escalate:** if it keeps happening when you expected messages.

### `deduped`
- **Usually means:** a matching message was already sent.
- **First action:** look for an earlier message for the same run date.
- **Escalate:** if dedupe happens but no earlier message exists.

### `failed`
- **Usually means:** Telegram delivery error.
- **First action:** check config values and bot/chat reachability.
- **Escalate:** after repeated failures (2+ runs) or for urgent production runs.

## Escalation note template (copy/paste)

`Run <run_id>, outcome=<sent|skipped|deduped|failed>, observed at <timestamp>, first checks completed: <short note>.`
