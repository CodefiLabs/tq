# Architecture

## System Overview

```
User / Cron
    │
    ▼
tq <queue.yaml>                        reads queue YAML (never mutates it)
    │
    ├── Step 1: Python parser (temp file via heredoc)
    │     │
    │     ├──► <queue-dir>/.tq/<basename>/<hash>.prompt        raw prompt text
    │     ├──► <queue-dir>/.tq/<basename>/<hash>.launch.py     launcher (OAuth baked in)
    │     ├──► ~/.tq/sessions/<hash>/settings.json             Claude Stop hook config
    │     ├──► ~/.tq/sessions/<hash>/hooks/on-stop.sh          marks task done on exit
    │     └──► stdout: JSON lines  {"hash":"a1b2c3d4", "first_line":"fix the login..."}
    │
    └── Step 2: Bash loop over JSON lines
          │
          ├── reads <queue-dir>/.tq/<basename>/<hash>          state file
          ├── checks `tmux has-session -t <session>`
          │
          ├── status=done          → skip  [done]
          ├── status=running + live session → skip  [running]
          ├── status=running + dead session → flip to done, skip  [done]
          └── no state / pending   → spawn  [spawned]
                │
                ├── writes state file (status=running, session=..., started=...)
                └── tmux new-session → send-keys "python3 <hash>.launch.py"
                                              │
                                              └── os.execvp():
                                                    claude
                                                      --settings ~/.tq/sessions/<hash>/settings.json
                                                      --dangerously-skip-permissions
                                                      --chrome <prompt>
                                                    (with CLAUDE_CODE_OAUTH_KEY in env)
                                                              │
                                                              └── on Claude Stop hook:
                                                                    on-stop.sh:
                                                                    sed -i '' status=running → done
```

```
tq --status <queue.yaml>
    │
    ├── reads <queue-dir>/.tq/<basename>/    (all state files)
    ├── skips *.prompt and *.launch.py files
    ├── for each state file with status=running:
    │     checks tmux has-session → if dead, flips to done
    └── prints columnar table: STATUS / SESSION / STARTED / PROMPT
```

## Module Responsibilities

### `scripts/tq` — Queue Runner
- Accepts: path to a YAML queue file
- Embeds a Python parser (written to temp file, cleaned up via `trap ... EXIT`)
- Parser: hand-rolled regex line scanner; handles inline, block-literal (`|`), block-folded (`>`), quoted prompts
- Generates per-task artifacts keyed by `sha256(prompt)[:8]`
- Reads OAuth token from macOS keychain at queue-run time; bakes into launcher
- Spawns: `tmux new-session` + `send-keys "python3 <hash>.launch.py"`
- Idempotent: safe to re-run; skips done and live running tasks

### `tq --status` — Status Reporter
- Accepts: `--status` flag followed by the same YAML queue file path
- Derives state dir: `<queue-dir>/.tq/<queue-basename>/`
- Iterates state files; skips `.prompt` and `.launch.py` files by extension
- Side effect: flips stale `running` states to `done` when tmux session is dead
- Output: `printf`-formatted table with 4 columns

### `scripts/tq-install.sh` — Installer
- Standalone; no runtime dependency on `tq`
- Resolves plugin root via `CLAUDE_PLUGIN_ROOT` env var or `dirname` of the script
- Symlinks `scripts/tq` into `/opt/homebrew/bin` (or `$TQ_INSTALL_DIR`)
- Creates `~/.tq/queues/` and `~/.tq/logs/`
- Prints example crontab lines on success

### `scripts/tq-converse` — Conversation Manager
- Subcommands: `start`, `spawn`, `route`, `send`, `stop`, `status`, `list`, `track-msg`, `lookup-msg`, `update-status`, `registry`
- `start` launches the orchestrator (a persistent Claude Code interactive session in tmux)
- `spawn <slug>` creates a child conversation session with its own tmux session, CLAUDE.md, and hooks
- `route <slug> <message>` injects a message into a child session via `tmux load-buffer` + `paste-buffer`
- Registry operations (embedded Python): JSON-based session and message ID tracking
- Auth capture: same keychain pattern as `tq`

