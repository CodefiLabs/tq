# CLAUDE.md — tq v2

## Overview

`tq` spawns Claude Code sessions in tmux, controlled via Telegram.
Every message = a session. Reply to continue. That's it.

Pure Python. Zero external dependencies. ~800 lines across 5 files.

## Architecture

```
tq/
  cli.py        # entry point + subcommands + queue parser
  daemon.py     # telegram long-poll + tmux health loop
  session.py    # tmux spawn/stop/route + hook generation
  store.py      # SQLite schema + queries (2 tables)
  telegram.py   # Bot API send/receive/react

~/.tq/
  tq.db         # all state (SQLite with WAL)
  config.json   # telegram bot token, chat_id, default_cwd
  hooks/<id>/   # generated per-session hooks (runtime only)
  daemon.pid    # daemon process ID
  daemon.log    # daemon stdout/stderr
```

One state location. One config file. One daemon process.

## Development

```bash
# Run CLI
python3 tq2 --help
python3 tq2 status
python3 tq2 run "fix the bug" --cwd ~/project

# Run daemon in foreground (for debugging)
python3 tq2 daemon start --foreground

# Run daemon in background
python3 tq2 daemon start
python3 tq2 daemon status
python3 tq2 daemon stop
```

## Data Model

Two SQLite tables:
- `sessions` — id, prompt, cwd, status, tmux_session, queue, timestamps
- `messages` — telegram_msg_id, session_id, direction (in/out), text, timestamp

## Routing Rules

1. Reply-to a tracked message → route to that session
2. Anything else → spawn new session

## Plugins

**Claude Code plugin** — `.claude-plugin/`, `.claude/commands/tq-reply.md`, `skills/tq/SKILL.md`
**OpenClaw plugin** — `openclaw-plugin/` with 3 tools, 1 service, 1 hook

## Queue Files (Optional)

```yaml
cwd: ~/project
tasks:
  - Review yesterday's commits
  - Run the test suite
```

Supports: `schedule`, `reset` (daily/weekly/hourly/always), `sequential`.

## Guardrails

- **Hash stability** — `hashlib.sha256(prompt.encode()).hexdigest()[:8]` is the session ID
- **OAuth from keychain** — never hardcode tokens; `security find-generic-password` at runtime
- **`--dangerously-skip-permissions`** — required for headless automation, do not remove
- **tmux load-buffer** — always use load-buffer + paste-buffer for message injection (safe for special chars)

## Git

- Short lowercase imperative commit messages
- Commit selectively — never `git add -A`
