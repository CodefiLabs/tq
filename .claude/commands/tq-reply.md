---
name: tq-reply
description: Send a response back to the user via Telegram in conversation mode.
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(tq-converse),Bash(cat),Bash(mkdir),Bash(date),Bash(echo)
---

Arguments: $ARGUMENTS

You are in Telegram conversation mode. Send your response back to the user.

## Steps

1. Detect your conversation slug. Check for a `current-slug` file:

```bash
SLUG=""
for dir in "$HOME/.tq/conversations/sessions"/*/; do
  if [[ -f "$dir/current-slug" ]]; then
    candidate="$(cat "$dir/current-slug")"
    session="tq-conv-${candidate}"
    # Check if WE are running in this session's tmux
    if tmux display-message -p '#{session_name}' 2>/dev/null | grep -qF "$session"; then
      SLUG="$candidate"
      break
    fi
  fi
done
echo "Slug: $SLUG"
```

2. Write a concise, Telegram-friendly response based on what you just accomplished or answered.
   - Lead with the answer or result
   - Use basic Markdown (*bold*, _italic_, `code`)
   - Keep under 4000 characters
   - No filler phrases like "I successfully..." or "Sure, I can..."

3. Get the reply-to message ID and save your response:

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

4. Write slug marker for outgoing message tracking, then send:

```bash
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"
tq-message --message "[$SLUG] <YOUR RESPONSE HERE>" --reply-to "$REPLY_TO"
```

Replace `<YOUR RESPONSE HERE>` with your actual response text. Do not explain what you are doing — just write the response and run the commands.
