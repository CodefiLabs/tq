# Code Change Points for Session Suspend/Resume

Analyzer: codebase-analyzer
Date: 2026-03-17
Source: /Users/kk/Sites/codefi/tq/

---

## 1. session.py spawn() — Lines 71-102

### Current Behavior

`spawn(db, sid, prompt, cwd)` creates a new tmux session, sets environment variables, and launches Claude Code with a prompt.

The claude command is built at **lines 95-99** as a string:

```python
cmd = f"claude --settings '{settings_path}' --dangerously-skip-permissions"
if prompt:
    safe_prompt = prompt.replace("'", "'\\''")
    cmd += f" --prompt '{safe_prompt}'"
```

This string is then sent to tmux at **line 100**:

```python
_tmux("send-keys", "-t", tmux_name, cmd, "Enter")
```

### Where --session-id Would Be Added

To support resume, `--session-id <sid>` (or whatever the Claude Code flag is) would be appended to `cmd` between the `--dangerously-skip-permissions` flag and the conditional `--prompt` block. Specifically, after line 95 and before line 96:

```python
cmd = f"claude --settings '{settings_path}' --dangerously-skip-permissions"
# NEW: add session-id for resume support
cmd += f" --session-id '{session_id_value}'"
if prompt:
    ...
```

The `session_id_value` would need to come from either:
- A new column in the sessions table (e.g., `claude_session_id`) stored after initial spawn
- Or, for resume, a parameter passed into `spawn()` or a new `resume()` function

### Key Observation

The function currently calls `store.start_session(db, sid, tmux_name)` at **line 80** which sets status to 'running'. For resume, this same call would work -- it updates status and tmux_session. But we'd need to know the Claude Code session ID from a prior run to pass `--session-id`.

### Hook Generation

`_write_hooks(sid, cwd)` at **lines 43-68** generates `on-stop.sh` which calls `tq _mark-done <sid>`. For suspend, we may want a different hook behavior -- mark as "suspended" rather than "done" when the stop is triggered by an idle timeout. This is a subtlety: the on-stop hook fires regardless of WHY claude stopped (user /exit, crash, suspend). One approach: the suspend flow calls `/exit` to gracefully stop, then explicitly sets status to "suspended" AFTER the on-stop hook would have fired. Since `stop()` already waits 2 seconds (line 131), the `_mark-done` hook would fire first, then the suspend logic would overwrite the status to "suspended".

---

## 2. session.py stop() — Lines 126-133

### Current Behavior

```python
def stop(sid):
    tmux_name = tmux_session_name(sid)
    if _session_exists(tmux_name):
        _tmux("send-keys", "-t", tmux_name, "/exit", "Enter")
        import time; time.sleep(2)
        if _session_exists(tmux_name):
            _tmux("kill-session", "-t", tmux_name)
```

Flow:
1. Checks if tmux session `tq-<sid>` exists
2. Sends `/exit` to gracefully stop Claude Code
3. Waits 2 seconds for Claude to process the exit
4. If tmux session still alive, force-kills it

### Reuse for Suspend

This function CAN be reused for suspend with one important nuance. The `/exit` command causes Claude Code to stop, which triggers the `on-stop.sh` hook, which calls `tq _mark-done <sid>`, which sets status to "done". For suspend, the caller must **overwrite the status to "suspended" AFTER calling stop()**, since the on-stop hook will have already fired during that 2-second sleep. The sequence would be:

```
suspend(sid):
    stop(sid)                     # sends /exit, triggers on-stop hook -> marks "done"
    store.mark_suspended(db, sid) # overwrites "done" -> "suspended"
```

Alternatively, a new `suspend()` function could be created that skips the hook or passes context to prevent the hook from marking done. But the overwrite approach is simpler and avoids hook complexity.

**Critical detail**: The on-stop hook script at line 55 does `tq _mark-done <sid>` which calls `store.mark_done()`. This is a fire-and-forget subprocess. There is a **race condition**: if the hook hasn't completed by the time suspend logic runs `mark_suspended()`, the hook could overwrite "suspended" back to "done". The 2-second sleep at line 131 mitigates this but is not guaranteed. A more robust approach: check/set status atomically with `UPDATE sessions SET status='suspended' WHERE id=? AND status IN ('running','done')`.

