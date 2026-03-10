# Auto Cron Sync Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `schedule:` key to queue YAML files so crontab entries are managed automatically by a new `tq-cron-sync` script, eliminating all manual crontab setup.

**Architecture:** A new `scripts/tq-cron-sync` Bash script (with embedded Python for YAML scanning) performs a full wipe-and-rebuild of all `# tq-managed:` crontab lines on every run, handling additions/removals/changes uniformly. The installer symlinks it and calls it once; it bootstraps itself as a `*/20 * * * *` watcher so future queue file changes are picked up automatically.

**Tech Stack:** Bash (`set -euo pipefail`, macOS BSD `sed -i ''`), embedded Python 3 (stdlib only), `crontab` CLI

**Spec:** `docs/superpowers/specs/2026-03-10-auto-cron-sync-design.md`

---

## Codebase Context

Read these files before implementing anything:
- `scripts/tq` — understand existing embedded Python patterns, ALL_CAPS bash vars, temp file handling
- `scripts/tq-install.sh` — symlink loop structure, INSTALL_DIR resolution
- `.claude/rules/anti-patterns.md` — critical: `sed -i ''`, `set -euo pipefail`, `trap`, heredoc patterns
- `.claude/rules/naming.md` — ALL_CAPS bash vars, snake_case Python vars, kebab-case script names
- `.claude/rules/queue-format.md` — current format; you'll be adding `schedule:` to it
- `CLAUDE.md` — project guardrails

---

## Chunk 1: `scripts/tq-cron-sync`

**Files:**
- Create: `scripts/tq-cron-sync`

---

- [ ] **Step 1.1: Create the script skeleton with strict mode and arg parsing**

Create `scripts/tq-cron-sync` with this exact content:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Ensure homebrew binaries are available (cron has minimal PATH)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

INTERVAL=20

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    --interval)
      if [[ $# -lt 2 ]]; then
        echo "Error: --interval requires a value" >&2; exit 1
      fi
      INTERVAL="$2"; shift; shift ;;
    *) echo "Unknown flag: $1" >&2; exit 1 ;;
  esac
done

QUEUES_DIR="${HOME}/.tq/queues"
LOGS_DIR="${HOME}/.tq/logs"
mkdir -p "$QUEUES_DIR" "$LOGS_DIR"
```

- [ ] **Step 1.2: Add embedded Python scanner via temp file**

Append to `scripts/tq-cron-sync`:

```bash
# ---------------------------------------------------------------------------
# Scan ~/.tq/queues/*.yaml for schedule: keys via embedded Python temp file
# ---------------------------------------------------------------------------
SCAN_SCRIPT=$(mktemp /tmp/tq-scan-XXXXXX.py)
CRONTAB_NEW=$(mktemp /tmp/tq-crontab-XXXXXX)
trap 'rm -f "$SCAN_SCRIPT" "$CRONTAB_NEW"' EXIT

cat > "$SCAN_SCRIPT" <<'PYEOF'
import sys, os, re, json, glob

queues_dir = sys.argv[1]
results = []

for yaml_path in sorted(glob.glob(os.path.join(queues_dir, '*.yaml'))):
    name = os.path.basename(yaml_path)[:-5]  # strip .yaml
    schedule = None
    try:
        with open(yaml_path) as f:
            for line in f:
                m = re.match(r'^schedule:\s*["\']?([^"\'#\n]+?)["\']?\s*$', line)
                if m:
                    schedule = m.group(1).strip()
                    break
    except Exception:
        pass
    if schedule:
        results.append({'name': name, 'schedule': schedule, 'path': yaml_path})

for r in results:
    print(json.dumps(r))
PYEOF
```

- [ ] **Step 1.3: Add TQ_BIN detection**

Append to `scripts/tq-cron-sync`:

```bash
# ---------------------------------------------------------------------------
# Detect installed tq binary path
# ---------------------------------------------------------------------------
if [[ -x "/opt/homebrew/bin/tq" ]]; then
  TQ_BIN="/opt/homebrew/bin/tq"
  SELF_BIN="/opt/homebrew/bin/tq-cron-sync"
elif [[ -x "/usr/local/bin/tq" ]]; then
  TQ_BIN="/usr/local/bin/tq"
  SELF_BIN="/usr/local/bin/tq-cron-sync"
else
  echo "Error: tq not found in /opt/homebrew/bin or /usr/local/bin" >&2
  exit 1
fi
```

- [ ] **Step 1.4: Add crontab wipe-and-rebuild logic**

Append to `scripts/tq-cron-sync`:

```bash
# ---------------------------------------------------------------------------
# Read existing crontab, strip all tq-managed lines into temp file
# ---------------------------------------------------------------------------
{ crontab -l 2>/dev/null || true; } | grep -v '# tq-managed:' > "$CRONTAB_NEW" || true

# ---------------------------------------------------------------------------
# Append new managed lines for each scheduled queue
# ---------------------------------------------------------------------------
while IFS= read -r JSON_LINE; do
  [[ -z "$JSON_LINE" ]] && continue
  NAME="$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['name'])" "$JSON_LINE")"
  SCHEDULE="$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['schedule'])" "$JSON_LINE")"
  YAML_PATH="$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['path'])" "$JSON_LINE")"
  echo "${SCHEDULE} ${TQ_BIN} ${YAML_PATH} >> ${LOGS_DIR}/tq.log 2>&1 # tq-managed:${NAME}:run" >> "$CRONTAB_NEW"
  echo "*/30 * * * * ${TQ_BIN} --status ${YAML_PATH} >> ${LOGS_DIR}/tq.log 2>&1 # tq-managed:${NAME}:status" >> "$CRONTAB_NEW"
