---
name: converse
description: Manage Telegram conversation sessions
tags: tq, telegram, conversation, orchestrator
allowed-tools: Bash(tq-converse), Bash(which)
argument-hint: "[start|stop|status|list|spawn <slug>]"
---

Arguments: $ARGUMENTS

Manage Telegram conversation sessions via `tq-converse`.

1. Verify `tq-converse` is installed:
   ```bash
   which tq-converse
   ```
   If missing, suggest running `/install` first and stop.

2. Parse the arguments according to these subcommands:
   - No arguments or `start`: start the orchestrator (`tq-converse start`)
   - `stop`: stop the orchestrator (`tq-converse stop`)
   - `stop <slug>`: stop a specific conversation session (`tq-converse stop <slug>`)
   - `status`: show all session statuses (`tq-converse status`)
   - `list`: list active conversation slugs (`tq-converse list`)
   - `spawn <slug> [--cwd <dir>] [--desc <desc>]`: create a new child session (`tq-converse spawn <slug> ...`)

3. If the arguments do not match any subcommand above, report the available subcommands and stop.

4. Run the corresponding command. If it exits non-zero, report the error output.

5. Display the command output to the user.

Related: `/setup-telegram` to configure Telegram bot, `/pause` and `/schedule` for queue scheduling.