---

## 3. store.py Schema — Lines 10-31

### Exact CREATE TABLE

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    prompt TEXT,
    cwd TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    tmux_session TEXT,
    queue TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);
```

### Column Inventory

| Column | Type | Constraints | Notes |
|--------|------|------------|-------|
| id | TEXT | PRIMARY KEY | 8-char SHA256 hash |
| prompt | TEXT | nullable | The task prompt |
| cwd | TEXT | NOT NULL | Working directory |
| status | TEXT | NOT NULL, DEFAULT 'pending' | **No CHECK constraint** |
| tmux_session | TEXT | nullable | e.g., "tq-abc12345" |
| queue | TEXT | nullable | Queue name if from queue file |
| created_at | TEXT | NOT NULL | ISO timestamp |
| started_at | TEXT | nullable | Set when status -> running |
| completed_at | TEXT | nullable | Set when status -> done |

### Key Finding: No CHECK Constraint on Status

The `status` column has **no CHECK constraint**. Current values used in code: 'pending', 'running', 'done'. The status_emoji dict at daemon.py:122 also references 'failed' but no code path actually sets that status. The CLI status display at cli.py:63 also maps 'failed'.

**This means "suspended" can be added as a status value with zero schema migration.** Just start writing it. No ALTER TABLE needed.

### Missing Column for Resume

There is **no column to store the Claude Code session ID**. For `--session-id` resume, we would need either:
- A new `claude_session_id TEXT` column (requires ALTER TABLE or schema migration)
- Store it in the `tmux_session` column (overloading, not recommended)
- Store it in a separate metadata approach (e.g., in a file under `~/.tq/hooks/<sid>/`)

The simplest approach: `ALTER TABLE sessions ADD COLUMN claude_session_id TEXT`. Since `connect()` calls `executescript(SCHEMA)` on every connection, adding the column to SCHEMA won't work (CREATE TABLE IF NOT EXISTS doesn't add new columns). A migration step would be needed in `connect()`.

### Messages Table

```sql
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_msg_id INTEGER UNIQUE,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    text TEXT,
    created_at TEXT NOT NULL
);
```

No changes needed for suspend/resume.

---

## 4. daemon.py handle_message() — Lines 64-107

### Full Routing Logic

```
1. Validate chat_id matches config (line 67) — ignore if mismatch
2. Extract text and msg_id (lines 70-73) — skip if empty
3. If text starts with "/" -> handle_command() (lines 76-78)
4. React with eyes emoji to acknowledge (line 81)
5. Check if reply-to another message (line 84)
6. If reply-to, look up session from message table (line 88)
7. If target_session found AND status == "running" (line 93):
     -> route_message() to tmux session (line 94)
     -> track the message (line 95)
8. If target_session found BUT NOT running (line 96-97):
     -> send "Session {id} is no longer running." (LINE 97)
9. If no target_session (new message, line 98-107):
     -> make_id from msg_id + text
     -> create_session in DB
     -> spawn tmux + claude
     -> track message + send confirmation
```

### "No Longer Running" Message Location

**Line 97**: `telegram.send_plain(f"Session {target_session} is no longer running.", reply_to=msg_id)`

This fires when `s["status"] != "running"` -- i.e., for done, pending, failed, or any other status including a future "suspended".

### Where "Suspended" Handling Would Be Added

The critical insertion point is at **lines 90-97**, where the routing checks `s["status"] == "running"`. Currently:

```python
if target_session:
    s = store.get_session(db, target_session)
    if s and s["status"] == "running":
        session.route_message(target_session, text)
        store.track_message(db, msg_id, target_session, "in", text)
    else:
        telegram.send_plain(f"Session {target_session} is no longer running.", reply_to=msg_id)
