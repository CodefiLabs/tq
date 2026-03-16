# Sequential Queue Execution Implementation Plan

## Overview

Add a `sequential: true` queue-level option to tq that spawns tasks one at a time, waiting for each task's Claude session to complete (via its on-stop hook) before spawning the next. This enables use cases where tasks depend on the output of previous tasks (e.g., hill-climbing loops, multi-step pipelines).

## Current State Analysis

tq's queue mode is fire-and-forget: the embedded Python parser emits one JSON line per task, then a bash `while read` loop spawns every pending task in a single pass with no waiting. Task completion is signaled asynchronously via Claude's `Stop` hook (`on-stop.sh`) that marks the state file `status=done`, but nothing currently uses that signal to trigger a next task.

### Key Discoveries:
- The `reset:` key demonstrates the exact pattern for flowing a queue-level option through the system: regex scan → variable → JSON output → bash extraction → stop hook behavior (@scripts/tq:162-167)
- The stop hook already has `TQ_QUEUE_FILE` embedded at generation time (@scripts/tq:341), so re-invoking `tq` from the hook requires no new plumbing
- The spawning loop's idempotency logic already skips `done` and `running` tasks (@scripts/tq:449-491), so re-invoking `tq <queue.yaml>` after a task completes will naturally spawn exactly the next pending task
- Task order is preserved: Python parser emits tasks in YAML order, bash `while read` preserves line order

## Desired End State

A queue file with `sequential: true` runs tasks one at a time in YAML order:

```yaml
sequential: true
cwd: /Users/kk/Sites/myproject
tasks:
  - name: step-1
    prompt: "Analyze the codebase and write findings to docs/analysis.md"
  - name: step-2
    prompt: "Read docs/analysis.md and implement the top 3 recommendations"
  - name: step-3
    prompt: "Run the test suite and fix any failures from the previous changes"
```

Running `tq queue.yaml` spawns only `step-1`. When step-1's Claude session finishes, its on-stop hook re-invokes `tq queue.yaml`, which skips step-1 (done) and spawns step-2. When step-2 finishes, the same mechanism spawns step-3. After step-3 finishes, re-invocation finds no pending tasks and exits.

### Verification:
1. Create a 3-task sequential queue where each task writes to a file and the next task reads it
2. Run `tq <queue.yaml>` — only the first task should spawn
3. Wait for it to complete — the second task should auto-spawn
4. `tq --status <queue.yaml>` should show correct status throughout
5. Verify `reset: daily` + `sequential: true` works (resets all state, then chains from task 1)
6. Verify `reset: on-complete` + `sequential: true` errors at parse time

## What We're NOT Doing

- **Per-task sequential control** (e.g., `sequential: [1,2]` to chain only some tasks) — all-or-nothing for now
- **Failure handling / retry logic** — if a task dies without its stop hook firing, the chain breaks until the next cron run of `tq`, which is acceptable
- **Cross-queue dependencies** — tasks can only depend on prior tasks within the same queue file
- **OAuth token refresh** — tokens are captured once at parse time; long chains may hit expiry, but this is a pre-existing limitation
- **Chrome window cleanup** — previous task's Chrome window stays open; same as current behavior

## Implementation Approach

Re-invoke tq from the on-stop hook. This reuses the existing idempotency state machine instead of building a new chaining mechanism. Three code changes + docs update.

---

## Phase 1: YAML Parser — Extract `sequential:` Key

### Overview
Add `sequential:` extraction to the embedded Python parser, validate it against `reset: on-complete`, and include it in the JSON output so the bash loop and on-stop hook can use it.

### Changes Required:

#### 1. Extract `sequential:` key (after `reset:` extraction)
**File**: `scripts/tq`
**Location**: After the `reset_mode` extraction block (after line 167), add a parallel block for `sequential`:

```python
    # Extract top-level sequential flag
    sequential = False
    for line in lines:
        m = re.match(r'^sequential:\s*(.+)$', line)
        if m:
            val = m.group(1).strip().strip('"\'').lower()
            sequential = val in ('true', 'yes', '1')
            break
```

#### 2. Validate incompatible options
**File**: `scripts/tq`
**Location**: After extracting both `reset_mode` and `sequential` (before the reset-clearing logic at line 175):

```python
    # Validate: sequential + on-complete creates an infinite loop
    if sequential and reset_mode == 'on-complete':
        print("Error: sequential: true is incompatible with reset: on-complete", file=sys.stderr)
        print("  on-complete deletes task state, causing sequential to re-run the same task forever", file=sys.stderr)
        sys.exit(1)
```

#### 3. Pass `sequential` through the JSON output
**File**: `scripts/tq`
**Location**: Line 413, add `sequential` to the JSON dict:

```python
    print(json.dumps({'hash': h, 'first_line': first_line, 'name': name, 'reset': reset_mode, 'sequential': sequential}))
```

