# tq Cron Expression Reference

## Natural Language to Cron Mapping

| Natural Language | Cron Expression | Notes |
|-----------------|-----------------|-------|
| "every morning" / "daily at 9am" | `0 9 * * *` | Default morning time |
| "every night" / "nightly" | `0 22 * * *` | 10pm |
| "every weekday" | `0 9 * * 1-5` | Mon-Fri at 9am |
| "every weekday at 6pm" | `0 18 * * 1-5` | Mon-Fri at 6pm |
| "every monday" / "weekly on mondays" | `0 9 * * 1` | 9am Monday |
| "every monday at 8am" | `0 8 * * 1` | 8am Monday |
| "every hour" / "hourly" | `0 * * * *` | Top of each hour |
| "every 4 hours" | `0 */4 * * *` | Every 4 hours |
| "every 30 minutes" | `*/30 * * * *` | Every 30 min |
| "daily" | `0 9 * * *` | Default to 9am |
| "weekly" | `0 9 * * 1` | Default to Monday 9am |

## Day-of-Week Numbers

| Number | Day |
|--------|-----|
| 0 or 7 | Sunday |
| 1 | Monday |
| 2 | Tuesday |
| 3 | Wednesday |
| 4 | Thursday |
| 5 | Friday |
| 6 | Saturday |

## Automatic vs Manual Crontab Management

Two paths to scheduling:

| Method | How | When |
|--------|-----|------|
| **Automatic** (`tq-cron-sync`) | Add `schedule:` key to queue YAML. `tq-cron-sync` syncs to crontab every 20 min. | Preferred — source of truth lives in the queue file. |
| **Manual** (`/schedule`, `/todo`) | Commands directly modify crontab. | When you need immediate scheduling or custom cron expressions. |

If a queue has a `schedule:` key, `tq-cron-sync` manages it. Manual edits will be overwritten on the next sync cycle. To override: remove the `schedule:` key from the YAML first.

## Standard tq Crontab Block

Every scheduled queue gets two cron lines:

```cron
# Run queue (spawn pending tasks)
<cron> $(command -v tq) ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1

# Status sweep (reap dead sessions every 30 min)
*/30 * * * * $(command -v tq) --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
```

## Updating Crontab

Replace existing lines for the same queue by filtering out old entries before appending new ones:

```bash
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; \
  echo "<cron> $(command -v tq) ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * $(command -v tq) --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

The `grep -v` removes all existing lines referencing this queue before appending new ones, preventing duplicates.

## Queue Name to Schedule Name Inference

When no queue name is given, infer from the schedule keyword:

| Schedule keyword | Queue name |
|-----------------|------------|
| "morning" / "9am" | `morning` |
| "daily" | `daily` |
| "weekday" / "weekdays" | `weekday` |
| "weekly" / "monday" | `weekly` |
| "hourly" / "every hour" | `hourly` |
| "nightly" / "night" | `nightly` |
| no schedule | `basename` of current working directory |
