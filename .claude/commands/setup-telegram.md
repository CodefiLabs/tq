---
name: setup-telegram
description: Configure Telegram bot and notifications for tq
tags: tq, setup, telegram, notify
allowed-tools: Bash(curl), Bash(mkdir), Bash(cat), Bash(python3), Bash(tq-setup), Write
argument-hint: [bot-token]
---

Arguments: $ARGUMENTS

Guide the user through Telegram notification setup interactively. If `$ARGUMENTS` contains a bot token, skip step 1.

## Step 1 — Get bot token

Instruct the user to create a bot via @BotFather in Telegram (`/newbot`), then paste the token (format: `123456:ABCdef...`). Wait for input.

## Step 2 — Discover user ID

Ask the user to send any message to their new bot, then confirm. Run:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```
Extract `from.id` from the first message. If no messages found, ask them to send one and retry.

## Step 3 — Content type

Ask which notification type to use on task completion:
- `status` -- task name, done/failed, duration (default)
- `summary` -- Claude writes a 2-3 sentence digest (requires live session)

Default to `status` if unspecified.

## Step 4 — Test and write config

1. Send a test message via the Telegram API. If it fails, report the error and stop.
2. On success, run `mkdir -p ~/.tq ~/.tq/workspace ~/.tq/logs ~/.tq/config` and write `~/.tq/config/message.yaml`:

```yaml
default_service: telegram
content: <CONTENT_TYPE>

telegram:
  bot_token: "<TOKEN>"
  user_id: "<USER_ID>"
```

## Step 5 — Final instructions

Tell the user the config path (`~/.tq/config/message.yaml`) and instruct them to add the polling cron entry:
```
* * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1
```
