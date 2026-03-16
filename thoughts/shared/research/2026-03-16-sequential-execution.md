---
date: 2026-03-16T12:00:00-05:00
researcher: Claude Code
git_commit: 5d25d3f1e3cfc9029f1b3420f4f47ae84653aa0e
branch: main
repository: tq
topic: "How tq launches tasks and what would need to change for sequential execution"
tags: [research, codebase, queue-mode, task-spawning, on-stop-hook, sequential-execution]
status: complete
last_updated: 2026-03-16
last_updated_by: Claude Code
---

# Research: Sequential Execution Architecture in tq

**Date**: 2026-03-16T12:00:00-05:00
**Researcher**: Claude Code
**Git Commit**: 5d25d3f1e3cfc9029f1b3420f4f47ae84653aa0e
**Branch**: main
**Repository**: tq

## Research Question

tq currently launches all tasks in a queue simultaneously into separate tmux windows. There is no sequential/chained execution mode — every task starts at the same time regardless of order in the YAML. Document how the current parallel execution works end-to-end, identifying every component involved in task lifecycle (parsing, spawning, completion signaling, notification) to map out what a `sequential: true` queue-level option would need to interact with.

## Summary

tq's queue mode is a fire-and-forget pipeline: a YAML file is parsed by embedded Python into one JSON line per task, then a bash `while read` loop iterates through all tasks in a single pass, spawning each as an independent tmux session with no waiting between spawns. Task completion is signaled asynchronously via a Claude Code `Stop` hook (`on-stop.sh`) that marks the state file `status=done` — but nothing currently listens for that signal or uses it to trigger the next task. The system has three distinct state locations, a well-defined completion mechanism, and an existing queue-level option pattern (`reset:`) that demonstrates how top-level YAML keys flow through the parser to the bash spawning loop.

## Detailed Findings

### 1. The YAML Parser (Embedded Python, `scripts/tq:134-415`)

The parser runs as a heredoc temp file (`/tmp/tq-parse-XXXXXX.py`). It:

- Reads top-level keys via `^key:\s*(.+)$` regex — currently `cwd` (@scripts/tq:154-159) and `reset` (@scripts/tq:162-167). Each scans all lines, takes the first match, and breaks.
- Parses the `tasks:` array with a stateful `while i < len(lines)` loop (@scripts/tq:206-267) that tracks `current_name` across iterations and handles three prompt forms: inline, block-literal (`|`), and block-folded (`>`).
- Emits one JSON line per task: `{"hash": "<8-char>", "first_line": "<truncated>", "name": "<yaml-name>", "reset": "<mode>"}` (@scripts/tq:413).
- Each task is collected as a 4-tuple `(prompt, cwd, name, reset_mode)` (@scripts/tq:266).
- The `schedule:` key is **not** parsed here — it belongs to `tq-cron-sync`.

**Adding a new top-level key** (like `sequential`) requires three changes in the Python parser:
1. A new scan loop after line 167 to extract the value
2. Adding the value to the task tuple/passing it through
3. Including it in the JSON output at line 413

### 2. The Spawning Loop (Bash, `scripts/tq:440-528`)

The `while IFS= read -r JSON_LINE` loop processes tasks from the parser output. For each task:

**State machine (3 branches):**
1. **`status=done`** (@scripts/tq:451-478): Skip the task. Exception: if `reset_mode` specifies a TTL (e.g., `daily`, `weekly`), check `completed=` timestamp and delete state file if TTL expired, allowing re-spawn.
2. **`status=running`** (@scripts/tq:480-491): Check `tmux has-session -t "$SESSION"`. If alive → skip. If dead → mark done via `sed -i '' 's/^status=running/status=done/'` and skip.
3. **No state file** (@scripts/tq:494-527): Spawn a new tmux session.

