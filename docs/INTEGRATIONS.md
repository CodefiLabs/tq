# Integrations

## claude CLI

- **What**: The Anthropic Claude Code CLI — the worker process for every task
- **How invoked**: Via `os.execvp` in the generated `<hash>.launch.py` launcher
- **Flags**: `--settings <settings.json>` (per-task hook config), `--dangerously-skip-permissions` (required for headless), `--chrome <prompt>` (Chrome extension bridge mode)
- **Requirement**: Must be on PATH. Install via `npm install -g @anthropic-ai/claude-code` or equivalent
- **Failure mode**: If `claude` is not on PATH, `os.execvp` raises `FileNotFoundError` and the tmux window shows an error. The state file remains `status=running` until `tq --status` detects the dead session

## tmux

- **What**: Terminal multiplexer — one named session per Claude task
- **How used**:
  - `tq` calls `tmux start-server`, `tmux new-session -d -s <session>`, `tmux new-window`, `tmux send-keys`
  - `tq` (in both run and `--status` modes) calls `tmux has-session -t <session>` for liveness checks
- **Session naming**: `tq-<first-3-words-slug>-<last-6-digits-of-epoch>` — e.g., `tq-fix-the-login-451234`
- **Requirement**: Must be installed. Install via `brew install tmux`
- **Failure mode**: `tq` will fail immediately if tmux is not on PATH (caught by `set -euo pipefail`). The `tmux start-server` call will error out

## macOS Keychain (`security` CLI)

- **What**: macOS system utility for reading stored credentials
- **Command**: `security find-generic-password -s 'Claude Code-credentials' -a $USER -w`
- **Returns**: JSON string containing `claudeAiOauth.accessToken`
- **Purpose**: Capture the live Claude OAuth token at queue-run time and bake it into each task's launcher script
- **macOS only**: This is not available on Linux. The fallback is `CLAUDE_CODE_OAUTH_KEY` or `ANTHROPIC_API_KEY` environment variables
- **Failure mode**: If keychain read fails (returns non-zero), Python catches `Exception` silently and falls back to env vars. If neither keychain nor env vars provide a token, Claude will fail to authenticate

## Google Chrome

- **What**: Browser used for the Claude Chrome extension bridge
- **How invoked**: `subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])` in the launcher
- **Profile**: Profile 5 (`halbotkirchner@gmail.com`) — hardcoded, not configurable
- **Timing**: Launched 2 seconds before `claude --chrome <prompt>` executes (launcher calls `time.sleep(2)`)
- **Purpose**: The `--chrome` flag connects Claude to an already-running Chrome extension instance
- **Failure mode**: If Chrome is not installed or Profile 5 does not exist, Claude may fail to connect to the extension. The task still runs but without Chrome integration

## crontab

- **What**: Unix job scheduler for periodic queue execution
- **Pattern**:
  ```cron
  # Run queue at 9am daily
  0 9 * * * /opt/homebrew/bin/tq ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1
  # Sweep dead sessions every 30 min
  */30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1
  ```
- **Log**: Output is appended to `~/.tq/logs/tq.log` (created by `tq-install.sh`)
- **Note**: Cron has a minimal PATH — `tq` exports `/opt/homebrew/bin:/usr/local/bin` at startup to ensure tmux, python3, and claude are found

## Claude Stop Hook

- **What**: A callback mechanism built into the Claude CLI that fires when a Claude session exits
- **Registration**: Per-session `settings.json` at `~/.tq/sessions/<hash>/settings.json`:
  ```json
  {
    "hooks": {
      "Stop": [{ "hooks": [{ "type": "command", "command": "/path/to/on-stop.sh" }] }]
    }
  }
  ```
- **Script**: `~/.tq/sessions/<hash>/hooks/on-stop.sh` — runs `sed -i '' 's/^status=running/status=done/' <state-file>`
- **Purpose**: The only automated write path from `claude` back to `tq`'s task state
- **Failure mode**: If the hook is not registered correctly, tasks stay `status=running` forever. `tq --status` provides a fallback by detecting dead tmux sessions

## Failure Mode Summary

| Dependency | Missing | Effect |
|------------|---------|--------|
| tmux | not installed | `tq` exits with error on `tmux start-server` |
| claude | not on PATH | Launcher `execvp` fails; tmux window shows error; state stays `running` |
| python3 | not on PATH | `tq` fails at `python3 "$PARSE_SCRIPT"` |
| macOS keychain | read fails | Silently falls back to env vars; fails if neither source has token |
| Chrome / Profile 5 | missing | Claude `--chrome` may fail to connect; task still runs without browser |
| Stop hook | not fired | Tasks stay `running`; `tq --status` reaps them on next run |
