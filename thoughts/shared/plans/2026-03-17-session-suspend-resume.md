# Session Suspend/Resume Implementation Plan

## Overview

Add session suspend/resume to tq so that idle sessions are automatically closed to save resources (~60 MB RAM each), sessions orphaned by computer restart are suspended instead of lost, and replying to a suspended session auto-resumes it with full conversation history via `claude --resume`. Each resumed session gets the latest Claude Code version.

## Current State Analysis

- tq treats tmux as a disposable process container — if a session dies, it's marked "done" permanently
- 41 idle claude processes currently consume 2.4 GB RAM, many idle 2-3 days
- Claude Code has `--session-id <uuid>` (pre-set UUID at spawn) and `--resume <uuid>` (restore full conversation) flags
- Session state is persisted automatically to `~/.claude/projects/{slug}/{uuid}.jsonl`
- No migration system exists — schema is a single `CREATE TABLE IF NOT EXISTS` block
- Status field is unconstrained TEXT (no CHECK constraint) — adding "suspended" is trivial
- The `on-stop.sh` hook calls `tq _mark-done` which unconditionally sets status="done" — race condition with suspend

### Key Discoveries:
- `session.py:95-100` — claude command built as f-string, `--session-id` slots in directly
- `store.py:14` — status is `TEXT NOT NULL DEFAULT 'pending'`, no CHECK constraint
- `store.py:66-70` — `mark_done()` is unconditional UPDATE, must become conditional
- `daemon.py:90-97` — routing checks `s["status"] == "running"`, needs "suspended" branch
- `daemon.py:174-177` — health check runs every ~30s, idle check can piggyback here
- `config.json` — flat JSON dict with `cfg.get("key", default)` pattern for optional keys

## Desired End State

After implementation:
1. Every tq session stores its Claude Code UUID in SQLite
2. Idle sessions (no messages for N minutes AND no tmux activity for M minutes) are gracefully suspended
3. Sessions orphaned by restart/crash are marked "suspended" instead of "done"
4. Replying to a suspended session in Telegram auto-resumes it with full conversation context
5. `tq status` shows suspended sessions distinctly
6. `tq suspend <id>` and `tq resume <id>` work from CLI

### Verification:
- `tq run "hello"` → session starts, `tq status` shows running with a claude_session_id
- Wait for idle timeout → session suspended, tmux session gone, `tq status` shows suspended
- Reply to the session in Telegram → session resumes with conversation history, `tq status` shows running
- Kill tmux server → restart daemon → orphaned sessions show as suspended, not done
- Reply to orphaned session → resumes correctly

## What We're NOT Doing