### `scripts/tq-telegram-poll` — Telegram Message Router
- Cron-driven (every minute): fetches updates from Telegram Bot API
- Extracts `message_id`, `chat_id`, `reply_to_message_id`, and text
- 3-tier routing: reply threading → #slug prefix → orchestrator
- Handles Telegram commands: `/converse`, `/stop`, `/status`, `/list`
- Falls back to `tq --prompt` (legacy one-off mode) when no orchestrator is running

### `scripts/tq-message` — Notification Delivery
- Delivers messages via Telegram (or Slack) with reply threading support
- `--reply-to <msg_id>` threads responses under the user's original message
- Tracks outgoing message IDs in the conversation registry for bidirectional threading
- 3-layer config resolution: global config → queue YAML → env vars

### `skills/tq/SKILL.md` — Claude Plugin Skill
- Consumed by the Claude model only, not by any script
- Defines trigger phrases (when Claude activates this skill)
- Documents: queue YAML format, state model, slash commands, crontab pattern, Chrome integration
- References `${CLAUDE_PLUGIN_ROOT}` resolved by the Claude plugin system at runtime

## State Directory Layout

```
State is split across two locations by design:

<queue-dir>/                       (wherever the queue YAML lives)
└── .tq/
    └── <queue-basename>/          e.g. morning/ for morning.yaml
        ├── a1b2c3d4               task state file (key=value, no extension)
        ├── a1b2c3d4.prompt        raw prompt text
        ├── a1b2c3d4.launch.py     generated launcher (contains OAuth token at runtime)
        ├── b5e6f7a8               another task...
        └── ...

~/.tq/
└── sessions/
    └── a1b2c3d4/                  per-task Claude settings (keyed by same hash)
        ├── settings.json          Claude hooks config (Stop hook path)
        └── hooks/
            └── on-stop.sh         executed by Claude on session stop
```

