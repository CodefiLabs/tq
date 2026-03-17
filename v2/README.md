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
python3 tq2 setup

# 2. Start the daemon
python3 tq2 daemon start

# 3. Send a message to your bot on Telegram
```

That's it. You're running Claude Code from your phone.

## CLI

```
tq2 daemon start|stop|status   Start/stop the Telegram daemon
tq2 status                     List all sessions
tq2 stop <id>                  Kill a session
tq2 run <prompt> [--cwd DIR]   One-shot session (no Telegram)
tq2 run queue.yaml [--cwd DIR] Batch sessions from YAML
tq2 reply <id> <text>          Send reply to Telegram (internal)
tq2 setup                      Configure Telegram bot
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
tq2 run morning.yaml
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
claude plugin install /path/to/tq/v2
```

Claude sessions spawned by tq use `/tq-reply` to send responses back to Telegram.

### OpenClaw

Install as an OpenClaw plugin for multi-channel support:

```bash
openclaw plugins install /path/to/tq/v2/openclaw-plugin
```

Provides 3 tools (`tq_run`, `tq_status`, `tq_stop`), a health-check service,
and auto-injects active session context into agent prompts.

## Architecture

```
v2/
  tq/
    cli.py        320 lines  Entry point + queue parser
    daemon.py     183 lines  Telegram long-poll + health
    session.py    149 lines  tmux lifecycle + hooks
    store.py      104 lines  SQLite (2 tables)
    telegram.py    63 lines  Bot API
  tq2                        CLI entry point

  .claude-plugin/            Claude Code plugin
  .claude/commands/          /tq-reply slash command
  skills/tq/                 Skill definition

  openclaw-plugin/           OpenClaw plugin
    src/index.ts             3 tools + 1 service + 1 hook
    src/tq-bridge.ts         CLI bridge
```

~820 lines of Python. ~150 lines of TypeScript. Zero external dependencies.

## Security

- OAuth tokens read from macOS keychain at runtime — never stored in files
- `--dangerously-skip-permissions` is required for headless automation
- Telegram bot token lives in `~/.tq/config.json` — never commit this
- SQLite database may contain message text — treat `~/.tq/` as private

## License

MIT
