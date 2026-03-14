---
name: pause
description: Pause a tq queue's cron run schedule
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
argument-hint: [queue-name]
---

Pause a tq queue's cron schedule by removing the run line while keeping the status-check sweep. Accept natural language like "pause the weekday queue" or "pause morning".

Arguments: $ARGUMENTS

## Steps

1. **Infer the queue name** from `$ARGUMENTS` (e.g. "the weekday queue" → `weekday`, "morning" → `morning`).
   If no queue name is given, list tq run lines from the crontab and ask which to pause.

2. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

3. **Find the tq run line** for this queue (the `tq` run line, not `tq --status`).
   If not found, say "No active schedule found for `<name>` queue."

4. **Show the line to be removed** before modifying crontab. Ask for confirmation if the user is in interactive mode.

5. **Remove only the tq run line**, keeping the `tq --status` sweep:
   ```bash
   (crontab -l 2>/dev/null | grep -v "^[^#]*tq [^-].*/<name>\.yaml") | crontab -
   ```
   Use `/<name>\.yaml` (escaped dot, path separator) to avoid matching `morning-review` when pausing `morning`.

6. **Confirm**: Show what was removed and note that `tq --status` is still running.
   Suggest `/schedule <name>` to resume.

Related: `/schedule`, `/unschedule`, `/jobs`
