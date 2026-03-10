# Task Reset TTL

## Overview

Add a `reset:` top-level key to queue YAML files so tasks automatically become eligible to re-run after a configurable interval. This enables recurring cron queues without manual `rm -rf` of state.

## Current State Analysis

- `status=done` is permanent — once written to `<state-dir>/<hash>`, it is never cleared by tq itself
- The only reset mechanism is manual deletion of state files
- `on-stop.sh` currently writes `status=done` unconditionally on every Stop hook
- `--status` mode flips dead sessions to `done` but also never clears state
- No timestamp is recorded when a task completes

## Desired End State

```yaml
# Queue runs every weekday at 9am; tasks reset after 12h (auto-inferred)
reset: 12h
cwd: /Users/kk/Sites/myproject
tasks:
  - prompt: check the CI dashboard for failures
  - prompt: summarize open PRs
```

- `reset: Nh` / `reset: Nd` — TTL-based: dispatch loop clears state if `now - completed > TTL`
- `reset: on-complete` — stop hook deletes state file after task finishes, so next cron tick re-spawns it immediately
- No `reset:` key → current behavior unchanged (permanent done, no regression)
- `/schedule` and `/todo` commands auto-write `reset: Nh` based on cron interval × 0.5

### Verification:
- `bash scripts/tq <queue-with-reset-24h.yaml>` — task spawns, completes, next run after 12h spawns again
- `bash scripts/tq <queue-with-reset-on-complete.yaml>` — task spawns; after stop hook fires, state file is gone; next tq run re-spawns
- `bash scripts/tq <queue-without-reset.yaml>` — identical to today; `done` is permanent
- `shellcheck scripts/tq` — passes

## What We're NOT Doing

- Per-task `reset:` — top-level only; all tasks in a queue share one reset policy
- Error detection in the stop hook — `on-complete` treats all stops as success for now; distinguishing success from error requires exit-code tracking and is deferred
- `reset: auto` as a stored YAML value — `/schedule`/`/todo` compute and write the explicit duration; `auto` is never stored in the YAML

---

## Phase 1: Parse `reset:` + Add `completed` Timestamp

### Changes Required:

#### 1. Parse `reset:` top-level key in Python parser
**File**: `scripts/tq`
**Location**: After the `cwd` extraction loop (around line 153)

```python
    # Extract top-level reset policy
    reset_mode = ''
    for line in lines:
        m = re.match(r'^reset:\s*(.+)$', line)
        if m:
            reset_mode = m.group(1).strip().strip('"\'')
            break
```

#### 2. Include `reset_mode` in per-task JSON output
**File**: `scripts/tq`
**Location**: The `print(json.dumps(...))` line at the bottom of the task loop

```python
    print(json.dumps({'hash': h, 'first_line': first_line, 'name': name, 'reset': reset_mode}))
```

#### 3. Write `completed=<epoch>` in `on-stop.sh` when marking done
**File**: `scripts/tq`
**Location**: The stop_script generation block (around line 264)

After the existing `sed -i ''` line that sets `status=done`, append:
```python
    stop_script += "  echo \"completed=$(date +%s)\" >> \"$STATE_FILE\"\n"
```

So the relevant portion becomes:
```bash
if [[ -f "$STATE_FILE" ]]; then
  sed -i '' 's/^status=running/status=done/' "$STATE_FILE"
  echo "completed=$(date +%s)" >> "$STATE_FILE"
fi
```

#### 4. Write `completed` timestamp when `--status` flips dead sessions
**File**: `scripts/tq`
**Location**: Lines 96-97, the `sed -i ''` inside the `--status` loop

```bash
        sed -i '' 's/^status=running/status=done/' "$STATE_FILE"
        echo "completed=$(date +%s)" >> "$STATE_FILE"
```

#### 5. Extract `RESET_MODE` in bash dispatch loop
**File**: `scripts/tq`
**Location**: Lines 388-390, alongside HASH / FIRST_LINE / TASK_NAME_FIELD extractions

