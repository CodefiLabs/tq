---
name: jobs
description: List scheduled tq cron jobs and queue status
tags: tq, cron, schedule, queue, status, list
allowed-tools: Bash(crontab), Bash(tq), Bash(ls), Bash(test)
argument-hint: "[queue-name]"
---

Arguments: $ARGUMENTS

List all scheduled tq cron jobs with queue status. Optional filter: "morning", "refactor", etc.

## 1. Read crontab

```bash
crontab -l 2>/dev/null | grep '/tq ' || true
```

If no tq lines found, report "No tq cron jobs scheduled." and suggest `/todo <task> every morning` or `/schedule <queue> <time>`. Stop.

## 2. Filter (if specified)

If `$ARGUMENTS` names a queue, filter to lines matching that filename (use `/<name>\.yaml` to avoid prefix collisions).

## 3. Display table

| Queue | Action | Schedule | Human-readable | Path |
|-------|--------|----------|----------------|------|
| morning | run | `0 9 * * *` | daily 9am | `~/.tq/queues/morning.yaml` |
| morning | sweep | `*/30 * * * *` | every 30 min | `~/.tq/queues/morning.yaml` |

**Action**: `run` for `tq <queue>`, `sweep` for `tq --status <queue>`

## 4. Queue state

For each unique queue:
```bash
test -f ~/.tq/queues/<name>.yaml && tq --status ~/.tq/queues/<name>.yaml 2>/dev/null
```

If queue file is missing, warn: "Orphaned cron entry — run `/unschedule <name>` to clean up."

## 5. No match

If `$ARGUMENTS` filter matched nothing, report that and list existing queue names.

Related: `/schedule` to add, `/unschedule` to remove, `/pause` to pause, `/todo` to create.
