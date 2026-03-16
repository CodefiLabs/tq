# YAML Parser Analysis — scripts/tq (lines 134–415)

## Overview

The embedded Python YAML parser lives entirely inside a heredoc (`<<'PYEOF'`) that is written to a `mktemp` temp file at lines 131–415 of `scripts/tq`. It is invoked via `python3 "$PARSE_SCRIPT"` and uses only Python stdlib (`sys`, `os`, `hashlib`, `re`, `json`, `stat`, `subprocess`). It is **not** a general-purpose YAML parser — it is a hand-rolled regex parser purpose-built for the tq queue format.

---

## 1. Top-Level Key Parsing

### `cwd` (lines 153–159)

```python
cwd = ''
for line in lines:
    m = re.match(r'^cwd:\s*(.+)$', line)
    if m:
        cwd = m.group(1).strip().strip('"\'')
        break
```

- Pattern: `^cwd:\s*(.+)$` — anchored to start of line (no leading whitespace), so it only matches the top-level key, not an indented task-level key.
- Takes the first match and breaks. Single-pass linear scan.
- Strips surrounding quotes (single or double) after stripping whitespace.

### `reset` (lines 161–167)

```python
reset_mode = ''
for line in lines:
    m = re.match(r'^reset:\s*(.+)$', line)
    if m:
        reset_mode = m.group(1).strip().strip('"\'')
        break
```

- Pattern: `^reset:\s*(.+)$` — same structure as `cwd`.
- First match, breaks immediately.
- The extracted `reset_mode` string is then used in lines 175–200 to optionally clear the state directory before task evaluation.

### Keys NOT parsed by this script

- `schedule:` — not read here at all. It is read separately by `tq-cron-sync`, which scans queue YAML files independently.
- `message:` — not read here. It is read by `tq-message` at notification time via its own parsing.
- `tasks:` — not parsed as a key; the parser instead scans for list items by indentation/prefix.

---

## 2. Task Parsing Loop (lines 202–267)

The parser scans the full `lines` list in a `while i < len(lines)` loop, tracking a `current_name` variable across iterations.

### Phase A: Detect task list item start (line 208)

```python
if re.match(r'^  - ', lines[i]) and not re.match(r'^  - prompt:', lines[i]):
    current_name = ''
    m_name = re.match(r'^  - name:\s*(.*)', lines[i])
    if m_name:
        current_name = m_name.group(1).strip().strip('"\'')
    i += 1
    continue
```

- Matches any `  - ` list item (two-space indent + `- `).
- Resets `current_name` to `''` on each new list item.
- If the list item is `  - name:`, captures the name value.
- Skips `  - prompt:` lines here so they fall through to Phase B.

### Phase B: Detect `prompt:` key (line 216)

```python
m = re.match(r'^(?:  - |    )prompt:\s*(.*)', lines[i])
```

- Matches `prompt:` in two positions:
  - `  - prompt:` (two-space + dash + space, i.e., inline task object with prompt as first key)
  - `    prompt:` (four-space indent, i.e., prompt as a subsequent key after `name:`)
- Captures everything after `prompt:` as `inline`.

### Phase C: Block scalar handling (lines 223–253)

If `inline` is `|` or `>`:

- Scans forward, collecting lines that are indented relative to the first continuation line.
- `indent` is set from the first non-blank continuation line's leading spaces.
- Any line with `cur_indent < indent` terminates the block.
- Trailing blank lines are stripped.
- `|` (literal): lines joined with `'\n'`.
- `>` (folded): blank lines become `'\n'`, non-blank lines become space-joined. The fold logic appends `'\n'` for blank lines and the line text for non-blank lines, then calls `' '.join(out).strip()`.

### Phase D: Inline prompt handling (lines 254–262)

- If `inline` is not a block scalar indicator, it is the literal prompt text.
- Strips surrounding matching double or single quotes.

### Task tuple construction (lines 264–267)

```python
prompt = prompt.strip()
if prompt:
    tasks.append((prompt, cwd, current_name, reset_mode))
    current_name = ''
```

- Empty prompts are silently dropped.
- `current_name` is cleared after being consumed into the tuple, so it doesn't bleed into the next task.

---

## 3. Per-Task Fields Extracted

| Field | Source | Notes |
|-------|--------|-------|
| `prompt` | `prompt:` YAML key | Inline, block-literal (`\|`), or block-folded (`>`) |
| `name` | `name:` YAML key | Optional; defaults to `''` |
| `cwd` | top-level `cwd:` | Shared across all tasks; no per-task override |
| `reset_mode` | top-level `reset:` | Shared across all tasks; no per-task override |