**Why the split?** The `<queue-dir>/.tq/` holds task identity and status (tied to the queue file's location). The `~/.tq/sessions/` holds Claude session configuration (tied to the `claude` process). The same 8-char hash links them.

## Task State Machine

```
                    ┌──────────┐
  (no state file)   │          │
  ─────────────────►│ pending  │
                    │          │
                    └────┬─────┘
                         │  tq spawns tmux session
                         ▼
                    ┌──────────┐
                    │          │
                    │ running  │
                    │          │
                    └────┬─────┘
                         │  on-stop.sh fires (Claude exits)
                         │  OR: tq/tq --status detects dead tmux session
                         ▼
                    ┌──────────┐
                    │          │
                    │   done   │
                    │          │
                    └──────────┘

Reset: delete the state file → task returns to pending
```

## Data Flow: How a Task Moves from Pending to Done

1. User creates `~/.tq/queues/morning.yaml` with one or more `tasks[*].prompt` entries
2. `tq morning.yaml` runs
3. Python parser computes `h = sha256(prompt)[:8]`, writes `<h>.prompt`, `<h>.launch.py`, `settings.json`, `on-stop.sh`
4. Bash loop finds no state file for `h` → it's pending
5. Writes state file: `status=running`, `session=tq-fix-the-login-451234`, `started=...`
6. `tmux new-session -d -s tq-fix-the-login-451234` then `send-keys "python3 <h>.launch.py"`
7. Launcher opens Chrome Profile 5, sleeps 2s, then `os.execvp('claude', [...])` — replaces the Python process
8. Claude runs the task with `--dangerously-skip-permissions --chrome <prompt>`
9. When Claude exits, the Stop hook fires: `on-stop.sh` runs `sed -i '' 's/^status=running/status=done/' <state-file>`
10. Next run of `tq` sees `status=done` and skips the task

## Conversation Mode Architecture

```
Telegram
    │
    ▼
tq-telegram-poll (cron, every minute)
    │
    ├── Tier 1: reply_to_message_id in registry
    │     └── tq-converse route <slug> <message>    deterministic
    │
    ├── Tier 2: message starts with #slug
    │     └── tq-converse route <slug> <message>    deterministic
    │
    └── Tier 3: everything else
          └── tq-converse send "[tq-msg msg_id=X chat_id=Y] message"
                │
                ▼
          tq-orchestrator (persistent Claude Code session in tmux)
                │
                ├── reads ~/.tq/conversations/registry.json
                ├── decides: existing session or new?
                │
                ├── existing → tq-converse route <slug> <message>
                └── new      → tq-converse spawn <slug> --cwd <dir> --desc <desc>
                               then tq-converse route <slug> <message>
                                     │
                                     ▼
                               tq-conv-<slug> (child Claude Code session in tmux)
                                     │
                                     ├── Claude processes message
                                     ├── uses /tq-reply slash command
                                     │     └── tq-message --message "[slug] response" --reply-to <msg_id>
                                     │           └── Telegram sendMessage (threaded reply)
                                     └── outgoing msg_id tracked in registry
```

### Conversation State Layout

```
~/.tq/conversations/
├── registry.json              session & message ID registry (JSON)
├── latest-msg-id              last incoming Telegram message ID
├── latest-chat-id             last incoming Telegram chat ID
├── latest-reply-slug          slug marker for outgoing msg tracking
├── orchestrator/
│   ├── .tq-orchestrator.md    orchestrator instructions (Claude reads this)
│   ├── settings.json          Claude hooks config
│   └── hooks/
│       ├── on-stop.sh         marks orchestrator stopped, notifies Telegram
│       └── on-notification.sh forwards Claude notifications to Telegram
└── sessions/
    └── <slug>/
        ├── .tq-converse.md    child session instructions (Claude reads this)
        ├── settings.json      Claude hooks config
        ├── current-slug       slug identifier file (read by /tq-reply)
        ├── reply-to-msg-id    Telegram msg_id for reply threading
        ├── inbox/             received messages (timestamped .txt files)
        ├── outbox/            sent responses (timestamped .txt files)
        └── hooks/
            ├── on-stop.sh
            └── on-notification.sh
```

### Registry Format

```json
{
  "sessions": {
    "fix-auth": {
      "description": "Fix authentication bug in login module",
      "tmux": "tq-conv-fix-auth",
      "cwd": "/Users/kk/Sites/myproject",
      "conv_dir": "/Users/kk/.tq/conversations/sessions/fix-auth",
      "created": "2026-03-14T10:00:00",
      "last_active": "2026-03-14T10:30:00",
      "status": "active"
    }
  },
  "messages": {
    "12345": "fix-auth",
    "12346": "fix-auth"
  }
}
```

The `messages` map tracks Telegram message IDs (both incoming and outgoing) → session slugs, enabling reply threading.

## Skill vs Scripts: Who Consumes What

| Consumer | Consumes |
|----------|---------- |
| User (CLI) | `scripts/tq`, `scripts/tq-converse` (after install) |
| Claude (agent) | `skills/tq/SKILL.md` + `skills/tq/references/` |
| Shell (cron) | `/opt/homebrew/bin/tq`, `/opt/homebrew/bin/tq-telegram-poll` (symlinks) |
| Claude per-task | `~/.tq/sessions/<hash>/settings.json` (hooks config) |
| Claude Stop event | `~/.tq/sessions/<hash>/hooks/on-stop.sh` |
| Claude orchestrator | `~/.tq/conversations/orchestrator/.tq-orchestrator.md` |
| Claude conversation | `~/.tq/conversations/sessions/<slug>/.tq-converse.md` |
| tq-telegram-poll | `~/.tq/conversations/registry.json` (message routing) |
