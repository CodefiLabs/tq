---
date: "2026-03-17T21:13:13Z"
researcher: Claude
git_commit: 124b6c48524ff2c51a726e44b9c2425ce05da919
branch: main
repository: CodefiLabs/tq
topic: "Using tmux-resurrect (and tmux-continuum) to save and restore tq sessions from disk"
tags: [research, codebase, tmux, tmux-resurrect, tmux-continuum, session-persistence, daemon]
status: complete
last_updated: "2026-03-17"
last_updated_by: Claude
last_updated_note: "Added follow-up research on Claude Code session IDs and --resume flag"
---

# Research: Using tmux-resurrect/continuum to Save and Restore tq Sessions

**Date**: 2026-03-17T21:13:13Z
**Researcher**: Claude
**Git Commit**: 124b6c48524ff2c51a726e44b9c2425ce05da919
**Branch**: main
**Repository**: CodefiLabs/tq

## Research Question

How can tmux plugins like tmux-resurrect (optionally with tmux-continuum) be used to save and later restore tq sessions from disk?

## Summary

tmux-resurrect saves the full tmux session/window/pane topology, working directories, and optionally running programs and pane contents to plain-text TSV files in `~/.tmux/resurrect/`. tmux-continuum layers automatic periodic saving (default 15 min) and auto-restore on tmux server start on top of resurrect. Both can be triggered programmatically via shell scripts, and resurrect provides 5 hook points (pre/post save and restore).

The current system (tmux 3.6a on macOS) has zero tmux plugins installed — a clean slate. tq manages tmux sessions purely as ephemeral runtimes: the daemon's health check marks any vanished tmux session as "done" in SQLite within 30-60 seconds. There is no mechanism to detect or reconnect to restored sessions.

The key gap for tq integration is that tmux-resurrect restores the *tmux shell environment* (panes, directories, layouts), but it does NOT restore *process state*. It can only re-issue the original launch command. For tq, this means resurrect could recreate the `tq-{sid}` tmux sessions and re-run `claude --settings ... --prompt ...`, but the Claude Code conversation context (what Claude was doing, tool results, in-progress work) would be lost. The session would start over from the original prompt.

## Detailed Findings

### 1. Current tq tmux Session Lifecycle

tq creates tmux sessions via `session.spawn()` (`tq/session.py:71-102`):

1. Creates detached tmux session: `tmux new-session -d -s tq-{sid} -x 220 -y 50`
2. Injects env vars via `send-keys`: `TQ_SESSION_ID` and `CLAUDE_CODE_OAUTH_KEY`
3. Sets working directory: `cd '{cwd}'`
4. Launches Claude: `claude --settings '{settings_path}' --dangerously-skip-permissions --prompt '{prompt}'`

All setup is via `tmux send-keys` (typing into shell), not `tmux set-environment`. This means:
- Environment variables exist only in the shell process, not in tmux's session env table
- tmux-resurrect would NOT capture these env vars
- Resurrect would see the pane running `claude` (or a shell) but not know about `TQ_SESSION_ID`

**Health check** (`session.py:136-144`): Runs every ~30s, queries all `status='running'` sessions, checks `tmux has-session`, and marks missing ones as `done`. This is the primary obstacle — any restored session would be marked done before it could reconnect.

**State split**:
- SQLite has: session ID, original prompt, cwd, tmux name, status, all Telegram messages
- tmux has: the running Claude process, shell env vars, scrollback buffer
- Filesystem has: `~/.tq/hooks/{sid}/` (settings.json, on-stop.sh) — these survive restarts

### 2. tmux-resurrect: What It Saves and Restores

**Save file**: Plain-text TSV at `~/.tmux/resurrect/tmux_resurrect_<timestamp>.txt` with a `last` symlink to the most recent. Configurable directory via `set -g @resurrect-dir`.

**Each line is typed**: `pane`, `window`, `state`, or `grouped_session` followed by tab-separated fields:

```
pane<TAB>session_name<TAB>window_index<TAB>window_active<TAB>window_flags<TAB>pane_index<TAB>pane_title<TAB>pane_current_path<TAB>pane_active<TAB>pane_current_command<TAB>pane_pid<TAB>history_size
window<TAB>session_name<TAB>window_index<TAB>window_name<TAB>window_active<TAB>window_flags<TAB>window_layout
state<TAB>client_session<TAB>client_last_session
```

