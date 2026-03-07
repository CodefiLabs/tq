---
name: setup-telegram
description: Configure Telegram notifications for tq. Guides you through bot token setup and writes ~/.tq/message.yaml.
tags: tq, setup, telegram, notify
allowed-tools: Bash(curl),Bash(mkdir),Bash(cat),Bash(python3),Bash(tq-setup)
---

Arguments: $ARGUMENTS

Help the user configure Telegram notifications for tq interactively.

## Step 1 — Get bot token

Tell the user:

> To set up Telegram notifications, you need a bot token from @BotFather.
> 1. Open Telegram and search for @BotFather
> 2. Send `/newbot` and follow the prompts
> 3. Copy the token it gives you (looks like `123456:ABCdef...`)
>
> Paste your bot token here:

Wait for the user to paste their token.

## Step 2 — Discover user ID

Tell the user:

> Now send any message to your new bot in Telegram, then tell me when you've done it.

Once they confirm, run:

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```

Parse the response to extract `from.id` from the first message. Tell the user their user ID.

If no message is found, ask them to send a message to the bot and try again.

## Step 3 — Content type

Ask:

> What type of notification do you want when a tq task finishes?
> - `status` — task name, done/failed, duration (default, always works)
> - `summary` — Claude writes a 2-3 sentence digest of what it accomplished (requires live session)

Default to `status` if they don't specify or say "default".

## Step 4 — Write config and test

Send a test message:

```bash
curl -s -X POST \
  "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<USER_ID>" \
  --data-urlencode "text=tq is configured. Notifications are working." \
  -d "parse_mode=Markdown"
```

If it fails, report the error and stop.

If it succeeds, write the config:

```bash
mkdir -p ~/.tq ~/.tq/workspace ~/.claude/logs
cat > ~/.tq/message.yaml <<EOF
default_service: telegram
content: <CONTENT_TYPE>

telegram:
  bot_token: "<TOKEN>"
  user_id: "<USER_ID>"
EOF
```

## Step 5 — Final instructions

Tell the user:

> Config written to ~/.tq/message.yaml.
>
> To receive your Telegram messages as tq tasks, add this to your crontab (`crontab -e`):
> ```
> * * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.claude/logs/tq-telegram.log 2>&1
> ```
>
> tq will now notify you via Telegram when tasks complete.
