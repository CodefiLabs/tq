# Dependency Map

This is a pure Bash + Python project with no package manager. Dependencies are runtime
binaries and data-flow contracts between scripts and state files.

## Runtime Dependency Graph

```
tq-install.sh
  └── runtime deps: bash, ln, mkdir
  └── output: symlinks in /opt/homebrew/bin or $TQ_INSTALL_DIR

scripts/tq
  ├── reads:   <queue-yaml> (user-authored, never mutated)
  ├── reads:   macOS keychain via `security find-generic-password -s 'Claude Code-credentials'`
  ├── reads:   CLAUDE_CODE_OAUTH_KEY, ANTHROPIC_API_KEY (env var fallback)
  ├── writes:  <queue-dir>/.tq/<basename>/<hash>          (state file)
  ├── writes:  <queue-dir>/.tq/<basename>/<hash>.prompt   (prompt text)
  ├── writes:  <queue-dir>/.tq/<basename>/<hash>.launch.py (launcher with baked-in token)
  ├── writes:  ~/.tq/sessions/<hash>/settings.json         (Claude hook config)
  ├── writes:  ~/.tq/sessions/<hash>/hooks/on-stop.sh      (Stop hook script)
  ├── invokes: python3 (embedded parser via temp file)
  └── invokes: tmux (new-session, send-keys, has-session, start-server)

scripts/tq-status
  ├── reads:   <queue-yaml> (for path derivation only)
  ├── reads:   <queue-dir>/.tq/<basename>/<hash>          (state files)
  ├── reads:   <queue-dir>/.tq/<basename>/<hash>.prompt   (for display)
  ├── writes:  <queue-dir>/.tq/<basename>/<hash>          (flips running→done for dead sessions)
  └── invokes: tmux has-session (liveness check)

skills/tq/SKILL.md
  └── consumed by: Claude model (agent) only
  └── references:  tq and tq-status CLI names (must be on PATH after install)

~/.tq/sessions/<hash>/hooks/on-stop.sh
  ├── invoked by: claude CLI Stop hook mechanism
  └── writes:     <queue-dir>/.tq/<basename>/<hash> (status=running → status=done)
```

## State Contract

The state file at `<queue-dir>/.tq/<basename>/<hash>` (no extension) is a newline-separated
key=value store. All three scripts and the Stop hook read/write it:

```
status=running        # running | done  (pending = file absent)
session=tq-fix-the-login-451234
window=fix-the
prompt=fix the login bug in auth service
started=2026-03-05T10:00:00
```

**Writers**: `tq` (initial write, dead-session flip), `tq-status` (dead-session flip), `on-stop.sh` (running→done)
**Readers**: `tq` (idempotency check), `tq-status` (display), `on-stop.sh` (conditional write)

The `<hash>.prompt` file contains the full raw prompt text. The `status` file's `prompt=` line
holds only the first line (truncated). `tq-status` prefers the `.prompt` file for display.

## Hash Link Between State Locations

The same 8-char SHA-256 hash links state in two locations:

```
sha256(prompt_text)[:8]
    ├──► <queue-dir>/.tq/<basename>/<hash>         task state
    ├──► <queue-dir>/.tq/<basename>/<hash>.prompt  prompt text
    ├──► <queue-dir>/.tq/<basename>/<hash>.launch.py launcher
    └──► ~/.tq/sessions/<hash>/                    Claude settings + hook
```

Changing the hashing algorithm breaks this link for all existing tasks.

## External Dependency Versions

| Dependency | Required | Notes |
|------------|----------|-------|
| bash | 3.2+ | macOS default |
| python3 | 3.x (stdlib only) | Must be on PATH |
| tmux | any | Must be running; `tmux start-server` called before use |
| claude CLI | any | Must be on PATH; installed via npm or direct download |
| security (macOS) | macOS 10.x+ | Part of macOS; not available on Linux |
| reattach-to-user-namespace | optional | Homebrew; fixes keychain access in tmux |
| Google Chrome | any | Must be installed; Profile 5 must exist |

## The Stop Hook as the Only Return Channel

`on-stop.sh` is the **only** write path from `claude` back to `tq`'s state. It is:
1. Generated at queue-run time by the Python parser
2. Registered in `~/.tq/sessions/<hash>/settings.json` as a `Stop` hook
3. Called by `claude` automatically when the session exits
4. Its sole action: `sed -i '' 's/^status=running/status=done/' "$STATE_FILE"`

If this hook is not registered, tasks never auto-complete. `tq-status` provides a fallback
by detecting dead tmux sessions and flipping state manually.
