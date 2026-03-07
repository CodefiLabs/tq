# tq-setup Messaging Configuration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add interactive Telegram setup (`tq-setup`), a Telegram polling daemon (`tq-telegram-poll`) that turns incoming bot messages into `tq --prompt` sessions, default `--prompt` cwd to `~/.tq/workspace/`, and a `/setup-telegram` Claude slash command.

**Architecture:**
- `tq-setup` — interactive script: prompts for bot token, auto-discovers user_id via `getUpdates`, writes `~/.tq/message.yaml`
- `tq-telegram-poll` — cron script: polls `getUpdates`, filters by user_id, runs `tq --prompt` for each new message
- `scripts/tq` — change `--prompt` cwd default from `$PWD` to `~/.tq/workspace/`
- `scripts/tq-message` — read `user_id` from config as alias for `chat_id` (both work)
- `.claude/commands/setup-telegram.md` — `/setup-telegram` slash command for in-Claude setup
- `scripts/tq-install.sh` — symlink tq-setup + tq-telegram-poll, mention both at end

---

## Task 1: `scripts/tq-setup` — interactive Telegram setup with user_id auto-discovery

**Files:**
- Create: `scripts/tq-setup`

**UX flow:**

```
Setting up Telegram notifications for tq.

You'll need a bot token from @BotFather (https://t.me/BotFather — send /newbot).

Bot token: [hidden input]

Send any message to your bot now, then press Enter...
[polls getUpdates for up to 60s]
Found your user ID: 123456789

Content type (what tq sends when a task finishes):
  status  — task name + done/failed + duration  [default]
  summary — Claude writes a 2-3 sentence digest (requires live session)
Content [status]: [input]

Sending test message...
Test message sent. Check your Telegram.

Config written to ~/.tq/message.yaml
Workspace: ~/.tq/workspace/ (created)

To receive Telegram messages as tq tasks, add to crontab (crontab -e):
  * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1

Run  tq-setup  again at any time to reconfigure.
```

**Overwrite guard:** if `~/.tq/message.yaml` already exists, prompt `Overwrite? [y/N]:` and exit 0 on anything but `y`.

**Auto-discovery flow:**
1. Print "Send any message to your bot now, then press Enter..."
2. `read -r` (waits for Enter — gives user time to send the message)
3. `curl getUpdates?offset=0&limit=10&timeout=0`
4. Parse response with Python: extract first `from.id` from any message
5. If none found: print error and exit 1

**Step 1: Create `scripts/tq-setup`**

