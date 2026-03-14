# CLAUDE.md — tq

## Project Overview

`tq` is a pure Bash + embedded Python 3 CLI tool that manages Claude Code sessions via tmux. It operates in two modes:

1. **Queue mode** — batches Claude Code prompts into YAML queue files and spawns each as an independent tmux session. Tasks are idempotent: re-running `tq` skips tasks that are already `done` or have a live `running` session.
2. **Conversation mode** — maintains persistent interactive Claude Code sessions orchestrated via Telegram. An orchestrator Claude session routes incoming messages to the appropriate conversation, spawning new sessions or resuming existing ones.

Designed for macOS power users who want to schedule, queue, and converse with Claude tasks via cron and Telegram.

## Tech Stack

- **Bash** (primary) — requires bash 3.2+ (macOS default); `set -euo pipefail` throughout
- **Python 3** — embedded inline via heredoc temp file for YAML parsing, state management, and launcher generation; stdlib only (`sys`, `os`, `hashlib`, `re`, `json`, `stat`, `subprocess`)
- **No package manager** — zero npm/pip/cargo dependencies; no build step
- **Runtime deps**: `tmux`, `claude` CLI, `python3`, macOS `security` CLI, Google Chrome, `reattach-to-user-namespace` (optional Homebrew, for tmux keychain)

## Architecture

```
tq/
  scripts/
    tq                  # Queue runner + status reporter (--status flag)
    tq-converse         # Conversation mode: orchestrator + multi-session manager
    tq-message          # Notification delivery (Telegram/Slack)
    tq-telegram-poll    # Polls Telegram for messages, routes to orchestrator or spawns tasks
    tq-telegram-watchdog # Ensures poll cron entry exists
    tq-cron-sync        # Syncs queue schedule: keys to crontab
    tq-setup            # Interactive setup wizard
    tq-install.sh       # Installer: symlinks into /opt/homebrew/bin
  skills/
    tq/
      SKILL.md          # Claude plugin skill definition
      references/
        cron-expressions.md
        session-naming.md
  .claude/commands/
    tq-reply.md         # Slash command: Claude sends response back to Telegram
    converse.md         # Slash command: manage conversation sessions
    tq-message.md       # Slash command: write task completion summary
    ...                 # Other slash commands (todo, schedule, etc.)
  .claude-plugin/
    plugin.json         # Plugin metadata (name, version, license)
```

**Three separate state locations — do not confuse:**
- `<queue-dir>/.tq/<queue-basename>/<hash>` — task state files (status, session, prompt, started)
- `~/.tq/sessions/<hash>/` — per-task Claude settings.json + hooks/on-stop.sh
- `~/.tq/conversations/` — conversation mode state (registry, session dirs, orchestrator)

**Queue mode data flow:** YAML queue file → Python parser (temp file) → `<hash>.prompt`, `<hash>.launch.py` → tmux session → `claude --dangerously-skip-permissions --chrome <prompt>` → Stop hook (`on-stop.sh`) marks `status=done`

**Conversation mode data flow:** Telegram message → `tq-telegram-poll` → 3-tier routing (reply threading / #slug / orchestrator) → `tq-converse route <slug>` → tmux send-keys into child session → Claude processes → `/tq-reply` → `tq-message --reply-to` → Telegram response (threaded)

## Development Commands

```bash
# Install (symlinks scripts into /opt/homebrew/bin or /usr/local/bin)
bash "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
# Override target: TQ_INSTALL_DIR=/usr/local/bin bash scripts/tq-install.sh

# Run a queue
tq ~/.tq/queues/morning.yaml

# Check status / reap dead sessions
tq --status ~/.tq/queues/morning.yaml

# Schedule via cron (crontab -e)
0 9 * * * /opt/homebrew/bin/tq ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1

# Reset one task (delete state file — tq will re-run it)
rm ~/.tq/queues/.tq/morning/a1b2c3d4

# Reset entire queue
rm -rf ~/.tq/queues/.tq/morning/

# Lint bash scripts
shellcheck scripts/tq scripts/tq-install.sh

# Start conversation mode (orchestrator)
tq-converse start

# Spawn a conversation session
tq-converse spawn fix-auth --cwd ~/Sites/myproject --desc "Fix authentication bug"

# Route a message to a session
tq-converse route fix-auth "check the login flow"

# List active conversations
tq-converse list

# Check all session status
tq-converse status

# Stop a conversation
tq-converse stop fix-auth
```

## Code Style & Conventions

See `.claude/rules/naming.md` for full naming conventions and examples.

## Testing

No tests exist. See `.claude/rules/testing.md` for test targets and recommended approach.

Until tests exist, limit each change to a single function or code block. After any edit to `scripts/tq`, run `bash scripts/tq <queue.yaml>` and confirm no errors before proceeding.

## Git Conventions

- Single `main` branch
- Short lowercase imperative commit messages: `add tq-cli scripts and Claude plugin structure`
- No "Generated with" or "Co-authored-by" suffixes in commit messages
- Commit selectively — never `git add -A`

## Guardrails

Critical rules — violations break the tool or expose credentials:

- **`sed -i ''` syntax** — macOS BSD sed requires the empty string; `sed -i` (no quotes) is GNU syntax and will fail or create backup files
- **`#!/usr/bin/env bash`** — never use `#!/bin/bash`; applies to source scripts and heredoc-generated scripts alike
- **`os.execvp()` in launchers is intentional** — process replacement, not subprocess; do not change to `subprocess.run()`
- **Hash stability** — `hashlib.sha256(prompt.encode()).hexdigest()[:8]` is the stable task ID; changing it orphans all existing state files
- **`.tq/` is in `.gitignore`** — never override this, never use `git add -f` on these paths; `*.launch.py` files contain live OAuth tokens

See `.claude/rules/anti-patterns.md` for full examples.

## Security

See `.claude/rules/security.md` for credential and token handling rules.

## Maintenance

- Add tests before making logic changes to the YAML parser or idempotency state machine
