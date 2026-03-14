---
name: jobs
description: List scheduled tq cron jobs and queue status
tags: tq, cron, schedule, queue, status
allowed-tools: Bash(crontab), Bash(tq), Bash(ls)
argument-hint: [queue-name]
---

List all scheduled tq cron jobs with their queue status. Accepts optional filter like "show morning jobs" or "what's scheduled for refactor".

Arguments: $ARGUMENTS

## Steps

1. **Read crontab and filter**:
   ```bash
   crontab -l 2>/dev/null | grep '/tq ' || true
   ```
   If no tq lines found, say "No tq cron jobs scheduled." and suggest `/todo <task> every morning` or `/schedule <queue> <time>`. Stop.

2. **If `$ARGUMENTS` names a specific queue**, filter to lines matching that queue filename only.

3. **Display a table** with one row per cron line:

   | Queue | Action | Schedule | Human | Path |
   |-------|--------|----------|-------|------|
   | morning | run | `0 9 * * *` | daily at 9am | `~/.tq/queues/morning.yaml` |
   | morning | status-check | `*/30 * * * *` | every 30 min | `~/.tq/queues/morning.yaml` |

   - **Action**: `run` for `tq <queue>`, `status-check` for `tq --status <queue>`
   - **Human**: plain-English translation of the cron expression

4. **Show queue state** for each unique queue found:
   ```bash
   tq --status ~/.tq/queues/<name>.yaml 2>/dev/null
   ```
   If the queue file no longer exists, warn: "Queue file missing -- cron entry is orphaned. Run `/unschedule <name>` to clean up."

5. If `$ARGUMENTS` filter matched no queues, say so and list the queue names that do exist.

Related: `/schedule` to add/update, `/unschedule` to remove, `/todo` to create queues.
