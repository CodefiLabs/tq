---
name: tq-reply
description: Reply to Telegram user from conversation session
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(tq-converse),Bash(cat),Bash(mkdir),Bash(date),Bash(echo)
argument-hint: (no arguments)
---

Send a response back to the Telegram user from this conversation session. The slug is auto-detected.

## 1. Detect conversation slug

Read the marker file written by tq-converse when routing a message to this session:

```bash
SLUG_DIR="$HOME/.tq/conversations/sessions"
SLUG=""

# Primary: read marker file written by tq-converse route
for dir in "$SLUG_DIR"/*/; do
  if [[ -f "$dir/current-slug" ]]; then
    candidate="$(cat "$dir/current-slug")"
    # Verify this Claude instance is inside this session's tmux
    if tmux display-message -p '#{session_name}' 2>/dev/null | grep -qF "tq-conv-${candidate}"; then
      SLUG="$candidate"
      break
    fi
  fi
done

# Fallback: extract slug from tmux session name (tq-conv-<slug>)
if [[ -z "$SLUG" ]]; then
  SESSION_NAME="$(tmux display-message -p '#{session_name}' 2>/dev/null)"
  if [[ "$SESSION_NAME" =~ ^tq-conv-(.+)$ ]]; then
    SLUG="${BASH_REMATCH[1]}"
  fi
fi

echo "Slug: $SLUG"
```

If SLUG is empty, stop and report: "Could not detect conversation slug. Are you running inside a tq-conv-* tmux session?"

## 2. Write the response

Write a concise, Telegram-friendly response:
- Lead with the answer or result
- Use basic Markdown (`*bold*`, `_italic_`, `` `code` ``)
- Keep under 3500 characters (Telegram limit is 4096; leave room for slug prefix)
- No filler phrases ("I successfully...", "Sure, I can...")

## 3. Save to outbox and send

```bash
SLUG_DIR="$HOME/.tq/conversations/sessions/$SLUG"

# Get reply-to message ID for threading
REPLY_TO=""
if [[ -f "$SLUG_DIR/reply-to-msg-id" ]]; then
  REPLY_TO="$(cat "$SLUG_DIR/reply-to-msg-id")"
fi

# Save to outbox
mkdir -p "$SLUG_DIR/outbox"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
cat > "$SLUG_DIR/outbox/${TIMESTAMP}.txt" <<'MSGEOF'
<RESPONSE>
MSGEOF

# Record slug marker and send
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"

# Send with reply threading (omit --reply-to if no message ID)
if [[ -n "$REPLY_TO" ]]; then
  tq-message --message "[$SLUG] <RESPONSE>" --reply-to "$REPLY_TO"
else
  tq-message --message "[$SLUG] <RESPONSE>"
fi
```

Replace `<RESPONSE>` with the actual response text. Do not explain what you are doing.