**Spawn sequence:**
```
tmux start-server
tmux new-session -d -s "$SESSION"                              # create session
WIN_IDX=$(tmux new-window -P -F '#{window_index}' -t "$SESSION" -n "$WINDOW")  # add window
tmux send-keys -t "$SESSION:$WIN_IDX" "python3 '$LAUNCHER'" Enter              # launch Claude
(sleep 10 && tmux send-keys -t "$SESSION:$WIN_IDX" "" Enter) &                 # nudge newline
```

**Critical observation**: All spawns happen in one pass with zero waiting. The loop iterates through every JSON line and spawns every pending task before exiting. There is no mechanism to pause the loop or wait for a task to complete before processing the next one.

The `(sleep 10 && tmux send-keys ...)` background subshell sends an empty newline 10 seconds after launch as a "nudge" — likely to work around a timing issue with Claude's initial prompt handling.

### 3. The On-Stop Hook (`scripts/tq:304-354`)

The Python parser generates a per-task `on-stop.sh` script at `~/.tq/sessions/<hash>/hooks/on-stop.sh`. When Claude finishes (the Stop event fires):

1. **Mark done**: `sed -i '' 's/^status=running/status=done/' "$STATE_FILE"` and `echo "completed=$(date +%s)" >> "$STATE_FILE"` (@scripts/tq:316-317)
2. **Exception for `on-complete` reset**: Skips the mark-done step; instead deletes the state file entirely after notifications (@scripts/tq:312-314, 349-351)
3. **Optional `--notify` action**: macOS notification, bell, or custom script (@scripts/tq:320-336)
4. **`tq-message` call**: Always emitted; runs synchronously; exits silently if unconfigured (@scripts/tq:337-347)

The hook is registered in `~/.tq/sessions/<hash>/settings.json` (@scripts/tq:287-302):
```json
{
  "hooks": {
    "Stop": [{ "hooks": [{ "type": "command", "command": "<path-to-on-stop.sh>" }] }]
  }
}
```

Claude receives this via `--settings settings_file` in the launcher.

**Key insight for sequential execution**: The stop hook runs synchronously. After `tq-message` completes (line 347), any additional commands appended to the hook would execute reliably, with the task already marked `done`.

### 4. The State File Format

State files live at `<queue-dir>/.tq/<queue-basename>/<hash>` (no extension). Contents:
```
status=running
session=tq-fix-the-login-451234
window=fix-the
prompt=fix the login bug
started=2026-03-16T12:00:00
```

After completion (via stop hook or status reaper):
```
status=done
...
completed=1710590400
```

### 5. The Status Reaper (`scripts/tq:60-123`)

`tq --status <queue.yaml>` prints a status table and reaps dead sessions. For each `status=running` task, it calls `tmux has-session` — if the session is gone, it marks the task `done` and appends `completed=`. It also checks if all tasks are done and fires `tq-message --queue` for queue-level completion notification (guarded by `.queue-notified` sentinel).

### 6. The `tq-message` Notification System

`tq-message` accepts `--task`, `--queue`, `--session`, `--state-file`, `--reply-to`, and `--message`. Config resolution: global `~/.tq/config/message.yaml` → queue file `message:` block → env vars. Four content types: `summary` (requires live tmux session, polls up to 90s for Claude to write a handshake file), `status`, `details`, `log`. Delivers via Telegram `sendMessage` API with optional `reply_to_message_id`.

### 7. Conversation Mode Comparison (`scripts/tq-converse`)

Conversation mode is also entirely parallel — the orchestrator makes AI-driven routing decisions and dispatches to independent child sessions. Messages are injected via `load-buffer` + `paste-buffer` with no blocking. Session completion is detected via a Stop hook that calls `tq-converse update-status <slug> stopped`. There is no sequential chaining in conversation mode either.

### 8. Existing Queue-Level Option Pattern: `reset:`

The `reset:` key demonstrates how queue-level options flow through the system:

1. **Parser**: Scanned with regex at top of file → stored in variable → passed through task tuple → included in JSON output
2. **Bash loop**: Extracted from JSON → used in state machine logic (TTL expiry check)
3. **Stop hook**: `RESET_MODE` is hardcoded into the generated script at generation time → controls whether task is marked done or deleted

