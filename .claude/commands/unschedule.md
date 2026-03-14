---
name: unschedule
description: Remove all cron lines for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
argument-hint: [queue-name]
---

Fully remove all cron lines for a tq queue (both run and status-check). Accept natural language like "unschedule the weekday queue" or "remove morning from cron".

Arguments: $ARGUMENTS

## Steps

1. **Infer the queue name** from `$ARGUMENTS` (e.g. "the weekday queue" → `weekday`, "morning" → `morning`).
   If no queue name is given, list all tq cron lines and ask which to remove.

2. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

3. **Find all tq lines** for this queue (both `tq` run and `tq --status`).
   If none found, say "No cron schedule found for `<name>` queue."

4. **Remove all lines** referencing this queue:
   ```bash
   (crontab -l 2>/dev/null | grep -v "tq.*<name>.yaml") | crontab -
   ```

5. **Confirm**: Show what was removed. Note that the queue file and task state are untouched —
   only the cron schedule was removed. Suggest `/schedule <name>` to reschedule.
