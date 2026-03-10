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

Also read the workspace map for context:
```bash
cat ~/.tq/workspace-map.md 2>/dev/null || echo "(no workspace map — run /init to generate one)"
```

Use the workspace map to:
- Match a project name mentioned in `$ARGUMENTS` (e.g. "fix the login bug in samson" → look up `samson` → use its path as `TASK_CWD`)
- Confirm `TASK_CWD` is a known project (informational only — don't block if it's not listed)
- Suggest `cwd` if the user hasn't implied one and the current directory isn't a recognizable project

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
mkdir -p ~/.tq/logs
(crontab -l 2>/dev/null | grep -v "tq.*<name>.yaml"; \
  echo "<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

**After writing cron lines**, compute and write `reset: <N>h` (or `reset: <N>d`) into the queue YAML as the first top-level key (before `cwd:`).

**Inference rules** (apply the first that matches):
- `*/N` in the hour field (e.g. `0 */4 * * *`) → interval = N hours → TTL = `floor(N * 0.5)`h
- List in the hour field (e.g. `0 8,12,18 * * *`) → min gap = smallest difference between consecutive hours → TTL = `floor(min_gap * 0.5)`h
- Single hour value with a weekly schedule (one specific day-of-week, e.g. `0 9 * * 1`) → interval = 168h → TTL = `3d`
- Single hour value with any other schedule (daily, weekday, etc.) → interval = 24h → TTL = `12h`
- Always enforce a minimum of `1h` regardless of computed value

Re-read the queue file you just wrote in Step 4, then:
- If it already has a `reset:` line (e.g. it was there before this command ran), **skip — do not overwrite it**.
- Otherwise, prepend `reset: <value>` as the very first line (before `cwd:`), then rewrite the file with the Write tool.

If no schedule was detected in Step 2, skip this reset computation entirely — do not add `reset:` to one-off tasks.

## Step 6 — Confirm

Show:
- Queue file path and contents
- `cwd` that will be used when tasks run
- Cron schedule in plain English (or "not scheduled — run manually with `tq ~/.tq/queues/<name>.yaml`")