done < <(python3 "$SCAN_SCRIPT" "$QUEUES_DIR")

# Self-watcher entry
echo "*/${INTERVAL} * * * * ${SELF_BIN} >> ${LOGS_DIR}/tq-cron-sync.log 2>&1 # tq-managed:tq-cron-sync" >> "$CRONTAB_NEW"

# Write merged crontab
crontab "$CRONTAB_NEW"
echo "tq-cron-sync: crontab synced ($(grep -c '# tq-managed:' "$CRONTAB_NEW" || true) managed entries)"
```

- [ ] **Step 1.5: Make the script executable**

```bash
chmod +x scripts/tq-cron-sync
```

- [ ] **Step 1.6: Manual smoke test — script runs without error**

```bash
bash scripts/tq-cron-sync --interval 20
```

Expected: prints `tq-cron-sync: crontab synced (N managed entries)` with no errors.
Then verify crontab was written:

```bash
crontab -l | grep 'tq-managed'
```

Expected: shows at least the self-watcher line:
```
*/20 * * * * /opt/homebrew/bin/tq-cron-sync >> /Users/<you>/.tq/logs/tq-cron-sync.log 2>&1 # tq-managed:tq-cron-sync
```

- [ ] **Step 1.7: Smoke test — schedule: key in a queue file is picked up**

Create a test queue file (you'll delete it after):
```bash
cat > ~/.tq/queues/test-schedule.yaml <<'EOF'
schedule: "0 8 * * *"
cwd: /tmp
tasks:
  - prompt: "test task"
EOF
```

Run sync:
```bash
bash scripts/tq-cron-sync
```

Check crontab:
```bash
crontab -l | grep 'tq-managed'
```

Expected: two new lines for `test-schedule` (run + status-check), plus the self-watcher.

- [ ] **Step 1.8: Smoke test — removing schedule: key cleans up crontab**

Remove the `schedule:` line from the test file:
```bash
cat > ~/.tq/queues/test-schedule.yaml <<'EOF'
cwd: /tmp
tasks:
  - prompt: "test task"
EOF
```

Run sync:
```bash
bash scripts/tq-cron-sync
```

Verify `test-schedule` entries are gone:
```bash
crontab -l | grep 'tq-managed'
```

Expected: only the self-watcher line. Then clean up:
```bash
rm ~/.tq/queues/test-schedule.yaml
```

- [ ] **Step 1.9: Smoke test — changing schedule: value updates crontab**

```bash
cat > ~/.tq/queues/test-schedule.yaml <<'EOF'
schedule: "0 9 * * *"
cwd: /tmp
tasks:
  - prompt: "test task"
EOF
bash scripts/tq-cron-sync
crontab -l | grep 'tq-managed:test-schedule:run'
# Should show 0 9 * * *
```

Change the schedule and re-sync:
```bash
cat > ~/.tq/queues/test-schedule.yaml <<'EOF'
schedule: "30 7 * * 1-5"
cwd: /tmp
tasks:
  - prompt: "test task"
EOF
bash scripts/tq-cron-sync
crontab -l | grep 'tq-managed:test-schedule:run'
# Should now show 30 7 * * 1-5
rm ~/.tq/queues/test-schedule.yaml
bash scripts/tq-cron-sync
```

- [ ] **Step 1.9b: Smoke test — non-tq crontab lines survive a sync**

This is the most critical correctness property: existing user-managed cron entries must never be touched.

```bash
# Add a non-tq crontab line
(crontab -l 2>/dev/null || true; echo "0 5 * * * /usr/bin/backup.sh # my personal backup") | crontab -

# Run sync
bash scripts/tq-cron-sync

