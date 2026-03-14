---
name: tq-reply
description: Reply to Telegram user from conversation session
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(tq-converse),Bash(cat),Bash(mkdir),Bash(date)
---

Arguments: $ARGUMENTS

No arguments needed -- the conversation slug is auto-detected from the current tmux session.

## 1. Detect conversation slug

Find which conversation this Claude instance belongs to by matching the tmux session name against registered slugs:

```bash
SLUG=""
for DIR in "$HOME/.tq/conversations/sessions"/*/; do
  [[ -f "$DIR/current-slug" ]] || continue
  CANDIDATE="$(cat "$DIR/current-slug")"
  SESSION="tq-conv-${CANDIDATE}"
  if tmux display-message -p '#{session_name}' 2>/dev/null | grep -qF "$SESSION"; then
    SLUG="$CANDIDATE"
    break
  fi
done
echo "Slug: $SLUG"
```

If SLUG is empty, stop and report: "Could not detect conversation slug. This command must run inside a `tq-conv-*` tmux session."

## 2. Write the response

Write a concise, Telegram-friendly response based on what was just accomplished or answered:
- Lead with the answer or result
- Use Telegram Markdown (`*bold*`, `_italic_`, `` `code` ``)
- Keep under 3500 characters (Telegram limit is 4096; slug prefix takes space)
- No filler ("I successfully...", "Sure, I can...")

Store the response text mentally -- it will be used in steps 3 and 4.

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

Write the response text to `$SLUG_DIR/outbox/${TIMESTAMP}.txt` for audit.

## 4. Send via tq-message

```bash
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"
RESPONSE='<response text here>'
tq-message --message "[$SLUG] $RESPONSE" --reply-to "$REPLY_TO"
```

If `tq-message` exits non-zero, report the error.

Do not explain what you are doing. Write the response and run the commands.

> Related: `/tq-message` (queue task summaries), `/converse` (manage sessions)