There is no per-task `cwd` or `reset` override. Both values are captured once from the top of the file and threaded into every task tuple unchanged.

---

## 4. Task Tuple Structure

```python
tasks.append((prompt, cwd, current_name, reset_mode))
```

Positional 4-tuple: `(prompt, cwd, name, reset_mode)`.

Consumed at line 269:

```python
for (prompt, cwd, name, reset_mode) in tasks:
```

No named fields, no dict — positional only.

---

## 5. Script Invocation Modes

### `--prompt` mode (line 141–143)

```python
if len(sys.argv) > 1 and sys.argv[1] == '--prompt':
    tasks = [(sys.argv[2].strip(), sys.argv[4] if len(sys.argv) > 4 else '', '', '')]
    state_dir = sys.argv[3]
```

Arguments: `--prompt <text> <state_dir> [cwd]`

- Constructs a single-element `tasks` list directly, bypassing all YAML parsing.
- `name` and `reset_mode` are both `''`.
- Called from Bash at line 423: `python3 "$PARSE_SCRIPT" "--prompt" "$PROMPT_TEXT" "$STATE_DIR" "$TASK_CWD"`

### Queue-file mode (line 144–146)

```python
queue_file = sys.argv[1]
state_dir  = sys.argv[2]
```

Arguments: `<queue_file> <state_dir>`

- Reads the file and runs the full YAML parsing logic.
- Called from Bash at line 425: `python3 "$PARSE_SCRIPT" "$QUEUE_FILE" "$STATE_DIR"`

---

## 6. Output Format (line 413)

```python
print(json.dumps({'hash': h, 'first_line': first_line, 'name': name, 'reset': reset_mode}))
```

One JSON line per task, printed to stdout. Fields:

| Key | Value | Example |
|-----|-------|---------|
| `hash` | `sha256(prompt)[:8]` | `"a1b2c3d4"` |
| `first_line` | `prompt.split('\n')[0][:80]` | `"Review auth module"` |
| `name` | Task name or `""` | `"review-auth"` |
| `reset` | Queue reset mode or `""` | `"daily"` |

The Bash caller reads this line-by-line in a `while IFS= read -r LINE` loop (starting at line ~430) and uses `python3 -c` one-liners to extract individual fields from each JSON object.

---

## 7. `schedule:` Key — Not Parsed Here

`schedule:` does not appear anywhere in the embedded Python. It is intentionally excluded. The `tq-cron-sync` script reads queue YAML files independently using its own regex scan to extract `schedule:` values and manage crontab entries. The parser in `scripts/tq` has no awareness of scheduling.

---

## 8. Where to Add a New Top-Level Key (e.g., `sequential`)

A new top-level key would need to be added in three places:

### A. Parse it alongside `cwd` and `reset` (after line 167)

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

Pattern convention: `^<key>:\s*(.+)$`, anchored at line start, first-match-breaks, strip quotes.

### B. Thread it into the task tuple (line 266)

The tuple is currently `(prompt, cwd, current_name, reset_mode)`. Either extend to a 5-tuple:

```python
tasks.append((prompt, cwd, current_name, reset_mode, sequential))
```

Or — cleaner — switch to a dict to avoid positional fragility:

```python
tasks.append({'prompt': prompt, 'cwd': cwd, 'name': current_name, 'reset': reset_mode, 'sequential': sequential})
```

Note: the `for (prompt, cwd, name, reset_mode) in tasks:` loop at line 269 would need to be updated to match.

### C. Include it in the JSON output (line 413)

```python
print(json.dumps({'hash': h, 'first_line': first_line, 'name': name, 'reset': reset_mode, 'sequential': sequential}))
```

The Bash caller would then need to extract the new field from each JSON line and use it to control execution flow (e.g., `tmux wait-for` or a blocking `while` loop between task spawns).

---

## Key Implementation Notes

- The parser is sequential and stateful: `current_name` persists across the `while` loop iterations and is consumed when a `prompt:` is found.
- There is no `tasks:` key validation — the parser simply finds all `  - ` and `    prompt:` patterns anywhere in the file.
- YAML anchors (`&`, `*`) are not supported.
- Multi-document YAML (`---`) is not supported.
- The `cwd` and `reset_mode` values are captured once before the task loop and passed to every task unchanged — there is no mechanism for per-task overrides of either value today.
- The `on-stop.sh` hook is generated per-task at parse time, embedding the `reset_mode` value as a literal string inside the generated script (line 311: `stop_script += 'RESET_MODE=' + json.dumps(reset_mode) + '\n'`).