Note: `sequential` is queue-level (same for all tasks), but passing it per-task in JSON follows the established `reset` pattern and ensures each task's on-stop hook can access the value.

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq` passes (no new warnings)
- [ ] A queue file with `sequential: true` + `reset: on-complete` prints an error and exits non-zero
- [ ] A queue file with `sequential: true` parses successfully and emits JSON with `"sequential": true`
- [ ] A queue file without `sequential:` emits JSON with `"sequential": false`
- [ ] Existing queue files (no `sequential` key) still parse correctly with no behavior change

#### Manual Verification:
- [ ] Run the parser on a test YAML with `sequential: true` and inspect the JSON output

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding.

---

## Phase 2: Bash Spawning Loop — Break After First Spawn

### Overview
When `sequential` is true, the spawning loop should stop after spawning the first pending task instead of continuing through all tasks.

### Changes Required:

#### 1. Extract `SEQUENTIAL` from JSON in the spawning loop
**File**: `scripts/tq`
**Location**: After the existing JSON field extractions (after line 444), add:

```bash
  SEQUENTIAL="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('sequential', False))" "$JSON_LINE")"
```

#### 2. Break after first spawn in sequential mode
**File**: `scripts/tq`
**Location**: After the `echo "  [spawned] ..."` line (line 527), add:

```bash
  # Sequential mode: only spawn one task per invocation
  if [[ "$SEQUENTIAL" == "True" ]]; then
    echo "  [sequential] waiting for completion before next task"
    break
  fi
```

This `break` exits the `while read` loop. The on-stop hook (Phase 3) will re-invoke `tq` to spawn the next task.

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq` passes
- [ ] Running `tq` on a 3-task sequential queue spawns exactly 1 tmux session (verify with `tmux list-sessions | grep tq-`)
- [ ] Running `tq` on a 3-task non-sequential queue still spawns all 3 sessions
- [ ] Running `tq` on a sequential queue where task 1 is already `done` spawns task 2 (idempotency still works)
- [ ] Running `tq` on a sequential queue where all tasks are `done` spawns nothing

#### Manual Verification:
- [ ] Observe `[sequential] waiting for completion before next task` in tq output after the first spawn

**Implementation Note**: After completing this phase, pause for manual verification before proceeding.

---

## Phase 3: On-Stop Hook — Re-Invoke tq for Next Task

### Overview
When a task completes in sequential mode, the on-stop hook should re-invoke `tq <queue.yaml>` to spawn the next pending task. This is the mechanism that chains tasks together.

### Changes Required:

#### 1. Pass `sequential` flag into the generated on-stop.sh
**File**: `scripts/tq`
**Location**: In the on-stop.sh generation block (after the `RESET_MODE` line at ~line 310), add:

```python
    stop_script += 'SEQUENTIAL=' + json.dumps(sequential) + '\n'
```

#### 2. Append sequential re-invocation at the end of the stop hook
**File**: `scripts/tq`
**Location**: After the `on-complete` deletion block (after line 351, before the `with open(stop_hook)` write), append:

```python
    # Sequential mode: re-invoke tq to spawn the next task
    if sequential:
        stop_script += '\n# Sequential mode: spawn next task in queue\n'
        stop_script += 'if [[ -n "$TQ_QUEUE_FILE" ]] && command -v tq &>/dev/null; then\n'
        stop_script += '  tq "$TQ_QUEUE_FILE" &\n'
        stop_script += 'fi\n'
```

