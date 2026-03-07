# tq-message Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `tq-message` — a CLI + Claude slash command that sends per-task and queue-level notifications to Telegram (and future services) with AI-generated summaries via the live Claude session.

**Architecture:** `scripts/tq-message` is a standalone Bash script (same style as `tq`) that resolves three-layer config (global `~/.tq/config/message.yaml` → queue YAML `message:` block → env vars) and delivers messages via `curl`. For AI summaries, `tq-message` uses `tmux send-keys` to ask the still-live Claude session to run the `/tq-message` slash command, which generates the summary and calls back `tq-message --message "..."`. Non-summary content types (status/details/log) are formatted and sent directly. `scripts/tq` is updated to call `tq-message` from `on-stop.sh` and to detect queue completion in `--status` mode.

**Tech Stack:** Bash + embedded Python 3 stdlib (same as tq), curl (Telegram Bot API), tmux send-keys, Claude plugin slash command

**Design doc:** `docs/plans/2026-03-07-tq-message-design.md`

---

## Task 1: `scripts/tq-message` — scaffold and arg parsing

**Files:**
- Create: `scripts/tq-message`

**What to build:** The shell scaffolding — shebang, strict mode, PATH fix, arg parsing, usage error. No delivery logic yet.

**Step 1: Create the file**

```bash
#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

TASK_HASH=""
QUEUE_FILE=""
MESSAGE_TEXT=""
SESSION=""

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    --task)    TASK_HASH="${2:-}";    shift 2 ;;
    --queue)   QUEUE_FILE="${2:-}";   shift 2 ;;
    --message) MESSAGE_TEXT="${2:-}"; shift 2 ;;
    --session) SESSION="${2:-}";      shift 2 ;;
    --) shift; break ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *)  break ;;
  esac
done

if [[ -z "$TASK_HASH" && -z "$QUEUE_FILE" ]]; then
  echo "Usage: tq-message --task <hash> --queue <file.yaml> [--message <text>] [--session <name>]" >&2
  echo "       tq-message --queue <file.yaml> [--message <text>]" >&2
  exit 1
fi

if [[ -n "$QUEUE_FILE" ]]; then
  QUEUE_FILE="$(realpath "$QUEUE_FILE")"
  if [[ ! -f "$QUEUE_FILE" ]]; then
    echo "Error: queue file not found: $QUEUE_FILE" >&2
    exit 1
  fi
fi

echo "[tq-message] task=$TASK_HASH queue=$QUEUE_FILE message=${MESSAGE_TEXT:0:40}"
```

**Step 2: Make executable**

```bash
chmod +x scripts/tq-message
```

**Step 3: Smoke test**

```bash
bash scripts/tq-message --task abc123 --queue ~/.tq/queues/morning.yaml
# Expected: [tq-message] task=abc123 queue=... message=

bash scripts/tq-message
# Expected: Usage: ... (exit 1)
```

**Step 4: Commit**

```bash
git add scripts/tq-message
git commit -m "add tq-message scaffold with arg parsing"
```

---

## Task 2: Config resolution (embedded Python)

**Files:**
- Modify: `scripts/tq-message`

**What to build:** Embedded Python that reads `~/.tq/config/message.yaml` (global config), parses the `message:` block from the queue YAML, then applies env var overrides. Outputs resolved config as JSON.

**Config priority (lowest → highest):** `~/.tq/config/message.yaml` → queue YAML `message:` block → env vars

**Step 1: Add the Python config resolver after the arg parsing in `scripts/tq-message`**

Replace the `echo "[tq-message] ..."` line with:

