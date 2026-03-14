---
name: pause
description: Pause a tq queue's cron run schedule
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab), Bash(grep)
argument-hint: "[queue-name]"
---

Pause a tq queue's cron schedule by removing the run line while keeping the status-check sweep. Accept natural language like "pause the weekday queue" or "pause morning".

Arguments: $ARGUMENTS

## 1. Infer queue name

Extract queue name from `$ARGUMENTS` (e.g. "the weekday queue" -> `weekday`, "morning" -> `morning`).
If no queue name is given, list tq run lines from the crontab and ask which to pause.

## 2. Read current crontab

```bash
crontab -l 2>/dev/null || echo "(no crontab)"
```

## 3. Find the tq run line

Locate the `tq` run line for this queue (NOT `tq --status`).
If not found, say "No active schedule found for `<name>` queue." and stop.

## 4. Show the line

Display the line that will be removed before removing it.

## 5. Remove the run line

Remove only the tq run line, keeping the `tq --status` sweep:
```bash
(crontab -l 2>/dev/null | grep -v "^[^#]*tq [^-].*/<name>\.yaml") | crontab -
```
Use `/<name>\.yaml` to avoid matching queues with similar prefixes (e.g. `morning` vs `morning-review`).
The `tq --status` line is kept so dead sessions are still reaped.

## 6. Verify removal

```bash
crontab -l 2>/dev/null | grep "<name>.yaml" || echo "(none)"
```

If the run line still appears, report the error and stop.

## 7. Confirm

Show a summary:

| Item | Value |
|------|-------|
| Queue | `<name>` |
| Removed | run line (`<cron-expression>`) |
| Kept | `tq --status` sweep (every 30 min) |
| Resume | `/schedule <name> <time>` |

Related: `/schedule` to resume, `/unschedule` to fully remove, `/jobs` to list all.
