---
name: converse
description: Start, stop, or check status of Telegram conversation sessions and the orchestrator.
tags: tq, telegram, conversation
allowed-tools: Bash(tq-converse)
---

Arguments: $ARGUMENTS

Manage Telegram conversation sessions. Parse the arguments:

- No arguments or `start`: start the orchestrator (auto-converse mode)
- `stop`: stop the orchestrator
- `stop <slug>`: stop a specific conversation session
- `status`: show all sessions
- `list`: list active conversation slugs
- `spawn <slug> [--cwd <dir>] [--desc <desc>]`: create a new child session

Run the appropriate command:

```bash
tq-converse <parsed-command> [options]
```

Show the output to the user.
