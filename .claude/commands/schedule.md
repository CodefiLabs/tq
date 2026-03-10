---
name: schedule
description: Add or update a cron schedule for a tq queue. Accepts natural language like "run the morning queue every day at 9am" or "schedule refactor queue every weekday at 6pm".
tags: tq, cron, schedule, queue
allowed-tools: Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
---

You are a cron schedule manager for the `tq` CLI tool.

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

   Given the cron expression from step 1, determine the minimum interval between consecutive runs and write `reset: <N>h` (or `reset: <N>d`) into the queue YAML as the first top-level key (before `cwd:`).

   **Inference rules** (apply the first that matches):
   - `*/N` in the hour field (e.g. `0 */4 * * *`) → interval = N hours → TTL = `floor(N * 0.5)`h
   - List in the hour field (e.g. `0 8,12,18 * * *`) → min gap = smallest difference between consecutive hours → TTL = `floor(min_gap * 0.5)`h
   - Single hour value with a weekly schedule (one specific day-of-week, e.g. `0 9 * * 1`) → interval = 168h → TTL = `3d`
   - Single hour value with any other schedule (daily, weekday, every-minute, etc.) → interval = 24h → TTL = `12h`
   - Always enforce a minimum of `1h` regardless of computed value

   Read the queue file with the Read tool, then:
   - If the file already has a `reset:` line with a non-auto value (e.g. `reset: on-complete` or any manually set value), **skip this step entirely — do not overwrite it**.
   - Otherwise, insert or replace `reset: <value>` as the very first line of the YAML (before `cwd:`), then write the file back with the Write tool.

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