# Verify the personal line is still there
crontab -l | grep 'my personal backup'
```

Expected: the personal backup line appears unchanged. Clean up:
```bash
crontab -l | grep -v 'my personal backup' | crontab - || true
```

- [ ] **Step 1.10: Commit**

```bash
git add scripts/tq-cron-sync
git commit -m "add tq-cron-sync script for automatic crontab management"
```

---

## Chunk 2: Update `scripts/tq-install.sh`

**Files:**
- Modify: `scripts/tq-install.sh`

---

- [ ] **Step 2.1: Add `tq-cron-sync` to the symlink loop**

In `scripts/tq-install.sh`, find the line:
```bash
for SCRIPT in tq tq-message tq-setup tq-telegram-poll tq-telegram-watchdog; do
```

Change it to:
```bash
for SCRIPT in tq tq-message tq-setup tq-telegram-poll tq-telegram-watchdog tq-cron-sync; do
```

- [ ] **Step 2.2: Add post-install sync call**

Find the `mkdir -p ~/.tq/queues ~/.tq/logs ~/.tq/config` line. After it, add:

```bash
# Run initial cron sync to pick up any existing queue schedules
# Use $INSTALL_DIR directly — PATH may not reflect the just-created symlink yet
"$INSTALL_DIR/tq-cron-sync" --interval 20
```

- [ ] **Step 2.3: Update the output message**

Find and replace the old manual crontab instructions block:
```bash
echo ""
echo "tq installed. Crontab example (crontab -e):"
echo ""
echo "  0 9 * * * /opt/homebrew/bin/tq ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1"
echo "  */30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/morning.yaml >> ~/.tq/logs/tq.log 2>&1"
echo ""
```

Replace with:
```bash
echo ""
echo "tq installed. Cron schedules are managed automatically."
echo ""
echo "Add a schedule: key to any queue file in ~/.tq/queues/ to auto-schedule it:"
echo ""
echo "  schedule: \"0 9 * * *\"   # runs daily at 9am"
echo "  cwd: /path/to/project"
echo "  tasks: ..."
echo ""
echo "tq-cron-sync runs every 20 minutes and syncs all queue schedules to crontab."
echo "To change the sync interval: tq-cron-sync --interval <minutes>"
echo ""
```

- [ ] **Step 2.4: Manual verification**

Run the installer in dry-run style (just check the script parses cleanly):
```bash
bash -n scripts/tq-install.sh
```

Expected: no output (no syntax errors).

- [ ] **Step 2.5: Commit**

```bash
git add scripts/tq-install.sh
git commit -m "update installer to symlink tq-cron-sync and run post-install sync"
```

---

## Chunk 3: Update Docs

**Files:**
- Modify: `.claude/rules/queue-format.md`

---

- [ ] **Step 3.1: Add `schedule:` to the top-level keys section**

In `.claude/rules/queue-format.md`, find:
```markdown
## Required Top-Level Keys

- `cwd` — working directory for all tasks (string, absolute path recommended)
- `tasks` — array of task objects
```

Replace with:
```markdown
## Required Top-Level Keys

- `cwd` — working directory for all tasks (string, absolute path recommended)
- `tasks` — array of task objects

## Optional Top-Level Keys

- `schedule` — cron expression for automatic scheduling via `tq-cron-sync` (string)
- `message` — notification config block (see Queue-Level Messaging below)
```

- [ ] **Step 3.2: Add `schedule:` section with examples**

After the `## Optional Top-Level Keys` section, add a new section before `## Queue-Level Messaging`:

```markdown
## Automatic Scheduling

Add `schedule:` with a raw cron expression to have `tq-cron-sync` manage the crontab entry automatically. No manual `crontab -e` needed.

```yaml
schedule: "0 9 * * *"
cwd: /Users/kk/Sites/myproject
tasks:
  - name: morning-review
    prompt: "Review yesterday's commits and summarize in docs/daily.md"
```

`tq-cron-sync` scans `~/.tq/queues/*.yaml` every 20 minutes and syncs crontab:
- Queues with `schedule:` get a run entry + a `*/30 * * * *` status-check entry
- Removing `schedule:` or deleting the queue file removes the crontab entries on the next sync
- Changing `schedule:` updates the crontab entry on the next sync

Use an LLM to translate natural language ("daily at 9am") to cron expressions ("0 9 * * *").
```

- [ ] **Step 3.3: Fix the "Do Not" section**

The `## Do Not` section currently says:
```markdown
- Do not add extra top-level keys — only `cwd` and `tasks` are processed
```

Update it to:
```markdown
- Do not add top-level keys other than `cwd`, `tasks`, `schedule`, and `message` — others are ignored
```

- [ ] **Step 3.4: Commit**

```bash
git add .claude/rules/queue-format.md
git commit -m "document schedule key in queue-format rules"
```

---

## Execution Note

This plan is implemented via a tq queue at `~/.tq/queues/tq-schedule-feature.yaml`. Each chunk above maps to one task in the queue, running as an independent Claude session in `/Users/kk/Sites/codefi/tq`.