```bash
CONFIG_SCRIPT=$(mktemp /tmp/tq-message-config-XXXXXX.py)
trap 'rm -f "$CONFIG_SCRIPT"' EXIT

cat > "$CONFIG_SCRIPT" <<'PYEOF'
import sys, os, re, json

def parse_flat_block(text, top_key):
    """Extract key: value pairs from an indented block under top_key."""
    lines = text.split('\n')
    in_block = False
    block_indent = None
    result = {}
    for line in lines:
        m = re.match(r'^' + re.escape(top_key) + r':\s*$', line)
        if m:
            in_block = True
            block_indent = None
            continue
        if in_block:
            if not line.strip():
                continue
            cur = len(line) - len(line.lstrip())
            if block_indent is None:
                block_indent = cur
            if cur < block_indent:
                break
            kv = re.match(r'^\s+(\w+):\s*(.+)$', line)
            if kv:
                result[kv.group(1)] = kv.group(2).strip().strip('"\'')
    return result

def parse_top_key(text, key):
    """Extract a single top-level key: value."""
    m = re.search(r'^' + re.escape(key) + r':\s*(.+)$', text, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else ''

# --- 1. Global config: ~/.tq/config/message.yaml ---
config = {}
global_path = os.path.expanduser('~/.tq/config/message.yaml')
if os.path.exists(global_path):
    with open(global_path) as f:
        g = f.read()
    config['service'] = parse_top_key(g, 'default_service')
    config['content'] = parse_top_key(g, 'content')
    tg = parse_flat_block(g, 'telegram')
    if tg.get('bot_token'): config['telegram_bot_token'] = tg['bot_token']
    if tg.get('chat_id'):   config['telegram_chat_id']   = tg['chat_id']
    sl = parse_flat_block(g, 'slack')
    if sl.get('webhook'):   config['slack_webhook'] = sl['webhook']

# --- 2. Queue YAML message: block ---
queue_file = sys.argv[1] if len(sys.argv) > 1 else ''
if queue_file and os.path.exists(queue_file):
    with open(queue_file) as f:
        q = f.read()
    msg = parse_flat_block(q, 'message')
    if msg.get('service'):  config['service']              = msg['service']
    if msg.get('content'):  config['content']              = msg['content']
    if msg.get('chat_id'):  config['telegram_chat_id']     = msg['chat_id']
    if msg.get('webhook'):  config['slack_webhook']        = msg['webhook']

# --- 3. Env var overrides ---
if os.environ.get('TQ_MESSAGE_SERVICE'): config['service'] = os.environ['TQ_MESSAGE_SERVICE']
if os.environ.get('TQ_MESSAGE_CONTENT'): config['content'] = os.environ['TQ_MESSAGE_CONTENT']
if os.environ.get('TQ_TELEGRAM_BOT_TOKEN'): config['telegram_bot_token'] = os.environ['TQ_TELEGRAM_BOT_TOKEN']
if os.environ.get('TQ_TELEGRAM_CHAT_ID'):   config['telegram_chat_id']   = os.environ['TQ_TELEGRAM_CHAT_ID']
if os.environ.get('TQ_SLACK_WEBHOOK'):      config['slack_webhook']       = os.environ['TQ_SLACK_WEBHOOK']

# Defaults
if not config.get('service'): config['service'] = 'telegram'
if not config.get('content'): config['content'] = 'summary'

print(json.dumps(config))
PYEOF

CONFIG_JSON="$(python3 "$CONFIG_SCRIPT" "${QUEUE_FILE:-}")"

SERVICE="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('service',''))" "$CONFIG_JSON")"
CONTENT="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('content',''))" "$CONFIG_JSON")"
TG_TOKEN="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('telegram_bot_token',''))" "$CONFIG_JSON")"
TG_CHAT="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('telegram_chat_id',''))" "$CONFIG_JSON")"

if [[ -z "$SERVICE" ]] || { [[ "$SERVICE" == "telegram" ]] && [[ -z "$TG_TOKEN" || -z "$TG_CHAT" ]]; }; then
  # No messaging configured — exit silently
  exit 0
fi

echo "[tq-message] service=$SERVICE content=$CONTENT task=$TASK_HASH"
```

**Step 2: Smoke test — no config file**

```bash
bash scripts/tq-message --task abc123 --queue ~/.tq/queues/morning.yaml
# Expected: silent exit (no ~/.tq/config/message.yaml)
```

**Step 3: Smoke test — with config file**

```bash
mkdir -p ~/.tq
cat > ~/.tq/config/message.yaml <<'EOF'
default_service: telegram
content: status

telegram:
  bot_token: "botTEST"
  chat_id: "12345"
EOF

bash scripts/tq-message --task abc123 --queue ~/.tq/queues/morning.yaml
# Expected: [tq-message] service=telegram content=status task=abc123
```

**Step 4: Commit**

```bash
git add scripts/tq-message
git commit -m "add config resolution to tq-message (yaml + env vars)"
```

---

## Task 3: Content formatters — status, details, log

**Files:**
- Modify: `scripts/tq-message`

**What to build:** Three non-Claude content types. State file lives at `<queue-dir>/.tq/<basename>/<hash>`. Prompt file at `<queue-dir>/.tq/<basename>/<hash>.prompt`.

