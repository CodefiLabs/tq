---
name: health
description: Verify tq binaries, cron, queues, and logs
tags: tq, health, status, diagnostics
allowed-tools: Bash(ls), Bash(which), Bash(crontab), Bash(tmux), Bash(tail), Bash(tq), Bash(cat), Bash(grep)
argument-hint: [queue-name]
---

Arguments: $ARGUMENTS

Run all checks below, then summarize with a pass/warn/fail status for each. If `$ARGUMENTS` names a specific queue, focus checks 3-5 on that queue only.

## 1. Binary check

Run `ls -la /opt/homebrew/bin/tq` and `which tq`. Pass if exists and executable. Fail: suggest `/install`.

## 2. Cron jobs check

Run `crontab -l 2>/dev/null | grep tq`. Warn if no tq cron jobs found.

## 3. Queue inventory

List `~/.tq/queues/*.yaml`. For each queue, run `tq --status ~/.tq/queues/<name>.yaml` and summarize: total tasks, done/running/pending counts. Warn if any queue has 0 tasks or only pending tasks with no cron schedule.

## 4. Zombie session check

For any task with `status=running` in state files, verify the tmux session is alive with `tmux has-session -t "<session>"`. Flag running-state tasks whose session is dead.

## 5. Log check

Run `tail -50 ~/.tq/logs/tq.log`. Surface lines containing `error`, `Error`, `failed`, or `Exit code`. Warn if log file is missing but cron jobs are configured.

## Output format

Print a summary table:

```
SYSTEM CHECK          STATUS   NOTES
--------------------  -------  ----------------------------------------
tq binary             pass     /opt/homebrew/bin/tq
cron jobs             pass     2 jobs registered
queues found          pass     3 queues (morning, refactor, cleanup)
morning queue         pass     5 done, 0 running, 0 pending
zombie sessions       pass     none
recent log errors     pass     no errors in last 50 lines
```

Then show per-queue `tq --status` output beneath.
