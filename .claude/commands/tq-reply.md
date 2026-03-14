---
name: tq-reply
description: Send a response back to the user via Telegram in conversation mode.
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(cat),Bash(mkdir),Bash(date)
---

Arguments: $ARGUMENTS

You are in Telegram conversation mode. Send your response back to the user.

## Steps

1. Write a concise, Telegram-friendly response based on what you just accomplished or answered.
   - Lead with the answer or result
   - Use basic Markdown (*bold*, _italic_, `code`)
   - Keep it under 4000 characters
   - No filler phrases like "I successfully..." or "Sure, I can..."
   - If the work involved code changes, mention the specific files and what changed

2. Save the response and deliver it:

```bash
mkdir -p "$HOME/.tq/conversations/active/outbox"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
cat > "$HOME/.tq/conversations/active/outbox/${TIMESTAMP}.txt" <<'MSGEOF'
<YOUR RESPONSE HERE>
MSGEOF
```

3. Send via Telegram:

```bash
tq-message --message "<YOUR RESPONSE HERE>"
```

Replace `<YOUR RESPONSE HERE>` with your actual response text. Make sure to properly escape any special characters for the shell.

Do not explain what you are doing. Just write the response and run the commands.
