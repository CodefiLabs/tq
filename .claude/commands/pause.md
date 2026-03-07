---
name: pause
description: Pause a tq queue's cron schedule by removing the run line while keeping the status-check sweep. Accepts natural language like "pause the weekday queue" or "pause morning".
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
---

You are a cron schedule manager for the `tq` CLI tool.

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

4. **Remove only the tq run line**, keeping the `tq --status` sweep:
   ```bash
   (crontab -l 2>/dev/null | grep -v "^[^#]*tq [^-].*<name>.yaml") | crontab -
   ```
   (The `tq --status` line is kept so state continues to be maintained.)

5. **Confirm**: Show what was removed and note that `tq --status` is still running.
   Suggest `/schedule <name>` to resume.
