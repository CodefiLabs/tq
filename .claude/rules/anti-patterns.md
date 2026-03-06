# Anti-Patterns

## sed Syntax: Use macOS BSD, Not GNU

```bash
# CORRECT — macOS BSD sed
sed -i '' 's/^status=running/status=done/' "$STATE_FILE"

# WRONG — GNU sed (Linux); creates backup files or errors on macOS
sed -i 's/^status=running/status=done/' "$STATE_FILE"
```

This trips up AI assistants constantly. The empty string `''` after `-i` is required on macOS.
All three scripts use this pattern — do not "fix" it to the GNU form.

## Strict Mode: Always `set -euo pipefail`

```bash
# CORRECT
set -euo pipefail

# WRONG — incomplete; unbound variables and pipe failures go undetected
set -e
```

Every script in this codebase uses `set -euo pipefail`. Never weaken this.

## Temp File Cleanup: Always Use `trap`

```bash
# CORRECT
PARSE_SCRIPT=$(mktemp /tmp/tq-parse-XXXXXX.py)
trap 'rm -f "$PARSE_SCRIPT"' EXIT

# WRONG — leaks temp files on script error or exit
PARSE_SCRIPT=$(mktemp /tmp/tq-parse-XXXXXX.py)
# ... use it ...
rm -f "$PARSE_SCRIPT"   # only runs on success
```

## Shebang: Use env

```bash
#!/usr/bin/env bash   # CORRECT — portable

#!/bin/bash           # WRONG — hardcodes path; fails if bash is at different location
```

**Note**: This also applies to scripts generated via heredoc at runtime. Any `cat > file.sh << 'EOF'` block that writes a shell script must use `#!/usr/bin/env bash` in the heredoc body.

## Embedded Python: Use Heredoc Temp File, Not `python3 -c`

```bash
# CORRECT — established pattern in scripts/tq
PARSE_SCRIPT=$(mktemp /tmp/tq-parse-XXXXXX.py)
trap 'rm -f "$PARSE_SCRIPT"' EXIT
cat > "$PARSE_SCRIPT" <<'PYEOF'
# ... multi-line Python ...
PYEOF
python3 "$PARSE_SCRIPT" arg1 arg2

# WRONG — does not scale; bash 3.2 quote-scanning bug with heredoc inside $()
PARSE_OUTPUT=$(python3 -c "
import sys
# ... multi-line ...
")
```

The `python3 -c "..."` idiom is acceptable ONLY for single-expression JSON field extraction:
```bash
HASH="$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['hash'])" "$JSON_LINE")"
```

## Process Replacement: Use `os.execvp`, Not `subprocess.run`

```python
# CORRECT — replaces the Python process with claude; no zombie processes
os.execvp('claude', ['claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])

# WRONG — creates a subprocess; the Python wrapper stays alive
subprocess.run(['claude', '--settings', settings_file, ...])
```

The `os.execvp()` call in generated `.launch.py` files is intentional. Do not change it.

## State Directories: Do Not Confuse the Two

| What | Path | Purpose |
|------|------|---------|
| Task state | `<queue-dir>/.tq/<queue-basename>/<hash>` | status, session name, started timestamp |
| Claude session | `~/.tq/sessions/<hash>/settings.json` | Claude hook config for this task |

They share the same `<hash>` but live in completely different locations. Mixing them up
causes tq to fail silently or write to the wrong location.

## Hash Stability: Do Not Change the Hashing Logic

```python
h = hashlib.sha256(prompt.encode()).hexdigest()[:8]
```

This is the stable task identity. Changing the algorithm, encoding, or slice length orphans
all existing state files — tq will re-run every task that was already `done`.
