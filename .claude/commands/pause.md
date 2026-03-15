---
name: pause
description: Pause a tq queue's cron run schedule
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
argument-hint: <queue-name>
---

Pause a tq queue's cron schedule by removing the run line while keeping the status-check sweep. Accept natural language like "pause the weekday queue" or "pause morning".

Arguments: $ARGUMENTS

## Steps

1. **Infer the queue name** from `$ARGUMENTS` (e.g. "the weekday queue" -> `weekday`, "morning" -> `morning`).
   If no queue name is given, list tq run lines from the crontab and ask which to pause.

2. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

3. **Find the tq run line** for this queue (the `tq` run line, NOT `tq --status`).
   If not found, say "No active schedule found for `<name>` queue." and stop.

4. **Show the line** that will be removed before removing it.

5. **Remove only the tq run line**, keeping the `tq --status` sweep:
   ```bash
   (crontab -l 2>/dev/null | grep -v "^[^#]*tq [^-].*/<name>\.yaml") | crontab -
   ```
   The `tq --status` line is kept so state continues to be maintained.

6. **Verify** the line was actually removed:
   ```bash
   crontab -l 2>/dev/null | grep "/<name>\.yaml" || echo "(none)"
   ```

7. **Confirm**: Show what was removed and note that `tq --status` is still running.

Related: `/schedule <name>` to resume, `/unschedule <name>` to fully remove, `/jobs` to see all scheduled queues.
