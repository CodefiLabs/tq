---
name: tq
description: >
  This skill should be used when the user asks to "add to queue", "run queue", "queue these tasks",
  "schedule with tq", "tq status", "check task queue", "create a tq queue", "set up cron for tq",
  "run claude in background", "batch prompts in tmux", or wants to manage Claude prompts running
  in tmux sessions via the tq CLI tool. Triggers on phrases like "queue", "tq", "task queue",
  "tmux queue", "scheduled claude tasks".
version: 1.0.0
---

# tq — Claude Task Queue Runner

Scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/tq`, `${CLAUDE_PLUGIN_ROOT}/scripts/tq-status`

Installed to PATH via `/install`: `/opt/homebrew/bin/tq`, `/opt/homebrew/bin/tq-status`

## Overview

tq batches Claude prompts into YAML queue files and spawns each as an independent tmux session.
Tasks are idempotent — running `tq` again skips `done` and live `running` tasks.

## Queue File Format

Location: `~/.claude/queues/<name>.yaml`

```yaml
cwd: /path/to/working/directory   # optional — where claude runs for each task
tasks:
  - prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```

Queue files are **read-only** — tq never modifies them.

## State

State dir: `~/.claude/queues/.tq/<queue-basename>/`
One file per task, named by 8-char shasum of the prompt:

```
status=running
session=fix-the-login-23451
window=fix-the
prompt=fix the login bug in auth service
started=2026-03-05T10:00:00
```

Statuses: `pending` → `running` → `done`

## Commands

| Command | Purpose |
|---------|---------|
| `/todo <natural language>` | Create/update queue + optionally schedule |
| `/schedule <natural language>` | Add/update cron schedule for a queue |
| `/pause <queue>` | Remove run line, keep status-check (resume with `/schedule`) |
| `/unschedule <queue>` | Remove all cron lines for a queue |
| `/jobs [filter]` | List all scheduled tq cron jobs |
| `/health [queue]` | System-wide diagnostics |
| `/install` | Symlink tq binaries to PATH |

## CLI Usage

```bash
tq <queue.yaml>         # spawn pending tasks in tmux; skip running/done
tq-status <queue.yaml>  # print status table; flip dead sessions to done
```

## Crontab Pattern

```cron
0 9 * * * /opt/homebrew/bin/tq ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq-status ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1
```

The `tq-status` cron runs every 30 min to reap dead sessions and flip their state to `done`.

## Queue Name Inference

When using `/todo` without an explicit queue name:

- Schedule keyword present → use it: "every morning" → `morning`, "daily" → `daily`, "weekly" → `weekly`
- No schedule → use `basename` of current working directory

## Reset

- One task: delete its state file from `.tq/<queue-basename>/`
- Entire queue: `rm -rf ~/.claude/queues/.tq/<queue-basename>/`

## Chrome Integration

tq launches claude with `--chrome` and opens **Chrome Profile 5** (halbotkirchner@gmail.com) automatically before connecting.

### Multiple Chrome profiles / extensions

If you need to interact with a Chrome profile that has a different Claude extension instance (e.g. different account), use the `chrome-devtools` MCP with the `--isolated` flag to run isolated browser extension sessions that don't conflict across profiles.

### Setting the browser display name

The Claude extension stores the browser name as `bridgeDisplayName` in the extension's `chrome.storage.local`. To set it for the first time on a profile:
- Right-click the Claude extension icon in the Chrome toolbar → **Options**
- Or open the sidepanel and look for a settings/gear icon with a name field

## Additional Resources

- **`references/session-naming.md`** — Session/window name generation algorithm and examples
- **`references/cron-expressions.md`** — Natural language → cron expression mapping table