```bash
  RESET_MODE="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('reset', ''))" "$JSON_LINE")"
```

### Success Criteria:

#### Automated Verification:
- [x] `shellcheck scripts/tq` — no errors
- [ ] Create a test queue with `reset: 24h`, run it to completion, check that the state file contains `completed=<epoch>`
- [ ] Verify `--status` dead-session flip also writes `completed=`

---

## Phase 2: TTL-Based Reset in Dispatch Loop

When a task is `done` and `RESET_MODE` is a duration (not blank, not `on-complete`), check if enough time has passed since `completed`. If yes, delete the state file and fall through to spawn logic.

### Changes Required:

#### 1. Add TTL check after the `status=done` early-exit
**File**: `scripts/tq`
**Location**: Lines 396-400, the `if [[ "$STATUS" == "done" ]]` block

Replace:
```bash
    if [[ "$STATUS" == "done" ]]; then
      echo "  [done]    $FIRST_LINE"
      continue
    fi
```

With:
```bash
    if [[ "$STATUS" == "done" ]]; then
      if [[ -n "$RESET_MODE" && "$RESET_MODE" != "on-complete" ]]; then
        COMPLETED="$(grep '^completed=' "$STATE_FILE" | cut -d= -f2)"
        NOW="$(date +%s)"
        TTL_SECONDS="$(python3 -c "
import sys
s = sys.argv[1]
if s.endswith('h'):
    print(int(s[:-1]) * 3600)
elif s.endswith('d'):
    print(int(s[:-1]) * 86400)
elif s.endswith('m'):
    print(int(s[:-1]) * 60)
else:
    print(0)
" "$RESET_MODE")"
        if [[ -n "$COMPLETED" && "$TTL_SECONDS" -gt 0 && $(( NOW - COMPLETED )) -gt "$TTL_SECONDS" ]]; then
          rm -f "$STATE_FILE"
          echo "  [reset]   $FIRST_LINE (TTL expired)"
          # Fall through to spawn logic below
        else
          echo "  [done]    $FIRST_LINE"
          continue
        fi
      else
        echo "  [done]    $FIRST_LINE"
        continue
      fi
    fi
```

### Success Criteria:

#### Automated Verification:
- [x] `shellcheck scripts/tq` — no errors
- [ ] Manually set `completed=<epoch 25 hours ago>` in a state file with `reset: 24h`; run `bash scripts/tq <queue>` → task shows `[reset]` and re-spawns
- [ ] Same state file with `completed=<epoch 1 hour ago>` → shows `[done]`, no re-spawn

---

## Phase 3: `on-complete` Mode in Stop Hook

When `reset: on-complete`, the stop hook deletes the state file after running tq-message, instead of marking it done. Next cron invocation sees no state file → re-spawns.

### Changes Required:

#### 1. Pass reset_mode into on-stop.sh generation
**File**: `scripts/tq`
**Location**: The `stop_script` generation block (around line 264)

At the top of stop_script, after the STATE_FILE assignment:
```python
    stop_script += 'RESET_MODE=' + json.dumps(reset_mode) + '\n'
```

#### 2. Conditional delete vs mark-done logic
**File**: `scripts/tq`
**Location**: The existing `if [[ -f "$STATE_FILE" ]]; then ... fi` block in stop_script

Replace the current unconditional mark-done block with:
```python
    stop_script += 'if [[ -f "$STATE_FILE" ]]; then\n'
    stop_script += '  if [[ "$RESET_MODE" == "on-complete" ]]; then\n'
    stop_script += '    # on-complete: tq-message runs first, then state is cleared for re-run\n'
    stop_script += '    : # state deletion happens after tq-message below\n'
    stop_script += '  else\n'
    stop_script += "    sed -i '' 's/^status=running/status=done/' \"$STATE_FILE\"\n"
    stop_script += '    echo "completed=$(date +%s)" >> "$STATE_FILE"\n'
    stop_script += '  fi\n'
    stop_script += 'fi\n'
```

