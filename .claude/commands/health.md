---
name: health
description: Verify tq binaries, cron, queues, and logs
tags: tq, health, status, diagnostics
allowed-tools: Bash(ls), Bash(command), Bash(crontab), Bash(tmux), Bash(tail), Bash(tq), Bash(cat), Bash(grep)
argument-hint: [queue-name]
---

Arguments: $ARGUMENTS

Run all checks below, then summarize with a pass/warn/fail status for each. If `$ARGUMENTS` names a specific queue, focus checks 3-6 on that queue only.

## 1. Binary check

Check all 7 binaries: `tq`, `tq-converse`, `tq-message`, `tq-telegram-poll`, `tq-telegram-watchdog`, `tq-cron-sync`, `tq-setup`.

```bash
for bin in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
  command -v "$bin" >/dev/null 2>&1 && echo "pass: $bin" || echo "FAIL: $bin"
done
```

Fail: suggest `/install`.

## 2. Cron jobs check

Run `crontab -l 2>/dev/null | grep tq`. Warn if no tq cron jobs found. Check for orphaned entries referencing missing queue files.

## 3. Queue inventory

List `~/.tq/queues/*.yaml`. For each queue, run `tq --status ~/.tq/queues/<name>.yaml` and summarize: total tasks, done/running/pending counts. Warn if any queue has 0 tasks or only pending tasks with no cron schedule.

## 4. Zombie session check

For any task with `status=running` in state files, verify the tmux session is alive with `tmux has-session -t "<session>"`. Flag running-state tasks whose session is dead.

## 5. Conversation mode check

Check if the orchestrator is running: `tmux has-session -t tq-orchestrator 2>/dev/null`. List active conversation sessions: `ls ~/.tq/conversations/sessions/*/current-slug 2>/dev/null`. Warn if registry is stale (sessions in registry but tmux sessions dead).

## 6. Config check

Verify workspace config exists: `~/.tq/config/workspaces.yaml`. Check messaging config: `~/.tq/config/message.yaml`. Warn if messaging config has insecure permissions:
```bash
stat -f '%Lp' ~/.tq/config/message.yaml 2>/dev/null
```
Should be `600`. Warn if more permissive.

## 7. Log check

Run `tail -50 ~/.tq/logs/tq.log`. Surface lines containing `error`, `Error`, `failed`, or `Exit code`. Warn if log file is missing but cron jobs are configured. Also check `~/.tq/logs/tq-telegram.log` if Telegram is configured.

## Output format

```
SYSTEM CHECK          STATUS   NOTES
--------------------  -------  ----------------------------------------
tq binaries           pass     7/7 found in PATH
cron jobs             pass     2 run + 2 status-check entries
queues found          pass     3 queues (morning, refactor, cleanup)
morning queue         pass     5 done, 0 running, 0 pending
zombie sessions       pass     none
conversation mode     pass     orchestrator running, 2 active sessions
config files          pass     workspaces + messaging configured
recent log errors     warn     1 error in last 50 lines
```

Related: `/jobs`, `/install`
