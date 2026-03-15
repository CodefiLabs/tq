---
name: tq-reply
description: Reply to Telegram user from conversation session
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(cat),Bash(mkdir),Bash(date),Bash(tmux)
argument-hint: (no arguments)
---

Arguments: $ARGUMENTS

Auto-detect the conversation slug and send a response back to the Telegram user.

## 1. Detect conversation slug

Read the marker file for this session, then fall back to tmux session name:

```bash
SLUG=""
# Method 1: marker file written by .tq-converse.md setup
SLUG_FILE="$HOME/.tq/conversations/sessions/$(tmux display-message -p '#{session_name}' 2>/dev/null | sed 's/^tq-conv-//')/current-slug"
if [[ -f "$SLUG_FILE" ]]; then
  SLUG="$(cat "$SLUG_FILE")"
fi

# Method 2: extract from tmux session name
if [[ -z "$SLUG" ]]; then
  CURRENT_SESSION="$(tmux display-message -p '#{session_name}' 2>/dev/null)"
  if [[ "$CURRENT_SESSION" == tq-conv-* ]]; then
    SLUG="${CURRENT_SESSION#tq-conv-}"
  fi
fi
```

If SLUG is empty, stop and report: "Could not detect conversation slug. This command must run inside a `tq-conv-*` tmux session."

## 2. Write the response

Write a concise, Telegram-friendly response:
- Lead with the answer or result
- Use Telegram Markdown (`*bold*`, `_italic_`, `` `code` ``)
- Keep under 3500 characters (Telegram limit is 4096; slug prefix takes space)
- No filler ("I successfully...", "Sure, I can...")

Save the response text in a variable `RESPONSE_TEXT` for use in steps 3-4.

## 3. Look up reply-to ID and save to outbox

```bash
SLUG_DIR="$HOME/.tq/conversations/sessions/$SLUG"
REPLY_TO=""
if [[ -f "$SLUG_DIR/reply-to-msg-id" ]]; then
  REPLY_TO="$(cat "$SLUG_DIR/reply-to-msg-id")"
fi

mkdir -p "$SLUG_DIR/outbox"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
```

Write `RESPONSE_TEXT` to `$SLUG_DIR/outbox/${TIMESTAMP}.txt` for audit.

## 4. Send via tq-message

Write the response to a temp file to avoid quoting issues, then send:

```bash
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"
MSG_TMPFILE=$(mktemp /tmp/tq-reply-XXXXXX.txt)
cat > "$MSG_TMPFILE" <<'REPLYEOF'
<RESPONSE_TEXT here>
REPLYEOF
RESPONSE="$(cat "$MSG_TMPFILE")"
rm -f "$MSG_TMPFILE"

if [[ -n "$REPLY_TO" ]]; then
  tq-message --message "[$SLUG] $RESPONSE" --reply-to "$REPLY_TO"
else
  tq-message --message "[$SLUG] $RESPONSE"
fi
```

If `tq-message` exits non-zero, report the error and stop.

Do not explain what you are doing. Write the response and run the commands.

Related: `/tq-message` (queue task summaries), `/converse` (manage sessions)