#### 3. Delete state file after tq-message for `on-complete`
**File**: `scripts/tq`
**Location**: After the `tq-message` block in stop_script

```python
    stop_script += '# on-complete: delete state file so next tq run re-spawns this task\n'
    stop_script += 'if [[ "$RESET_MODE" == "on-complete" && -f "$STATE_FILE" ]]; then\n'
    stop_script += '  rm -f "$STATE_FILE"\n'
    stop_script += 'fi\n'
```

### Success Criteria:

#### Automated Verification:
- [x] `shellcheck scripts/tq` — no errors
- [ ] Create a queue with `reset: on-complete`; spawn a task; manually invoke the generated `on-stop.sh`; confirm state file is deleted
- [ ] `on-stop.sh` for a queue without `reset:` still writes `status=done` (no regression)

---

## Phase 4: Auto-Infer `reset:` in `/schedule` and `/todo`

When a cron schedule is written to crontab, compute `reset:` as 50% of the minimum interval between cron firings and write it into the queue YAML.

### Changes Required:

#### 1. Update `/schedule` command
**File**: `.claude/commands/schedule.md`

After step 2 (validate queue file), add:

**Step 2b — Compute reset TTL**:

> Given the cron expression, determine the minimum interval between consecutive runs (in hours), then set `reset_hours = floor(interval_hours * 0.5)`. Write `reset: <N>h` into the queue YAML as a top-level key (before `cwd:`).
>
> Inference rules:
> - `*/N` in the hour field → interval = N hours → TTL = floor(N * 0.5)h
> - List in hour field (e.g. `8,12,18`) → min gap = minimum consecutive diff → TTL = floor(min_gap * 0.5)h
> - Single hour value with daily/weekday schedule → interval = 24h → TTL = 12h
> - Single hour value with weekly schedule (single day-of-week) → interval = 168h → TTL = 84h (3.5d, round to `3d`)
> - Always minimum 1h TTL regardless of computed value
>
> Read the queue file first, update or insert the `reset:` line at the top (before `cwd:`).

#### 2. Update `/todo` command
**File**: `.claude/commands/todo.md`

In Step 5 (schedule handling), after writing the cron lines:

> Also compute and write `reset: <N>h` into the queue YAML using the same TTL inference rules as `/schedule`. Insert or update the `reset:` line at the top of the queue file (before `cwd:`).

### Success Criteria:

#### Manual Verification:
- [x] Run `/schedule run morning queue every weekday at 9am` → queue YAML gets `reset: 12h`
- [x] Run `/todo check CI every 4 hours` → queue YAML gets `reset: 2h`
- [x] Run `/todo fix login bug` (no schedule) → no `reset:` added to queue YAML
- [x] Existing queue with manual `reset: on-complete` is not overwritten by `/schedule`

---

## Testing Strategy

### Test Fixtures

```yaml
# tests/fixtures/reset-ttl.yaml
reset: 1h
cwd: /tmp
tasks:
  - prompt: "echo ttl reset task"
```

```yaml
# tests/fixtures/reset-on-complete.yaml
reset: on-complete
cwd: /tmp
tasks:
  - prompt: "echo on-complete reset task"
```

```yaml
# tests/fixtures/no-reset.yaml
cwd: /tmp
tasks:
  - prompt: "echo no reset task"
```

### Manual Testing Steps

1. TTL expiry: run `reset-ttl.yaml`, mark task done with `completed=$(date -v -2H +%s)` (2 hours ago), re-run → `[reset]`
2. TTL not expired: same but `completed=$(date -v -30M +%s)` (30 min ago), re-run → `[done]`
3. `on-complete`: run `reset-on-complete.yaml`, manually invoke the `on-stop.sh` for that hash, verify state file is gone
4. No reset: run `no-reset.yaml`, mark done, re-run → `[done]` always

## References

- State machine: `scripts/tq:394-412`
- on-stop.sh generation: `scripts/tq:264-301`
- `--status` dead-session flip: `scripts/tq:94-99`
- Queue format docs: `.claude/rules/queue-format.md`
