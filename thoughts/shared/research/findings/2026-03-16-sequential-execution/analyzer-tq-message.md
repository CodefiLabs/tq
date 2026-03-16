# tq-message: Complete Analysis

## Script Location

`/Users/kk/Sites/codefi/tq/scripts/tq-message`

---

## 1. Arguments Accepted

Parsed at lines 13–25 via a `while` loop:

| Flag | Variable | Purpose |
|---|---|---|
| `--task <hash>` | `TASK_HASH` | 8-char SHA-256 hash identifying the task |
| `--queue <file.yaml>` | `QUEUE_FILE` | Absolute path to the queue YAML file |
| `--message <text>` | `MESSAGE_TEXT` | Pre-built message body (bypasses generation) |
| `--session <name>` | `SESSION` | tmux session name (used for `log` content and `summary` mode) |
| `--state-file <path>` | `EXPLICIT_STATE_FILE` | Explicit path to a state file (alternative to `--task + --queue`) |
| `--reply-to <msg_id>` | `REPLY_TO_MSG_ID` | Telegram message ID to thread replies under |

Three usage modes (lines 29–32):
- `--task <hash> --queue <file.yaml>` — per-task notification from the stop hook
- `--queue <file.yaml>` (no `--task`) — queue-completion notification
- `--message <text>` (no `--task` or `--queue`) — direct message delivery (conversation mode)

If none of those three are provided, the script exits with a usage error (line 33).

---

## 2. Config Resolution (Three-Layer Priority)

Config is built in an embedded Python script written to a temp file (`CONFIG_SCRIPT`, lines 43–117). Resolution order (each layer overwrites the previous):

### Layer 1: Global config `~/.tq/config/message.yaml` (lines 80–92)

Read via `parse_top_key` and `parse_flat_block` helpers. Fields extracted:

- `default_service` → `config['service']`
- `content` → `config['content']`
- `telegram.bot_token` → `config['telegram_bot_token']`
- `telegram.chat_id` OR `telegram.user_id` → `config['telegram_chat_id']`
- `slack.webhook` → `config['slack_webhook']`

### Layer 2: Queue-level `message:` block (lines 94–103)

Reads the same queue YAML passed as `sys.argv[1]` and calls `parse_flat_block(q, 'message')`. Overrides:

- `message.service` → `config['service']`
- `message.content` → `config['content']`
- `message.chat_id` → `config['telegram_chat_id']`
- `message.webhook` → `config['slack_webhook']`

### Layer 3: Environment variable overrides (lines 105–110)

- `TQ_MESSAGE_SERVICE`
- `TQ_MESSAGE_CONTENT`
- `TQ_TELEGRAM_BOT_TOKEN`
- `TQ_TELEGRAM_CHAT_ID`
- `TQ_SLACK_WEBHOOK`

### Defaults (lines 112–114)

- `service` defaults to `'telegram'`
- `content` defaults to `'summary'`

### Abort Condition (lines 126–129)

If `SERVICE` is empty, or if `SERVICE == telegram` but `TG_TOKEN` or `TG_CHAT` is empty, the script exits 0 silently. This is how "no messaging configured" is handled.

---

## 3. State File and Prompt File Resolution (lines 131–150)

When `--queue` is provided, the state directory is derived:
```
QUEUE_DIR  = dirname(QUEUE_FILE)
STATE_DIR  = QUEUE_DIR/.tq/QUEUE_BASENAME
STATE_FILE = STATE_DIR/TASK_HASH
PROMPT_FILE = STATE_DIR/TASK_HASH.prompt
```

When `--state-file` is provided directly (and no `--task`/`--queue`), `EXPLICIT_STATE_FILE` is used as `STATE_FILE` and `EXPLICIT_STATE_FILE + ".prompt"` as `PROMPT_FILE`.

---

## 4. Content Types

### `status` (lines 196–200)

Produces a 3-line plain-text message:
```
tq: task <status>
<first 100 chars of first prompt line>
Duration: <Xs or Xm Ys>    (omitted if no duration)
```

### `details` (lines 201–205)

Produces:
```
tq: task <status> [<hash>]
Prompt: <first 200 chars of first prompt line>
Duration: <Xs or Xm Ys>    (omitted if no duration)
```

### `log` (lines 206–228)

Requires a live `SESSION`. Captures last 200 lines of the tmux pane scrollback via `tmux capture-pane -t "$session" -p -S -200`, then truncates to the last 1500 characters of that. Wraps in a Markdown code block:
```
tq: task <status> [<hash>]
<first 80 chars of first prompt line>

Last output:
```
<pane text>
```
```

If the session is no longer active, falls back to a one-liner `(session no longer active — log unavailable)`.

### `summary` — the special case (lines 259–265 and 343–370)

`summary` is not built by `build_message`. It delegates to the live Claude session:

