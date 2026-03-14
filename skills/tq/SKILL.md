---
name: tq
description: >
  This skill should be used when the user asks to "add to queue", "run queue", "queue these tasks",
  "schedule with tq", "tq status", "check task queue", "create a tq queue", "set up cron for tq",
  "run claude in background", "batch prompts in tmux", "start a conversation", "start conversation mode",
  "converse via telegram", "telegram conversation mode", "telegram bot", "message routing",
  "route a message", "spawn a session", "orchestrator", or wants to manage Claude prompts running
  in tmux sessions via the tq CLI tool. Triggers on phrases like "queue", "tq", "task queue",
  "tmux queue", "scheduled claude tasks", "conversation mode", "telegram chat", "converse",
  "telegram session", "poll telegram", "tq-converse".
version: 1.2.0
---

# tq -- Claude Task Queue Runner

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/tq`

Installed to PATH via `/install`: `/opt/homebrew/bin/tq`

## Overview

tq manages Claude Code sessions via tmux in two modes:

1. **Queue mode** -- batch prompts into YAML queue files, spawn each as an independent tmux session. Idempotent: re-running `tq` skips `done` and live `running` tasks.
2. **Conversation mode** -- maintain persistent interactive Claude Code sessions orchestrated via Telegram. An orchestrator routes messages to the right conversation, spawning new sessions or resuming existing ones.

## Queue File Format

Location: `~/.tq/queues/<name>.yaml`

```yaml
cwd: /path/to/working/directory   # optional -- where claude runs for each task
tasks:
  - prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```

Queue files are read-only -- tq never modifies them.

## State

State dir: `~/.tq/queues/.tq/<queue-basename>/`
One file per task, named by 8-char SHA-256 of the prompt:

```
status=running
session=fix-the-login-23451
window=fix-the
prompt=fix the login bug in auth service
started=2026-03-05T10:00:00
```

Statuses: `pending` -> `running` -> `done`

## Commands

| Command | Purpose |
|---------|---------|
| `/todo <natural language>` | Create/update queue and optionally schedule |
| `/schedule <natural language>` | Add/update cron schedule for a queue |
| `/pause <queue>` | Remove run line, keep status-check (resume with `/schedule`) |
| `/unschedule <queue>` | Remove all cron lines for a queue |
| `/jobs [filter]` | List all scheduled tq cron jobs |
| `/health [queue]` | Run system-wide diagnostics |
| `/install` | Symlink tq binaries to PATH |
| `/init` | Configure workspace directories and build project catalog |
| `/review` | Lint and review staged changes before commit |
| `/converse [start\|stop\|status\|list]` | Manage conversation orchestrator and sessions |
| `/tq-reply` | Send response back to Telegram (conversation mode) |
| `/tq-message` | Write and send task completion summary |
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

- Schedule keyword present -> derive from it: "every morning" -> `morning`, "daily" -> `daily`, "weekly" -> `weekly`
- No schedule -> use `basename` of current working directory

## Reset

- One task: delete its state file from `.tq/<queue-basename>/`
- Entire queue: `rm -rf ~/.tq/queues/.tq/<queue-basename>/`

## Conversation Mode

Start the orchestrator via `tq-converse start` or send `/converse` from Telegram.

The orchestrator routes incoming Telegram messages using 3-tier routing:

1. **Reply threading** -- Telegram reply to a known message routes to that session automatically
2. **Slug prefix** -- `#slug message` routes to the named session
3. **Orchestrator fallback** -- new topic triggers the orchestrator to spawn a new session with a descriptive slug

Each conversation is a persistent Claude Code interactive session in its own tmux window.
Child sessions use `/tq-reply` to send responses back to Telegram as threaded replies.

### Key CLI commands

```bash
tq-converse start                         # start orchestrator
tq-converse spawn <slug> --cwd <dir>      # create new conversation session
tq-converse route <slug> <message>        # send message to a session
tq-converse list                          # list active sessions
tq-converse status                        # show all session statuses
tq-converse stop [<slug>]                 # stop session or orchestrator
```

## Additional Resources

- **`references/session-naming.md`** -- session/window name generation algorithm and examples
- **`references/cron-expressions.md`** -- natural language to cron expression mapping table
- **`references/chrome-integration.md`** -- Chrome profile setup, multiple profiles, and browser display name configuration
