# Auto Cron Sync — Design Spec

**Date:** 2026-03-10
**Status:** Approved

## Problem

Users must manually add crontab lines after installing tq and after creating each new queue file. This friction breaks the "drop a queue file and go" experience.

## Solution

Queue files declare their own schedule via a `schedule:` key. A new `tq-cron-sync` script syncs crontab automatically — running at install time and every 20 minutes thereafter via a self-bootstrapped watcher entry.

## Queue File Format Change

Add an optional top-level `schedule:` key accepting a raw cron expression:

```yaml
schedule: "0 9 * * *"
cwd: /Users/kk/Sites/myproject
tasks:
  - name: morning-review
    prompt: "Review yesterday's commits and summarize in docs/daily.md"
```

- Queue files without `schedule:` are ignored by `tq-cron-sync` — existing manually-scheduled queues are unaffected
- Raw cron expressions only (no natural language parsing); LLMs can translate natural language for users at queue-creation time
- The existing Python parser already skips unknown top-level keys — no breakage

## `tq-cron-sync` Script

### Location
`scripts/tq-cron-sync` — symlinked into PATH by the installer alongside `tq`, `tq-message`, etc.

### Interface
```
tq-cron-sync [--interval <minutes>]
```
`--interval` controls the self-watcher cron frequency (default: 20).

### Algorithm
1. Scan `~/.tq/queues/*.yaml` — extract `schedule:` value and queue name via embedded Python
2. Read current crontab (`crontab -l 2>/dev/null || echo ""`)
3. Strip all lines tagged `# tq-managed:*`
4. Rebuild managed entries for each queue with a `schedule:` key:
   - **Run entry:** `<schedule> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1 # tq-managed:<name>:run`
   - **Status-check entry:** `*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1 # tq-managed:<name>:status`
5. Add or update self-watcher: `*/<interval> * * * * /opt/homebrew/bin/tq-cron-sync >> ~/.tq/logs/tq-cron-sync.log 2>&1 # tq-managed:tq-cron-sync`
6. Write merged crontab back via `echo "..." | crontab -`

### Full-Sync Semantics
Wipe-and-rebuild on every run. This handles additions, removals, and changes to `schedule:` expressions uniformly — no diffing or state tracking required. A queue whose cron expression changed gets the new value written automatically on the next sync.

### What Gets Synced
All queue files in `~/.tq/queues/` — both user queues and any tq-managed system queues live in the same directory. No distinction between tiers.

### TQ_BIN Detection
Checks `/opt/homebrew/bin/tq` then `/usr/local/bin/tq`, consistent with installer resolution logic.

## Installer Changes (`tq-install.sh`)

1. Add `tq-cron-sync` to the symlink loop
2. After symlinking, call `tq-cron-sync --interval 20`
3. Replace the manual crontab example in the output message with a note that schedules are auto-managed via the `schedule:` queue key

## Implementation Delivery

Implementation tasks are queued in `~/.tq/queues/tq-schedule-feature.yaml` and executed via tq itself (self-hosted). Tasks run sequentially in the tq project directory.

## Files Changed

| File | Change |
|------|--------|
| `scripts/tq-cron-sync` | **New** — core sync script |
| `scripts/tq-install.sh` | Add symlink + post-install call |
| `.claude/rules/queue-format.md` | Document `schedule:` key |

## Non-Goals

- Natural language schedule parsing (use an LLM at queue-creation time)
- Per-queue status-check interval (fixed at `*/30 * * * *`)
- Multi-user / system-wide queue directories
