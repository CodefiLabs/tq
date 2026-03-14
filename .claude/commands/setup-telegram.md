---
name: setup-telegram
description: Configure Telegram bot and notifications
tags: tq, setup, telegram, notify
allowed-tools: Bash(curl), Bash(mkdir), Bash(chmod), Bash(cat), Bash(python3), Bash(tq-setup), Bash(command), Read, Write
argument-hint: [bot-token]
---

Arguments: $ARGUMENTS

Guide the user through Telegram notification setup interactively. If `$ARGUMENTS` contains a bot token, skip step 1.

## Step 0 — Pre-flight checks

1. Verify `tq-message` is installed: `command -v tq-message`. If missing, suggest `/install` and stop.
2. Check for existing config: `cat ~/.tq/config/message.yaml 2>/dev/null`. If it exists, show current config and ask: "Overwrite existing Telegram config? (y/n)". If no, stop.

## Step 1 — Get bot token

Instruct the user to create a bot via @BotFather in Telegram (`/newbot`), then paste the token (format: `123456:ABCdef...`). Wait for input.

## Step 2 — Discover user ID

Ask the user to send any message to their new bot, then confirm. Run:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```
Extract `from.id` from the first message result. If no messages found, ask them to send one and retry (up to 3 attempts, then stop with troubleshooting advice).

## Step 3 — Content type

Ask which notification type to use on task completion:
- `status` — task name, done/failed, duration (default)
- `summary` — Claude writes a 2-3 sentence digest (requires live session)

Default to `status` if unspecified.

## Step 4 — Test and write config

1. Send a test message via the Telegram API:
   ```bash
   curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id="<USER_ID>" -d text="tq setup test — notifications working"
   ```
   If it fails, report the error and stop.

2. Create directories and write config:
   ```bash
   mkdir -p ~/.tq/config ~/.tq/workspace ~/.tq/logs
   ```

3. Write `~/.tq/config/message.yaml`:
   ```yaml
   default_service: telegram
   content: <CONTENT_TYPE>

   telegram:
     bot_token: "<TOKEN>"
     user_id: "<USER_ID>"
   ```

4. Set restrictive permissions (file contains bot token):
   ```bash
   chmod 600 ~/.tq/config/message.yaml
   ```

## Step 5 — Polling setup

Tell the user to add the polling cron entry for receiving Telegram messages:
```
* * * * * $(command -v tq-telegram-poll) >> ~/.tq/logs/tq-telegram.log 2>&1
```

Confirm config path: `~/.tq/config/message.yaml`

Related: `/converse`, `/tq-reply`, `/health`
