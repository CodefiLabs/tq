"""The brain — Telegram long-poll + tmux health check."""

import os
import json
import time
import signal
import sys

from . import store, session, telegram

PID_FILE = os.path.expanduser("~/.tq/daemon.pid")
CONFIG_PATH = os.path.expanduser("~/.tq/config.json")
HEALTH_INTERVAL = 30  # seconds
IDLE_CHECK_INTERVAL = 300  # 5 minutes


def load_config():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    telegram.configure(cfg["telegram_bot_token"], cfg["chat_id"])
    return cfg


def save_pid():
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def read_pid():
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_running():
    pid = read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_daemon():
    pid = read_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped daemon (pid {pid})")
        except OSError:
            print("Daemon not running")
        try:
            os.unlink(PID_FILE)
        except FileNotFoundError:
            pass
    else:
        print("Daemon not running")


def handle_message(db, cfg, msg):
    """Route a single Telegram message."""
    chat_id = str(msg.get("chat", {}).get("id", ""))
    if chat_id != str(cfg["chat_id"]):
        return  # ignore messages from other chats

    text = msg.get("text", "").strip()
    msg_id = msg.get("message_id")
    if not text or not msg_id:
        return

    # Handle /commands
    if text.startswith("/"):
        handle_command(db, text, msg_id)
        return

    # React to acknowledge
    telegram.react(msg_id)

    # Route: reply-to → existing session, else → new session
    reply_to = msg.get("reply_to_message", {}).get("message_id")
    target_session = None

    if reply_to:
        target_session = store.lookup_message(db, reply_to)

    if target_session:
        # Route to existing session
        s = store.get_session(db, target_session)
        if s and s["status"] == "running":
            session.route_message(target_session, text)
            store.track_message(db, msg_id, target_session, "in", text)
        elif s and s["status"] == "suspended":
            # Resume the session, then route the message
            session.resume(db, target_session)
            store.track_message(db, msg_id, target_session, "in", text)
            time.sleep(3)
            session.route_message(target_session, text)
            sent_id = telegram.send_plain(f"Resumed session {target_session}.", reply_to=msg_id)
            if sent_id:
                store.track_message(db, sent_id, target_session, "out", f"Resumed session {target_session}.")
        else:
            telegram.send_plain(f"Session {target_session} is no longer running.", reply_to=msg_id)
    else:
        # Spawn new session
        sid = session.make_id(f"{msg_id}-{text}")
        cwd = cfg.get("default_cwd", "~")
        store.create_session(db, sid, prompt=text, cwd=cwd)
        session.spawn(db, sid, text, cwd)
        store.track_message(db, msg_id, sid, "in", text)
        sent_id = telegram.send_plain(f"Session {sid} started.", reply_to=msg_id)
        if sent_id:
            store.track_message(db, sent_id, sid, "out", f"Session {sid} started.")


def handle_command(db, text, msg_id):
    """Handle Telegram /commands."""
    parts = text.split(None, 1)
    cmd = parts[0].lower()

    if cmd == "/status":
        sessions = store.all_sessions(db)
        if not sessions:
            telegram.send_plain("No sessions.", reply_to=msg_id)
            return
        lines = []
        for s in sessions[:15]:
            status_emoji = {"running": "🟢", "done": "✅", "pending": "⏳", "failed": "❌", "suspended": "💤"}.get(s["status"], "❓")
            lines.append(f"{status_emoji} {s['id']} — {(s['prompt'] or 'interactive')[:40]}")
        telegram.send_plain("\n".join(lines), reply_to=msg_id)

    elif cmd == "/stop" and len(parts) > 1:
        sid = parts[1].strip()
        s = store.get_session(db, sid)
        if s:
            session.stop(sid)
            store.mark_done(db, sid)
            telegram.send_plain(f"Stopped {sid}.", reply_to=msg_id)
        else:
            telegram.send_plain(f"Unknown session: {sid}", reply_to=msg_id)

    elif cmd == "/help":
        telegram.send_plain(
            "tq commands:\n/status — list sessions\n/stop <id> — stop a session\n/help — this message",
            reply_to=msg_id,
        )


def run():
    """Main daemon loop."""
    cfg = load_config()
    db = store.connect()
    save_pid()

    def cleanup(sig, frame):
        try:
            os.unlink(PID_FILE)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    print(f"tq daemon running (pid {os.getpid()})")
    offset = None
    last_health = 0
    last_idle = 0

    while True:
        try:
            # Telegram long-poll
            updates = telegram.get_updates(offset=offset, timeout=HEALTH_INTERVAL)
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message")
                if msg:
                    handle_message(db, cfg, msg)

            # Health check
            now = time.time()
            if now - last_health > HEALTH_INTERVAL:
                session.check_health(db)
                last_health = now

            # Idle auto-suspend
            if now - last_idle > IDLE_CHECK_INTERVAL:
                idle_timeout = cfg.get("idle_timeout_minutes", 60)
                activity_grace = cfg.get("activity_grace_minutes", 30)
                if idle_timeout > 0:
                    suspended = session.check_idle(db, idle_timeout, activity_grace)
                    for sid in suspended:
                        telegram.send_plain(f"💤 Suspended idle session {sid}")
                last_idle = now

        except KeyboardInterrupt:
            cleanup(None, None)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            time.sleep(5)