Key details:
- **Guarded by `$TQ_QUEUE_FILE`**: In `--prompt` mode, `TQ_QUEUE_FILE` is empty, so this is a no-op (correct — single prompts don't chain)
- **Guarded by `command -v tq`**: Defensive check in case tq binary isn't in PATH
- **Backgrounded with `&`**: The stop hook returns immediately; `tq` runs asynchronously to spawn the next task. This prevents any timeout issues with Claude's hook execution.
- **Placed after `on-complete` deletion**: Although we validate against `on-complete` + `sequential` at parse time, belt-and-suspenders ordering means this code would never run in that case anyway.

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq` passes
- [ ] Inspect a generated `on-stop.sh` for a sequential task — should contain the `tq "$TQ_QUEUE_FILE" &` block
- [ ] Inspect a generated `on-stop.sh` for a non-sequential task — should NOT contain the sequential block
- [ ] The generated `on-stop.sh` is executable (`-rwxr-xr-x`)

#### Manual Verification:
- [ ] Create a 3-task sequential queue where task 1 writes `echo step1 > /tmp/tq-seq-test.txt`, task 2 appends `echo step2 >> /tmp/tq-seq-test.txt`, task 3 appends `echo step3 >> /tmp/tq-seq-test.txt`
- [ ] Run `tq <queue.yaml>` — only task 1 spawns
- [ ] Wait for task 1 to finish — task 2 auto-spawns within seconds
- [ ] Wait for task 2 to finish — task 3 auto-spawns
- [ ] After task 3 finishes, verify `/tmp/tq-seq-test.txt` contains all 3 lines in order
- [ ] Run `tq --status <queue.yaml>` — all 3 tasks show `done`
- [ ] Test crash recovery: kill a tmux session mid-task, then run `tq <queue.yaml>` manually — it should mark the dead task done and spawn the next one

**Implementation Note**: After completing this phase, pause for the full end-to-end manual test before proceeding to docs.

---

## Phase 4: Documentation

### Overview
Update all documentation to describe the new `sequential:` option.

### Changes Required:

#### 1. Queue Format Rules
**File**: `.claude/rules/queue-format.md`

Add `sequential` to the "Optional Top-Level Keys" section:
```markdown
- `sequential` — when `true`, tasks run one at a time in order; each waits for the previous to complete (boolean, default `false`)
```

Add a new section after "Reset Modes":
```markdown
## Sequential Execution

Add `sequential: true` to run tasks one at a time in YAML order. Each task waits for
the previous task's Claude session to complete before spawning.

```yaml
sequential: true
cwd: /Users/kk/Sites/myproject
tasks:
  - name: analyze
    prompt: "Analyze the codebase and write findings to docs/analysis.md"
  - name: implement
    prompt: "Read docs/analysis.md and implement the top 3 recommendations"
  - name: test
    prompt: "Run the test suite and fix any failures"
```

**How it works**: `tq` spawns only the first pending task. When that task's Claude session
finishes, its on-stop hook re-invokes `tq`, which skips completed tasks and spawns the next
pending one. This continues until all tasks are done.

**Crash recovery**: If a task's tmux session dies without the stop hook firing (e.g., OOM kill),
the chain breaks. The next scheduled `tq` run (or manual `tq <queue.yaml>`) detects the dead
session, marks it done, and spawns the next task.

**Compatible with `reset:`**: `reset: daily` + `sequential: true` resets all task state at the
start of the day, then runs tasks sequentially from the beginning.

**Incompatible with `reset: on-complete`**: This combination is rejected at parse time because
`on-complete` deletes task state on completion, which would cause sequential to re-run the
same task indefinitely.
```

Add `sequential` to the "Do Not" section:
```markdown
- Do not combine `sequential: true` with `reset: on-complete` — tq will error at parse time
```

#### 2. CLAUDE.md Project Overview
**File**: `CLAUDE.md`

In the "Queue File Format" reference within Architecture section, no changes needed — the rules file is the canonical reference. But add a note to the Development Commands section with a sequential example if desired.

#### 3. Skill Definition
**File**: `skills/tq/SKILL.md`

If the skill definition lists supported queue-level keys, add `sequential` to the list.

### Success Criteria:

#### Automated Verification:
- [ ] No broken markdown links in updated docs
- [ ] `sequential` appears in queue-format.md

#### Manual Verification:
- [ ] Documentation reads clearly and covers the key behaviors (chaining mechanism, crash recovery, reset compatibility)

---

## Testing Strategy

### Manual Testing Steps:
1. **Happy path**: 3-task sequential queue, each writes to a shared file — verify ordered output
2. **Idempotency**: Re-run `tq` on a partially-complete sequential queue — verify it resumes from the right task
3. **Crash recovery**: Kill a tmux session mid-task, then run `tq` — verify chain resumes
4. **Compatibility**: `reset: daily` + `sequential: true` — verify daily reset clears state and chain restarts
5. **Incompatibility**: `reset: on-complete` + `sequential: true` — verify error at parse time
6. **Non-regression**: Run an existing parallel queue file — verify all tasks still spawn simultaneously
7. **Status mode**: `tq --status` on a sequential queue — verify correct status reporting
8. **`--prompt` mode**: `tq --prompt "test"` — verify no sequential behavior (single task)

### Test Queue File:
```yaml
# ~/.tq/queues/test-sequential.yaml
sequential: true
cwd: /tmp
tasks:
  - name: step-1
    prompt: "Write 'step 1 done' to /tmp/tq-seq-test.txt"
  - name: step-2
    prompt: "Append 'step 2 done' to /tmp/tq-seq-test.txt"
  - name: step-3
    prompt: "Append 'step 3 done' to /tmp/tq-seq-test.txt"
```

## Performance Considerations

- Sequential mode adds one `tq` re-invocation per task completion (parse + state check). This is sub-second overhead.
- The backgrounded `tq` call in the stop hook means the spawning happens asynchronously — Claude's shutdown is not blocked.
- Long sequential chains may encounter OAuth token expiry (tokens are captured once at parse time). This is a pre-existing limitation, not introduced by this change.

## References

- Research document: `thoughts/shared/research/2026-03-16-sequential-execution.md`
- Research findings: `thoughts/shared/research/findings/2026-03-16-sequential-execution/`
- Queue format rules: `.claude/rules/queue-format.md`
- Anti-patterns: `.claude/rules/anti-patterns.md`
- Security rules: `.claude/rules/security.md`
