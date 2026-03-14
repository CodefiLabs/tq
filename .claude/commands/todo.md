---
name: todo
description: Add tasks to a tq queue with optional scheduling
tags: tq, queue, tasks, schedule, tmux
allowed-tools: Bash(pwd), Bash(cat), Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [task description] [schedule]
---

Arguments: $ARGUMENTS

## Step 1 — Capture CWD and workspace context

1. Run `pwd` and store as `TASK_CWD`.
2. Read `~/.tq/workspace-map.md` (fall back to suggesting `/init` if missing).
3. Use the workspace map to resolve project names in `$ARGUMENTS` (e.g. "fix bug in samson" -> look up samson's path as `TASK_CWD`). Don't block if project is unlisted.

## Step 2 — Parse the request

From `$ARGUMENTS`, extract:
- **Task prompt(s)**: the work to do
- **Schedule** (optional): time/frequency language ("every morning", "daily at 9am", "weekly on mondays")
- **Queue name** (optional): if explicitly stated ("add to the refactor queue")

Queue name inference (if not explicit):
- From schedule keyword: "every morning" -> `morning`, "daily" -> `daily`, "weekday" -> `weekday`, "weekly" -> `weekly`, "hourly" -> `hourly`
- No schedule: use basename of `TASK_CWD`

If no arguments provided, list existing queues: `ls ~/.tq/queues/*.yaml 2>/dev/null`

## Step 3 — Read existing queue (if any)

Read `~/.tq/queues/<name>.yaml`. Note if it's a new file.

## Step 4 — Write the updated queue YAML

Merge tasks (never remove existing ones, dedup by exact prompt text). Always include `cwd:` at top.

Write to `~/.tq/queues/<name>.yaml`. If existing queue has a different `cwd:`, warn the user and ask which to keep before writing.

## Step 5 — Schedule (if detected)

Translate schedule to cron expression (e.g. "every morning" -> `0 9 * * *`, "every weekday" -> `0 9 * * 1-5`, "nightly" -> `0 22 * * *`).

Follow the same steps as `/schedule` to install cron entries and compute `reset:` TTL. Use `$(command -v tq)` for the binary path and `grep -v "tq.*/<name>\.yaml"` to avoid prefix collisions.

Skip scheduling entirely for unscheduled (one-off) tasks.

## Step 6 — Confirm

Show: queue file path and contents, `cwd` for task execution, cron schedule in plain English (or "not scheduled — run manually with `tq ~/.tq/queues/<name>.yaml`").

Related: `/schedule`, `/jobs`, `/health`