This is the exact pattern a `sequential:` key would follow.

### 9. Three State Locations

| Location | Path | Purpose |
|----------|------|---------|
| Task state | `<queue-dir>/.tq/<queue-basename>/<hash>` | Status, session, prompt, started, completed |
| Claude session | `~/.tq/sessions/<hash>/` | settings.json, hooks/on-stop.sh |
| Queue sentinel | `<queue-dir>/.tq/<queue-basename>/.queue-notified` | One-shot completion flag |

### 10. Task Identity

`hashlib.sha256(prompt.encode()).hexdigest()[:8]` — the 8-char hex digest of the prompt text. This is stable across runs: same prompt → same hash → same state file. Changing the prompt creates a new identity (old state is orphaned).

## Code References

- @scripts/tq:134-415 — Embedded Python YAML parser + launcher/hook generator
- @scripts/tq:154-159 — `cwd` extraction regex
- @scripts/tq:162-167 — `reset` extraction regex
- @scripts/tq:206-267 — Task parsing loop
- @scripts/tq:269-413 — Per-task artifact generation (prompt file, settings.json, on-stop.sh, launcher)
- @scripts/tq:304-354 — On-stop.sh generation (the completion signal)
- @scripts/tq:440-528 — Spawning loop (the parallel execution point)
- @scripts/tq:449-492 — State machine (done/running/absent)
- @scripts/tq:517-527 — tmux session creation + launch
- @scripts/tq:60-123 — Status mode / dead session reaper
- @scripts/tq-cron-sync:31-54 — Schedule key parsing (separate from main parser)
- @scripts/tq-message — Notification system
- @scripts/tq-converse — Conversation mode (parallel comparison)

## Architecture Documentation

**Current execution model**: Parse-all-then-spawn-all. The Python parser runs to completion first, emitting all JSON lines, then the bash loop consumes them all in one pass. There is no interleaving of parsing and spawning.

**Completion signaling**: Claude Code's `Stop` hook → `on-stop.sh` → `sed` state file → `tq-message`. This is the only path for a task to signal completion. The `--status` mode is a passive reaper, not an active listener.

**Idempotency**: Running `tq <queue.yaml>` multiple times is safe — tasks that are `done` or `running` (with live sessions) are skipped. Only tasks with no state file or expired TTL are spawned.

**Queue completion**: Detected by `--status` mode when `TOTAL_TASKS == DONE_TASKS` and `.queue-notified` doesn't exist. This is polled (typically via cron every 30 min), not event-driven.

## Findings Files

Full agent findings are preserved in the findings directory for deeper reference:
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/analyzer-stop-hook.md — On-stop.sh generation, state marking, reset modes
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/pattern-finder-queue-files.md — Real-world queue files and format documentation
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/analyzer-spawning-loop.md — Task spawning loop, state machine, tmux session creation
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/analyzer-yaml-parser.md — YAML parser structure, key extraction, output format
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/analyzer-converse-comparison.md — Conversation mode execution model comparison
- @thoughts/shared/research/findings/2026-03-16-sequential-execution/analyzer-tq-message.md — Notification system, content types, Telegram delivery

## Open Questions

1. **Task ordering**: The Python parser emits tasks in YAML order, and the bash loop processes them in that order — but is this guaranteed? (The `while read` over piped output preserves line order, so yes.)
2. **Chrome singleton**: The launcher opens Chrome with `--profile-directory=Profile 5` before each task. In sequential mode, only one Claude session would need Chrome at a time, but the previous session's Chrome window would still be open.
3. **OAuth token freshness**: Tokens are captured once at parse time and embedded in all launchers. For long-running sequential queues, the token captured at the start might expire before the last task spawns.
4. **`tq-message --queue` interaction**: Queue completion notification currently fires from `--status` mode when all tasks are done. Sequential execution adds a question: should the queue completion notification fire only after the last sequential task, or is the existing `--status` mechanism sufficient?
