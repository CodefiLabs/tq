# tq — Claude Code via Telegram

Send a message. Get a Claude Code session. Reply to continue.

## How It Works

```
You (Telegram)  →  tq daemon  →  tmux session  →  Claude Code
                ←             ←                ←  /tq-reply
```

Every Telegram message spawns a Claude Code session in tmux.
Reply to the bot's response to continue that conversation.
Send a new message to start a new session.

Two routing rules. That's the whole system.

## Requirements

- macOS (uses `security` CLI for keychain OAuth)
- Python 3 (stdlib only — no pip install)
- tmux
- `claude` CLI ([Claude Code](https://claude.ai/code))
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

## Setup

```bash
# 1. Configure Telegram
tq setup

# 2. Start the daemon
tq daemon start

# 3. Send a message to your bot on Telegram
```

That's it. You're running Claude Code from your phone.

## Installation

```bash
# From the repo root:
bash migrate-v1-to-v2.sh
```

This installs a `tq` wrapper to `/opt/homebrew/bin/` (or set `TQ_INSTALL_DIR`).

Or manually:

```bash
# Create a wrapper script
cat > /opt/homebrew/bin/tq <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
TQ_ROOT="/path/to/tq/repo"
export PYTHONPATH="$TQ_ROOT:${PYTHONPATH:-}"
exec python3 -m tq "$@"
EOF
chmod +x /opt/homebrew/bin/tq
```

## CLI

```
tq daemon start|stop|status   Start/stop the Telegram daemon
tq status                     List all sessions
tq stop <id>                  Kill a session
tq run <prompt> [--cwd DIR]   One-shot session (no Telegram)
tq run queue.yaml [--cwd DIR] Batch sessions from YAML
tq reply <id> <text>          Send reply to Telegram (internal)
tq setup                      Configure Telegram bot
```

## Queue Files

For batch automation without Telegram:

```yaml
cwd: ~/project
tasks:
  - Review yesterday's commits
  - Run the test suite
  - Add documentation
```

```bash
tq run morning.yaml
```

Optional features:
- `schedule: "0 9 * * *"` — cron scheduling
- `reset: daily` — auto-clear state so tasks re-run
- `sequential: true` — run tasks one at a time in order

## State

Everything lives in `~/.tq/`:

```
~/.tq/
  tq.db          SQLite database (all sessions + messages)
  config.json    Telegram bot token + chat ID
  hooks/<id>/    Generated per-session hooks (runtime)
  daemon.pid     Daemon process ID
  daemon.log     Daemon output
```

One database. One config file. No scattered state directories.

## Plugins

tq works as both a **Claude Code plugin** and an **OpenClaw plugin**.

### Claude Code

Install the plugin to get the `/tq-reply` slash command:

```bash
claude plugin install /path/to/tq
```

Claude sessions spawned by tq use `/tq-reply` to send responses back to Telegram.

### OpenClaw

Install as an OpenClaw plugin for multi-channel support:

```bash
openclaw plugins install /path/to/tq/openclaw-plugin
```

Provides 3 tools (`tq_run`, `tq_status`, `tq_stop`), a health-check service,
and auto-injects active session context into agent prompts.

## Architecture

```
tq/
  __init__.py     Version
  __main__.py     python -m tq entry point
  cli.py          320 lines  Entry point + queue parser
  daemon.py       183 lines  Telegram long-poll + health
  session.py      149 lines  tmux lifecycle + hooks
  store.py        104 lines  SQLite (2 tables)
  telegram.py      63 lines  Bot API

.claude-plugin/            Claude Code plugin
.claude/commands/          /tq-reply slash command
skills/tq/                 Skill definition

openclaw-plugin/           OpenClaw plugin
  src/index.ts             3 tools + 1 service + 1 hook
  src/tq-bridge.ts         CLI bridge
```

~820 lines of Python. ~150 lines of TypeScript. Zero external dependencies.

## Migrating from v1

If you're upgrading from tq v1 (the bash version):

```bash
bash migrate-v1-to-v2.sh
```

The migration script:
1. Stops v1 processes and removes v1 symlinks
2. Cleans v1 crontab entries
3. Removes v1 files (`scripts/`, `tools/`, `docs/`, etc.)
4. Promotes `v2/` contents to repo root
5. Renames all `tq2` references to `tq`
6. Installs a `tq` wrapper to PATH
7. Preserves `~/.tq/` runtime state

**v1 state (`~/.tq/queues/.tq/`)** is not migrated — v2 uses SQLite (`~/.tq/tq.db`).
If you had v1 queue files, they still work with `tq run queue.yaml`.

## Security

- OAuth tokens read from macOS keychain at runtime — never stored in files
- `--dangerously-skip-permissions` is required for headless automation
- Telegram bot token lives in `~/.tq/config.json` — never commit this
- SQLite database may contain message text — treat `~/.tq/` as private

## License

MIT
