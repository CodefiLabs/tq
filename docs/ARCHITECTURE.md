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
tq-status <queue.yaml>
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

### `scripts/tq-status` — Status Reporter
- Accepts: same YAML queue file path as `tq`
- Derives state dir: `<queue-dir>/.tq/<queue-basename>/`
- Iterates state files; skips `.prompt` and `.launch.py` files by extension
- Side effect: flips stale `running` states to `done` when tmux session is dead
- Output: `printf`-formatted table with 4 columns

### `scripts/tq-install.sh` — Installer
- Standalone; no runtime dependency on `tq` or `tq-status`
- Resolves plugin root via `CLAUDE_PLUGIN_ROOT` env var or `dirname` of the script
- Symlinks `scripts/tq` and `scripts/tq-status` into `/opt/homebrew/bin` (or `$TQ_INSTALL_DIR`)
- Creates `~/.claude/queues/` and `~/.claude/logs/`
- Prints example crontab lines on success

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
                         │  OR: tq/tq-status detects dead tmux session
                         ▼
                    ┌──────────┐
                    │          │
                    │   done   │
                    │          │
                    └──────────┘

Reset: delete the state file → task returns to pending
```

## Data Flow: How a Task Moves from Pending to Done

1. User creates `~/.claude/queues/morning.yaml` with one or more `tasks[*].prompt` entries
2. `tq morning.yaml` runs
3. Python parser computes `h = sha256(prompt)[:8]`, writes `<h>.prompt`, `<h>.launch.py`, `settings.json`, `on-stop.sh`
4. Bash loop finds no state file for `h` → it's pending
5. Writes state file: `status=running`, `session=tq-fix-the-login-451234`, `started=...`
6. `tmux new-session -d -s tq-fix-the-login-451234` then `send-keys "python3 <h>.launch.py"`
7. Launcher opens Chrome Profile 5, sleeps 2s, then `os.execvp('claude', [...])` — replaces the Python process
8. Claude runs the task with `--dangerously-skip-permissions --chrome <prompt>`
9. When Claude exits, the Stop hook fires: `on-stop.sh` runs `sed -i '' 's/^status=running/status=done/' <state-file>`
10. Next run of `tq` or `tq-status` sees `status=done` and skips the task

## Skill vs Scripts: Who Consumes What

| Consumer | Consumes |
|----------|---------- |
| User (CLI) | `scripts/tq`, `scripts/tq-status` (after install) |
| Claude (agent) | `skills/tq/SKILL.md` + `skills/tq/references/` |
| Shell (cron) | `/opt/homebrew/bin/tq`, `/opt/homebrew/bin/tq-status` (symlinks) |
| Claude per-task | `~/.tq/sessions/<hash>/settings.json` (hooks config) |
| Claude Stop event | `~/.tq/sessions/<hash>/hooks/on-stop.sh` |
