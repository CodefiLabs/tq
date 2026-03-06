---
name: health
description: System-wide health check for tq. Verifies binaries, cron jobs, queue states, and log errors. No arguments needed, or say "check morning queue" to focus on one.
tags: tq, health, status, diagnostics
allowed-tools: Bash(ls), Bash(which), Bash(crontab), Bash(tmux), Bash(tail), Bash(tq-status)
---

You are a diagnostic assistant for the `tq` task queue system.

Arguments: $ARGUMENTS

## Steps

Run all checks, then summarize with a pass/warn/fail status for each.

### 1. Binary check
```bash
ls -la /opt/homebrew/bin/tq /opt/homebrew/bin/tq-status 2>&1
which tq tq-status 2>&1
```
Pass: both exist and are executable. Fail: missing — suggest running `/install`.

### 2. Cron jobs check
```bash
crontab -l 2>/dev/null | grep tq || echo "(no tq cron jobs)"
```
Warn if no cron jobs found (tq is only useful when scheduled or run manually).

### 3. Queue inventory
```bash
ls ~/.tq/queues/*.yaml 2>/dev/null || echo "(no queues)"
```
For each queue found, run:
```bash
tq-status ~/.tq/queues/<name>.yaml 2>/dev/null
```
Summarize per queue: total tasks, how many done/running/pending.
Warn if any queue has 0 tasks or only pending tasks with no cron schedule.

### 4. Zombie session check
For any task showing `status=running` in state files, verify the tmux session is alive:
```bash
tmux has-session -t "<session>" 2>&1
```
Flag any running-state tasks whose session is dead (these should have been caught by `tq-status` but weren't).

### 5. Log check
```bash
tail -50 ~/.claude/logs/tq.log 2>/dev/null || echo "(no log file)"
```
Scan for lines containing `error`, `Error`, `failed`, or `Exit code` and surface them.
Warn if log file doesn't exist and cron jobs are configured (logging may be broken).

## Output format

Print a summary table:

```
SYSTEM CHECK          STATUS   NOTES
--------------------  -------  ----------------------------------------
tq binary             pass     /opt/homebrew/bin/tq
tq-status binary      pass     /opt/homebrew/bin/tq-status
cron jobs             pass     2 jobs registered
queues found          pass     3 queues (morning, refactor, cleanup)
morning queue         pass     5 done, 0 running, 0 pending
refactor queue        warn     0 done, 0 running, 2 pending — never run?
zombie sessions       pass     none
recent log errors     pass     no errors in last 50 lines
```

Then show per-queue `tq-status` output beneath.

If `$ARGUMENTS` mentions a specific queue, focus checks 3-5 on that queue only.
