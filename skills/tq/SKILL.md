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

## Session Lifecycle

```
tq suspend <id>       # gracefully stop (resumable)
tq resume <id>        # resume a suspended session
tq stop <id>          # kill (non-resumable)
```

### Recovering session IDs from orphaned tmux sessions

If tmux sessions exist without tracked `claude_session_id` (legacy or crash), extract IDs by sending `/exit` to the Claude TUI:

```bash
tmux send-keys -t "<tmux_session>:0.0" "/exit" Enter
# wait a few seconds
tmux capture-pane -t "<tmux_session>:0.0" -p -S -30 | grep 'claude --resume'
# → claude --resume <uuid>
```

Claude exits gracefully, prints the resume command, and the tmux shell stays alive. Safe to kill the tmux session after capturing the ID.

## State

All state in `~/.tq/tq.db` (SQLite). Config in `~/.tq/config.json`.