**What it saves:**
- All sessions, windows, panes (names, indices, layout geometry)
- Working directories per pane
- Active/alternate session and window state, zoom state
- Optionally: running program commands (`@resurrect-processes`)
- Optionally: visible pane text (`@resurrect-capture-pane-contents`)

**What it CANNOT restore:**
- Shell history, environment variables, scrollback buffer
- Running process state (only re-issues the command from scratch)
- Complex application state (editor buffers, database connections, conversation context)
- tmux options set at runtime but not in `.tmux.conf`

**Restore process** (`scripts/restore.sh`):
1. Reads save file line by line
2. Recreates sessions/windows/panes via `tmux new-session`, `new-window`, `split-window`
3. Sets working directories with `-c <dir>`
4. Applies layouts via `select-layout`
5. Re-issues program commands via `send-keys` (for configured processes)
6. Restores zoom, focus, and active pane state
7. Process is idempotent — skips elements that already exist

### 3. tmux-resurrect: Program Restoration

Configured via `@resurrect-processes` in `.tmux.conf`:

| Syntax | Meaning | Example |
|--------|---------|---------|
| `name` | Restore exact program name | `vim` |
| `"name args"` | Program with specific args | `"rails server"` |
| `~name` | Partial/fuzzy match | `~claude` |
| `name->cmd` | Restore using different command | `irb->irb` |
| `name->cmd *` | Restore with original arguments | `"claude->claude *"` |
| `:all:` | Restore ALL programs | `:all:` |
| `false` | Disable all restoration | `false` |

For tq, the relevant configuration would be:
```bash
set -g @resurrect-processes '"~claude"'
```
This would match any command starting with "claude" and re-issue the full command line on restore. However, it re-issues via `tmux send-keys`, which means the restored session would start a fresh Claude conversation — it would NOT resume the previous conversation.

### 4. tmux-resurrect: Hooks

5 hooks available:

| Hook | When |
|------|------|
| `@resurrect-hook-post-save-layout` | After session/pane/window state saved |
| `@resurrect-hook-post-save-all` | End of save process |
| `@resurrect-hook-pre-restore-all` | Before any tmux state is altered |
| `@resurrect-hook-pre-restore-pane-processes` | Before pane processes are restored |
| `@resurrect-hook-post-restore-all` | End of restore process |

Set via tmux options:
```bash
set -g @resurrect-hook-post-restore-all '/path/to/script.sh'
```

### 5. Programmatic Save/Restore

Both save and restore can be triggered from scripts:

```bash
# Direct invocation
~/.tmux/plugins/tmux-resurrect/scripts/save.sh
~/.tmux/plugins/tmux-resurrect/scripts/restore.sh

# Via tmux run-shell (from outside tmux)
tmux run-shell ~/.tmux/plugins/tmux-resurrect/scripts/save.sh

# Discover paths at runtime
tmux show-option -gv @resurrect-save-script-path
tmux show-option -gv @resurrect-restore-script-path
```

The save script supports `SCRIPT_OUTPUT="quiet"` for suppressing display messages in automated use.

### 6. tmux-continuum: Auto-Save and Auto-Restore

**Dependency**: Requires tmux-resurrect.

**Auto-save mechanism**: Piggybacks on tmux's `status-right` refresh cycle (not a cron job). Every time tmux redraws the status bar, continuum checks if the save interval has elapsed and triggers resurrect's save if so.

| Option | Default | Description |
|--------|---------|-------------|
| `@continuum-save-interval` | `15` | Minutes between auto-saves. `0` = disabled. |
| `@continuum-restore` | `off` | Auto-restore on server start. Set to `'on'`. |
| `@continuum-boot` | `off` | Auto-start tmux on system boot. |

**Critical requirements**:
- tmux status bar must be enabled (`set -g status on`)
- Continuum must be the LAST plugin in TPM list (anything that overwrites `status-right` breaks it)
- Auto-restore only fires on tmux server start, not config reload
- Multi-server protection: disables auto-save if another tmux server is running

**Preventing auto-restore**: Create `~/tmux_no_auto_restore` sentinel file.

### 7. Current System State

