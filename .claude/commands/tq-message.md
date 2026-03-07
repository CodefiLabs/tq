---
name: tq-message
description: Send a tq task completion summary to the configured messaging service. Called automatically by tq on-stop hooks.
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message)
---

Arguments: $ARGUMENTS

You have just completed a tq task. Parse the arguments to get the task hash and queue file:
- First argument: task hash (8-char string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a .yaml file)

## Steps

1. Write a 2-3 sentence summary of what you accomplished in this session. Be specific: mention what files were changed, what was fixed or built, and any notable outcome. Keep it concise enough to read in a Telegram message.

2. Call Bash to send the summary:

```bash
tq-message --task <hash> --queue <queue_file> --message "<your summary here>"
```

Replace `<hash>` with the first argument, `<queue_file>` with the second argument, and `<your summary here>` with your written summary.

Do not explain what you are doing. Just write the summary and run the command.