**Step 1: Add content formatting after the config resolution block**

```bash
# Resolve state dir from queue file and task hash
if [[ -n "$TASK_HASH" && -n "$QUEUE_FILE" ]]; then
  QUEUE_DIR="$(dirname "$QUEUE_FILE")"
  QUEUE_BASENAME="$(basename "$QUEUE_FILE" .yaml)"
  STATE_DIR="$QUEUE_DIR/.tq/$QUEUE_BASENAME"
  STATE_FILE="$STATE_DIR/$TASK_HASH"
  PROMPT_FILE="$STATE_DIR/$TASK_HASH.prompt"
else
  STATE_DIR=""
  STATE_FILE=""
  PROMPT_FILE=""
fi

build_message() {
  local content_type="$1"
  local hash="$2"
  local state_file="$3"
  local prompt_file="$4"
  local session="$5"

  local first_line status started duration msg

  if [[ -f "$prompt_file" ]]; then
    first_line="$(head -1 "$prompt_file")"
  elif [[ -f "$state_file" ]]; then
    first_line="$(grep '^prompt=' "$state_file" | cut -d= -f2-)"
  else
    first_line="(unknown task)"
  fi

  if [[ -f "$state_file" ]]; then
    status="$(grep '^status=' "$state_file" | cut -d= -f2)"
    started="$(grep '^started=' "$state_file" | cut -d= -f2)"
  else
    status="done"
    started=""
  fi

  # Calculate duration in minutes
  duration=""
  if [[ -n "$started" ]]; then
    start_epoch="$(python3 -c "import datetime; print(int(datetime.datetime.fromisoformat('${started}').timestamp()))" 2>/dev/null || echo "")"
    if [[ -n "$start_epoch" ]]; then
      now_epoch="$(date +%s)"
      elapsed=$(( now_epoch - start_epoch ))
      duration="${elapsed}s"
      if (( elapsed >= 60 )); then
        duration="$(( elapsed / 60 ))m $(( elapsed % 60 ))s"
      fi
    fi
  fi

  case "$content_type" in
    status)
      msg="tq: task ${status}
${first_line:0:100}
${duration:+Duration: $duration}"
      ;;
    details)
      msg="tq: task ${status} [${hash}]
Prompt: ${first_line:0:200}
${duration:+Duration: $duration}"
      ;;
    log)
      if [[ -n "$session" ]] && tmux has-session -t "$session" 2>/dev/null; then
        local pane_text
        pane_text="$(tmux capture-pane -t "$session" -p -S -200 2>/dev/null || echo "(could not capture pane)")"
        msg="tq: task ${status} [${hash}]
${first_line:0:80}

Last output:
\`\`\`
${pane_text: -1500}
\`\`\`"
      else
        msg="tq: task ${status} [${hash}]
${first_line:0:80}
(session no longer active — log unavailable)"
      fi
      ;;
    *)
      msg="(unknown content type: $content_type)"
      ;;
  esac

  echo "$msg"
}
```

**Step 2: Wire content generation into main flow (after config block)**

```bash
# If --message provided directly (e.g. from /tq-message slash command), skip generation
if [[ -z "$MESSAGE_TEXT" ]]; then
  case "$CONTENT" in
    summary)
      # summary mode: handled by send-keys in Task 4
      # if no session available, fall back to details
      if [[ -z "$SESSION" ]]; then
        MESSAGE_TEXT="$(build_message "details" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "")"
      fi
      ;;
    status|details|log)
      MESSAGE_TEXT="$(build_message "$CONTENT" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "$SESSION")"
      ;;
    *)
      echo "Error: unknown content type: $CONTENT" >&2
      exit 1
      ;;
  esac
fi
```

**Step 3: Smoke test**

```bash
# Create a fake state dir to test against
mkdir -p /tmp/tq-test/.tq/test
echo "test task prompt" > /tmp/tq-test/.tq/test/abc12345.prompt
cat > /tmp/tq-test/.tq/test/abc12345 <<EOF
status=done
session=tq-test-123456
started=$(date -u +%Y-%m-%dT%H:%M:%S)
prompt=test task prompt
EOF
cat > /tmp/tq-test/test.yaml <<EOF
cwd: /tmp
tasks:
  - prompt: test task prompt
EOF

bash scripts/tq-message --task abc12345 --queue /tmp/tq-test/test.yaml
# Expected: [tq-message] ... then exits (no delivery yet — that's Task 4)
```

