---
name: tq-reply
description: Reply to Telegram from conversation session
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message), Bash(mkdir), Bash(date), Bash(tmux), Read, Write
argument-hint: "(no args -- auto-detects slug)"
---

Arguments: $ARGUMENTS

Send the current response back to the Telegram user. No arguments needed.

## 1. Detect conversation slug

Use the Read tool to read `.tq-converse.md` in the current directory. The marker is written by `tq-converse` when spawning the session and contains a line like `Your conversation slug is: **<slug>**`. Extract the slug from between the `**` markers.

Fallback: get the current tmux session name and derive the slug:
```bash
tmux display-message -p '#{session_name}' 2>/dev/null
```
If session name matches `tq-conv-<slug>`, extract `<slug>` by stripping the `tq-conv-` prefix.

If SLUG is empty, stop: "Could not detect conversation slug. Run this inside a `tq-conv-*` session or ensure `.tq-converse.md` exists."

## 2. Write the response

Write a concise Telegram-friendly response:
- Lead with the answer, not reasoning
- Telegram Markdown: `*bold*`, `_italic_`, `` `code` ``
- Max 3500 chars (4096 limit minus slug prefix)
- No filler phrases

## 3. Save and send

Set `SLUG_DIR="$HOME/.tq/conversations/sessions/$SLUG"`.

Use Read to check `$SLUG_DIR/reply-to-msg-id`. If it exists, capture the message ID as `REPLY_TO`.

```bash
mkdir -p "$SLUG_DIR/outbox"
```

Use Write to save the slug to `$SLUG_DIR/current-slug` and `$HOME/.tq/conversations/latest-reply-slug`.

Use Write to save the response to `$SLUG_DIR/outbox/<timestamp>.txt` (use `date +%Y%m%d-%H%M%S` for the filename). Then send:

```bash
tq-message --message "[$SLUG] <response>" --reply-to "$REPLY_TO"
```

If `tq-message` exits non-zero, report the error and stop.

Related: `/tq-message` (queue summaries), `/converse` (manage sessions)
