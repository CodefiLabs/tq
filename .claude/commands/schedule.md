---
name: schedule
description: Add or update a cron schedule for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [queue-name] [schedule]
---

Add or update a cron schedule for a tq queue. Accept natural language like "run the morning queue every day at 9am" or "schedule refactor queue every weekday at 6pm".

Arguments: $ARGUMENTS

## Steps

1. **Interpret the request naturally** from `$ARGUMENTS`:
   - Infer the queue name (e.g. "the morning queue" -> `morning`, "refactor" -> `refactor`)
   - Translate the schedule description into a cron expression:
     - "every day at 9am" -> `0 9 * * *`
     - "every weekday at 6pm" -> `0 18 * * 1-5`
     - "every hour" -> `0 * * * *`
     - "every 4 hours" -> `0 */4 * * *`
     - "every monday at 8am" -> `0 8 * * 1`
   - If a raw cron expression is given, use it directly
   - If no schedule is mentioned, ask: "What schedule? (e.g. 'every day at 9am', 'every weekday at 6pm')"

2. **Validate the queue file exists**:
   ```bash
   ls ~/.tq/queues/<name>.yaml
   ```
   If missing, suggest running `/todo <name>` first.

2b. **Compute and write `reset:` TTL**:

   Determine the minimum interval between consecutive cron runs. Write `reset: <N>h` (or `<N>d`) as the first top-level key in the queue YAML (before `cwd:`).

   **Inference rules** (first match wins):
   | Cron pattern | Interval | TTL |
   |---|---|---|
   | `*/N` in hour field | N hours | `floor(N * 0.5)`h |
   | Comma-list in hour field | smallest gap between hours | `floor(min_gap * 0.5)`h |
   | Single hour, one day-of-week | 168h | `3d` |
   | Single hour, any other | 24h | `12h` |

   Minimum: `1h`. Read the queue file first. If `reset:` already has a non-auto value (e.g. `on-complete`), skip this step entirely. Otherwise insert or replace `reset:` before `cwd:`.

3. **Ensure log dir exists**:
   ```bash
   mkdir -p ~/.tq/logs
   ```

4. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo ""
   ```

5. **Build the two cron lines** for this queue:
   ```
   <cron-expression> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   */30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   ```

6. **Merge into crontab**:
   - Remove any existing lines referencing `tq` and this queue name
   - Append the two new lines
   - Write back with: `(crontab -l 2>/dev/null | grep -v "tq.*<name>.yaml"; echo "<line1>"; echo "<line2>") | crontab -`

7. **Confirm**: Show the updated crontab lines for this queue and what they do.