**Step 4: Commit**

```bash
git add scripts/tq-message
git commit -m "add status/details/log content formatters to tq-message"
```

---

## Task 4: Telegram delivery + summary send-keys flow

**Files:**
- Modify: `scripts/tq-message`

**What to build:** The Telegram curl call, and for `summary` mode: `tmux send-keys` to invoke `/tq-message` in the live Claude session.

**Step 1: Add delivery function after the content block**

```bash
send_telegram() {
  local token="$1"
  local chat_id="$2"
  local text="$3"

  local response
  response="$(curl -s -X POST \
    "https://api.telegram.org/bot${token}/sendMessage" \
    -d "chat_id=${chat_id}" \
    --data-urlencode "text=${text}" \
    -d "parse_mode=Markdown" 2>&1)"

  if echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('ok') else 1)" 2>/dev/null; then
    echo "[tq-message] sent via Telegram"
  else
    echo "[tq-message] Telegram error: $response" >&2
    exit 1
  fi
}

deliver() {
  local service="$1"
  local msg="$2"
  case "$service" in
    telegram) send_telegram "$TG_TOKEN" "$TG_CHAT" "$msg" ;;
    *) echo "[tq-message] unknown service: $service" >&2; exit 1 ;;
  esac
}
```

**Step 2: Add summary send-keys dispatch and final delivery at the bottom of the script**

```bash
# Summary mode with a live session: ask Claude to generate and send
if [[ "$CONTENT" == "summary" && -n "$SESSION" && -z "$MESSAGE_TEXT" ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    # Pass hash and queue path as arguments to the slash command
    tmux send-keys -t "$SESSION" "/tq-message ${TASK_HASH} ${QUEUE_FILE}" Enter
    # Give Claude time to summarize and call back tq-message --message
    sleep 45
    # Close the session
    tmux send-keys -t "$SESSION" "" Enter
    exit 0
  else
    # Session gone — fall back to details
    MESSAGE_TEXT="$(build_message "details" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "")"
  fi
fi

# Deliver message if we have one
if [[ -n "$MESSAGE_TEXT" ]]; then
  deliver "$SERVICE" "$MESSAGE_TEXT"
fi
```

**Step 3: Manual test — Telegram delivery (requires real bot token)**

Set up `~/.tq/config/message.yaml` with a real Telegram bot token and chat ID. Run:

```bash
bash scripts/tq-message --task abc12345 --queue /tmp/tq-test/test.yaml
# Expected: [tq-message] sent via Telegram
# Verify message appears in Telegram chat
```

**Step 4: Test fallback — summary mode without session**

```bash
# content=summary but no --session → should fall back to details and send
TQ_MESSAGE_CONTENT=summary bash scripts/tq-message \
  --task abc12345 --queue /tmp/tq-test/test.yaml
# Expected: sends a details-formatted message via Telegram
```

**Step 5: Commit**

```bash
git add scripts/tq-message
git commit -m "add Telegram delivery and summary send-keys flow to tq-message"
```

---

## Task 5: `.claude/commands/tq-message.md` slash command

**Files:**
- Create: `.claude/commands/tq-message.md`

**What to build:** A Claude plugin slash command that runs inside the live Claude session. It receives the task hash and queue file path as `$ARGUMENTS`, generates a 2-3 sentence summary of the session, then calls `tq-message --message "..."` via the Bash tool.

**Step 1: Create the file**

```markdown
---
name: tq-message
description: Send a tq task completion summary to the configured messaging service. Called automatically by tq on-stop hooks.
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message)
---

Arguments: $ARGUMENTS

You have just completed a tq task. Parse the arguments to get the task hash and queue file:
- First argument: task hash (8-char string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a .yaml file)

## Steps

1. Write a 2-3 sentence summary of what you accomplished in this session. Be specific: mention what files were changed, what was fixed or built, and any notable outcome. Keep it concise enough to read in a Telegram message.

2. Call Bash to send the summary:

```bash
tq-message --task <hash> --queue <queue_file> --message "<your summary here>"
```

Replace `<hash>` with the first argument, `<queue_file>` with the second argument, and `<your summary here>` with your written summary.

Do not explain what you are doing. Just write the summary and run the command.
```

**Step 2: Verify the file is recognized by the plugin**

