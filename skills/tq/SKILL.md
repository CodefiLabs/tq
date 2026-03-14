---
name: tq
description: >
  This skill should be used when the user asks to "add to queue", "run queue", "queue these tasks",
  "schedule with tq", "tq status", "check task queue", "create a tq queue", "set up cron for tq",
  "run claude in background", "batch prompts in tmux", "start a conversation", "converse via telegram",
  "telegram conversation mode", or wants to manage Claude prompts running in tmux sessions via the
  tq CLI tool. Triggers on phrases like "queue", "tq", "task queue", "tmux queue", "scheduled claude tasks",
  "conversation mode", "telegram chat", "converse".
version: 1.1.0
---

# tq — Claude Task Queue Runner

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/tq`

Installed to PATH via `/install`: `/opt/homebrew/bin/tq`

## Overview

tq manages Claude Code sessions via tmux in two modes:
1. **Queue mode** — batches prompts into YAML queue files, spawns each as an independent tmux session. Idempotent — running `tq` again skips `done` and live `running` tasks.
2. **Conversation mode** — persistent interactive Claude Code sessions orchestrated via Telegram. An orchestrator routes messages to the right conversation, creating new sessions or resuming existing ones.

## Queue File Format

Location: `~/.tq/queues/<name>.yaml`

```yaml
cwd: /path/to/working/directory   # optional — where claude runs for each task
tasks:
  - prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```

Queue files are **read-only** — tq never modifies them.

## State

State dir: `~/.tq/queues/.tq/<queue-basename>/`
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
| `/converse [start\|stop\|status]` | Manage Telegram conversation sessions |
| `/tq-reply` | Send response back to Telegram (conversation mode) |
| `/setup-telegram` | Configure Telegram bot token and notifications |

## CLI Usage

```bash
tq <queue.yaml>           # spawn pending tasks in tmux; skip running/done
tq --status <queue.yaml>  # print status table; flip dead sessions to done
```

## Crontab Pattern

```cron
0 9 * * * /opt/homebrew/bin/tq ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1
```

The `tq --status` cron runs every 30 min to reap dead sessions and flip their state to `done`.

## Queue Name Inference

When using `/todo` without an explicit queue name:

- Schedule keyword present → use it: "every morning" → `morning`, "daily" → `daily`, "weekly" → `weekly`
- No schedule → use `basename` of current working directory

## Reset

- One task: delete its state file from `.tq/<queue-basename>/`
- Entire queue: `rm -rf ~/.tq/queues/.tq/<queue-basename>/`

## Chrome Integration

tq launches claude with `--chrome` and opens **Chrome Profile 5** (halbotkirchner@gmail.com) automatically before connecting.

### Multiple Chrome profiles / extensions

If you need to interact with a Chrome profile that has a different Claude extension instance (e.g. different account), use the `chrome-devtools` MCP with the `--isolated` flag to run isolated browser extension sessions that don't conflict across profiles.

### Setting the browser display name

The Claude extension stores the browser name as `bridgeDisplayName` in the extension's `chrome.storage.local`. To set it for the first time on a profile:
- Right-click the Claude extension icon in the Chrome toolbar → **Options**
- Or open the sidepanel and look for a settings/gear icon with a name field

## Conversation Mode

Start an orchestrator: `tq-converse start` or send `/converse` from Telegram.

The orchestrator routes incoming Telegram messages to the appropriate conversation session:
- Telegram reply to a known message → routes to that session automatically
- `#slug message` → routes to the named session
- New topic → orchestrator spawns a new session with a descriptive slug

Each conversation is a persistent Claude Code interactive session in its own tmux window.
Child sessions use `/tq-reply` to send responses back to Telegram as threaded replies.

### Conversation CLI

```bash
tq-converse start                         # start orchestrator
tq-converse spawn <slug> --cwd <dir>      # new conversation session
tq-converse route <slug> <message>        # send to a session
tq-converse list                          # list active sessions
tq-converse stop [<slug>]                 # stop session or orchestrator
```

### Telegram Commands

| Command | Purpose |
|---------|---------|
| `/converse` | Start the orchestrator |
| `/stop [slug]` | Stop orchestrator or a specific session |
| `/status` | Show all sessions |
| `/list` | List active conversations |

## Additional Resources

- **`references/session-naming.md`** — Session/window name generation algorithm and examples
- **`references/cron-expressions.md`** — Natural language → cron expression mapping table
