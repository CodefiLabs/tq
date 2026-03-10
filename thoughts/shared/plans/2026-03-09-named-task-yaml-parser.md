# Named Task YAML Parser Fix

## Overview

Fix the hand-rolled YAML parser in `scripts/tq` to correctly handle tasks with a `name:` field. Currently, any task with `name:` before `prompt:` is silently dropped because the parser only matches `  - prompt:` (2-space indent + list marker) but not `    prompt:` (4-space indent, continuation key). Also extract the `name:` value and use it for tmux session/window naming.

## Current State Analysis

The parser regex at line 164:
```python
m = re.match(r'^  - prompt:\s*(.*)', lines[i])
```

Matches only when `prompt` is the first key in a list item (`  - prompt:`). When a task starts with `name:`, the YAML looks like:
```yaml
  - name: review-auth    # 2-space + "- " → parser sees this but does nothing
    prompt: "Review..."  # 4-space indent → does NOT match regex → silently dropped
```

Session names are currently derived from `first_line` (first 80 chars of prompt text) by extracting 3 words, slugifying, and appending epoch suffix. The `name:` field from YAML is never read.

## Desired End State

```yaml
tasks:
  - name: review-auth
    prompt: "Review the authentication module"
  - prompt: "Fix the login bug"  # unnamed task still works
```

- Both tasks are parsed and spawned
- Named task gets tmux session `tq-review-auth-<epoch>`, window `review-auth`
- Unnamed task gets session derived from prompt text (unchanged behavior)
- All existing unnamed-task queue files continue to work identically

### Verification:
- `bash scripts/tq <queue-with-names.yaml>` — all tasks spawned, named sessions visible in `tmux ls`
- `bash scripts/tq <queue-without-names.yaml>` — identical behavior to today
- `shellcheck scripts/tq` — passes

## What We're NOT Doing

- Not supporting any other YAML task keys (`cwd:` per task, `env:`, etc.)
- Not supporting YAML anchors
- Not changing hash stability — hash is still `SHA-256(prompt)[:8]`
- Not changing how `--prompt` mode works (no YAML involved)

---

## Phase 1: Fix Parser + Add Name Extraction

### Changes Required:

#### 1. Track `current_name` in the scan loop
**File**: `scripts/tq`
**Location**: Line 163, just before `while i < len(lines):`
**Change**: Add `current_name = ''` initialization

```python
    tasks = []
    current_name = ''
    i = 0
    while i < len(lines):
```

#### 2. Reset `current_name` on new list item; capture `name:` key
**File**: `scripts/tq`
**Location**: Inside the `while i < len(lines):` loop, before the existing `m = re.match(...)` line

Add these lines before `m = re.match(...)`:
```python
        # Reset name at start of each new list item
        if re.match(r'^  - ', lines[i]) and not re.match(r'^  - prompt:', lines[i]):
            current_name = ''
            m_name = re.match(r'^  - name:\s*(.*)', lines[i])
            if m_name:
                current_name = m_name.group(1).strip().strip('"\'')
            i += 1
            continue
```

#### 3. Fix prompt regex to match both indent styles
**File**: `scripts/tq`
**Location**: Line 164 (the `m = re.match(r'^  - prompt:...')` line)
**Change**: Extend regex to also match 4-space indent

```python
        m = re.match(r'^(?:  - |    )prompt:\s*(.*)', lines[i])
```

#### 4. Capture name at point of task creation; reset after use
**File**: `scripts/tq`
**Location**: Line 212-214, the `prompt = prompt.strip() / if prompt: tasks.append(...)` block
**Change**: Include name in the tuple and clear `current_name`

```python
        prompt = prompt.strip()
        if prompt:
            tasks.append((prompt, cwd, current_name))
            current_name = ''
```

#### 5. Update the task iteration to unpack 3-tuple
**File**: `scripts/tq`
**Location**: Line 216, `for (prompt, cwd) in tasks:`
**Change**:

```python
for (prompt, cwd, name) in tasks:
```

#### 6. Include `name` in JSON output
**File**: `scripts/tq`
**Location**: Line 349, the `print(json.dumps(...))` line
**Change**:

```python
    print(json.dumps({'hash': h, 'first_line': first_line, 'name': name}))
```

#### 7. Extract `name` field in bash dispatch loop
**File**: `scripts/tq`
**Location**: Lines 377-378, alongside the existing `HASH` and `FIRST_LINE` extractions
**Change**: Add extraction:

```bash
  TASK_NAME_FIELD="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('name', ''))" "$JSON_LINE")"
```

#### 8. Use `name` for session/window naming when present
**File**: `scripts/tq`
**Location**: Lines 403-407 (the session/window naming block)
**Change**: Replace with conditional logic:

```bash
  # Generate session/window names: prefer YAML name field, fall back to prompt words
  EPOCH_SUFFIX="$(date +%s | tail -c 6)"
  if [[ -n "$TASK_NAME_FIELD" ]]; then
    SESSION_BASE="$(echo "$TASK_NAME_FIELD" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-20)"
    WINDOW="$(echo "$TASK_NAME_FIELD" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-15)"
  else
    SESSION_BASE="$(echo "$FIRST_LINE" | awk '{print $1" "$2" "$3}' | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-20)"
    WINDOW="$(echo "$FIRST_LINE" | awk '{print $1" "$2}' | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-15)"
  fi
  SESSION="tq-${SESSION_BASE}-${EPOCH_SUFFIX}"
```

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq` passes with no errors
- [ ] Named task queue file spawns all tasks: create `tests/fixtures/named-tasks.yaml` with 2 named + 1 unnamed task, run `bash scripts/tq tests/fixtures/named-tasks.yaml`, verify 3 `[spawned]` lines
- [ ] Named task session uses YAML name: `tmux ls | grep review-auth` shows a session
- [ ] Unnamed task session uses prompt words (unchanged): `tmux ls | grep tq-fix-the`
- [ ] Generated `.launch.py` content unchanged (name field not written to launcher)

#### Manual Verification:
- [ ] Run `tq ~/.tq/queues/morning.yaml` (existing un-named queue) — identical behavior, no regressions
- [ ] Create a test queue with `name:` tasks, confirm correct tmux session names in `tmux ls`

---

## Testing Strategy

### Test Fixture

Create `tests/fixtures/named-tasks.yaml`:
```yaml
cwd: /tmp
tasks:
  - name: review-auth
    prompt: "echo review auth task"
  - name: update-docs
    prompt: |
      echo update docs task
      echo with multiline prompt
  - prompt: "echo unnamed task no name field"
```

### Verification Commands:
```bash
# Run the fixture
bash scripts/tq tests/fixtures/named-tasks.yaml

# Verify sessions exist with correct names
tmux ls | grep 'review-auth'
tmux ls | grep 'update-docs'
tmux ls | grep 'tq-echo-unnamed'  # unnamed task → derived from prompt

# Cleanup
tmux kill-session -t "$(tmux ls | grep review-auth | cut -d: -f1)" 2>/dev/null || true
tmux kill-session -t "$(tmux ls | grep update-docs | cut -d: -f1)" 2>/dev/null || true
```

## References

- Parser regex: `scripts/tq:164`
- Task tuple / JSON output: `scripts/tq:216`, `scripts/tq:349`
- Bash dispatch loop: `scripts/tq:376-432`
- Queue format docs: `.claude/rules/queue-format.md`
- Naming conventions: `.claude/rules/naming.md`
