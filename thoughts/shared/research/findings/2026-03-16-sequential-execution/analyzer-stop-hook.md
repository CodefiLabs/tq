# Stop Hook Mechanism — tq

**Source file**: `/Users/kk/Sites/codefi/tq/scripts/tq`

---

## 1. How on-stop.sh Is Generated (lines 304–354)

The stop hook is generated entirely inside the embedded Python block (lines 134–415) that runs as a temp file. For each parsed task, the Python code constructs the stop hook as a string (`stop_script`) and writes it to disk.

**Key paths computed (lines 279–283):**
- `session_dir  = ~/.tq/sessions/<hash>/`
- `hooks_dir    = ~/.tq/sessions/<hash>/hooks/`
- `stop_hook    = ~/.tq/sessions/<hash>/hooks/on-stop.sh`
- `state_file   = <queue-dir>/.tq/<queue-basename>/<hash>`

The `hooks_dir` is created with `os.makedirs(hooks_dir, exist_ok=True)` at line 284.

The stop script string is assembled at lines 306–351 and written at line 352–353. Permissions are set at line 354: `stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH` (owner rwx, group rx, other rx).

The `state_file` path and `reset_mode` value are baked into the stop script as hardcoded shell variable assignments using `json.dumps()` to safely quote the paths:

```python
stop_script += 'STATE_FILE=' + json.dumps(state_file) + '\n'
stop_script += 'RESET_MODE=' + json.dumps(reset_mode) + '\n'
```

This means the stop hook is entirely self-contained — it carries its own knowledge of where the state file lives.

---

## 2. What the Stop Hook Does When Claude Finishes (lines 311–351)

The generated `on-stop.sh` has the following structure:

```
#!/usr/bin/env bash
set -euo pipefail
STATE_FILE="<absolute-path-to-hash-state-file>"
RESET_MODE="<on-complete|daily|weekly|hourly|always|empty>"

if [[ -f "$STATE_FILE" ]]; then
  if [[ "$RESET_MODE" == "on-complete" ]]; then
    : # do nothing here; state deletion happens after tq-message
  else
    sed -i '' 's/^status=running/status=done/' "$STATE_FILE"
    echo "completed=$(date +%s)" >> "$STATE_FILE"
  fi
fi

# [optional --notify block if TQ_NOTIFY was set]

# tq-message notification
export TQ_HASH="<hash>"
export TQ_QUEUE_FILE="<queue-file-path-or-empty>"
if command -v tq-message &>/dev/null; then
  SESSION="$(grep '^session=' "$STATE_FILE" | cut -d= -f2)"
  tq-message --task "$TQ_HASH" --queue "$TQ_QUEUE_FILE" --state-file "$STATE_FILE" --session "$SESSION"
fi

# on-complete: delete state file so next tq run re-spawns this task
if [[ "$RESET_MODE" == "on-complete" && -f "$STATE_FILE" ]]; then
  rm -f "$STATE_FILE"
fi
```

### Marking status=done (lines 315–317)

For all reset modes except `on-complete`, the stop hook:
1. Rewrites `status=running` to `status=done` in the state file using BSD `sed -i ''`
2. Appends `completed=<epoch-seconds>` to the state file

### Handling reset_mode="on-complete" (lines 312–314, 348–351)

When `RESET_MODE` is `on-complete`:
- The `sed` and `completed=` lines are **skipped** (the `else` branch is not taken)
- `tq-message` is still called while the state file still exists (so it can read `session=` from it)
- After `tq-message` completes, `rm -f "$STATE_FILE"` deletes the state file entirely
- Result: next time `tq` runs, no state file exists for this task, so it is treated as new and re-spawned

### tq-message Notification (lines 337–347)

`tq-message` is always invoked if the binary is on `PATH`. The call passes:
- `--task <hash>` — the 8-char SHA-256 hash
- `--queue <queue-file>` — absolute path to the YAML queue file (empty string for `--prompt` mode)
- `--state-file <state-file>` — absolute path to the task state file
- `--session <session>` — the tmux session name read from the state file

`TQ_HASH` and `TQ_QUEUE_FILE` are exported into the environment before the call (lines 339–343).

---

## 3. How the Stop Hook Is Registered in settings.json (lines 286–302)

For each task, a `settings.json` is written to `~/.tq/sessions/<hash>/settings.json`. Its content:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<user>/.tq/sessions/<hash>/hooks/on-stop.sh"
          }
        ]
      }
    ]
  }
}
```

This is the Claude Code hooks configuration format. The `Stop` event triggers when Claude finishes a session. The `command` value is the absolute path to the generated `on-stop.sh`.

The launcher script (`<hash>.launch.py`) passes this settings file to Claude via `--settings <settings_file>` at line 385 and line 401. Claude reads the hooks from this file and executes `on-stop.sh` when it stops.

---

## 4. Relationship Between State File Path and Stop Hook Path

These are two entirely separate directory trees that share the same `<hash>` as their key:

| Artifact | Path |
|---|---|
| State file | `<queue-dir>/.tq/<queue-basename>/<hash>` |
| Stop hook | `~/.tq/sessions/<hash>/hooks/on-stop.sh` |
| Settings | `~/.tq/sessions/<hash>/settings.json` |

The state file lives next to the queue YAML file (in a `.tq/` subdirectory). The stop hook lives in the user's home directory under `~/.tq/sessions/`. The `<hash>` (`hashlib.sha256(prompt.encode()).hexdigest()[:8]`) ties them together.

The stop hook has the state file path **hardcoded into it** at generation time (line 309), so the hook can locate and modify the state file without any runtime path resolution. This is why the stop hook is self-contained.

---

## 5. --status Mode: Dead Session Detection (lines 60–123)

`--status` mode iterates over every file in `STATE_DIR` (line 76), skipping `.prompt`, `.launch.py`, and `.queue-notified` files (lines 78–80).

For each state file (lines 82–99):
1. Reads `status=`, `session=`, `started=` fields with `grep` and `cut`
2. If `status` is `running`, calls `tmux has-session -t "$SESSION"` (line 95)
3. If the tmux session **does not exist** (non-zero exit), it:
   - Rewrites `status=running` → `status=done` with BSD `sed -i ''` (line 96)
   - Appends `completed=$(date +%s)` to the state file (line 97)
   - Sets `STATUS="done"` in the local variable for display (line 98)

The same dead-session detection exists in the run-mode path (lines 480–490), where `tq` also checks `tmux has-session` and marks the session done if the tmux session no longer exists — but in run mode the `completed=` timestamp is **not** appended (line 487 only does the `sed`; contrast with status mode line 97).

After iterating all tasks, if `TOTAL_TASKS > 0` and all tasks are done and `.queue-notified` sentinel does not exist (line 115), `tq-message --queue "$QUEUE_FILE"` is called for a queue-level completion notification and the sentinel file is touched.