- tmux-resurrect/continuum plugin installation (unnecessary — tq handles its own persistence)
- Headless/print mode (`-p`) — all sessions are interactive
- Automatic resume of all suspended sessions on daemon start (only resume on demand)
- Scrollback/terminal history preservation (Claude's `--resume` handles conversation state)
- Changes to the Telegram bot commands (beyond what routing changes require)

## Implementation Approach

Four incremental phases, each independently testable. The core insight: tq already has everything it needs in SQLite to resume sessions — we just need to store the Claude session UUID and change the lifecycle from "dead = done" to "dead = suspended, resumable on demand."

---

## Phase 1: Schema + Session ID Tracking

### Overview
Add `claude_session_id` column to the sessions table and pass `--session-id` when spawning claude. This is the foundation — no behavior changes yet, just data capture.

### Changes Required:

#### 1. Schema migration in store.py
**File**: `tq/store.py`
**Changes**: Add `_migrate()` helper and `claude_session_id` column

```python
def _migrate(db):
    """Add columns that don't exist yet."""
    cols = {r[1] for r in db.execute("PRAGMA table_info(sessions)").fetchall()}
    if "claude_session_id" not in cols:
        db.execute("ALTER TABLE sessions ADD COLUMN claude_session_id TEXT")
        db.commit()
```

Call `_migrate(db)` at the end of `connect()`, after `db.executescript(SCHEMA)`.

#### 2. Store the UUID in create_session
**File**: `tq/store.py`
**Changes**: Add `claude_session_id` parameter to `create_session()`

```python
def create_session(db, sid, prompt=None, cwd="~", queue=None, claude_session_id=None):
    db.execute(
        "INSERT INTO sessions (id, prompt, cwd, status, claude_session_id, created_at) VALUES (?, ?, ?, 'pending', ?, ?)",
        (sid, prompt, cwd, claude_session_id, _now()),
    )
    db.commit()
    return sid
```

#### 3. Generate UUID and pass --session-id at spawn
**File**: `tq/session.py`
**Changes**: Add `import uuid` at top. Modify `spawn()` to generate a UUID, store it, and pass `--session-id` to claude.

```python
import uuid

def spawn(db, sid, prompt, cwd, claude_session_id=None):
    """Spawn a new Claude Code session in tmux."""
    from . import store

    cwd = os.path.expanduser(cwd)
    tmux_name = tmux_session_name(sid)
    settings_path = _write_hooks(sid, cwd)
    oauth = _get_oauth()

    # Generate or use provided Claude session ID
    if not claude_session_id:
        claude_session_id = str(uuid.uuid4())

    store.start_session(db, sid, tmux_name, claude_session_id)

    # ... (existing tmux new-session, env var injection, cd) ...

    # Launch claude with --session-id
    cmd = f"claude --session-id '{claude_session_id}' --settings '{settings_path}' --dangerously-skip-permissions"
    if prompt:
        safe_prompt = prompt.replace("'", "'\\''")
        cmd += f" --prompt '{safe_prompt}'"
    _tmux("send-keys", "-t", tmux_name, cmd, "Enter")

    return tmux_name
```

#### 4. Update start_session to store claude_session_id
**File**: `tq/store.py`
**Changes**: Add `claude_session_id` parameter to `start_session()`

```python
def start_session(db, sid, tmux_session, claude_session_id=None):
    if claude_session_id:
        db.execute(
            "UPDATE sessions SET status='running', tmux_session=?, claude_session_id=?, started_at=? WHERE id=?",
            (tmux_session, claude_session_id, _now(), sid),
        )
    else:
        db.execute(
            "UPDATE sessions SET status='running', tmux_session=?, started_at=? WHERE id=?",
            (tmux_session, _now(), sid),
        )
    db.commit()
```

#### 5. Update callers to pass claude_session_id through
**File**: `tq/daemon.py` — `handle_message()` line 102-103
**File**: `tq/cli.py` — `cmd_run()` line 95-96, `run_queue()` line 174-175

No changes needed to callers — `spawn()` generates the UUID internally and passes it to `start_session()`.

#### 6. Show claude_session_id in status output
**File**: `tq/cli.py` — `cmd_status()` lines 56-66
**Changes**: Add claude_session_id to status display (truncated)

```python
def cmd_status(args):
    db = store.connect()
    sessions = store.all_sessions(db)
    if not sessions:
        print("No sessions.")
        return
    for s in sessions:
        icon = {"running": "●", "done": "✓", "pending": "○", "failed": "✗", "suspended": "◉"}
        status = icon.get(s["status"], "?")
        prompt = (s["prompt"] or "interactive")[:50]
        csid = f"  [{s['claude_session_id'][:8]}]" if s["claude_session_id"] else ""
        print(f"  {status} {s['id']}  {s['status']:<10}  {prompt}{csid}")
```

### Success Criteria:

#### Automated Verification:
- [ ] `python3 -m tq status` runs without error (schema migration works)
- [ ] `python3 -m tq run "test session"` spawns session with `--session-id` in the claude command
- [ ] `sqlite3 ~/.tq/tq.db "SELECT id, claude_session_id FROM sessions ORDER BY created_at DESC LIMIT 1"` shows a UUID

#### Manual Verification:
- [ ] Attach to a spawned tmux session, verify claude command includes `--session-id`
- [ ] Claude session works normally (conversation, tool use, etc.)
- [ ] `tq status` shows the truncated UUID

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Suspend Infrastructure

### Overview
Add the "suspended" status, make `mark_done` conditional so it doesn't clobber "suspended", add a `suspend()` function, and update the health check to mark orphaned sessions as "suspended" instead of "done".

### Changes Required:

#### 1. Conditional mark_done in store.py
**File**: `tq/store.py`
**Changes**: Only mark done if currently running (prevents on-stop hook from overwriting "suspended")

```python
def mark_done(db, sid):
    db.execute(
        "UPDATE sessions SET status='done', completed_at=? WHERE id=? AND status='running'",
        (_now(), sid),
    )
    db.commit()
```

#### 2. Add mark_suspended in store.py
**File**: `tq/store.py`
**Changes**: New function for suspending sessions

```python
def mark_suspended(db, sid):
    db.execute(
        "UPDATE sessions SET status='suspended', completed_at=? WHERE id=? AND status='running'",
        (_now(), sid),
    )
    db.commit()
```

#### 3. Add suspend() in session.py
**File**: `tq/session.py`
**Changes**: New function — graceful stop that marks as suspended, not done

```python
def suspend(db, sid):
    """Suspend a session — stop claude, keep session resumable."""
    from . import store

    store.mark_suspended(db, sid)  # Mark BEFORE stopping, so on-stop hook can't override
    tmux_name = tmux_session_name(sid)
    if _session_exists(tmux_name):
        _tmux("send-keys", "-t", tmux_name, "/exit", "Enter")
        import time; time.sleep(2)
        if _session_exists(tmux_name):
            _tmux("kill-session", "-t", tmux_name)
```

Key: `mark_suspended` runs BEFORE `/exit` is sent. When claude exits, the on-stop hook calls `tq _mark-done`, but `mark_done` now requires `status='running'` — since we already set it to "suspended", the hook's UPDATE matches zero rows. Race condition resolved.

#### 4. Update check_health to mark orphans as suspended
**File**: `tq/session.py`
**Changes**: Change `mark_done` to `mark_suspended` for sessions that have a `claude_session_id` (resumable), keep `mark_done` for sessions without one (legacy, not resumable)

```python
def check_health(db):
    """Check all running sessions, mark dead ones suspended (or done if not resumable)."""
    from . import store
    dead = []
    for s in store.running_sessions(db):
        if s["tmux_session"] and not _session_exists(s["tmux_session"]):
            if s["claude_session_id"]:
                store.mark_suspended(db, s["id"])
            else:
                store.mark_done(db, s["id"])
            dead.append(s["id"])
    return dead
```

#### 5. Update running_sessions query to return claude_session_id
**File**: `tq/store.py`
**Changes**: Already returns `SELECT *`, so `claude_session_id` is included after migration. No change needed.

#### 6. Add CLI suspend command
**File**: `tq/cli.py`
**Changes**: Add `tq suspend <id>` subcommand

```python
def cmd_suspend(args):
    db = store.connect()
    s = store.get_session(db, args.id)
    if not s:
        print(f"Unknown session: {args.id}")
        sys.exit(1)
    if s["status"] != "running":
        print(f"Session {args.id} is not running (status: {s['status']})")
        sys.exit(1)
    session.suspend(db, args.id)
    print(f"Suspended {args.id}")
```

Add to parser and `cmds` dict:
```python
# suspend
p = sub.add_parser("suspend")
p.add_argument("id")
```

### Success Criteria:

#### Automated Verification:
- [ ] `python3 -m tq run "test suspend"` → session starts
- [ ] `python3 -m tq suspend <id>` → prints "Suspended <id>", tmux session is killed
- [ ] `sqlite3 ~/.tq/tq.db "SELECT id, status FROM sessions WHERE id='<id>'"` → status is "suspended"
- [ ] `python3 -m tq status` → shows ◉ icon and "suspended" for the session

#### Manual Verification:
- [ ] Suspend a session, then verify the on-stop hook didn't change it back to "done"
- [ ] Kill the tmux server (`tmux kill-server`), restart daemon, verify running sessions are now "suspended"
- [ ] Legacy sessions (without claude_session_id) still get marked "done" on death

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 3.

---

## Phase 3: Resume on Demand

### Overview
Add a `resume()` function that respawns a suspended session using `claude --resume`, and update the daemon routing logic to auto-resume when a message arrives for a suspended session.

### Changes Required:

#### 1. Add resume() in session.py
**File**: `tq/session.py`
**Changes**: New function to resume a suspended session

```python
def resume(db, sid):
    """Resume a suspended session via claude --resume."""
    from . import store

    s = store.get_session(db, sid)
    if not s or not s["claude_session_id"]:
        return None

    cwd = os.path.expanduser(s["cwd"])
    tmux_name = tmux_session_name(sid)
    settings_path = _write_hooks(sid, cwd)
    oauth = _get_oauth()

    store.mark_running(db, sid, tmux_name)

    # Create tmux session
    _tmux("new-session", "-d", "-s", tmux_name, "-x", "220", "-y", "50")

    # Set session env + OAuth
    _tmux("send-keys", "-t", tmux_name, f"export TQ_SESSION_ID='{sid}'", "Enter")
    if oauth:
        _tmux("send-keys", "-t", tmux_name,
               f"export CLAUDE_CODE_OAUTH_KEY='{oauth}'", "Enter")

    # cd to working directory — CRITICAL: must match original cwd
    # because claude --resume resolves session files by project directory
    # (~/.claude/projects/{path-encoded-cwd}/{uuid}.jsonl)
    _tmux("send-keys", "-t", tmux_name, f"cd '{cwd}'", "Enter")

    # Launch claude with --resume
    cmd = f"claude --resume '{s['claude_session_id']}' --settings '{settings_path}' --dangerously-skip-permissions"
    _tmux("send-keys", "-t", tmux_name, cmd, "Enter")

    return tmux_name
```

#### 2. Add mark_running in store.py
**File**: `tq/store.py`
**Changes**: New function to transition suspended → running

```python
def mark_running(db, sid, tmux_session):
    db.execute(
        "UPDATE sessions SET status='running', tmux_session=?, started_at=?, completed_at=NULL WHERE id=?",
        (tmux_session, _now(), sid),
    )
    db.commit()
```

#### 3. Update daemon routing for suspended sessions
**File**: `tq/daemon.py`
**Changes**: Add "suspended" branch in `handle_message()` at line ~90-97

```python
    if target_session:
        s = store.get_session(db, target_session)
        if s and s["status"] == "running":
            session.route_message(target_session, text)
            store.track_message(db, msg_id, target_session, "in", text)
        elif s and s["status"] == "suspended":
            # Resume the session, then route the message
            session.resume(db, target_session)
            store.track_message(db, msg_id, target_session, "in", text)
            # Give claude a moment to start before sending the message
            import time; time.sleep(3)
            session.route_message(target_session, text)
            sent_id = telegram.send_plain(f"Resumed session {target_session}.", reply_to=msg_id)
            if sent_id:
                store.track_message(db, sent_id, target_session, "out", f"Resumed session {target_session}.")
        else:
            telegram.send_plain(f"Session {target_session} is no longer running.", reply_to=msg_id)
```

#### 4. Add CLI resume command
**File**: `tq/cli.py`
**Changes**: Add `tq resume <id>` subcommand

```python
def cmd_resume(args):
    db = store.connect()
    s = store.get_session(db, args.id)
    if not s:
        print(f"Unknown session: {args.id}")
        sys.exit(1)
    if s["status"] != "suspended":
        print(f"Session {args.id} is not suspended (status: {s['status']})")
        sys.exit(1)
    if not s["claude_session_id"]:
        print(f"Session {args.id} has no Claude session ID — cannot resume")
        sys.exit(1)
    session.resume(db, args.id)
    print(f"Resumed {args.id}")
```

Add to parser and `cmds` dict:
```python
# resume
p = sub.add_parser("resume")
p.add_argument("id")
```

#### 5. Update Telegram /status to show suspended count
**File**: `tq/daemon.py`
**Changes**: Update `handle_command()` — add "suspended" emoji in status display

Already handled by the icon dict in `cli.py`, but the Telegram `/status` at daemon.py:122 also needs the emoji:

```python
status_emoji = {"running": "🟢", "done": "✅", "pending": "⏳", "failed": "❌", "suspended": "💤"}.get(s["status"], "❓")
```

### Success Criteria:

#### Automated Verification:
- [ ] `python3 -m tq run "test resume"` → session starts
- [ ] `python3 -m tq suspend <id>` → session suspended
- [ ] `python3 -m tq resume <id>` → session resumes, tmux session exists, claude is running with `--resume`
- [ ] `sqlite3 ~/.tq/tq.db "SELECT status FROM sessions WHERE id='<id>'"` → "running"

#### Manual Verification:
- [ ] Suspend a session that had conversation history, then resume it — verify claude shows previous messages
- [ ] Send a Telegram reply to a suspended session — verify it auto-resumes and the message is delivered
- [ ] Telegram /status shows 💤 for suspended sessions
- [ ] After resume, further messages route correctly (load-buffer/paste-buffer pattern works)

**Implementation Note**: After completing this phase, pause for manual confirmation before proceeding to Phase 4.

---

## Phase 4: Idle Auto-Suspend

### Overview
Add configurable idle detection to the daemon. Sessions with no Telegram messages for N minutes AND no tmux activity for M minutes are automatically suspended.

### Changes Required:

#### 1. Add idle_timeout to config
**File**: `~/.tq/config.json`
**Changes**: Add optional `idle_timeout_minutes` key (default: 60)

No code change to config loading — `cfg.get("idle_timeout_minutes", 60)` in daemon.py.

#### 2. Add suspended_sessions query in store.py
**File**: `tq/store.py`
**Changes**: Add helper to find sessions eligible for idle suspend

```python
def idle_running_sessions(db, idle_minutes=60):
    """Find running sessions with no messages for idle_minutes."""
    return db.execute("""
        SELECT s.*, MAX(m.created_at) as last_message_at
        FROM sessions s
        LEFT JOIN messages m ON m.session_id = s.id
        WHERE s.status = 'running'
        GROUP BY s.id
        HAVING last_message_at IS NULL
           OR last_message_at < datetime('now', ? || ' minutes')
    """, (f"-{idle_minutes}",)).fetchall()
```

#### 3. Add check_idle in session.py
**File**: `tq/session.py`
**Changes**: New function to check for idle sessions and suspend them

```python
def check_idle(db, idle_timeout_minutes=60, activity_grace_minutes=30):
    """Suspend sessions that are idle (no messages + no tmux activity)."""
    from . import store
    import time

    candidates = store.idle_running_sessions(db, idle_timeout_minutes)
    if not candidates:
        return []

    # Get tmux activity timestamps
    result = _tmux("list-sessions", "-F", "#{session_name} #{session_activity}")
    activity = {}
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            parts = line.split(None, 1)
            if len(parts) == 2:
                activity[parts[0]] = int(parts[1])

    now = time.time()
    grace_secs = activity_grace_minutes * 60
    suspended = []

    for s in candidates:
        tmux_name = s["tmux_session"]
        if not tmux_name:
            continue
        # Check tmux activity — don't suspend if recent output
        last_activity = activity.get(tmux_name, 0)
        if now - last_activity < grace_secs:
            continue
        # Both conditions met: no messages + no tmux activity
        suspend(db, s["id"])
        suspended.append(s["id"])

    return suspended
```

#### 4. Add check_idle to daemon loop
**File**: `tq/daemon.py`
**Changes**: Call `check_idle` alongside `check_health` in the main loop

```python
IDLE_CHECK_INTERVAL = 300  # 5 minutes

# In run():
last_idle = 0

# Inside the while True loop, after health check:
if now - last_idle > IDLE_CHECK_INTERVAL:
    idle_timeout = cfg.get("idle_timeout_minutes", 60)
    activity_grace = cfg.get("activity_grace_minutes", 30)
    if idle_timeout > 0:
        suspended = session.check_idle(db, idle_timeout, activity_grace)
        if suspended:
            for sid in suspended:
                telegram.send_plain(f"💤 Suspended idle session {sid}")
    last_idle = now
```

#### 5. Add tq setup reminder for idle_timeout
**File**: `tq/cli.py` — `cmd_setup()`
**Changes**: Add optional idle timeout config during setup (or just document it)

No code change — document in CLAUDE.md that `idle_timeout_minutes` and `activity_grace_minutes` are optional config keys.

### Success Criteria:

#### Automated Verification:
- [ ] Daemon starts without error with `idle_timeout_minutes` in config
- [ ] Daemon starts without error without `idle_timeout_minutes` in config (default 60)
- [ ] Setting `idle_timeout_minutes: 0` disables idle checking

#### Manual Verification:
- [ ] Start a session, wait for idle timeout → session gets suspended automatically
- [ ] Telegram receives "💤 Suspended idle session <id>" notification
- [ ] A session that is actively producing output (tmux activity) is NOT suspended even if no messages
- [ ] Reply to the auto-suspended session → it resumes correctly
- [ ] Set `idle_timeout_minutes: 1` for quick testing, verify it works within ~5 minutes

**Implementation Note**: After completing this phase, verify the full lifecycle end-to-end: spawn → idle → auto-suspend → reply → resume → conversation continues.

---

## Testing Strategy

### Manual Testing Steps:
1. Spawn a session via CLI: `tq run "say hello"`
2. Verify `--session-id` in the claude command (attach to tmux)
3. Suspend it: `tq suspend <id>`
4. Resume it: `tq resume <id>` — verify conversation history loads
5. Suspend again, then send a Telegram reply — verify auto-resume
6. Kill tmux server, restart daemon — verify orphaned sessions become "suspended"
7. Set `idle_timeout_minutes: 1`, start a session, wait — verify auto-suspend
8. Reply to auto-suspended session — verify full resume with conversation

### Edge Cases to Test:
- Suspend a session that's mid-tool-call (claude should handle gracefully on resume)
- Resume a session whose JSONL was deleted (should fail gracefully)
- Two rapid messages to a suspended session (should not spawn two tmux sessions)
- Session with no `claude_session_id` (legacy) — should mark "done" not "suspended" on death
- Resume from wrong directory — if cwd was deleted or moved, `--resume` will fail to find the session JSONL (JSONL is stored under `~/.claude/projects/{path-encoded-cwd}/`)

## Performance Considerations

- `check_idle` queries SQLite + one `tmux list-sessions` call every 5 minutes — negligible overhead
- Suspending ~35 idle sessions reclaims ~2.1 GB RAM
- Resume adds ~3 second latency (tmux spawn + claude startup) before the message is delivered

## Migration Notes

- `ALTER TABLE sessions ADD COLUMN claude_session_id TEXT` runs automatically on first `connect()` after upgrade
- Existing sessions will have `claude_session_id = NULL` — these are treated as non-resumable (marked "done" on death, not "suspended")
- No data loss — existing sessions continue to work normally
- Rollback: simply don't use `--session-id` flag; NULL column is harmless

## References

- Research: `thoughts/shared/research/2026-03-17-tmux-resurrect-session-persistence.md`
- Claude Code CLI flags: `claude --help` (--session-id, --resume, --continue, --fork-session)
- Session storage: `~/.claude/projects/{slug}/{uuid}.jsonl`
- PID mapping: `~/.claude/sessions/{pid}.json`

## Research Findings

Full agent findings are preserved in the findings directory for deeper reference:
- `thoughts/shared/plans/findings/2026-03-17-session-suspend-resume/analyzer-code-change-points.md` — Exact code locations and change requirements
- `thoughts/shared/plans/findings/2026-03-17-session-suspend-resume/pattern-finder-schema-status.md` — Schema patterns, status references, config patterns
- `thoughts/shared/research/findings/2026-03-17-tmux-resurrect-session-persistence/` — Full research findings (6 files)
