---
name: converse
description: Manage Telegram conversation sessions
tags: tq, telegram, conversation
allowed-tools: Bash(tq-converse)
argument-hint: "[start|stop|status|list|spawn <slug>]"
---

Arguments: $ARGUMENTS

Manage Telegram conversation sessions via `tq-converse`.

1. Parse the arguments according to these subcommands:
   - No arguments or `start`: start the orchestrator (auto-converse mode)
   - `stop`: stop the orchestrator
   - `stop <slug>`: stop a specific conversation session
   - `status`: show all session statuses
   - `list`: list active conversation slugs
   - `spawn <slug> [--cwd <dir>] [--desc <desc>]`: create a new child session

2. If the arguments do not match any subcommand above, report the available subcommands and stop.

3. Run the corresponding command:
   ```bash
   tq-converse <subcommand> [options]
   ```

4. If the command exits non-zero, report the error output.

5. Display the command output to the user.
