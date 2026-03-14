---
name: tq-message
description: Send task completion summary via messaging
tags: tq, notify, message, summary, telegram
allowed-tools: Bash(tq-message), Bash(which), Bash(test)
argument-hint: "<task-hash> <queue-file>"
---

Arguments: $ARGUMENTS

## 1. Validate

Check `tq-message` is on PATH:
```bash
which tq-message
```
If missing, stop: "Run `/install` first."

Extract from `$ARGUMENTS`:
- **First**: task hash (8 hex chars, e.g. `a1b2c3d4`)
- **Second**: queue file path (absolute, ending `.yaml`)

If no arguments provided, stop: "Usage: `/tq-message <task-hash> <queue-file>`"
If hash is not exactly 8 hex characters, stop: "Invalid task hash: expected 8 hex chars (e.g. `a1b2c3d4`)."
If path doesn't end in `.yaml`, stop: "Invalid queue file: expected `.yaml` path."
If `~/.tq/config/message.yaml` is missing, stop: "No messaging config found — run `/setup-telegram` first."

## 2. Write summary

Write a specific summary of what was accomplished:

| Rule | Example |
|------|---------|
| Lead with output | "Wrote a 106-line guide at docs/tips.md" |
| 3-6 numbered items | Each with em dash description |
| Max 3500 chars | Telegram limit minus prefix |
| No filler | Never "I successfully..." or "In this session..." |

## 3. Send

```bash
tq-message --task "<HASH>" --queue "<QUEUE_FILE>" --message '<summary>'
```

If exit code is non-zero, report the error and stop.

Do not narrate. Write summary, run command.

Related: `/tq-reply` (conversation replies), `/converse` (sessions)
