---
name: tq-reply
description: Reply to user via Telegram in conversation mode
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(tq-converse),Bash(cat),Bash(mkdir),Bash(date),Bash(echo)
---

Arguments: $ARGUMENTS

Send a response back to the Telegram user from this conversation session. No arguments needed -- the slug is auto-detected from the current tmux session.

## Steps

### 1. Detect conversation slug

Iterate over conversation session dirs, find the one whose `current-slug` matches
this tmux session name (pattern: `tq-conv-<slug>`). This identifies which
conversation this Claude instance belongs to.

```bash
SLUG=""
for dir in "$HOME/.tq/conversations/sessions"/*/; do
  if [[ -f "$dir/current-slug" ]]; then
    candidate="$(cat "$dir/current-slug")"
    session="tq-conv-${candidate}"
    # Verify this Claude instance is running inside this session's tmux
    if tmux display-message -p '#{session_name}' 2>/dev/null | grep -qF "$session"; then
      SLUG="$candidate"
      break
    fi
  fi
done
echo "Slug: $SLUG"
```

If SLUG is empty, stop and report that the conversation slug could not be detected.

### 2. Write the response

Write a concise, Telegram-friendly response based on what was just accomplished or answered:
- Lead with the answer or result
- Use basic Markdown (`*bold*`, `_italic_`, `` `code` ``)
- Keep under 4000 characters
- No filler phrases like "I successfully..." or "Sure, I can..."

### 3. Retrieve reply-to message ID and save to outbox

Look up the inbound Telegram message ID so the response threads correctly,
then persist the response to the session outbox for audit.

```bash
REPLY_TO=""
SLUG_DIR="$HOME/.tq/conversations/sessions/$SLUG"
if [[ -n "$SLUG" && -f "$SLUG_DIR/reply-to-msg-id" ]]; then
  REPLY_TO="$(cat "$SLUG_DIR/reply-to-msg-id")"
fi

mkdir -p "$SLUG_DIR/outbox"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
cat > "$SLUG_DIR/outbox/${TIMESTAMP}.txt" <<'MSGEOF'
<YOUR RESPONSE HERE>
MSGEOF
```

### 4. Record slug marker and send

Write the slug to `latest-reply-slug` for outgoing message tracking, then deliver
via `tq-message` with reply threading.

```bash
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"
tq-message --message "[$SLUG] <YOUR RESPONSE HERE>" --reply-to "$REPLY_TO"
```

Replace every `<YOUR RESPONSE HERE>` placeholder with the actual response text.

Do not explain what you are doing. Write the response and run the commands.