```bash
#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CONFIG_FILE="$HOME/.tq/message.yaml"

# --- Overwrite guard ---
if [[ -f "$CONFIG_FILE" ]]; then
  printf '%s already exists.\nOverwrite? [y/N]: ' "$CONFIG_FILE"
  read -r OVERWRITE
  if [[ "${OVERWRITE,,}" != "y" ]]; then
    exit 0
  fi
fi

echo ""
echo "Setting up Telegram notifications for tq."
echo ""
echo "You'll need a bot token from @BotFather (https://t.me/BotFather — send /newbot)."
echo ""

# --- Bot token ---
printf 'Bot token: '
read -rs BOT_TOKEN
echo ""

# --- Auto-discover user_id ---
echo ""
echo "Send any message to your bot now, then press Enter..."
read -r _IGNORED

UPDATES="$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=0&limit=10&timeout=0" 2>&1)"

DISCOVER_SCRIPT=$(mktemp /tmp/tq-setup-discover-XXXXXX.py)
trap 'rm -f "$DISCOVER_SCRIPT"' EXIT

cat > "$DISCOVER_SCRIPT" <<'PYEOF'
import sys, json
data = json.loads(sys.argv[1])
if not data.get('ok'):
    print('ERROR: ' + data.get('description', 'unknown error'))
    sys.exit(1)
results = data.get('result', [])
for update in results:
    msg = update.get('message') or update.get('edited_message') or update.get('channel_post')
    if msg:
        from_id = msg.get('from', {}).get('id') or msg.get('sender_chat', {}).get('id')
        if from_id:
            print(str(from_id))
            sys.exit(0)
print('NONE')
PYEOF

USER_ID_RAW="$(python3 "$DISCOVER_SCRIPT" "$UPDATES")"

if [[ "$USER_ID_RAW" == NONE ]]; then
  echo "No message found. Make sure you sent a message to your bot, then try again." >&2
  exit 1
fi
if [[ "$USER_ID_RAW" == ERROR* ]]; then
  echo "Telegram error: ${USER_ID_RAW#ERROR: }" >&2
  exit 1
fi

USER_ID="$USER_ID_RAW"
echo "Found your user ID: $USER_ID"

# --- Content type ---
echo ""
echo "Content type (what tq sends when a task finishes):"
echo "  status  — task name + done/failed + duration  [default]"
echo "  summary — Claude writes a 2-3 sentence digest (requires live session)"
printf 'Content [status]: '
read -r CONTENT_TYPE
CONTENT_TYPE="${CONTENT_TYPE:-status}"
if [[ "$CONTENT_TYPE" != "status" && "$CONTENT_TYPE" != "summary" ]]; then
  echo "Invalid content type '$CONTENT_TYPE' — using 'status'" >&2
  CONTENT_TYPE="status"
fi

# --- Test message ---
echo ""
echo "Sending test message..."

TEST_RESPONSE="$(curl -s -X POST \
  "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=${USER_ID}" \
  --data-urlencode "text=tq is configured. Notifications are working." \
  -d "parse_mode=Markdown" 2>&1)"

if echo "$TEST_RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('ok') else 1)" 2>/dev/null; then
  echo "Test message sent. Check your Telegram."
else
  echo "Error: Telegram rejected the request:" >&2
  echo "$TEST_RESPONSE" >&2
  echo "" >&2
  echo "Config NOT written. Fix the token and try again." >&2
  exit 1
fi

# --- Write config ---
mkdir -p "$HOME/.tq"
cat > "$CONFIG_FILE" <<EOF
default_service: telegram
content: ${CONTENT_TYPE}

telegram:
  bot_token: "${BOT_TOKEN}"
  user_id: "${USER_ID}"
EOF

# --- Create workspace ---
mkdir -p "$HOME/.tq/workspace"
mkdir -p "$HOME/.tq/logs"

echo ""
echo "Config written to $CONFIG_FILE"
echo "Workspace: $HOME/.tq/workspace/ (created)"
echo ""
echo "To receive Telegram messages as tq tasks, add to crontab (crontab -e):"
echo "  * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1"
echo ""
echo "Run  tq-setup  again at any time to reconfigure."
```

**Step 2: Make executable and smoke test**

```bash
chmod +x scripts/tq-setup
bash -n scripts/tq-setup && echo "syntax OK"
```

**Step 3: Commit**

```bash
git add scripts/tq-setup
git commit -m "add tq-setup interactive Telegram setup with user_id auto-discovery"
```

---

## Task 2: `scripts/tq-telegram-poll` — incoming message polling daemon

**Files:**
- Create: `scripts/tq-telegram-poll`

