---
name: todo
description: Add tasks to a tq queue with optional scheduling
tags: tq, queue, tasks, schedule
allowed-tools: Bash(pwd), Bash(cat), Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [task description] [schedule]
---

Add task(s) to a tq queue file. Optionally schedule the queue via cron. Accepts natural language like "review auth module every morning" or "add tests to the refactor queue".

Arguments: $ARGUMENTS

## Step 1 -- Capture CWD and workspace context

1. Run `pwd` and store as `TASK_CWD`.
2. Read `~/.tq/workspace-map.md`. If missing, warn "No workspace map found -- run `/init` to set one up." but continue.
3. Use the workspace map to resolve project names in `$ARGUMENTS` (e.g. "fix bug in samson" -> look up samson's path as `TASK_CWD`). Continue even if project is unlisted.

## Step 2 -- Parse the request

If no arguments provided, list existing queues (`ls ~/.tq/queues/*.yaml 2>/dev/null`) and stop.

From `$ARGUMENTS`, extract:
- **Task prompt(s)**: the work to do
- **Schedule** (optional): time/frequency language ("every morning", "daily at 9am", "weekly on mondays")
- **Queue name** (optional): if explicitly stated ("add to the refactor queue")

Queue name inference (if not explicit):
- From schedule keyword: "every morning" -> `morning`, "daily" -> `daily`, "weekday" -> `weekday`, "weekly" -> `weekly`, "hourly" -> `hourly`
- No schedule: use basename of `TASK_CWD`

## Step 3 -- Read or create queue

```bash
mkdir -p ~/.tq/queues
```

Read `~/.tq/queues/<name>.yaml` if it exists. Note whether this is a new or existing file.

## Step 4 -- Write the updated queue YAML

Merge tasks into existing queue (never remove existing tasks, dedup by exact prompt text). Always include `cwd:` at top.

Write to `~/.tq/queues/<name>.yaml`. If existing queue has a different `cwd:`, warn the user and ask which to keep before writing.

Format must follow queue-format rules: required keys `cwd` and `tasks`, optional `schedule`, `reset`, `message`.

## Step 5 -- Schedule (if schedule language detected)

If no schedule language in `$ARGUMENTS`, skip to Step 6.

Add `schedule:` to the queue YAML with the translated cron expression (e.g. "every morning" -> `"0 9 * * *"`). Then install cron entries using the same approach as `/schedule` — see that command's steps 3-7 for cron installation and reset TTL computation.

## Step 6 -- Confirm

Show:
- Queue file path and full contents
- `cwd` for task execution
- Cron schedule in plain English, or "Not scheduled -- run manually with `tq ~/.tq/queues/<name>.yaml`"

Related: `/schedule` to change schedule, `/jobs` to list all cron jobs, `/unschedule` to remove schedule.
