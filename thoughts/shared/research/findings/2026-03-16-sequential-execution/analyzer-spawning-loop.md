# Task Spawning Loop — `scripts/tq` lines 440-528

## Overview

After the Python parser runs and its JSON output is captured in `$PARSE_OUTPUT` (line 425), the Bash loop at lines 440-528 processes every task in a single uninterrupted pass. There is no `wait`, `sleep`, or synchronization between tasks — spawning is fire-and-forget.

---

## 1. The `while IFS= read -r JSON_LINE` loop (lines 440-528)

`PARSE_OUTPUT` is a newline-delimited stream of JSON objects, one per task. The loop is fed via a here-string (`<<< "$PARSE_OUTPUT"`, line 528). For each line the loop extracts four fields with inline `python3 -c` one-liners:

- `HASH` — the 8-char SHA-256 digest that is the stable task identity (line 441)
- `FIRST_LINE` — the first line of the prompt, used for display and as a fallback for session naming (line 442)
- `TASK_NAME_FIELD` — the optional `name:` YAML key; empty string if absent (line 443)
- `RESET_MODE` — the per-task reset TTL string (e.g. `1h`, `7d`); empty string if absent (line 444)

`STATE_FILE` and `LAUNCHER` paths are derived from `$STATE_DIR/$HASH` and `$STATE_DIR/$HASH.launch.py` respectively (lines 445-446). `STATE_DIR` is the queue-scoped state directory established earlier in the script.

---

## 2. State machine

The state check begins at line 449.

### Case A — state file exists, `status=done` (lines 451-478)

When `STATUS == "done"` the loop checks whether a TTL-based reset applies:

- If `RESET_MODE` is non-empty and is not the literal string `on-complete` (line 452), the TTL path runs (lines 453-474):
  1. `COMPLETED` is read from the `completed=` field in the state file (line 453).
  2. `NOW` is captured via `date +%s` (line 454).
  3. A `python3 -c` inline call converts the `RESET_MODE` string to seconds: `h` suffix → multiply by 3600, `d` → 86400, `m` → 60, anything else → 0 (lines 455-466).
  4. If `COMPLETED` is set, `TTL_SECONDS > 0`, and the elapsed time exceeds the TTL, the state file is deleted and the loop falls through to the spawn logic with a `[reset]` log line (lines 467-470).
  5. Otherwise (TTL not yet expired, or no `completed=` field) the task is logged as `[done]` and skipped with `continue` (lines 471-473).
- If `RESET_MODE` is empty or equals `on-complete`, the task is unconditionally logged `[done]` and skipped (lines 475-478).

### Case B — state file exists, `status=running` (lines 480-491)

`SESSION` is read from the `session=` field (line 481). `tmux has-session -t "$SESSION"` is tested (line 482):

- If the session is alive → log `[running]`, `continue` (lines 483-484).
- If the session is gone (command exits non-zero) → the state file is patched in-place with `sed -i '' 's/^status=running/status=done/'` (line 487), logged as `[done] (session ended)`, and skipped with `continue` (lines 488-489).

### Case C — no state file (falls through to spawn logic, lines 494-527)

Any task that reaches line 494 has no state file, or had its state file deleted by the TTL reset path.

---

## 3. tmux session creation (lines 521-525)

Spawn happens in four steps:

1. `tmux start-server` (line 521) — ensures the tmux server is running; a no-op if it already is.
2. `tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION"` (line 522) — creates a detached session only if one with that name does not already exist.
3. `WIN_IDX=$(tmux new-window -P -F '#{window_index}' -t "$SESSION" -n "$WINDOW")` (line 523) — adds a new window to the session, capturing its numeric index into `WIN_IDX`.
4. `tmux send-keys -t "$SESSION:$WIN_IDX" "python3 '$LAUNCHER'" Enter` (line 524) — types the launcher invocation into the new window and presses Enter. This runs inside the user's default shell (zsh with `.zshrc` sourced), which is why the session is started without an explicit command — the shell provides keychain and OAuth access.

`send-keys` (not `respawn-pane` or a direct command) is used deliberately so the shell environment is inherited.

---

## 4. Single-pass, no waiting

The loop iterates every task and issues all spawns in sequence without any `wait` or synchronization. Each `tmux new-session` / `new-window` / `send-keys` trio takes milliseconds. All Claude sessions start nearly simultaneously. The Bash process does not block on any session completing.

---

## 5. The `(sleep 10 && tmux send-keys ... "" Enter) &` background process (line 525)

```bash
(sleep 10 && tmux send-keys -t "$SESSION:$WIN_IDX" "" Enter) &
```

A subshell is forked into the background. After 10 seconds it sends an empty string followed by Enter to the newly-created window. This sends a bare newline into the Claude CLI after it has had time to initialize. The intent is to nudge the process if it is waiting for input — acting as a soft kick to start execution in cases where the CLI does not auto-start after receiving the prompt via `os.execvp`.

The `&` detaches it completely; the main loop continues to the next task without waiting.

---

## 6. Session and window naming (lines 495-503)

`EPOCH_SUFFIX` is the last 6 digits of the current Unix epoch (line 495), providing uniqueness within a second.

**When `TASK_NAME_FIELD` is non-empty (lines 496-499):**
- `SESSION_BASE` — `TASK_NAME_FIELD` lowercased, non-alphanumeric characters replaced with `-`, leading/trailing dashes stripped, truncated to 20 characters.
- `WINDOW` — same transformation on `TASK_NAME_FIELD`, truncated to 15 characters.

**When `TASK_NAME_FIELD` is empty (lines 499-502):**
- `SESSION_BASE` — first three whitespace-delimited words of `FIRST_LINE`, same slug transformation, truncated to 20 characters.
- `WINDOW` — first two words of `FIRST_LINE`, same transformation, truncated to 15 characters.

`SESSION` is always assembled as `tq-<SESSION_BASE>-<EPOCH_SUFFIX>` (line 503).

---

## 7. State file write (lines 505-512)

Immediately before spawning, a state file is written at `$STATE_FILE`:

```
status=running
session=<SESSION>
window=<WINDOW>
prompt=<FIRST_LINE>
started=<UTC ISO-8601 timestamp>
```

This file is what the state machine reads on subsequent runs. The `on-stop.sh` hook (generated earlier by the Python parser) will overwrite `status=running` with `status=done` and set `completed=<epoch>` when Claude exits.

---

## 8. Queue-notified sentinel cleared on spawn (line 515)

```bash
rm -f "$STATE_DIR/.queue-notified"
```

This line executes for every task that reaches the spawn path. The `.queue-notified` sentinel file prevents duplicate completion notifications from firing when `tq --status` runs and all tasks are already done. Deleting it on any new spawn ensures the notification will fire again after the newly-spawned task(s) complete.
