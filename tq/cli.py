"""tq — Claude Code sessions via Telegram + tmux.

Usage:
    tq daemon start|stop|status
    tq status
    tq stop <id>
    tq run [file|prompt] [--cwd DIR]
    tq reply <session-id> <text>
    tq setup
    tq _mark-done <id>
"""

import argparse
import hashlib
import json
import os
import re
import sys

from . import store, session, telegram, daemon


def cmd_daemon(args):
    if args.action == "start":
        if daemon.is_running():
            print(f"Already running (pid {daemon.read_pid()})")
            return
        if not os.path.exists(daemon.CONFIG_PATH):
            print("Run 'tq setup' first.")
            sys.exit(1)
        if args.foreground:
            daemon.run()
        else:
            pid = os.fork()
            if pid > 0:
                print(f"Daemon started (pid {pid})")
                return
            os.setsid()
            # Redirect stdio
            log = os.path.expanduser("~/.tq/daemon.log")
            fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            os.dup2(fd, 1)
            os.dup2(fd, 2)
            os.close(fd)
            os.close(0)
            daemon.run()
    elif args.action == "stop":
        daemon.stop_daemon()
    elif args.action == "status":
        if daemon.is_running():
            print(f"Running (pid {daemon.read_pid()})")
        else:
            print("Not running")


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


def cmd_stop(args):
    db = store.connect()
    s = store.get_session(db, args.id)
    if not s:
        print(f"Unknown session: {args.id}")
        sys.exit(1)
    session.stop(args.id)
    store.mark_done(db, args.id)
    print(f"Stopped {args.id}")


def cmd_run(args):
    db = store.connect()
    target = args.target
    cwd = os.path.expanduser(args.cwd or os.getcwd())

    if target and os.path.isfile(target):
        # Queue file
        run_queue(db, target, cwd)
    elif target:
        # Single prompt
        sid = session.make_id(target)
        existing = store.get_session(db, sid)
        if existing and existing["status"] in ("running", "done"):
            print(f"Session {sid} already {existing['status']}, skipping.")
            return
        store.create_session(db, sid, prompt=target, cwd=cwd)
        session.spawn(db, sid, target, cwd)
        print(f"Spawned {sid}")
    else:
        print("Usage: tq run <prompt or queue.yaml> [--cwd DIR]")
        sys.exit(1)


def run_queue(db, filepath, default_cwd):
    """Parse a YAML queue file and spawn sessions."""
    with open(filepath) as f:
        content = f.read()
    lines = content.split("\n")

    # Extract top-level keys
    cwd = default_cwd
    queue_name = os.path.splitext(os.path.basename(filepath))[0]
    sequential = False
    reset_mode = None

    for line in lines:
        m = re.match(r'^cwd:\s*(.+)', line)
        if m:
            cwd = os.path.expanduser(m.group(1).strip().strip('"').strip("'"))
        m = re.match(r'^sequential:\s*(true|yes)', line, re.IGNORECASE)
        if m:
            sequential = True
        m = re.match(r'^reset:\s*(\S+)', line)
        if m:
            reset_mode = m.group(1).strip()

    # Parse tasks
    tasks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match task list items
        m = re.match(r'^\s+-\s+(?:prompt:\s*)?(.+)', line)
        if m:
            val = m.group(1).strip()
            # Block scalar
            if val in ("|", ">"):
                joiner = "\n" if val == "|" else " "
                block_lines = []
                i += 1
                while i < len(lines) and (lines[i].startswith("    ") or lines[i].strip() == ""):
                    block_lines.append(lines[i].strip())
                    i += 1
                val = joiner.join(block_lines).strip()
                tasks.append(val)
                continue
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if val and val.lower() not in ("name:", ""):
                tasks.append(val)
        i += 1

    if not tasks:
        print("No tasks found in queue file.")
        return

    # Handle reset
    if reset_mode == "always":
        for t in tasks:
            sid = session.make_id(t)
            s = store.get_session(db, sid)
            if s:
                db.execute("DELETE FROM sessions WHERE id=?", (sid,))
                db.commit()

    spawned = 0
    for prompt_text in tasks:
        sid = session.make_id(prompt_text)
        existing = store.get_session(db, sid)
        if existing and existing["status"] in ("running", "done"):
            continue

        if not existing:
            store.create_session(db, sid, prompt=prompt_text, cwd=cwd, queue=queue_name)
        session.spawn(db, sid, prompt_text, cwd)
        spawned += 1
        print(f"  Spawned {sid}: {prompt_text[:50]}")

        if sequential:
            break  # on-stop hook will re-invoke for next task

    if spawned == 0:
        print("All tasks already done or running.")