1. If `SESSION` is provided and the tmux session is alive (line 344):
   - Sends `/tq-message <hash> <queue_file>` via `tmux send-keys` (line 349) — this triggers the `.claude/commands/tq-message.md` slash command inside the running Claude session.
   - Polls for a handshake file `/tmp/tq-summary-<hash>.txt` every 3 seconds for up to 90 seconds (lines 352–360).
   - If the handshake file appears, the slash command already delivered the message — script exits 0 (line 361).
   - If polling times out, falls back to `details` content type (line 364).
2. If `SESSION` is absent (line 262–265), immediately falls back to `details`.

The slash command (`/tq-message`) is responsible for writing the handshake file AND delivering the Telegram message itself by calling `tq-message --message <text>`.

### `summary` handshake file written on delivery (lines 372–375)

When `MESSAGE_TEXT` is non-empty and `TASK_HASH` is set, a handshake file is written at `/tmp/tq-summary-<hash>.txt`. This is how the slash-command path signals back to the polling loop.

---

## 5. Queue Completion Notifications (`--queue` with no `--task`)

The `build_queue_message` function (lines 231–251) is called when `TASK_HASH` is empty but `QUEUE_BASENAME` is set (line 256).

It iterates all files in `STATE_DIR`, skipping `.prompt`, `.launch.py`, and `.queue-notified` files, counting total tasks and tasks with `status=done`. Output:
```
tq: queue complete
<queue_basename>.yaml (<done>/<total> tasks done)
```

The caller of this path (in `scripts/tq` at line 115–119) checks a sentinel file `$STATE_DIR/.queue-notified` before calling `tq-message --queue "$QUEUE_FILE"`. The sentinel is `touch`ed first to prevent double-notification on subsequent `--status` runs.

Duration computation for `build_message` (lines 180–193): reads `started=` from the state file, parses it with macOS `date -j -f "%Y-%m-%dT%H:%M:%S"`, reads `completed=` epoch if present, computes elapsed. Formats as `Xs` or `Xm Ys`.

---

## 6. How the Stop Hook Calls tq-message

The stop hook (`on-stop.sh`) is generated by the Python parser in `scripts/tq` at lines 337–351. The generated code is:

```bash
export TQ_HASH="<hash>"
export TQ_QUEUE_FILE="<queue_file>"
if command -v tq-message &>/dev/null; then
  SESSION="$(grep '^session=' "$STATE_FILE" | cut -d= -f2)"
  tq-message --task "$TQ_HASH" --queue "$TQ_QUEUE_FILE" --state-file "$STATE_FILE" --session "$SESSION"
fi
```

The `SESSION` name is read live from the state file at hook invocation time. `tq-message` is called after `status=done` has already been written to the state file (line 316), EXCEPT in `on-complete` reset mode, where state deletion happens after `tq-message` returns (lines 348–351).

---

## 7. Telegram API Integration

Function `send_telegram` (lines 278–330):

- Endpoint: `POST https://api.telegram.org/bot<token>/sendMessage`
- Parameters sent via `curl`:
  - `chat_id=<chat_id>` (form field)
  - `text=<message>` (via `--data-urlencode` — handles special characters)
  - `parse_mode=Markdown`
  - `reply_to_message_id=<id>` + `allow_sending_without_reply=true` (only when `$reply_to` is non-empty)
- Response is parsed with inline Python to extract `result.message_id`.
- If delivery succeeds and `$sent_msg_id` is non-empty, a side-effect fires: checks for `~/.tq/conversations/latest-reply-slug`, and if present, calls `tq-converse track-msg <slug> <sent_msg_id>` to register the outgoing message ID in the conversation registry for future reply threading (lines 316–325).

### Reply Threading Sources (lines 379–386)

`REPLY_TO_MSG_ID` is populated from:
1. `--reply-to <id>` flag (explicit, e.g., from the `/tq-reply` slash command)
2. `~/.tq/conversations/latest-msg-id` file (conversation mode fallback — set by `tq-telegram-poll`)

The `deliver` function (lines 332–340) dispatches to `send_telegram` for `telegram` service; `slack` is referenced in the config parser but not implemented in `deliver` (exits with "unknown service").

---

## 8. Relevance to Sequential Execution

The stop hook calls `tq-message` synchronously — `tq-message` must return before the stop hook exits. In `summary` mode with a live session, `tq-message` blocks for up to 90 seconds waiting for the slash command handshake file.

The stop hook runs after `status=done` is written (except `on-complete` mode). Any sequential-execution trigger inserted into the stop hook would therefore run after `tq-message` returns, and after the task is marked done — making `tq-message` and the next-task trigger naturally sequential with no conflicts, as long as the trigger is appended after the existing `tq-message` call in the generated stop script (around `scripts/tq` line 347).

The `SESSION` variable in the stop hook is read from the state file at invocation time, not baked in at generation time — so it reflects the actual tmux session that ran the task.
