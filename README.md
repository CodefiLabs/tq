# tq — Task Queue for Claude

A lightweight task queue runner that spawns Claude AI tasks as independent tmux sessions.

## What It Does

`tq` lets you define a list of Claude prompts in a YAML file and run them all as independent background jobs. Each prompt gets its own named tmux session running the `claude` CLI — you can attach to any session to watch progress, and detach without interrupting the work.

Tasks are idempotent: running `tq queue.yaml` again skips tasks that are already `done` or have a live `running` session. Task identity is derived from a SHA-256 hash of the prompt content, so changing a prompt text treats it as a new task while re-running unchanged prompts is always a no-op.

The tool is designed for macOS with cron scheduling in mind: drop a queue YAML in `~/.claude/queues/`, add a crontab line, and tasks run automatically every morning (or on whatever schedule you choose). A companion script `tq-status` reaps dead sessions and prints a status table.

## Requirements

- macOS (uses `security` CLI for keychain access to Claude OAuth tokens)
- tmux (`brew install tmux`)
- `claude` CLI — [Claude Code](https://claude.ai/code) (`npm install -g @anthropic-ai/claude-code` or similar)
- python3 (macOS system Python is sufficient — stdlib only, no pip installs needed)
- Google Chrome with Claude Code extension installed
- `reattach-to-user-namespace` (optional, `brew install reattach-to-user-namespace` — fixes keychain access in tmux)

## Installation

Clone the repo, then install as a Claude Code plugin from the local path:

```bash
git clone https://github.com/kevnk/tq ~/tq
```

```
/plugin install ~/tq
```

Then install the CLI tools to your PATH by running the plugin's install command inside Claude:

```
/install
```

This symlinks `tq` and `tq-status` into `/opt/homebrew/bin` (or `/usr/local/bin` on Intel Macs) and creates `~/.claude/queues/` and `~/.claude/logs/`.

To install to a custom location, run the install script directly:

```bash
TQ_INSTALL_DIR=/usr/local/bin bash scripts/tq-install.sh
```

## Quick Start

Create a queue file:

```yaml
# ~/.claude/queues/morning.yaml
cwd: /Users/yourname/projects/myapp

tasks:
  - prompt: fix the login bug in the auth service
  - prompt: write unit tests for the payment module
  - prompt: |
      Review the README and update it to reflect
      the current API endpoints and authentication flow
```

Run it:

```bash
tq ~/.claude/queues/morning.yaml
```

Output:

```
  [spawned] tq-fix-the-login-451234 -- fix the login bug in the auth service
  [spawned] tq-write-unit-test-451235 -- write unit tests for the payment module
  [spawned] tq-review-the-readme-451236 -- Review the README and update it to reflect
```

Check status:

```bash
tq-status ~/.claude/queues/morning.yaml
```

Output:

```
STATUS     SESSION                   STARTED                PROMPT
---------- ------------------------- ---------------------- ------
done       tq-fix-the-login-451234   2026-03-06T09:01:02    fix the login bug in the auth service
running    tq-write-unit-test-451235 2026-03-06T09:01:03    write unit tests for the payment module
running    tq-review-the-readme-451236 2026-03-06T09:01:04  Review the README and update it to reflect
```

## Queue File Format

Queue files are standard YAML with two top-level keys:

```yaml
cwd: /path/to/working/directory   # optional — sets working directory for each claude task

tasks:
  # Inline prompt (single line)
  - prompt: fix the login bug in auth service

  # Block literal (|) — preserves line breaks exactly
  - prompt: |
      Write comprehensive unit tests for the payment module.
      Cover happy path and all error cases.
      Use jest and mock the Stripe API.

  # Block folded (>) — newlines become spaces (like a paragraph)
  - prompt: >
      Refactor the authentication service to use JWT tokens
      instead of session cookies, updating all dependent endpoints.

  # Quoted inline
  - prompt: "update the README's installation section"
```

Queue files are **never modified** by `tq` — they are read-only inputs.

## Commands

### `tq <queue.yaml>`

Parses the queue file and spawns a new tmux session for each pending task.

- Skips tasks with `status=done`
- Skips tasks with `status=running` that have a live tmux session
- Flips tasks with `status=running` but a dead tmux session to `done`, then skips them
- Spawns all remaining (pending) tasks as new tmux sessions

```bash
tq ~/.claude/queues/morning.yaml
```

### `tq-status <queue.yaml>`

Prints a formatted status table for all tasks in the queue. Also reaps any dead tmux sessions by flipping their state from `running` to `done`.

```bash
tq-status ~/.claude/queues/morning.yaml
```

Run this via cron every 30 minutes to keep state accurate even if sessions die unexpectedly.

## How It Works

**Step 1 — Parse**: `tq` runs an embedded Python script (written to a temp file) that reads the queue YAML and generates three files per task, all named by an 8-character SHA-256 hash of the prompt:

- `<hash>.prompt` — the raw prompt text
- `<hash>.launch.py` — a small Python launcher that `execvp`s into `claude` (replacing itself with the claude process so the tmux window ends up running claude directly)
- `~/.tq/sessions/<hash>/settings.json` — Claude settings registering a Stop hook

**Step 2 — Auth capture**: The Python parser reads the Claude OAuth token from the macOS keychain (`security find-generic-password -s 'Claude Code-credentials'`) and bakes it into the launcher script. This means each task has its credentials embedded and can run unattended even in a cron context.

**Step 3 — Spawn**: For each pending task, `tq` creates a named tmux session (`tq-<slug>-<epoch>`) and sends `python3 <hash>.launch.py` to it via `tmux send-keys`. The launcher runs inside the tmux window, then `execvp`s into `claude --dangerously-skip-permissions --chrome <prompt>`, replacing itself so the window ends up running a live `claude` session.

**Step 4 — Completion**: When `claude` finishes, the Stop hook (`on-stop.sh`) fires automatically and updates the task's state file: `status=running` → `status=done`. The next `tq` run will skip this task.

## Claude Code Plugin

`tq` ships with a Claude skill definition at `skills/tq/SKILL.md`. Install it into Claude by copying or symlinking the `skills/tq/` directory into `~/.claude/skills/tq/`.

Once installed, Claude can manage your task queues via slash commands:

| Command | Purpose |
|---------|---------|
| `/todo <natural language>` | Create or update a queue and optionally schedule it |
| `/schedule <natural language>` | Add or update a cron schedule for a queue |
| `/pause <queue>` | Remove the run cron line (keep status-check) |
| `/unschedule <queue>` | Remove all cron lines for a queue |
| `/jobs` | List all scheduled tq cron jobs |
| `/health` | System-wide diagnostics |
| `/install` | Symlink tq binaries to PATH |

Claude will infer the queue name from context: "every morning" → `morning.yaml`, "daily" → `daily.yaml`, or the current directory's basename if no schedule keyword is present.

## State Files

State is stored in `.tq/` directories adjacent to the queue YAML file:

```
~/.claude/queues/
├── morning.yaml              ← your queue file
└── .tq/
    └── morning/
        ├── a1b2c3d4          ← task state file (key=value)
        ├── a1b2c3d4.prompt   ← raw prompt text
        ├── a1b2c3d4.launch.py ← generated launcher (contains OAuth token)
        └── ...
```

Each state file looks like:

```
status=done
session=tq-fix-the-login-451234
window=fix-the
prompt=fix the login bug in auth service
started=2026-03-06T09:01:02
```

**Resetting tasks:**

```bash
# Reset one task (tq will re-run it next time)
rm ~/.claude/queues/.tq/morning/a1b2c3d4

# Reset entire queue
rm -rf ~/.claude/queues/.tq/morning/
```

## Security Notes

The `.tq/` directories contain live OAuth tokens written in plaintext into `*.launch.py` launcher files at runtime. These files are ephemeral and local-only, but:

- **Never commit `.tq/` directories to git** — they contain your Claude auth tokens
- Add `.tq/` to your `.gitignore` if your queue files are inside a git repository

The `--dangerously-skip-permissions` flag is passed to every Claude session. This is required for unattended automation — without it, Claude would prompt for permission confirmations that no human is present to answer.

## Scheduling

Add cron entries to run your queues automatically:

```bash
crontab -e
```

```cron
# Run morning queue at 9am daily
0 9 * * * /opt/homebrew/bin/tq ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1

# Sweep dead sessions every 30 minutes (keeps status accurate)
*/30 * * * * /opt/homebrew/bin/tq-status ~/.claude/queues/morning.yaml >> ~/.claude/logs/tq.log 2>&1
```

Logs accumulate in `~/.claude/logs/tq.log`.

See `skills/tq/references/cron-expressions.md` for a natural language → cron expression reference.
