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
python3 -m tq --help
python3 -m tq status
python3 -m tq run "fix the bug" --cwd ~/project

# Run daemon in foreground (for debugging)
python3 -m tq daemon start --foreground

# Run daemon in background
python3 -m tq daemon start
python3 -m tq daemon status
python3 -m tq daemon stop
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

## Session Management

Sessions spawned after v2.1.0 track `claude_session_id` in SQLite and support suspend/resume natively via `tq suspend <id>` and `tq resume <id>`.

### Recovering session IDs from legacy sessions

For sessions spawned before v2.1.0 (no `claude_session_id` in the database), you can extract session IDs by gracefully exiting the Claude TUI without killing the tmux window:

```bash
# Send /exit to a specific tmux pane — claude exits, prints the resume line, shell stays alive
tmux send-keys -t "<tmux_session>:0.0" "/exit" Enter

# Wait a few seconds, then capture the session ID from pane output
tmux capture-pane -t "<tmux_session>:0.0" -p -S -30 | grep 'claude --resume'
# Output: claude --resume <session_id>
```

To do this in bulk across all non-attached sessions:

```bash
# 1. Send /exit to all claude processes in non-attached sessions
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{session_attached} #{pane_pid}' | while read pane attached pid; do
  if [ "$attached" = "0" ]; then
    has_claude=$(pgrep -P "$pid" -f "claude" 2>/dev/null | head -1)
    if [ -n "$has_claude" ]; then
      tmux send-keys -t "$pane" "/exit" Enter
    fi
  fi
done

# 2. Wait ~10 seconds for processes to exit

# 3. Harvest session IDs from pane output
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{session_attached}' | while read pane attached; do
  if [ "$attached" = "0" ]; then
    session_id=$(tmux capture-pane -t "$pane" -p -S -30 2>/dev/null | grep -oE 'claude --resume [0-9a-f-]+' | tail -1 | sed 's/claude --resume //')
    [ -n "$session_id" ] && echo "$pane|$session_id"
  fi
done

# 4. Kill the empty tmux sessions after saving the IDs
```

Note: autorun stage sessions may auto-destroy when claude exits (if `destroy-unattached` is set). Capture IDs quickly or accept that pipeline stages are disposable.

## Guardrails

- **Hash stability** — `hashlib.sha256(prompt.encode()).hexdigest()[:8]` is the session ID
- **OAuth from keychain** — never hardcode tokens; `security find-generic-password` at runtime
- **`--dangerously-skip-permissions`** — required for headless automation, do not remove
- **tmux load-buffer** — always use load-buffer + paste-buffer for message injection (safe for special chars)

## Git

- Short lowercase imperative commit messages
- Commit selectively — never `git add -A`
