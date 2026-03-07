---
name: todo
description: Add tasks to a tq queue, capture CWD, and optionally schedule — all in one command. Natural language. Examples: "check my linkedin saved posts every morning", "refactor the auth module weekly on mondays", "fix the login bug" (no schedule = just add to queue).
tags: tq, queue, tasks, schedule, tmux
allowed-tools: Bash(pwd), Bash(cat), Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
---

You are a task queue manager for the `tq` CLI tool.

Arguments: $ARGUMENTS

## Step 1 — Capture CWD

Run immediately:
```bash
pwd
```
Store this as `TASK_CWD`. This is where `claude` will run when the task executes.

## Step 2 — Parse the request naturally

From `$ARGUMENTS`, extract:
- **Task prompt(s)**: the actual work to be done (e.g. "check my linkedin saved posts using the linkedin skill")
- **Schedule** (optional): any time/frequency language (e.g. "every morning", "daily at 9am", "every weekday", "weekly on mondays at 8am")
- **Queue name** (optional): if explicitly stated (e.g. "add to the refactor queue")

**Queue name inference** (if not explicit):
- Schedule keyword -> name: "every morning" -> `morning`, "daily" -> `daily`, "weekday" -> `weekday`, "weekly" -> `weekly`, "hourly" -> `hourly`
- No schedule -> use basename of `TASK_CWD` (e.g. `/Users/kk/projects/myapp` -> `myapp`)

**If no arguments**: list existing queues: `ls ~/.tq/queues/*.yaml 2>/dev/null`

## Step 3 — Read existing queue (if any)

```bash
cat ~/.tq/queues/<name>.yaml 2>/dev/null || echo "(new file)"
```

## Step 4 — Write the updated queue YAML

Merge tasks (never remove existing ones, dedup by exact prompt text). Always include `cwd:` at the top.

```yaml
cwd: <TASK_CWD>
tasks:
  - prompt: <existing prompt>
  - prompt: <new prompt>
```

Write to `~/.tq/queues/<name>.yaml`

**Note on cwd**: If an existing queue already has a `cwd:` and it differs from `TASK_CWD`, warn the user and ask which to keep before writing.

## Step 5 — Schedule (if a schedule was detected)

Translate the schedule to a cron expression:
- "every morning" / "daily at 9am" -> `0 9 * * *`
- "every weekday" -> `0 9 * * 1-5`
- "every monday at 8am" -> `0 8 * * 1`
- "every hour" -> `0 * * * *`
- "every night" / "nightly" -> `0 22 * * *`
- "weekly on mondays" -> `0 9 * * 1`

Then:
```bash
mkdir -p ~/.claude/logs
(crontab -l 2>/dev/null | grep -v "tq.*<name>.yaml"; \
  echo "<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.claude/logs/tq.log 2>&1"; \
  echo "*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.claude/logs/tq.log 2>&1") | crontab -
```

## Step 6 — Confirm

Show:
- Queue file path and contents
- `cwd` that will be used when tasks run
- Cron schedule in plain English (or "not scheduled — run manually with `tq ~/.tq/queues/<name>.yaml`")
