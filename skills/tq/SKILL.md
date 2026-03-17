---
name: tq
description: >
  Use when the user mentions "tq", "telegram bot", "queue tasks",
  "tmux sessions", "daemon", "tq status", "tq run", "tq setup",
  or wants to manage Claude Code sessions via Telegram.
version: 2.0.0
---

# tq — Claude Code sessions via Telegram + tmux

Every Telegram message spawns a Claude Code session in tmux.
Reply to continue. That's it.

## CLI

```
tq daemon start       # start the Telegram daemon
tq daemon stop        # stop it
tq daemon status      # check if running
tq status             # list all sessions
tq stop <id>          # kill a session
tq run <prompt>       # one-shot session
tq run queue.yaml     # batch sessions from YAML
tq reply <id> <text>  # send reply to Telegram (used by /tq-reply)
tq setup              # configure Telegram bot
```

## How It Works

1. User sends message on Telegram
2. Daemon receives it, spawns a Claude Code session in tmux
3. Claude processes the prompt
4. Claude uses `/tq-reply` to send response back to Telegram
5. User replies to continue the conversation (threaded)

## Routing Rules

- Reply to a tracked message → route to that session
- New message → spawn new session

## Queue Files

Optional batch format:

```yaml
cwd: ~/project
tasks:
  - Review the code
  - Run the test suite
```

## State

All state in `~/.tq/tq.db` (SQLite). Config in `~/.tq/config.json`.
