---
name: unschedule
description: Remove cron schedule for a tq queue
tags: tq, cron, schedule, queue, remove
allowed-tools: Bash(crontab), Bash(ls), Bash(grep)
argument-hint: "<queue-name>"
---

Remove all cron lines (both run and status-check) for a tq queue. Accepts natural language like "unschedule the weekday queue" or "remove morning from cron".

Arguments: $ARGUMENTS

## 1. Infer queue name

Extract queue name from `$ARGUMENTS` (e.g. "the weekday queue" -> `weekday`, "morning" -> `morning`).
If no queue name given, list all tq cron lines (`crontab -l 2>/dev/null | grep '/tq '`) and ask which to remove.

## 2. Read current crontab

```bash
crontab -l 2>/dev/null || echo "(no crontab)"
```

## 3. Find matching tq lines

Match the exact queue filename to avoid false positives (e.g. "morning" must not remove "morning-review"):
```bash
crontab -l 2>/dev/null | grep "tq.*/<name>\.yaml"
```
If none found, say "No cron schedule found for `<name>` queue." and stop.

## 4. Show and remove

Show what will be removed and the lines being kept. Then remove:
```bash
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml") | crontab -
```

If crontab update fails, report the error and stop.

## 5. Confirm removal

Note that the queue file (`~/.tq/queues/<name>.yaml`) and task state are untouched -- only the cron schedule was removed.

Related: `/schedule` to reschedule, `/pause` to pause run only, `/jobs` to verify removal.
