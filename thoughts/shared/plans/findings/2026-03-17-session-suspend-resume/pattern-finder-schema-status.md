# Pattern Finder: Schema, Status, Config, and Test Patterns in tq

Analyzed: 2026-03-17
Source: `/Users/kk/Sites/codefi/tq/`
Files examined: `tq/store.py`, `tq/daemon.py`, `tq/session.py`, `tq/cli.py`, `tq/telegram.py`, `migrate-v1-to-v2.sh`

---

## 1. SQLite Schema Evolution Pattern

### Current Approach: CREATE TABLE IF NOT EXISTS (No Migration System)

**File**: `/Users/kk/Sites/codefi/tq/tq/store.py:9-31`

The entire schema is defined as a single `SCHEMA` constant string containing `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements. This is executed on every `connect()` call via `db.executescript(SCHEMA)` (line 44).

```python
SCHEMA = """
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
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_msg_id INTEGER UNIQUE,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    direction TEXT NOT NULL CHECK(direction IN ('in', 'out')),
    text TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_telegram ON messages(telegram_msg_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
"""
```

**Key observations**:
- **No migration system** -- no version tracking, no ALTER TABLE logic, no migration files
- **No schema_version table** -- the DB has no way to know what version it is
- `IF NOT EXISTS` means the schema constant is idempotent for table creation but **cannot add new columns** to existing tables
- Every `connect()` call (store.py:38-45) re-runs the full schema script -- this is safe because of `IF NOT EXISTS`
- `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` are set on every connection

### Implications for Adding Columns

**There is NO existing pattern for ALTER TABLE.** The codebase has never needed to add a column to an existing table. The grep for `ALTER TABLE|migrate|migration|schema_version` found zero hits in Python files.

The only migration that exists is `migrate-v1-to-v2.sh` (a bash script that migrated the entire project structure from v1 to v2) -- this was a full rewrite, not a schema migration.

### Recommended Pattern for Adding Columns

To add a new column (e.g., `claude_session_id TEXT` or a new status), the `connect()` function needs an ALTER TABLE block after `executescript(SCHEMA)`. The simplest approach consistent with tq's "no dependencies" philosophy:

```python
def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    _migrate(db)  # <-- new
    return db

def _migrate(db):
    """Add columns that don't exist yet. Safe to run on every connect."""
    cols = {r[1] for r in db.execute("PRAGMA table_info(sessions)").fetchall()}
    if "claude_session_id" not in cols:
        db.execute("ALTER TABLE sessions ADD COLUMN claude_session_id TEXT")
        db.commit()
```

This follows tq's existing pattern of running setup on every `connect()`.

---

## 2. Status Values: Complete Inventory

### Defined Statuses

There are **4 status values** referenced in the codebase. However, `"failed"` is never SET anywhere -- it only appears in display mappings.

| Status | Set Where | Read/Checked Where |
|--------|-----------|-------------------|
| `'pending'` | `store.create_session` (store.py:50) | cli.py:63 display, daemon.py:122 display |
| `'running'` | `store.start_session` (store.py:59) | daemon.py:93 routing check, store.py:78 `running_sessions()`, cli.py:92+170 skip check, cli.py:63 display, daemon.py:122 display |
| `'done'` | `store.mark_done` (store.py:67) | cli.py:92+170 skip check, cli.py:63 display, daemon.py:122 display |
| `'failed'` | **NEVER SET** | cli.py:63 display only, daemon.py:122 display only |

### Every Location That Sets Status

1. **store.py:50** -- `create_session()`: Sets `status='pending'` via INSERT
2. **store.py:59** -- `start_session()`: Sets `status='running'` via UPDATE
3. **store.py:67** -- `mark_done()`: Sets `status='done'` via UPDATE

### Every Location That Reads/Checks Status

1. **store.py:78** -- `running_sessions()`: `WHERE status='running'` -- used by health check
2. **daemon.py:93** -- `handle_message()`: `if s and s["status"] == "running"` -- routing gate for replies
3. **daemon.py:122** -- `handle_command()`: Display mapping `{"running": ..., "done": ..., "pending": ..., "failed": ...}`
4. **cli.py:63-64** -- `cmd_status()`: Display mapping `{"running": "...", "done": "...", "pending": "...", "failed": "..."}`
5. **cli.py:92** -- `cmd_run()`: `if existing["status"] in ("running", "done")` -- skip already-processed
6. **cli.py:170** -- `run_queue()`: `if existing["status"] in ("running", "done")` -- skip already-processed

### Adding a "suspended" Status

The status field has **no CHECK constraint** in the schema -- it's just `TEXT NOT NULL DEFAULT 'pending'`. Any string value can be stored. The changes needed to add `"suspended"`:

1. **store.py**: Add `suspend_session()` and `suspended_sessions()` functions (following `mark_done()`/`running_sessions()` pattern)
2. **daemon.py:93**: Add `elif s["status"] == "suspended"` branch for auto-resume
3. **daemon.py:122**: Add `"suspended"` to the emoji map
4. **cli.py:63**: Add `"suspended"` to the icon map
5. **cli.py:92, 170**: Decide if `"suspended"` should be in the skip set (probably not -- suspended sessions should be resumable)

### The "failed" Status Gap

`"failed"` is listed in both display maps but is never actually set by any code path. There is no `mark_failed()` function in store.py. This is a dead display path.

---

## 3. Config Options Pattern

### Config File Format

**Path**: `~/.tq/config.json`

**Current schema** (from cli.py:250-254 `cmd_setup`):
```json
{
    "telegram_bot_token": "<token>",
    "chat_id": "<chat_id>",
    "default_cwd": "~"
}
```

### How Config Is Loaded

**File**: `/Users/kk/Sites/codefi/tq/tq/daemon.py:12-20`

```python
CONFIG_PATH = os.path.expanduser("~/.tq/config.json")

