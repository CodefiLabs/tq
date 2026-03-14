---
name: health
description: Verify tq binaries, cron, queues, and logs
tags: tq, health, status, diagnostics, check, verify
allowed-tools: Bash(ls), Bash(which), Bash(crontab), Bash(tmux), Bash(tail), Bash(tq), Bash(tq-converse), Bash(cat), Bash(grep), Bash(test), Bash(launchctl), Bash(python3)
argument-hint: "[queue-name]"
---

Arguments: $ARGUMENTS

Run all checks below, then summarize with a pass/warn/fail status for each. If `$ARGUMENTS` names a specific queue, focus checks 3-6 on that queue only. Never stop on individual check failures — run all checks and report aggregate results.

## 1. Binary check

Verify all tq binaries exist and are executable:
```bash
for BIN in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
  which "$BIN" 2>/dev/null && echo "$BIN: pass" || echo "$BIN: FAIL"
done
```
Fail: suggest `/install`.

## 2. Cron jobs check

Run `crontab -l 2>/dev/null | grep tq`. Warn if no tq cron jobs found. Flag any queue that has a `schedule:` key in its YAML but no corresponding crontab entry.

## 3. Queue inventory

List `~/.tq/queues/*.yaml`. For each queue, run `tq --status ~/.tq/queues/<name>.yaml` and summarize: total tasks, done/running/pending counts. Warn if any queue has 0 tasks or only pending tasks with no cron schedule. Warn if no queue files exist and suggest `/todo` to create one.

## 4. Zombie session check

For any task with `status=running` in state files, verify the tmux session is alive with `tmux has-session -t "<session>"`. Flag running-state tasks whose session is dead.

## 5. Log check

```bash
tail -50 ~/.tq/logs/tq.log 2>/dev/null | grep -iE 'error|failed|exit code' || echo "(clean)"
```

Warn if log file is missing but cron jobs are configured. Warn if log file exceeds 10MB (suggest rotation).

## 6. Conversation mode check

| Check | Command | Fail Action |
|-------|---------|-------------|
| Orchestrator alive | `tmux has-session -t tq-orchestrator 2>/dev/null` | Suggest `/converse start` |
| Registry valid JSON | `python3 -c "import json; json.load(open('$HOME/.tq/conversations/registry.json'))"` | Warn: corrupt registry |
| Telegram config | `test -f ~/.tq/config/message.yaml` | Suggest `/setup-telegram` |
| Poll running | `crontab -l 2>/dev/null \| grep tq-telegram-poll` or `launchctl list com.tq.telegram-poll` | Suggest `tq-telegram-watchdog` |

Warn if orchestrator is down but conversations are registered.

## 7. Config check

Verify workspace config:
- `~/.tq/config/workspaces.yaml` exists (suggest `/init` if missing)
- `~/.tq/workspace-map.md` exists and is not stale (warn if older than 30 days)

## Output format

Print a summary table:

```
SYSTEM CHECK          STATUS   NOTES
--------------------  -------  ----------------------------------------
tq binaries           pass     7/7 on PATH
cron jobs             pass     2 jobs registered
queues found          pass     3 queues (morning, refactor, cleanup)
morning queue         pass     5 done, 0 running, 0 pending
zombie sessions       pass     none
recent log errors     pass     no errors in last 50 lines
conversation mode     pass     orchestrator running, 2 active sessions
workspace config      pass     32 projects cataloged
```

Then show per-queue `tq --status` output beneath.

Related: `/install` for missing binaries, `/converse` for session management, `/setup-telegram` for bot config, `/init` for workspace setup, `/jobs` for cron details.
