---
name: schedule
description: Add or update cron schedule for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [queue-name] [schedule]
---

Add or update a cron schedule for a tq queue. Accepts natural language like "run the morning queue every day at 9am" or "schedule refactor every weekday at 6pm".

Arguments: $ARGUMENTS

## Steps

1. **Parse the request** from `$ARGUMENTS`:
   - Infer queue name (e.g. "the morning queue" -> `morning`, "refactor" -> `refactor`)
   - Translate schedule to cron expression:
     - "every day at 9am" -> `0 9 * * *`
     - "every weekday at 6pm" -> `0 18 * * 1-5`
     - "every hour" -> `0 * * * *`
     - "every 4 hours" -> `0 */4 * * *`
     - "every monday at 8am" -> `0 8 * * 1`
   - If a raw cron expression is given (5 space-separated fields), use it directly
   - If no queue name given, list `~/.tq/queues/*.yaml` and ask which to schedule
   - If no schedule given, ask: "What schedule? (e.g. 'every day at 9am')"

2. **Validate the queue file exists**:
   ```bash
   ls ~/.tq/queues/<name>.yaml
   ```
   If missing, say "Queue `<name>` not found. Run `/todo <task description>` to create it first." and stop.

3. **Compute `reset:` TTL** based on the cron interval:

   | Cron pattern | Interval | TTL |
   |---|---|---|
   | `*/N` in hour field | N hours | `floor(N * 0.5)`h |
   | Comma-list in hour field | smallest gap | `floor(min_gap * 0.5)`h |
   | Single hour, one day-of-week | 168h | `3d` |
   | Single hour, any other | 24h | `12h` |

   Minimum: `1h`. Read the queue file. If `reset:` already exists with a named value (`daily`, `weekly`, `on-complete`, etc.), skip -- do not overwrite. Otherwise insert or replace `reset:` before `cwd:`.

4. **Ensure log dir exists**:
   ```bash
   mkdir -p ~/.tq/logs
   ```

5. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo ""
   ```

6. **Build two cron lines**:
   ```
   <cron-expression> $(command -v tq) ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   */30 * * * * $(command -v tq) --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   ```

7. **Merge into crontab** (remove existing lines for this queue first, match on `/<name>\.yaml`):
   ```bash
   (crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; echo "<line1>"; echo "<line2>") | crontab -
   ```

8. **Confirm**: Show the two new crontab lines and their plain-English meaning. If replacing an existing schedule, note what changed.

Related: `/jobs` to verify, `/unschedule <name>` to remove, `/todo` to create queues.
