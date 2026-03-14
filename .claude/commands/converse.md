---
name: converse
description: Manage Telegram conversation sessions
tags: tq, telegram, conversation, orchestrator, sessions
allowed-tools: Bash(tq-converse), Bash(which), Bash(tmux), Bash(test)
argument-hint: "[start|stop|status|list|spawn <slug>]"
---

Arguments: $ARGUMENTS

Manage Telegram conversation sessions via `tq-converse`.

## 1. Verify binary

```bash
which tq-converse
```
If missing, stop: "Run `/install` to set up tq binaries."

## 2. Parse and dispatch

| `$ARGUMENTS` | Command | Purpose |
|--------------|---------|---------|
| (none) or `start` | `tq-converse start` | Launch orchestrator |
| `stop` | `tq-converse stop` | Stop orchestrator |
| `stop <slug>` | `tq-converse stop <slug>` | Stop one session |
| `status` | `tq-converse status` | Show all session statuses |
| `list` | `tq-converse list` | List active slugs |
| `spawn <slug> [opts]` | `tq-converse spawn <slug> [--cwd <dir>] [--desc <desc>]` | Create child session |

If `$ARGUMENTS` doesn't match any subcommand, show the table above and stop.

## 3. Edge cases

- `start` when orchestrator already running: report "Orchestrator already active" and show status instead
- `stop <slug>` when slug not found: report "No session `<slug>` found" and list active sessions
- `spawn` without a slug: stop with "Usage: `/converse spawn <slug> [--cwd <dir>] [--desc <desc>]`"
- Telegram not configured (`~/.tq/config/message.yaml` missing): warn "Telegram not configured — run `/setup-telegram` first" but proceed (conversation mode works without Telegram for local-only use)

## 4. Execute

Run the matched command. If exit code is non-zero, report the error output and stop.

## 5. Verify (for start/spawn)

After `start`: confirm orchestrator tmux session exists:
```bash
tmux has-session -t tq-orchestrator 2>/dev/null && echo "Orchestrator running" || echo "FAILED to start"
```

After `spawn`: confirm child session:
```bash
tmux has-session -t "tq-conv-<slug>" 2>/dev/null && echo "Session active" || echo "FAILED to spawn"
```

## 6. Display output

Show a summary table:

| Item | Value |
|------|-------|
| Action | `start` / `stop` / `status` / `list` / `spawn` |
| Result | success or error message |
| Session | tmux session name (if applicable) |
| Active sessions | count (for `status` / `list`) |

Related: `/setup-telegram` for bot setup, `/tq-reply` for session replies, `/health` for diagnostics.