```

For suspend/resume, a new branch would be inserted between lines 93 and 96:

```python
if target_session:
    s = store.get_session(db, target_session)
    if s and s["status"] == "running":
        session.route_message(target_session, text)
        store.track_message(db, msg_id, target_session, "in", text)
    elif s and s["status"] == "suspended":
        # Resume the suspended session
        session.resume(db, s["id"], s["cwd"], s["claude_session_id"])
        session.route_message(target_session, text)
        store.track_message(db, msg_id, target_session, "in", text)
        telegram.send_plain(f"Session {target_session} resumed.", reply_to=msg_id)
    else:
        telegram.send_plain(f"Session {target_session} is no longer running.", reply_to=msg_id)
```

### handle_command() — Lines 110-140

The `/status` command at **line 122** builds status emojis from a dict:
```python
{"running": "🟢", "done": "✅", "pending": "⏳", "failed": "❌"}
```
A "suspended" entry would need to be added: e.g., `"suspended": "⏸️"`.

The `/stop` command at **lines 126-134** calls `session.stop(sid)` then `store.mark_done(db, sid)`. A `/suspend` command could be added here following the same pattern.

---

## 5. daemon.py run() — Lines 143-184

### Main Loop Structure

```python
def run():
    cfg = load_config()       # line 145
    db = store.connect()      # line 146
    save_pid()                # line 147
    # Signal handlers         # lines 149-157

    offset = None             # line 160
    last_health = 0           # line 161

    while True:               # line 163
        # Telegram long-poll  # lines 165-171
        updates = telegram.get_updates(offset=offset, timeout=HEALTH_INTERVAL)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if msg:
                handle_message(db, cfg, msg)

        # Health check        # lines 173-177
        now = time.time()
        if now - last_health > HEALTH_INTERVAL:
            session.check_health(db)
            last_health = now
```

### Where check_health Is Called

**Line 176**: `session.check_health(db)` — called every `HEALTH_INTERVAL` (30 seconds, line 13) inside the main while loop, after processing Telegram updates.

### Where check_idle Would Be Added

Directly after `check_health()` at **lines 176-177**. A new idle check would fit naturally here:

```python
if now - last_health > HEALTH_INTERVAL:
    session.check_health(db)
    session.check_idle(db)    # NEW: suspend idle sessions
    last_health = now
```

Or, if idle checking needs a different interval (e.g., 5 minutes), a separate `last_idle` timer would be added:

```python
last_health = 0
last_idle = 0                 # NEW
IDLE_INTERVAL = 300           # NEW: 5 minutes

while True:
    ...
    now = time.time()
    if now - last_health > HEALTH_INTERVAL:
        session.check_health(db)
        last_health = now
    if now - last_idle > IDLE_INTERVAL:           # NEW
        session.check_idle(db)                     # NEW
        last_idle = now                            # NEW
```

---

## 6. session.py check_health() — Lines 136-144

### Current Behavior

```python
def check_health(db):
    dead = []
    for s in store.running_sessions(db):
        if s["tmux_session"] and not _session_exists(s["tmux_session"]):
            store.mark_done(db, s["id"])
            dead.append(s["id"])
    return dead
```

Logic:
1. Get all sessions with `status='running'` (via `store.running_sessions()`)
2. For each, check if the tmux session still exists
3. If tmux session is gone, mark the DB session as "done"
4. Return list of dead session IDs

### How It Would Need to Change for "Suspended"

**The function itself does not need to change.** It only queries `running_sessions(db)` which returns sessions with `status='running'`. Suspended sessions have `status='suspended'`, so they would NOT be returned by `running_sessions()` and would NOT be checked by `check_health()`. This is correct behavior -- a suspended session has no tmux session to check.

However, `store.running_sessions()` at store.py:77-78 is:
```python
def running_sessions(db):
    return db.execute("SELECT * FROM sessions WHERE status='running'").fetchall()
```

This already filters to only 'running' status. Suspended sessions are excluded. No change needed here either.

**One edge case**: If a session is suspended but its tmux session hasn't been cleaned up yet (e.g., the `stop()` force-kill at line 132-133 somehow left a zombie tmux), health check wouldn't catch it because the session is no longer in 'running' status. This is a minor concern -- the `stop()` function already handles cleanup.

---

## 7. cli.py cmd_run() — Lines 80-101

### Current Behavior

```python
def cmd_run(args):
    db = store.connect()
    target = args.target
    cwd = os.path.expanduser(args.cwd or os.getcwd())

    if target and os.path.isfile(target):
        run_queue(db, target, cwd)          # queue file path
    elif target:
        sid = session.make_id(target)       # deterministic hash of prompt
        existing = store.get_session(db, sid)
        if existing and existing["status"] in ("running", "done"):
            print(f"Session {sid} already {existing['status']}, skipping.")
            return
        store.create_session(db, sid, prompt=target, cwd=cwd)
        session.spawn(db, sid, target, cwd)
        print(f"Spawned {sid}")
    else:
        print("Usage: ...")
