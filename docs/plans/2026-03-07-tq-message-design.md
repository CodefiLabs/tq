# tq-message Design

**Date:** 2026-03-07
**Status:** Approved

## Problem

tq runs Claude tasks in unattended tmux sessions. When a task completes — or when a whole queue finishes — there is no way to receive a notification on a phone or messaging app. The existing `--notify` flag covers local signals (macOS notification, bell, custom script) but has no concept of remote messaging services or AI-generated summaries.

## Solution

Add `tq-message`: a standalone CLI + Claude slash command that sends task and queue completion notifications to messaging services, with an AI-generated summary as the default content.

## Components

### 1. `scripts/tq-message`

A Bash script (same style as `tq`) installed alongside it. Handles config resolution, message formatting, and delivery.

**Interface:**

```bash
tq-message --task <hash> --queue <file.yaml> [--message <text>]
tq-message --queue <file.yaml> [--message <text>]
```

- `--task` mode: sends a per-task completion message
- `--queue` mode: sends a queue-level summary after all tasks complete
- `--message`: if provided, skips content generation and sends this text directly (used by the slash command after Claude writes the summary)

**Internal flow (when `--message` is not provided):**
- Content type `status`: formats task name, status, duration — no Claude involved
- Content type `details`: formats prompt first line, status, duration per task
- Content type `log`: captures last N lines from tmux pane scrollback
- Content type `summary` (default): relies on the `/tq-message` slash command to generate text and call `tq-message --message "..."` — `tq-message` itself does not generate AI content

### 2. `.claude/commands/tq-message.md`

A Claude slash command (part of the tq plugin) that runs inside the live Claude session after a task completes.

**Invoked by:** `tmux send-keys -t "$SESSION" "/tq-message" Enter`
**What it does:** Instructs Claude to write a 2-3 sentence summary of what it just accomplished, then call `tq-message` via the Bash tool with `--message "$SUMMARY"` and the queue file path from the environment.

### 3. Config File: `~/.tq/message.yaml`

Global credentials and defaults. Created manually by the user.

```yaml
default_service: telegram
content: summary        # summary | status | details | log

telegram:
  bot_token: "bot123..."
  chat_id: "987654321"

slack:
  webhook: "https://hooks.slack.com/..."
```

### 4. Queue YAML `message:` block

Per-queue overrides. Merged on top of the global config.

```yaml
cwd: /Users/kk/Sites/startups/myproject
message:
  service: telegram
  content: status        # override for this queue
  chat_id: "-100123456" # different channel for this queue
tasks:
  - prompt: ...
```

### 5. Environment Variables

Runtime overrides — useful in cron. Service-specific:

```bash
TQ_TELEGRAM_BOT_TOKEN=...
TQ_TELEGRAM_CHAT_ID=...
TQ_SLACK_WEBHOOK=...
TQ_MESSAGE_SERVICE=telegram    # which service
TQ_MESSAGE_CONTENT=summary     # content type (generic, not service-specific)
```

Priority: env vars > queue YAML > `~/.tq/message.yaml`

## Trigger Points

### Per-task (on-stop.sh)

When a task's `on-stop.sh` runs, if messaging is configured:

```bash
# For content=summary: ask the live Claude session to summarize
tmux send-keys -t "$SESSION" "/tq-message" Enter
# The slash command generates summary and calls tq-message --message "..."
# Then close the session
tmux send-keys -t "$SESSION" "" Enter

# For content=status|details|log: call tq-message directly
tq-message --task "$TQ_HASH" --queue "$TQ_QUEUE_FILE"
```

### Queue-level (`tq --status`)

When `tq --status` sweeps the queue and detects a transition from "some running/pending" to "all done", it calls:

```bash
tq-message --queue "$QUEUE_FILE"
```

For `content=summary`, this sends-keys to the last active session or formats a multi-task summary without Claude (since no single session is still live at queue completion time).

## Services

### Telegram (MVP)

Delivery via Bot API:

```bash
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  -d text="${MESSAGE}" \
  -d parse_mode="Markdown"
```

Config keys: `telegram.bot_token`, `telegram.chat_id`
Env vars: `TQ_TELEGRAM_BOT_TOKEN`, `TQ_TELEGRAM_CHAT_ID`

### Slack (future)

Delivery via incoming webhook URL. Config key: `slack.webhook`. Env var: `TQ_SLACK_WEBHOOK`.

### Email, Signal, macOS Messages (future)

Same pattern: service-specific config block + env var overrides.

## Content Types

| Type | Description | Claude required? |
|------|-------------|-----------------|
| `summary` | 2-3 sentence digest written by Claude | Yes (via slash command) |
| `status` | Task name, done/failed, duration | No |
| `details` | Prompt first line, status, duration, hash | No |
| `log` | Last N lines of tmux pane scrollback | No |

## Installation Changes

`tq-install.sh` symlink loop updated from:
```bash
for SCRIPT in tq; do
```
to:
```bash
for SCRIPT in tq tq-message; do
```

## Environment Variables Available in on-stop.sh

Already set by tq's Python launcher:
- `TQ_PROMPT` — first line of the prompt
- `TQ_HASH` — 8-char task hash
- `TQ_STATE_FILE` — path to the task state file

New variable added by tq's launcher generation:
- `TQ_QUEUE_FILE` — absolute path to the queue YAML (needed by tq-message to read the `message:` block)

## Out of Scope

- OAuth flows or interactive auth setup for any service
- Message threading or reply tracking
- Delivery receipts or retry logic
- Signal (requires signal-cli, too complex for MVP)
- Queue-level `summary` content (requires a live Claude session; queue completion uses `details` as fallback)