| Item | Status |
|------|--------|
| tmux version | 3.6a (Homebrew, `/opt/homebrew/Cellar/tmux/3.6a/bin/tmux`) |
| `~/.tmux.conf` | Minimal — only `set -g mouse on` |
| tpm (plugin manager) | Not installed |
| tmux-resurrect | Not installed |
| tmux-continuum | Not installed |
| `~/.tmux/` directory | Does not exist |
| Saved sessions | None |

Clean slate — no conflicts to worry about.

## Code References

- `tq/session.py:14-17` — `_tmux()` wrapper for all tmux subprocess calls
- `tq/session.py:20-21` — `_session_exists()` via `tmux has-session`
- `tq/session.py:24-26` — `tmux_session_name()` returns `tq-{sid}`
- `tq/session.py:43-68` — `_write_hooks()` generates per-session settings.json and on-stop.sh
- `tq/session.py:71-102` — `spawn()` full session creation flow
- `tq/session.py:105-123` — `route_message()` load-buffer/paste-buffer injection
- `tq/session.py:126-133` — `stop()` graceful then forceful shutdown
- `tq/session.py:136-144` — `check_health()` marks dead sessions done
- `tq/session.py:147-149` — `make_id()` SHA-256 hash for session IDs
- `tq/store.py:10-31` — SQLite schema (sessions + messages tables)
- `tq/daemon.py:143-184` — Main daemon loop (Telegram poll + health check)
- `tq/daemon.py:64-107` — `handle_message()` routing logic

## Architecture Documentation

### How tq Uses tmux Today

tq treats tmux as a **disposable process container**. Sessions are:
- Created on demand (Telegram message or CLI)
- Named deterministically (`tq-{sid}`)
- Set up entirely via `send-keys` (no persistent tmux config)
- Monitored by polling `has-session` every ~30s
- Cleaned up by marking dead ones as "done" in SQLite

There is no concept of session persistence, pause/resume, or reconnection. If a tmux session dies for any reason, it's gone.

### What tmux-resurrect Would Provide