The command file follows the same frontmatter format as `health.md`, `todo.md`, etc. — no additional registration needed.

**Step 3: Commit**

```bash
git add .claude/commands/tq-message.md
git commit -m "add /tq-message slash command for AI summary generation"
```

---

## Task 6: Update `scripts/tq` — expose session + queue file in `on-stop.sh`

**Files:**
- Modify: `scripts/tq` (Python section, on-stop.sh generation)

**What to build:** Two changes to the Python section of `scripts/tq`:
1. Add `TQ_QUEUE_FILE` and `TQ_HASH` exports to `on-stop.sh` (TQ_HASH already exported conditionally — make it unconditional)
2. Add a messaging block at the end of `on-stop.sh` that calls `tq-message`

**The on-stop.sh must read the session name from the state file at runtime** (not baked in at generation time, since session names aren't known when on-stop.sh is written).

**Step 1: Locate the on-stop.sh generation block in `scripts/tq`**

It starts at line 232 (`stop_script = '#!/usr/bin/env bash\n'`) and ends at line 258 (`os.chmod(...)`).

**Step 2: Add session read + tq-message call to the generated on-stop.sh**

After the existing `if notify:` block (before the `with open(stop_hook, 'w')` line), add:

```python
    # Messaging via tq-message (always emitted; tq-message exits silently if unconfigured)
    stop_script += '\n# tq-message notification\n'
    stop_script += 'export TQ_HASH=' + json.dumps(h) + '\n'
    stop_script += 'export TQ_QUEUE_FILE=' + json.dumps(queue_file) + '\n'
    stop_script += 'if command -v tq-message &>/dev/null; then\n'
    stop_script += '  SESSION="$(grep \'^session=\' "$STATE_FILE" | cut -d= -f2)"\n'
    stop_script += '  tq-message --task "$TQ_HASH" --queue "$TQ_QUEUE_FILE" --session "$SESSION"\n'
    stop_script += 'fi\n'
```

Note: `queue_file` is the variable already in scope in the Python block (it's `sys.argv[1]`).

**Step 3: Verify the queue_file variable is available in both code paths**

In the Python script, `queue_file` is set at the top for queue mode:
```python
queue_file = sys.argv[1]
```
For `--prompt` mode (`sys.argv[1] == '--prompt'`), there's no queue file. Add a guard:
```python
    if len(sys.argv) > 1 and sys.argv[1] != '--prompt':
        stop_script += 'export TQ_QUEUE_FILE=' + json.dumps(queue_file) + '\n'
    else:
        stop_script += 'export TQ_QUEUE_FILE=""\n'
```

**Step 4: Manual test — run tq on a queue and verify on-stop.sh contents**

```bash
tq ~/.tq/queues/morning.yaml
# Find the generated on-stop.sh:
cat ~/.tq/sessions/<hash>/hooks/on-stop.sh
# Expected: see TQ_HASH, TQ_QUEUE_FILE exports and tq-message call
```

**Step 5: Run tq and confirm no errors**

```bash
bash scripts/tq ~/.tq/queues/morning.yaml
# Expected: tasks spawn as before, no new errors
```

**Step 6: Commit**

```bash
git add scripts/tq
git commit -m "emit tq-message call in on-stop.sh with session + queue file"
```

---

## Task 7: Queue-completion detection in `tq --status`

**Files:**
- Modify: `scripts/tq` (status mode block, lines 58–101)

**What to build:** After the status sweep loop, count total tasks vs done tasks. If all done and a `.queue-notified` sentinel doesn't exist, call `tq-message --queue $QUEUE_FILE` and create the sentinel. Reset the sentinel when any task is spawned (in the run section).

**Step 1: Add counters to the status sweep loop**

Before the `for STATE_FILE in` loop (around line 71), add:

```bash
  TOTAL_TASKS=0
  DONE_TASKS=0
```

Inside the loop, after the `printf` output line, increment:

```bash
    TOTAL_TASKS=$(( TOTAL_TASKS + 1 ))
    if [[ "$STATUS" == "done" ]]; then
      DONE_TASKS=$(( DONE_TASKS + 1 ))
    fi
```

**Step 2: Add queue-completion check after the loop (before `exit 0`)**

```bash
  # Queue completion notification
  SENTINEL="$STATE_DIR/.queue-notified"
  if [[ "$TOTAL_TASKS" -gt 0 && "$TOTAL_TASKS" -eq "$DONE_TASKS" && ! -f "$SENTINEL" ]]; then
    touch "$SENTINEL"
    if command -v tq-message &>/dev/null; then
      tq-message --queue "$QUEUE_FILE"
    fi
  fi
```

**Step 3: Reset sentinel when a task is spawned**

In the run section, just before the `tmux start-server` line (around line 379), add:

```bash
  # Reset queue-notified sentinel so completion fires again after re-run
  rm -f "$STATE_DIR/.queue-notified"
```

**Step 4: Add `.queue-notified` to `.gitignore` if not already covered**

The `.tq/` entry in `.gitignore` already covers this (state dirs are excluded). Verify:

```bash
cat .gitignore | grep tq
# Expected: .tq/ or similar pattern
```

**Step 5: Manual test**

```bash
# Run a queue to completion, then:
tq --status ~/.tq/queues/morning.yaml
# Expected: if all tasks done → Telegram message with queue summary
# Second run of --status:
tq --status ~/.tq/queues/morning.yaml
# Expected: no second notification (sentinel exists)
```

**Step 6: Run tq --status and confirm no errors**

```bash
bash scripts/tq --status ~/.tq/queues/morning.yaml
```

**Step 7: Commit**

```bash
git add scripts/tq
git commit -m "detect queue completion in --status and call tq-message --queue"
```

---

## Task 8: Update `tq-install.sh` + queue format docs

**Files:**
- Modify: `scripts/tq-install.sh` (line 51)
- Modify: `.claude/rules/queue-format.md`

**Step 1: Add `tq-message` to the symlink loop in `tq-install.sh`**

Change line 51 from:
```bash
for SCRIPT in tq; do
```
to:
```bash
for SCRIPT in tq tq-message; do
```

**Step 2: Add `message:` block documentation to `.claude/rules/queue-format.md`**

After the `## Task Object Keys` section, add:

```markdown
## Queue-Level Messaging

Add an optional `message:` block at the top level to configure notifications for this queue.
Overrides `~/.tq/config/message.yaml` global config.

```yaml
message:
  service: telegram       # which service (telegram | slack)
  content: summary        # summary | status | details | log (default: summary)
  chat_id: "-100123456"  # override global chat_id for this queue
```

**Content types:**
- `summary` — Claude writes a 2-3 sentence digest of what it accomplished (requires live session)
- `status` — task name, done/failed, duration (no Claude required)
- `details` — prompt first line, status, duration, hash (no Claude required)
- `log` — last 200 lines of tmux pane scrollback (no Claude required)

**Global credentials** go in `~/.tq/config/message.yaml` — never in queue files (queue files may be shared).
```

**Step 3: Reinstall to verify**

```bash
bash scripts/tq-install.sh
which tq-message
# Expected: /opt/homebrew/bin/tq-message
tq-message
# Expected: Usage: ...
```

**Step 4: Commit**

```bash
git add scripts/tq-install.sh .claude/rules/queue-format.md
git commit -m "install tq-message via tq-install.sh, document message: block in queue format"
```

---

## Task 9: End-to-end smoke test

**No code changes — manual verification only.**

**Setup:**

1. Ensure `~/.tq/config/message.yaml` has valid Telegram credentials
2. Ensure `tq-message` is installed: `which tq-message`
3. Create a test queue:

```yaml
# /tmp/tq-smoke-test.yaml
cwd: /tmp
message:
  content: status
tasks:
  - name: smoke-test
    prompt: Write the word "hello" to /tmp/tq-smoke-output.txt
```

**Test 1: Per-task notification (status content)**

```bash
tq /tmp/tq-smoke-test.yaml
# Watch the tmux session complete
# Expected: Telegram message with "tq: task done / Write the word..."
```

**Test 2: Queue-completion notification**

```bash
tq --status /tmp/tq-smoke-test.yaml
# Expected: Telegram message (queue summary with details content type)
```

**Test 3: Second --status run (no duplicate)**

```bash
tq --status /tmp/tq-smoke-test.yaml
# Expected: no second Telegram message
```

**Test 4: Summary content type (requires live session)**

Update the test queue to `content: summary`, reset state, re-run:
```bash
rm -rf /tmp/.tq/tq-smoke-test/
tq /tmp/tq-smoke-test.yaml
# Watch the tmux session — after task completes, /tq-message should appear in the Claude window
# Expected: Telegram message with Claude-written summary
```