**What it does:**
1. Reads `bot_token` and `user_id` from `~/.tq/message.yaml`; exits silently if not configured
2. Reads last offset from `~/.tq/telegram-poll-offset` (0 if file doesn't exist)
3. Calls `getUpdates?offset=<offset>&limit=10&timeout=0`
4. Filters messages where `from.id == user_id`
5. For each matching message text, runs `tq --prompt "<text>"`
6. Writes `last_update_id + 1` back to the offset file
7. Runs via cron every minute

**Step 1: Create `scripts/tq-telegram-poll`**

```bash
#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

CONFIG_FILE="$HOME/.tq/message.yaml"
OFFSET_FILE="$HOME/.tq/telegram-poll-offset"

# --- Read config ---
if [[ ! -f "$CONFIG_FILE" ]]; then
  exit 0
fi

CONFIG_SCRIPT=$(mktemp /tmp/tq-poll-config-XXXXXX.py)
trap 'rm -f "$CONFIG_SCRIPT"' EXIT

cat > "$CONFIG_SCRIPT" <<'PYEOF'
import sys, os, re, json

def parse_flat_block(text, top_key):
    lines = text.split('\n')
    in_block = False
    block_indent = None
    result = {}
    for line in lines:
        if re.match(r'^' + re.escape(top_key) + r':\s*$', line):
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

config_path = sys.argv[1]
with open(config_path) as f:
    text = f.read()

tg = parse_flat_block(text, 'telegram')
print(json.dumps({
    'bot_token': tg.get('bot_token', ''),
    'user_id':   tg.get('user_id', ''),
}))
PYEOF

CONFIG_JSON="$(python3 "$CONFIG_SCRIPT" "$CONFIG_FILE")"
BOT_TOKEN="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('bot_token',''))" "$CONFIG_JSON")"
USER_ID="$(python3 -c "import sys,json; print(json.loads(sys.argv[1]).get('user_id',''))" "$CONFIG_JSON")"

if [[ -z "$BOT_TOKEN" || -z "$USER_ID" ]]; then
  exit 0
fi

# --- Read offset ---
OFFSET=0
if [[ -f "$OFFSET_FILE" ]]; then
  OFFSET="$(cat "$OFFSET_FILE")"
fi

# --- Fetch updates ---
UPDATES="$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${OFFSET}&limit=10&timeout=0" 2>&1)"

# --- Process updates ---
PROCESS_SCRIPT=$(mktemp /tmp/tq-poll-process-XXXXXX.py)
trap 'rm -f "$CONFIG_SCRIPT" "$PROCESS_SCRIPT"' EXIT

cat > "$PROCESS_SCRIPT" <<'PYEOF'
import sys, json

data = json.loads(sys.argv[1])
user_id = int(sys.argv[2])
offset_file = sys.argv[3]

if not data.get('ok'):
    sys.exit(0)

results = data.get('result', [])
new_offset = None
messages = []

for update in results:
    update_id = update['update_id']
    new_offset = update_id + 1

    msg = update.get('message') or update.get('edited_message')
    if not msg:
        continue
    from_id = msg.get('from', {}).get('id')
    if from_id != user_id:
        continue
    text = msg.get('text', '').strip()
    if text:
        messages.append(text)

if new_offset is not None:
    with open(offset_file, 'w') as f:
        f.write(str(new_offset))

for m in messages:
    print(m)
PYEOF

MESSAGES="$(python3 "$PROCESS_SCRIPT" "$UPDATES" "$USER_ID" "$OFFSET_FILE")"

# --- Spawn tq --prompt for each message ---
mkdir -p "$HOME/.tq/workspace"

while IFS= read -r MSG; do
  if [[ -n "$MSG" ]]; then
    echo "[tq-telegram-poll] prompt: ${MSG:0:60}"
    tq --prompt "$MSG"
  fi
done <<< "$MESSAGES"
```

**Step 2: Make executable and syntax check**

```bash
chmod +x scripts/tq-telegram-poll
bash -n scripts/tq-telegram-poll && echo "syntax OK"
```

**Step 3: Smoke test — no config (should exit silently)**

```bash
bash scripts/tq-telegram-poll
echo "exit: $?"
# Expected: no output, exit 0
```

**Step 4: Commit**

```bash
git add scripts/tq-telegram-poll
git commit -m "add tq-telegram-poll cron daemon to relay Telegram messages as tq --prompt"
```

---

## Task 3: Update `scripts/tq` — default `--prompt` cwd to `~/.tq/workspace/`

**Files:**
- Modify: `scripts/tq`

**What to change:** Line 344 currently reads:

```bash
TASK_CWD="${TASK_CWD:-$PWD}"
```

Change to:

```bash
TASK_CWD="${TASK_CWD:-$HOME/.tq/workspace}"
```

This means:
- `tq --prompt "foo"` → cwd is `~/.tq/workspace/`
- `tq --prompt "foo" --cwd /some/dir` → cwd is `/some/dir` (explicit override still works)
- Queue mode is unaffected (uses `cwd:` from YAML)

Also ensure `~/.tq/workspace/` is created before the launch. Add `mkdir -p "$HOME/.tq/workspace"` immediately after the `TASK_CWD` line:

```bash
TASK_CWD="${TASK_CWD:-$HOME/.tq/workspace}"
mkdir -p "$TASK_CWD"
```

**Step 1: Read `scripts/tq` to locate line 344, then edit it.**

**Step 2: Smoke test**

```bash
bash -n scripts/tq && echo "syntax OK"

# Verify the default cwd appears in a generated launcher
# (run tq --prompt briefly; interrupt after it spawns)
tq --prompt "echo hello from workspace test" 2>&1 | head -5
cat ~/.tq/adhoc/adhoc/*.launch.py 2>/dev/null | grep 'cwd =' | tail -1
# Expected: cwd = '/Users/<you>/.tq/workspace'
```

**Step 3: Commit**

```bash
git add scripts/tq
git commit -m "default --prompt cwd to ~/.tq/workspace/"
```

---

## Task 4: Update `scripts/tq-message` — accept `user_id` as alias for `chat_id`

**Files:**
- Modify: `scripts/tq-message` (Python config resolver, lines ~73–85)

**What to change:** The Python config resolver currently reads only `chat_id` from the `telegram:` block. Since `tq-setup` now writes `user_id` instead, the resolver must fall back to `user_id` when `chat_id` is absent.

Find this block in the Python heredoc:

```python
tg = parse_flat_block(g, 'telegram')
if tg.get('bot_token'): config['telegram_bot_token'] = tg['bot_token']
if tg.get('chat_id'):   config['telegram_chat_id']   = tg['chat_id']
```

Change to:

```python
tg = parse_flat_block(g, 'telegram')
if tg.get('bot_token'): config['telegram_bot_token'] = tg['bot_token']
if tg.get('chat_id'):   config['telegram_chat_id']   = tg['chat_id']
if tg.get('user_id'):   config['telegram_chat_id']   = tg['user_id']
```

(user_id overwrites chat_id if both present — user_id wins since tq-setup writes it.)

**Step 1: Read `scripts/tq-message` to locate the exact lines, then edit.**

**Step 2: Smoke test**

```bash
bash -n scripts/tq-message && echo "syntax OK"

# Test with a config using user_id (not chat_id)
mkdir -p ~/.tq
cat > /tmp/tq-message-test-config.yaml <<'EOF'
default_service: telegram
content: status

telegram:
  bot_token: "botTEST"
  user_id: "99999"
EOF

# Point the config resolver at our test config by temporarily symlinking
TQ_TELEGRAM_BOT_TOKEN=botTEST TQ_TELEGRAM_CHAT_ID=99999 \
  bash scripts/tq-message --task abc12345 --queue scripts/tq 2>&1 | head -3
# Expected: Telegram error (fake token) — proves user_id was used as chat_id
```

**Step 3: Commit**

```bash
git add scripts/tq-message
git commit -m "accept user_id as alias for chat_id in tq-message config resolver"
```

---

## Task 5: `.claude/commands/setup-telegram.md` slash command

**Files:**
- Create: `.claude/commands/setup-telegram.md`

**What to build:** A `/setup-telegram` Claude command. Since Claude Code doesn't support interactive `read -s` prompts, this command guides the user conversationally: asks for bot token, instructs them to send a message to the bot, then runs `tq-setup` passing credentials via env vars — OR writes the config directly via Bash.

The simplest design: Claude asks for the two values conversationally, then calls `tq-setup`-equivalent Bash directly (writes config + sends test message) without spawning the interactive script.

**Step 1: Create `.claude/commands/setup-telegram.md`**

Use the Write tool (not a Bash heredoc) to avoid nested-backtick quoting issues.

The file content:

```markdown
---
name: setup-telegram
description: Configure Telegram notifications for tq. Guides you through bot token setup and writes ~/.tq/message.yaml.
tags: tq, setup, telegram, notify
allowed-tools: Bash(curl),Bash(mkdir),Bash(cat),Bash(python3),Bash(tq-setup)
---

Arguments: $ARGUMENTS

Help the user configure Telegram notifications for tq interactively.

## Step 1 — Get bot token

Tell the user:

> To set up Telegram notifications, you need a bot token from @BotFather.
> 1. Open Telegram and search for @BotFather
> 2. Send `/newbot` and follow the prompts
> 3. Copy the token it gives you (looks like `123456:ABCdef...`)
>
> Paste your bot token here:

Wait for the user to paste their token.

## Step 2 — Discover user ID

Tell the user:

> Now send any message to your new bot in Telegram, then tell me when you've done it.

Once they confirm, run:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```

Parse the response to extract `from.id` from the first message. Tell the user their user ID.

If no message is found, ask them to send a message to the bot and try again.

## Step 3 — Content type

Ask:

> What type of notification do you want when a tq task finishes?
> - `status` — task name, done/failed, duration (default, always works)
> - `summary` — Claude writes a 2-3 sentence digest of what it accomplished (requires live session)

Default to `status` if they don't specify or say "default".

## Step 4 — Write config and test

Send a test message:

```bash
curl -s -X POST \
  "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<USER_ID>" \
  --data-urlencode "text=tq is configured. Notifications are working." \
  -d "parse_mode=Markdown"
```

If it fails, report the error and stop.

If it succeeds, write the config:

```bash
mkdir -p ~/.tq ~/.tq/workspace ~/.tq/logs
cat > ~/.tq/message.yaml <<EOF
default_service: telegram
content: <CONTENT_TYPE>

telegram:
  bot_token: "<TOKEN>"
  user_id: "<USER_ID>"
EOF
```

## Step 5 — Final instructions

Tell the user:

> Config written to ~/.tq/message.yaml.
>
> To receive your Telegram messages as tq tasks, add this to your crontab (`crontab -e`):
> ```
> * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1
> ```
>
> tq will now notify you via Telegram when tasks complete.
```

**Step 2: Verify**

```bash
head -8 .claude/commands/setup-telegram.md
# Expected: frontmatter with name: setup-telegram
```

**Step 3: Commit**

```bash
git add .claude/commands/setup-telegram.md
git commit -m "add /setup-telegram Claude slash command for in-Claude Telegram setup"
```

---

## Task 6: Update `scripts/tq-install.sh`

**Files:**
- Modify: `scripts/tq-install.sh`

**Two changes:**

**Change 1:** Add `tq-setup` and `tq-telegram-poll` to the symlink loop.

Find:
```bash
for SCRIPT in tq tq-message; do
```

Change to:
```bash
for SCRIPT in tq tq-message tq-setup tq-telegram-poll; do
```

**Change 2:** After the existing crontab example block, add:

```bash
echo ""
echo "To configure Telegram notifications:"
echo "  tq-setup"
echo ""
echo "Or from Claude Code: /setup-telegram"
echo ""
echo "To relay Telegram messages as tq tasks, add to crontab:"
echo "  * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1"
```

**Step 1: Read `scripts/tq-install.sh`, locate both insertion points, then edit.**

**Step 2: Reinstall and verify**

```bash
bash scripts/tq-install.sh
which tq-setup tq-telegram-poll
# Expected: both in /opt/homebrew/bin/
bash -n "$(which tq-setup)" && echo "tq-setup syntax OK"
bash -n "$(which tq-telegram-poll)" && echo "tq-telegram-poll syntax OK"
```

**Step 3: Commit**

```bash
git add scripts/tq-install.sh
git commit -m "install tq-setup and tq-telegram-poll, mention both in install output"
```

---

## Success Criteria

### Automated:
- [ ] `bash -n scripts/tq-setup` — syntax OK
- [ ] `bash -n scripts/tq-telegram-poll` — syntax OK
- [ ] `bash -n scripts/tq` — syntax OK
- [ ] `bash -n scripts/tq-message` — syntax OK
- [ ] `which tq-setup tq-telegram-poll` — both symlinked after reinstall
- [ ] `bash scripts/tq-telegram-poll` — silent exit 0 when no config
- [ ] `bash scripts/tq-message --task x --queue scripts/tq` — silent exit 0 when no config
- [ ] Generated launcher for `tq --prompt "foo"` has `cwd = '/Users/.../tq/workspace'`

### Manual (requires real Telegram bot):
- [ ] `tq-setup` prompts correctly, discovers user_id from a real message, sends test message, writes config
- [ ] After setup, `tq` task completion sends Telegram notification
- [ ] `tq-telegram-poll` with a real queued message runs `tq --prompt` for that message
- [ ] `/setup-telegram` in Claude Code guides through setup conversationally