1. **Periodic snapshots** of all tmux sessions (including tq's `tq-*` sessions) to disk
2. **Topology restoration** — recreating the `tq-{sid}` named sessions with correct working directories
3. **Program re-launch** — re-issuing the `claude` command that was running in each pane
4. **Hook integration** — notifying tq when save/restore events occur

### What tmux-resurrect Would NOT Provide

1. **Claude conversation continuity** — the most critical gap. Claude Code's in-progress conversation, tool results, and working context live in memory. A restored session would start a fresh `claude` invocation with the original prompt.
2. **Environment variable restoration** — `TQ_SESSION_ID` and `CLAUDE_CODE_OAUTH_KEY` set via `send-keys` are not captured by resurrect.
3. **tq daemon awareness** — the daemon's health check would need modification to distinguish "session died permanently" from "session died but will be restored."
4. **Scrollback preservation** — Claude's output history in the terminal would be lost (only visible area captured with `@resurrect-capture-pane-contents`).

### The Integration Surface

If tq were to use resurrect, the integration points would be:

1. **`@resurrect-processes`** — configure `"~claude"` to re-issue claude commands on restore
2. **`@resurrect-hook-post-restore-all`** — run a script that notifies tq daemon about restored sessions
3. **Health check modification** — add a grace period or "restoring" state so sessions aren't immediately marked done
4. **Env var injection** — a post-restore hook could re-inject `TQ_SESSION_ID` and `CLAUDE_CODE_OAUTH_KEY` into restored panes
5. **SQLite state update** — transition restored sessions back from "done" to "running"

## Findings Files

Full agent findings are preserved in the findings directory for deeper reference:

- @thoughts/shared/research/findings/2026-03-17-tmux-resurrect-session-persistence/analyzer-tmux-config.md — Current tmux installation, config, plugin status
- @thoughts/shared/research/findings/2026-03-17-tmux-resurrect-session-persistence/analyzer-tq-session-lifecycle.md — Full tq session lifecycle documentation
- @thoughts/shared/research/findings/2026-03-17-tmux-resurrect-session-persistence/perplexity-resurrect-continuum.md — tmux-resurrect and continuum feature research
- @thoughts/shared/research/findings/2026-03-17-tmux-resurrect-session-persistence/deepwiki-resurrect-continuum.md — Resurrect internals, save format, hooks, programmatic API

## External References

- https://github.com/tmux-plugins/tmux-resurrect
- https://github.com/tmux-plugins/tmux-continuum
- https://github.com/tmux-plugins/tmux-resurrect/blob/master/docs/save_dir.md
- https://github.com/tmux-plugins/tmux-resurrect/blob/master/docs/restoring_previously_saved_environment.md
- https://github.com/tmux-plugins/tmux-continuum/blob/master/docs/faq.md
- https://github.com/tmux-plugins/tmux-continuum/blob/master/docs/automatic_start.md

## Open Questions

1. ~~**Claude Code session resumption** — Does Claude Code have any mechanism to resume a previous conversation from disk?~~ **RESOLVED** — see Follow-up Research below.
2. **Selective session save** — tmux-resurrect saves ALL sessions. Is there a way to save only `tq-*` sessions, or conversely, exclude them? (No built-in support — would need a post-save hook to filter the save file.)
3. **OAuth token freshness** — If sessions are restored hours/days later, the OAuth token from keychain may have expired. The restore hook would need to fetch a fresh token.
4. **Daemon restart coordination** — If the tmux server dies, the tq daemon likely dies too (or loses its connection). How would the daemon detect that sessions were restored and need reconnection?
5. **Continuum's status-right dependency** — tq sessions are detached and have no status bar visible. Does continuum's auto-save still work for detached sessions? (Yes — the status-right evaluation happens server-side, not per-client.)

---

## Follow-up Research: Claude Code Session IDs and `--resume`

**Date**: 2026-03-17T21:25:00Z

### Claude Code CLI Session Flags

The `claude` CLI has full session persistence and resumption support:

| Flag | Description |
|------|-------------|
| `--session-id <uuid>` | Pre-set a specific UUID as the session ID (must be a valid UUID) |
| `-r, --resume [value]` | Resume by session ID, or open interactive picker with optional search term |
| `-c, --continue` | Continue the most recent conversation in the current directory |
| `--fork-session` | When resuming, create a new session ID instead of reusing the original |
| `-n, --name <name>` | Set a display name for the session (shown in `/resume` and terminal title) |
| `--no-session-persistence` | Disable session persistence (sessions not saved to disk, only works with `--print`) |

### Session Storage on Disk

Claude Code stores sessions in two locations:

**1. Per-project JSONL conversation logs:**
```
~/.claude/projects/{project-slug}/{session-uuid}.jsonl
```
Example: `~/.claude/projects/-Users-kk-Sites-codefi-tq/00e38f09-92a4-4b7d-9492-ecd2a576b486.jsonl`

Each JSONL line contains a message/event with fields including `sessionId`, `uuid`, `timestamp`, `cwd`, `type`, `data`, etc. This is the full conversation history that `--resume` reads.

**2. PID-to-session mapping:**
```
~/.claude/sessions/{PID}.json
```
Example:
```json
{
    "pid": 84917,
    "sessionId": "b55aaf70-1944-4c64-a1ae-c427af878b00",
    "cwd": "/Users/kk/Sites/codefi/tq",
    "startedAt": 1773586511784
}
```

**3. Session environment directory:**
```
~/.claude/session-env/{session-uuid}/
```
Empty directories that track active sessions.

### Two Approaches for tq Integration

#### Approach A: Pre-set UUID at spawn time (recommended)

At spawn time, tq generates a UUID and passes it to claude:

```python
import uuid

claude_session_id = str(uuid.uuid4())
cmd = f"claude --session-id '{claude_session_id}' --settings '{settings_path}' --dangerously-skip-permissions --prompt '{safe_prompt}'"
```

Store `claude_session_id` in the `sessions` SQLite table (new column). On restore:

```python
cmd = f"claude --resume '{claude_session_id}' --settings '{settings_path}' --dangerously-skip-permissions"
```

**Pros**: Deterministic, no timing races, UUID known before process starts.
**Cons**: Requires schema migration (add `claude_session_id` column to sessions table).

#### Approach B: Post-hoc discovery via PID

After spawning, discover the session ID from the running process:

1. Get pane PID: `tmux list-panes -t tq-{sid} -F '#{pane_pid}'`
2. Get claude child PID: `pgrep -P {pane_pid}`
3. Read session mapping: `~/.claude/sessions/{claude_pid}.json` → `sessionId`
4. Store in SQLite

**Pros**: No changes to spawn command.
**Cons**: Race condition (file written after claude starts), requires polling, fragile PID chain (shell → claude).

### Verified Discovery Chain

The full chain from tmux session to Claude session UUID works today:

```
tmux session name (tq-conv-fix-multiline-parser)
  → tmux list-panes -F '#{pane_pid}' → 84157 (shell PID)
    → pgrep -P 84157 → 84917 (claude PID)
      → cat ~/.claude/sessions/84917.json → sessionId: "b55aaf70-1944-4c64-a1ae-c427af878b00"
        → JSONL at ~/.claude/projects/-Users-kk-Sites-codefi-tq/b55aaf70-1944-4c64-a1ae-c427af878b00.jsonl ✓
          → claude --resume b55aaf70-1944-4c64-a1ae-c427af878b00 (would restore full conversation)
```

### The `--resume` Restore Command

To restore a tq session after tmux-resurrect recreates the tmux pane:

```bash
cd '{cwd}'
export TQ_SESSION_ID='{sid}'
export CLAUDE_CODE_OAUTH_KEY='{oauth}'
claude --resume '{claude_session_id}' --settings '{settings_path}' --dangerously-skip-permissions
```

This would load the full conversation history from the JSONL file and resume where it left off. The user (or tq daemon) could then continue sending messages to the session.

### What `--resume` Restores vs. What It Doesn't

**Restores:**
- Full conversation history (all messages, tool calls, results)
- Session context (system prompt, CLAUDE.md, project instructions)
- The session ID itself (same UUID, so hooks and references still work)

**Does NOT restore:**
- In-flight tool executions (if claude was mid-tool-call when killed)
- Background agent state (subagents would be lost)
- Exact terminal position / scrollback (tmux-resurrect captures layout, not full scrollback)

### Impact on tq Architecture

With `--session-id` at spawn + `--resume` on restore, the full session lifecycle becomes:

1. **Spawn**: `claude --session-id {uuid} --settings ... --prompt ...` → store UUID in SQLite
2. **Route**: existing load-buffer/paste-buffer pattern (unchanged)
3. **Save**: tmux-resurrect saves the tmux session topology (periodic or on-demand)
4. **Death**: tmux server dies, macOS restarts, etc.
5. **Restore**: tmux-resurrect recreates panes → post-restore hook runs
6. **Resume**: hook reads stored UUIDs from SQLite, re-launches `claude --resume {uuid} --settings ...`
7. **Reconnect**: tq daemon detects restored sessions, updates status back to "running"

### Additional Findings

- **`--name`** flag: tq could set `--name "tq-{sid}"` for easy identification in the `/resume` picker
- **`--fork-session`**: useful if you want to restart from a checkpoint without modifying the original session
- **`--continue`**: resumes the most recent session in the current cwd — could be a simpler alternative if sessions are cwd-scoped, but less precise than `--resume {uuid}`
- **No `CLAUDE_SESSION_ID` env var**: Claude Code does NOT export its session ID as an environment variable. The only way to discover it post-hoc is via the `~/.claude/sessions/{PID}.json` file.
- **No headless mode**: tq will never use `-p`/`--print` mode. All sessions are interactive terminal sessions. `--resume` works in interactive mode (confirmed).

---

## Follow-up Research: Idle Session Detection and Auto-Close

**Date**: 2026-03-17T21:30:00Z

### The Problem: Resource Waste from Idle Sessions

As of 2026-03-17, the system has **41 tq-managed claude processes** running simultaneously:

- **Total memory**: 2,499 MB (2.4 GB)
- **Average per process**: 61 MB
- **Many sessions idle 2-3 days** (e.g., `tq-conv-auto-improve-skills` last active 72.7 hours ago)
- **All sessions have a running claude process**, even those waiting indefinitely for input

Each idle claude process holds ~50-68 MB of resident memory and some CPU (0.0-9.6%), doing nothing but waiting for stdin. Closing these and resuming on demand via `--resume` would reclaim ~2 GB of RAM and ensure each resumed session gets the latest Claude Code version.

### tmux Activity Tracking (Built-in)

tmux provides session-level activity timestamps:

```bash
tmux list-sessions -F '#{session_name} #{session_activity}'
```

`#{session_activity}` is a Unix timestamp of the last activity (output) in the session. This can be compared to `time.time()` to determine idle duration.

**Other relevant tmux format variables:**
- `#{session_activity}` — last time any pane in the session had activity (epoch seconds)
- `#{session_last_attached}` — empty for never-attached sessions (all tq sessions are detached)
- `#{pane_pid}` — shell PID in the pane

**tmux monitoring options:**
- `monitor-silence <seconds>` — per-window option, fires `silence` alert after N seconds of no output
- `monitor-activity on/off` — triggers on any new output
- `activity-action other` — what to do on activity (other = flag in status line)
- `silence-action other` — what to do on silence

However, `monitor-silence` is designed for status line alerts, not for executing scripts. It's more useful for visual indicators than automated cleanup.

### Idle Detection Strategies for tq

#### Strategy 1: Poll `session_activity` from daemon health check (simplest)

Add to the existing 30-second health check loop in `daemon.py`:

```python
def check_idle(db, max_idle_seconds=3600):
    """Check for idle sessions and stop them."""
    import time
    result = subprocess.run(
        ["tmux", "list-sessions", "-F", "#{session_name} #{session_activity}"],
        capture_output=True, text=True
    )
    now = time.time()
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2 and parts[0].startswith("tq-"):
            name, activity = parts[0], int(parts[1])
            idle_secs = now - activity
            if idle_secs > max_idle_seconds:
                # Extract sid from session name, stop it
                ...
```

**Pros**: Uses existing daemon loop, no new dependencies, simple.
**Cons**: 30-second polling granularity (fine for hour+ idle thresholds).

#### Strategy 2: Claude process CPU monitoring

Check if the claude process has been consuming <1% CPU for an extended period:

```bash
ps -p {claude_pid} -o %cpu= -o etime=
```

A claude process that's been running for 2+ days at 0.0% CPU is definitively idle.

**Pros**: More precise than tmux activity (catches cases where tmux registers activity from shell prompts).
**Cons**: CPU can spike briefly even in idle sessions (garbage collection, etc.).

#### Strategy 3: Track last routed message timestamp in SQLite

tq already tracks messages in SQLite. Add a `last_message_at` column to sessions (or query from messages table):

```sql
SELECT s.id, MAX(m.created_at) as last_msg
FROM sessions s
LEFT JOIN messages m ON m.session_id = s.id
WHERE s.status = 'running'
GROUP BY s.id
HAVING last_msg < datetime('now', '-1 hour')
```

**Pros**: Exact — measures actual user interaction, not tmux/process activity.
**Cons**: Doesn't account for sessions doing autonomous work (no messages but actively running).

### Recommended Approach: Hybrid

Combine Strategy 1 + 3:
1. **Primary signal**: No new Telegram message routed to session for N minutes (from SQLite)
2. **Safety check**: tmux `session_activity` confirms no recent output
3. **Grace period**: Don't kill sessions that are still producing output (could be mid-task)

### The Close-and-Resume Lifecycle

1. **Detect idle**: session has no messages for 1 hour AND no tmux activity for 30 minutes
2. **Save claude session ID**: already stored in SQLite (from `--session-id` at spawn)
3. **Graceful stop**: send `/exit` to claude, wait for on-stop hook
4. **Mark as "suspended"**: new status in SQLite (not "done" — distinguishes intentional suspend from completion)
5. **Kill tmux session**: `tmux kill-session -t tq-{sid}`
6. **On new message for session**: detect it's "suspended", respawn tmux, `claude --resume {uuid}`
7. **Benefit**: fresh claude process with latest Claude Code version, ~60 MB RAM reclaimed per session

### New Session Status: "suspended"

Current statuses: `pending`, `running`, `done`, `failed`

Add: `suspended` — session was intentionally stopped to save resources, can be resumed.

Routing logic change in `daemon.handle_message`:
```python
if target_session:
    s = store.get_session(db, target_session)
    if s and s["status"] == "running":
        session.route_message(target_session, text)
    elif s and s["status"] == "suspended":
        # Resume: respawn tmux session with --resume
        session.resume(db, target_session, text)
    else:
        telegram.send_plain(f"Session {target_session} is no longer running.")
```

### Resource Impact Estimate

Current state: 41 processes × 61 MB avg = 2,499 MB
If sessions older than 1 hour are suspended: ~35 of 41 would be closed = **~2.1 GB freed**
Remaining: ~6 active sessions using ~366 MB