def cmd_reply(args):
    """Send a reply from a Claude session back to Telegram."""
    db = store.connect()
    sid = args.session_id
    text = args.text

    s = store.get_session(db, sid)
    if not s:
        print(f"Unknown session: {sid}")
        sys.exit(1)

    # Load config for telegram
    daemon.load_config()

    # Find the latest incoming message for this session to thread against
    row = db.execute(
        "SELECT telegram_msg_id FROM messages WHERE session_id=? AND direction='in' ORDER BY id DESC LIMIT 1",
        (sid,),
    ).fetchone()
    reply_to = row["telegram_msg_id"] if row else None

    sent_id = telegram.send_plain(text, reply_to=reply_to)
    if sent_id:
        store.track_message(db, sent_id, sid, "out", text)
        print(f"Sent (msg_id={sent_id})")
    else:
        print("Failed to send", file=sys.stderr)
        sys.exit(1)


def cmd_mark_done(args):
    """Internal: called by on-stop.sh hook."""
    db = store.connect()
    store.mark_done(db, args.id)


def cmd_setup(args):
    """Interactive setup wizard."""
    print("tq setup — configure Telegram bot\n")
    token = input("Bot token (from @BotFather): ").strip()
    if not token:
        print("Aborted.")
        return

    print("\nSend any message to your bot, then press Enter...")
    input()

    # Fetch the chat_id from recent updates
    telegram.configure(token, "0")
    updates = telegram.get_updates(timeout=5)
    chat_id = None
    for u in updates:
        msg = u.get("message", {})
        if msg.get("chat", {}).get("id"):
            chat_id = str(msg["chat"]["id"])
            break

    if not chat_id:
        chat_id = input("Could not auto-detect. Enter chat_id manually: ").strip()

    if not chat_id:
        print("Aborted.")
        return

    cfg = {
        "telegram_bot_token": token,
        "chat_id": chat_id,
        "default_cwd": os.path.expanduser("~"),
    }

    os.makedirs(os.path.dirname(daemon.CONFIG_PATH), exist_ok=True)
    with open(daemon.CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"\nConfig written to {daemon.CONFIG_PATH}")

    # Send test message
    telegram.configure(token, chat_id)
    telegram.send_plain("tq v2 connected.")
    print("Test message sent. Run 'tq daemon start' to begin.")


def main():
    session.TQ_BIN = os.path.abspath(sys.argv[0])

    parser = argparse.ArgumentParser(prog="tq", description="Claude Code sessions via Telegram + tmux")
    sub = parser.add_subparsers(dest="command")

    # daemon
    p = sub.add_parser("daemon")
    p.add_argument("action", choices=["start", "stop", "status"])
    p.add_argument("--foreground", "-f", action="store_true")

    # status
    sub.add_parser("status")

    # stop
    p = sub.add_parser("stop")
    p.add_argument("id")

    # run
    p = sub.add_parser("run")
    p.add_argument("target", nargs="?")
    p.add_argument("--cwd", default=None)

    # reply (used by /tq-reply slash command)
    p = sub.add_parser("reply")
    p.add_argument("session_id")
    p.add_argument("text")

    # _mark-done (internal, called by on-stop hook)
    p = sub.add_parser("_mark-done")
    p.add_argument("id")

    # setup
    sub.add_parser("setup")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {
        "daemon": cmd_daemon,
        "status": cmd_status,
        "stop": cmd_stop,
        "run": cmd_run,
        "reply": cmd_reply,
        "_mark-done": cmd_mark_done,
        "setup": cmd_setup,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