def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    telegram.configure(cfg["telegram_bot_token"], cfg["chat_id"])
    return cfg
```

The config dict is returned and passed around. It's accessed via:
- `cfg["telegram_bot_token"]` -- daemon.py:19 (required)
- `cfg["chat_id"]` -- daemon.py:19, daemon.py:67 (required)
- `cfg.get("default_cwd", "~")` -- daemon.py:101 (optional with default)

### Pattern for Adding Config Options

The existing pattern for optional config values is `cfg.get("key", default)` (daemon.py:101). To add an idle timeout setting:

```python
# In daemon.py or wherever it's needed:
idle_timeout = cfg.get("idle_timeout_seconds", 3600)  # default 1 hour
```

No schema validation. No required/optional distinction beyond whether `.get()` or `[]` is used. Adding a new key to config.json is backward-compatible as long as you use `.get()` with a default.

### Where Config Is Used in the Daemon Loop

The `cfg` dict is loaded once at startup (daemon.py:145) and passed to `handle_message` (daemon.py:171). It's never reloaded during runtime. To pick up config changes, the daemon must be restarted.

---

## 4. Existing Tests

### Result: NO TESTS EXIST

Searched for:
- `test_*.py` -- no files found
- `tests/` directory -- does not exist
- `pytest.ini` -- does not exist
- `conftest.py` -- does not exist
- `.pytest*` cache -- does not exist

The migration script (migrate-v1-to-v2.sh) actually **deleted** a previous `tests/` directory (line 101: `rm -rf tests/`), and no v2 tests were created.

The codebase has zero test coverage. There is no test infrastructure set up.

---

## 5. Summary of Patterns Relevant to Session Suspend/Resume

### Schema Changes
- **No migration system**. Must add ALTER TABLE logic to `connect()` or a `_migrate()` helper.
- Pattern: check `PRAGMA table_info(sessions)` then conditionally ALTER TABLE.

### New Status Value
- Status is unconstrained TEXT. Just store `"suspended"` -- no schema change needed for the status itself.
- Update 6 locations: 2 display maps (daemon.py:122, cli.py:63), 1 routing check (daemon.py:93), 2 skip checks (cli.py:92, 170), and add a new store function.

### New Store Functions Needed
Follow the pattern of existing functions in store.py:
```python
def suspend_session(db, sid, claude_session_id=None):
    db.execute(
        "UPDATE sessions SET status='suspended', completed_at=? WHERE id=?",
        (_now(), sid),
    )
    db.commit()

def suspended_sessions(db):
    return db.execute("SELECT * FROM sessions WHERE status='suspended'").fetchall()
```

### Config for Idle Timeout
Add to `~/.tq/config.json`:
```json
{
    "idle_timeout_seconds": 3600
}
```
Read with: `cfg.get("idle_timeout_seconds", 3600)` -- follows `default_cwd` pattern.

### Health Check Extension Point
The existing `check_health(db)` in session.py:136-144 runs every ~30 seconds. Idle detection can be added alongside the dead-session detection already there. The daemon loop at daemon.py:174-177 is the integration point.

### No Tests to Break
There are no existing tests, so no test updates are needed. However, this also means there's no safety net -- manual testing is the only verification.
