---
name: todo
description: Add tasks to a tq queue with optional scheduling
tags: tq, queue, tasks, schedule, tmux
allowed-tools: Bash(pwd), Bash(ls), Bash(mkdir), Bash(crontab), Bash(grep), Read, Write
argument-hint: "[task description] [schedule]"
---

Add task(s) to a tq queue file. Optionally schedule the queue via cron. Accepts natural language like "review auth module every morning" or "add tests to the refactor queue".

Arguments: $ARGUMENTS

## 1. Resolve working directory

1. Run `pwd` → `TASK_CWD`. If `pwd` fails, stop: "Cannot determine working directory."
2. Read `~/.tq/workspace-map.md`. If missing, warn "No workspace map — run `/init`." but continue.
3. If `$ARGUMENTS` names a project (e.g. "fix bug in samson"), resolve via workspace map. If unlisted, continue with current `TASK_CWD`.

## 2. Parse the request

If no arguments provided, list existing queues (`ls ~/.tq/queues/*.yaml 2>/dev/null`) and stop.

From `$ARGUMENTS`, extract:
- **Task prompt(s)**: the work to do
- **Schedule** (optional): time/frequency language ("every morning", "daily at 9am", "weekly on mondays")
- **Queue name** (optional): if explicitly stated ("add to the refactor queue")

Queue name inference (if not explicit):
- From schedule keyword: "every morning" -> `morning`, "daily" -> `daily`, "weekday" -> `weekday`, "weekly" -> `weekly`, "hourly" -> `hourly`
- No schedule: use basename of `TASK_CWD`

## 3. Read or create queue

```bash
mkdir -p ~/.tq/queues
```

Read `~/.tq/queues/<name>.yaml` if it exists. Note whether this is a new or existing file.

## 4. Write the updated queue YAML

Merge tasks into existing queue (never remove existing tasks, dedup by exact prompt text). Always include `cwd:` at top.

Write to `~/.tq/queues/<name>.yaml`. If the write fails, stop: "Failed to write queue file — check permissions on `~/.tq/queues/`." If existing queue has a different `cwd:`, warn the user and ask which to keep before writing.

Format must follow queue-format rules: required keys `cwd` and `tasks`, optional `schedule`, `reset`, `message`.

## 5. Schedule (if schedule language detected)

If no schedule language in `$ARGUMENTS`, skip to step 6.

Translate to cron expression (e.g. "every morning" -> `0 9 * * *`, "every weekday" -> `0 9 * * 1-5`, "nightly" -> `0 22 * * *`).

Install cron entries (match on exact queue filename to avoid clobbering other queues):
```bash
mkdir -p ~/.tq/logs
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; \
  echo "<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

Compute `reset:` TTL using the same rules as `/schedule` (see step 3 there). Insert before `cwd:` unless `reset:` already exists with a named value.

## 6. Confirm

Show:

| Item | Value |
|------|-------|
| Queue file | `~/.tq/queues/<name>.yaml` |
| Working dir | `<cwd>` |
| Tasks | `<count>` total (`<new>` new) |
| Schedule | plain English or "manual: `tq ~/.tq/queues/<name>.yaml`" |
| Reset | `<mode>` or "none" |

Then display the full queue file contents.

Related: `/schedule` to change schedule, `/jobs` to list all, `/unschedule` to remove.
