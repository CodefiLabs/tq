---
name: schedule
description: Add or update cron schedule for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(ls), Bash(mkdir), Bash(crontab), Bash(grep), Read, Write
argument-hint: "[queue-name] [schedule]"
---

Add or update a cron schedule for a tq queue. Accepts natural language like "run the morning queue every day at 9am" or "schedule refactor every weekday at 6pm".

Arguments: $ARGUMENTS

## 1. Parse the request

Extract from `$ARGUMENTS`:
- Infer queue name (e.g. "the morning queue" -> `morning`, "refactor" -> `refactor`)
- Translate schedule to cron (see `references/cron-expressions.md` for mapping table)
- If a raw cron expression is given (5 space-separated fields), use it directly
- If no queue name given, list `~/.tq/queues/*.yaml` and ask which to schedule
- If no schedule given, ask: "What schedule? (e.g. 'every day at 9am')"

## 2. Validate queue file

```bash
ls ~/.tq/queues/<name>.yaml
```
If missing, say "Queue `<name>` not found. Run `/todo <task description>` to create it first." and stop.

## 3. Compute reset TTL

Auto-set `reset:` so tasks re-run on each scheduled cycle. Rule: TTL = half the cron interval (minimum `1h`).

| Cron pattern | TTL |
|---|---|
| `*/N` in hour field | `floor(N * 0.5)`h |
| Comma-list in hour | `floor(min_gap * 0.5)`h |
| Single hour, one day-of-week | `3d` |
| Single hour, daily | `12h` |

If `reset:` already exists with a named value (`daily`, `weekly`, `on-complete`, etc.), do not overwrite. Otherwise insert `reset:` before `cwd:`.

## 4. Ensure log dir exists

```bash
mkdir -p ~/.tq/logs
```

## 5. Read current crontab

```bash
crontab -l 2>/dev/null || echo ""
```

## 6. Build two cron lines

```
<cron-expression> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
```

## 7. Merge into crontab

Remove existing lines for this queue first, match on `/<name>\.yaml`:
```bash
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; echo "<line1>"; echo "<line2>") | crontab -
```

If crontab update fails, report the error and stop.

## 8. Confirm

Show the two crontab lines with plain-English meaning. If replacing an existing schedule, show before/after.

Related: `/jobs` to verify, `/unschedule` to remove, `/pause` to pause, `/todo` to create queues.
