---
name: jobs
description: List all scheduled tq cron jobs. Accepts optional natural language filter like "show morning queue jobs" or "what's scheduled for refactor".
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab), Bash(tq-status)
---

You are a cron schedule inspector for the `tq` CLI tool.

## Steps

1. **Read crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

2. **Filter tq lines**: Extract only lines containing `/tq` or `tq-status`.

3. **For each tq cron line**, display a formatted table with columns:
   - **Queue** — the queue filename (basename without path)
   - **Action** — `run` (for `tq`) or `status-check` (for `tq-status`)
   - **Schedule** — the cron expression
   - **Human** — plain-English description of the schedule (e.g. "daily at 9am", "every 30 min")
   - **Queue file** — full path

4. **Also show queue state summary** for each unique queue found:
   ```bash
   tq-status ~/.tq/queues/<name>.yaml 2>/dev/null
   ```

5. **If `$ARGUMENTS` mentions a specific queue**, filter the output to that queue only.

6. **If no tq jobs found**: Say so and suggest `/todo check something every morning` as an example.
