---
name: converse
description: Start, stop, or check status of a Telegram conversation session with Claude Code.
tags: tq, telegram, conversation
allowed-tools: Bash(tq-converse)
---

Arguments: $ARGUMENTS

Manage a Telegram conversation session. Parse the arguments:

- No arguments or `start`: start a new conversation session
- `stop`: stop the active conversation session
- `status`: show conversation status
- `start --cwd /path`: start with a specific working directory

Run the appropriate command:

```bash
tq-converse <parsed-command> [options]
```

Show the output to the user.