```

### Key Logic at Lines 91-93

The skip check: `if existing and existing["status"] in ("running", "done")` means:
- **running** -> skip (already active)
- **done** -> skip (already completed)
- **pending** -> would be re-created (via create_session at line 95, but note this would fail on PRIMARY KEY conflict since the row already exists)
- **suspended** (future) -> would fall through to create_session, causing a PRIMARY KEY conflict

### Changes Needed for Suspend/Resume

1. **Status check at line 92**: Add "suspended" to the resume path:
```python
if existing and existing["status"] == "suspended":
    # Resume instead of spawn new
    session.resume(db, sid, cwd, existing["claude_session_id"])
    print(f"Resumed {sid}")
    return
if existing and existing["status"] in ("running", "done"):
    print(f"Session {sid} already {existing['status']}, skipping.")
    return
```

2. **--session-id**: Yes, `cmd_run()` would also need `--session-id` support since it calls `session.spawn()`. The `spawn()` function change (adding `--session-id` to the claude command) would apply to both CLI and daemon-triggered spawns automatically, since both go through `spawn()`.

3. **run_queue() at line 170**: Same pattern -- `existing["status"] in ("running", "done")` skips. "Suspended" sessions would need handling here too.

---

## Summary of All Change Points

### New Functions Needed

| Location | Function | Purpose |
|----------|----------|---------|
| session.py | `resume(db, sid, cwd, claude_session_id)` | Spawn tmux + claude with `--session-id` |
| session.py | `check_idle(db)` | Find idle running sessions, suspend them |
| store.py | `mark_suspended(db, sid)` | Set status='suspended' |
| store.py | `suspended_sessions(db)` | Query status='suspended' (optional, for /status) |

### Existing Functions to Modify

| File:Line | Function | Change |
|-----------|----------|--------|
| session.py:95 | `spawn()` | Add `--session-id` to claude command (for both new and resumed) |
| store.py:10-31 | SCHEMA | Add `claude_session_id TEXT` column + migration logic |
| store.py:38-45 | `connect()` | Add ALTER TABLE migration for existing DBs |
| daemon.py:90-97 | `handle_message()` | Add `elif s["status"] == "suspended"` branch for auto-resume |
| daemon.py:122 | `handle_command()` /status | Add "suspended" emoji mapping |
| daemon.py:176 | `run()` | Add `check_idle()` call in main loop |
| cli.py:92 | `cmd_run()` | Handle "suspended" status (resume instead of skip) |
| cli.py:63 | `cmd_status()` | Add "suspended" icon mapping |
| cli.py:170 | `run_queue()` | Handle "suspended" status in queue processing |

### New CLI Commands / Telegram Commands

| Command | Purpose |
|---------|---------|
| `tq suspend <id>` | CLI manual suspend |
| `/suspend <id>` | Telegram manual suspend |
| `tq resume <id>` | CLI manual resume (or reuse `tq run`) |

### Race Condition to Address

The on-stop.sh hook calls `tq _mark-done <sid>` asynchronously. When suspending, the flow is:
1. `stop(sid)` sends /exit -> triggers on-stop hook -> `_mark-done` sets "done"
2. Suspend logic sets "suspended"

If step 1's hook runs AFTER step 2, it overwrites "suspended" with "done". Fix: use conditional UPDATE:
```sql
UPDATE sessions SET status='suspended' WHERE id=? AND status IN ('running', 'done')
```
And modify `_mark-done` / `mark_done()` to not overwrite "suspended":
```sql
UPDATE sessions SET status='done', completed_at=? WHERE id=? AND status='running'
```
(Currently at store.py:67 it's unconditional: `WHERE id=?`)
