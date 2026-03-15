---
name: setup-telegram
description: Configure Telegram bot and notifications
tags: tq, setup, telegram, notify, conversation
allowed-tools: Bash(curl), Bash(mkdir), Bash(chmod), Bash(cat), Bash(test), Bash(python3), Bash(tq-setup), Bash(tq-telegram-watchdog), Bash(crontab), Write, Read
argument-hint: [bot-token]
---

Arguments: $ARGUMENTS

Guide the user through Telegram notification setup interactively. If `$ARGUMENTS` contains a bot token, skip step 1.

## Step 0 — Check existing config

Read `~/.tq/config/message.yaml` if it exists. If present, show the current `telegram.bot_token` (masked: first 5 chars + `...`) and `telegram.user_id`. Ask the user whether to reconfigure or keep the existing setup. If keeping, skip to step 5.

## Step 1 — Get bot token

Instruct the user to create a bot via @BotFather in Telegram (`/newbot`), then paste the token. Wait for input.

Validate the token format matches `\d+:[A-Za-z0-9_-]{35,}`. If invalid, show the expected format (`123456:ABCdef...`) and ask again.

## Step 2 — Discover user ID

Ask the user to send any message to their new bot, then confirm. Run:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```
Parse the JSON response with:
```bash
python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r['result'][0]['message']['from']['id'] if r.get('result') else '')"
```
Extract `from.id` from the first message. If no messages found, ask the user to send a message to the bot and retry (up to 3 attempts). If still empty after retries, ask the user to paste their numeric user ID manually.

## Step 3 — Content type

Ask which notification type to use on task completion:
- `status` -- task name, done/failed, duration (default)
- `summary` -- Claude writes a 2-3 sentence digest (requires live session)

Default to `status` if unspecified.

## Step 4 — Test and write config

1. Send a test message via the Telegram API:
   ```bash
   curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id="<USER_ID>" -d text="tq setup test -- Telegram notifications are working."
   ```
   Parse the response to check `"ok":true`. If it fails, report the error message from the API response and stop.

2. On success, run `mkdir -p ~/.tq ~/.tq/workspace ~/.tq/logs ~/.tq/config` and write `~/.tq/config/message.yaml`:

   ```yaml
   default_service: telegram
   content: <CONTENT_TYPE>

   telegram:
     bot_token: "<TOKEN>"
     user_id: "<USER_ID>"
   ```

3. Restrict file permissions (config contains the bot token):
   ```bash
   chmod 600 ~/.tq/config/message.yaml
   ```

## Step 5 — Install Telegram polling

Install the polling cron entry via the watchdog (preferred) or manually:

```bash
tq-telegram-watchdog
```

If `tq-telegram-watchdog` is not on PATH, fall back to manual cron installation:
```bash
mkdir -p ~/.tq/logs
(crontab -l 2>/dev/null | grep -v "tq-telegram-poll"; echo "* * * * * $(command -v tq-telegram-poll) >> ~/.tq/logs/tq-telegram.log 2>&1") | crontab -
```

Verify the cron entry was installed:
```bash
crontab -l 2>/dev/null | grep tq-telegram-poll
```

## Step 6 — Summary

Report:
- Config path: `~/.tq/config/message.yaml` (permissions: 600)
- Polling: active via cron or launchd
- Test message: sent successfully

Suggest next steps:
- Run `/converse start` to launch conversation mode via Telegram
- Run `/health` to verify the full system
