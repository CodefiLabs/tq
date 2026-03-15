# tq Cron Expression Reference

All cron expressions use the **system timezone** (check with `date +%Z`). There is no per-queue timezone override.

## Natural Language to Cron Mapping

| Natural Language | Cron Expression | Notes |
|-----------------|-----------------|-------|
| "every morning" / "daily at 9am" | `0 9 * * *` | Default morning time |
| "every night" / "nightly" | `0 22 * * *` | 10pm |
| "every weekday" | `0 9 * * 1-5` | Mon-Fri at 9am |
| "every weekday at 6pm" | `0 18 * * 1-5` | Mon-Fri at 6pm |
| "every monday" / "weekly on mondays" | `0 9 * * 1` | 9am Monday |
| "every monday at 8am" | `0 8 * * 1` | 8am Monday |
| "weekends" / "every weekend" | `0 10 * * 0,6` | Sat & Sun at 10am |
| "every hour" / "hourly" | `0 * * * *` | Top of each hour |
| "every 2 hours" | `0 */2 * * *` | Every 2 hours |
| "every 4 hours" | `0 */4 * * *` | Every 4 hours |
| "every 30 minutes" | `*/30 * * * *` | Every 30 min |
| "every 15 minutes" | `*/15 * * * *` | Every 15 min |
| "every 5 minutes" | `*/5 * * * *` | Every 5 min |
| "twice daily" / "morning and evening" | `0 9,18 * * *` | 9am and 6pm |
| "business hours" | `0 9-17 * * 1-5` | Every hour 9am-5pm Mon-Fri |
| "daily" | `0 9 * * *` | Default to 9am |
| "weekly" | `0 9 * * 1` | Default to Monday 9am |
| "first of the month" | `0 9 1 * *` | 9am on the 1st |

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

## Crontab Management

`tq-cron-sync` automatically manages crontab entries — see SKILL.md for details. For manual override, filter out old entries before appending:

```bash
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; \
  echo "<cron> $(command -v tq) ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * $(command -v tq) --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

## Queue Name Inference

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

Related: `/schedule` and `/todo` use this mapping. `/jobs` displays active schedules.
