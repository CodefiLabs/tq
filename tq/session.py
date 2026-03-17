"""Session lifecycle — spawn, route, stop. tmux is the runtime."""

import hashlib
import json
import os
import subprocess
import stat
import textwrap

HOOKS_DIR = os.path.expanduser("~/.tq/hooks")
TQ_BIN = None  # set by cli.py to the resolved path of the tq entry point


def _tmux(*args):
    return subprocess.run(
        ["tmux", *args], capture_output=True, text=True
    )


def _session_exists(name):
    return _tmux("has-session", "-t", name).returncode == 0


def tmux_session_name(sid):
    return f"tq-{sid}"


def _get_oauth():
    """Read OAuth token from macOS keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-a", os.environ.get("USER", ""), "-w"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            creds = json.loads(result.stdout.strip())
            return creds.get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        pass
    return os.environ.get("CLAUDE_CODE_OAUTH_KEY") or os.environ.get("ANTHROPIC_API_KEY")


def _write_hooks(sid, cwd):
    """Generate settings.json and on-stop.sh for a session."""
    hook_dir = os.path.join(HOOKS_DIR, sid)
    os.makedirs(os.path.join(hook_dir, "hooks"), exist_ok=True)

    # on-stop.sh — marks session done
    tq_bin = TQ_BIN or "tq"
    stop_script = os.path.join(hook_dir, "hooks", "on-stop.sh")
    with open(stop_script, "w") as f:
        f.write(textwrap.dedent(f"""\
            #!/usr/bin/env bash
            set -euo pipefail
            "{tq_bin}" _mark-done "{sid}"
        """))
    os.chmod(stop_script, os.stat(stop_script).st_mode | stat.S_IEXEC)

    # settings.json — Claude Code hooks config
    settings = {
        "hooks": {
            "Stop": [{"hooks": [{"type": "command", "command": stop_script}]}]
        }
    }
    with open(os.path.join(hook_dir, "settings.json"), "w") as f:
        json.dump(settings, f, indent=2)

    return os.path.join(hook_dir, "settings.json")


def spawn(db, sid, prompt, cwd):
    """Spawn a new Claude Code session in tmux."""
    from . import store

    cwd = os.path.expanduser(cwd)
    tmux_name = tmux_session_name(sid)
    settings_path = _write_hooks(sid, cwd)
    oauth = _get_oauth()

    store.start_session(db, sid, tmux_name)

    # Create tmux session
    _tmux("new-session", "-d", "-s", tmux_name, "-x", "220", "-y", "50")

    # Set session env + OAuth
    _tmux("send-keys", "-t", tmux_name, f"export TQ_SESSION_ID='{sid}'", "Enter")
    if oauth:
        _tmux("send-keys", "-t", tmux_name,
               f"export CLAUDE_CODE_OAUTH_KEY='{oauth}'", "Enter")

    # cd to working directory
    _tmux("send-keys", "-t", tmux_name, f"cd '{cwd}'", "Enter")

    # Launch claude
    cmd = f"claude --settings '{settings_path}' --dangerously-skip-permissions"
    if prompt:
        # Escape prompt for shell
        safe_prompt = prompt.replace("'", "'\\''")
        cmd += f" --prompt '{safe_prompt}'"
    _tmux("send-keys", "-t", tmux_name, cmd, "Enter")

    return tmux_name


def route_message(sid, text):
    """Send a message to an existing session via tmux."""
    tmux_name = tmux_session_name(sid)
    if not _session_exists(tmux_name):
        return False

    # Safe injection: load-buffer + paste-buffer handles special chars
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp = f.name
    try:
        _tmux("load-buffer", tmp)
        _tmux("paste-buffer", "-t", tmux_name)
        import time; time.sleep(0.2)
        _tmux("send-keys", "-t", tmux_name, "Enter")
    finally:
        os.unlink(tmp)
    return True


def stop(sid):
    """Stop a session — send /exit, then kill if needed."""
    tmux_name = tmux_session_name(sid)
    if _session_exists(tmux_name):
        _tmux("send-keys", "-t", tmux_name, "/exit", "Enter")
        import time; time.sleep(2)
        if _session_exists(tmux_name):
            _tmux("kill-session", "-t", tmux_name)


def check_health(db):
    """Check all running sessions, mark dead ones done."""
    from . import store
    dead = []
    for s in store.running_sessions(db):
        if s["tmux_session"] and not _session_exists(s["tmux_session"]):
            store.mark_done(db, s["id"])
            dead.append(s["id"])
    return dead


def make_id(text):
    """Deterministic 8-char hash from text."""
    return hashlib.sha256(text.encode()).hexdigest()[:8]
