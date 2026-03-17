---
name: tq-reply
description: Send response back to Telegram user
tags: tq, telegram, reply, conversation
allowed-tools: Bash(tq2,python3)
argument-hint: (no arguments — auto-detects session from $TQ_SESSION_ID)
---

Send your response back to the Telegram user via tq.

## Steps

1. Read the session ID from the environment:

```bash
echo "$TQ_SESSION_ID"
```

If `TQ_SESSION_ID` is empty, stop and report: "No session ID found. This command must run inside a tq session."

2. Write a concise, Telegram-friendly response:
   - Lead with the answer or result
   - Keep under 3500 characters
   - Use plain text (Telegram markdown is fragile)
   - No filler ("I successfully...", "Sure, I can...")

3. Send via tq:

```bash
tq2 reply "$TQ_SESSION_ID" "<your response text>"
```

If tq2 is not on PATH, use the full path: `python3 /path/to/v2/tq2 reply ...`

The response will be threaded as a reply to the user's most recent message in this session.
