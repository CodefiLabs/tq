---
name: tq
description: >
  This skill should be used when the user asks to "add to queue", "run queue", "queue these tasks",
  "schedule with tq", "tq status", "check task queue", "check queue status", "create a tq queue",
  "set up cron for tq", "run claude in background", "batch prompts in tmux",
  "background claude sessions", "headless claude", "automate claude tasks",
  "schedule claude tasks", "start a conversation", "start conversation mode",
  "converse via telegram", "telegram conversation mode", "telegram bot", "message routing",
  "route a message", "spawn a session", "list conversations", "stop conversation",
  "stop session", "orchestrator", "reset tasks", "reset queue", "clear task state",
  "notify on completion", "tq notification", "send telegram message", "reply via telegram",
  "tq health", "check tq health", "what's running", "what tasks are done",
  "tq setup", "setup telegram bot", "tq install", "pause schedule", "resume schedule",
  "remove from cron", "unschedule queue", "lint tq scripts", "review tq changes",
  "configure workspaces", "workspace setup", or wants to manage Claude prompts running
  in tmux sessions via the tq CLI tool. Triggers on phrases like "queue", "tq", "task queue",
  "tmux queue", "scheduled claude tasks", "conversation mode", "telegram chat", "converse",
  "telegram session", "poll telegram", "tq-converse", "tq-message", "task notification",
  "cron job", "tmux session", "queue file", "queue yaml".
version: 1.4.0
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
schedule: "0 9 * * *"              # optional -- auto-managed crontab via tq-cron-sync
reset: daily                        # optional -- daily|weekly|hourly|always|on-complete
cwd: /path/to/working/directory     # where claude runs for each task
message:                            # optional -- notification config
  service: telegram
  content: summary                  # summary|status|details|log
tasks:
  - name: review-auth               # optional -- used for session naming
    prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```

Queue files are read-only — tq never modifies them. Create/update queues via `/todo`.

### Reset Modes

Reset controls when task state is cleared so tasks re-run:

| Mode | Behavior |
|------|----------|
| `daily` | Clear once per calendar day |
| `weekly` | Clear once per ISO week |
| `hourly` | Clear once per hour |
| `always` | Clear on every `tq` run |
| `on-complete` | Per-task: delete state after task finishes |

## State

State dir: `<queue-dir>/.tq/<queue-basename>/` (e.g., `~/.tq/queues/.tq/morning/`)
One file per task, named by 8-char SHA-256 of the prompt:

```
status=running
session=tq-fix-the-login-451234
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

## Cron Scheduling

Add `schedule:` to any queue YAML and `tq-cron-sync` auto-manages crontab (runs every 20 min, scans `~/.tq/queues/*.yaml`). Each scheduled queue gets two cron lines:

```cron
<schedule> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
```

The `tq --status` line runs every 30 min to reap dead sessions and flip their state to `done`.

See `references/cron-expressions.md` for natural language to cron mapping.

## Queue Name Inference

When `/todo` has no explicit queue name: derive from schedule keyword ("every morning" -> `morning`, "daily" -> `daily`) or fall back to `basename` of cwd.

## Resetting State

- One task: `rm .tq/<queue-basename>/<hash>`
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

## Background Scripts

| Script | Purpose |
|--------|---------|
| `tq-cron-sync` | Scans `~/.tq/queues/*.yaml` every 20 min, syncs `schedule:` to crontab |
| `tq-telegram-poll` | Long-polls Telegram, routes messages via 3-tier routing |
| `tq-telegram-watchdog` | Ensures poll cron entry exists |
| `tq-message` | Sends notifications (Telegram/Slack) on task completion |

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Tasks stuck in `running` | tmux session died | `tq --status <queue>` reaps dead sessions |
| Same task re-runs after `done` | Prompt text changed (new hash) | Delete old state: `rm .tq/<queue>/<old-hash>` |
| Cron not firing | Missing crontab entry | `/schedule <queue> <time>` or check `tq-cron-sync` |
| Telegram messages not routing | Poll not running | `/health` → check poll cron |
| Chrome not connecting | Wrong profile or extension missing | See `references/chrome-integration.md` |

## Additional Resources

- **`references/session-naming.md`** — session/window name algorithm and examples
- **`references/cron-expressions.md`** — natural language to cron mapping table
- **`references/chrome-integration.md`** — Chrome `--chrome` flag, profile setup, troubleshooting
