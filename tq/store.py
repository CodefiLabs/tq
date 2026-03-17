"""SQLite state — two tables, one file, all of tq's memory."""

import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.expanduser("~/.tq/tq.db")

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


def _now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    return db


def create_session(db, sid, prompt=None, cwd="~", queue=None):
    db.execute(
        "INSERT INTO sessions (id, prompt, cwd, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (sid, prompt, cwd, _now()),
    )
    db.commit()
    return sid


def start_session(db, sid, tmux_session):
    db.execute(
        "UPDATE sessions SET status='running', tmux_session=?, started_at=? WHERE id=?",
        (tmux_session, _now(), sid),
    )
    db.commit()


def mark_done(db, sid):
    db.execute(
        "UPDATE sessions SET status='done', completed_at=? WHERE id=?",
        (_now(), sid),
    )
    db.commit()


def get_session(db, sid):
    return db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()


def running_sessions(db):
    return db.execute("SELECT * FROM sessions WHERE status='running'").fetchall()


def all_sessions(db):
    return db.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()


def sessions_by_queue(db, queue):
    return db.execute(
        "SELECT * FROM sessions WHERE queue=? ORDER BY created_at", (queue,)
    ).fetchall()


def track_message(db, telegram_msg_id, session_id, direction, text):
    db.execute(
        "INSERT OR IGNORE INTO messages (telegram_msg_id, session_id, direction, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (telegram_msg_id, session_id, direction, text, _now()),
    )
    db.commit()


def lookup_message(db, telegram_msg_id):
    row = db.execute(
        "SELECT session_id FROM messages WHERE telegram_msg_id=?",
        (telegram_msg_id,),
    ).fetchone()
    return row["session_id"] if row else None
