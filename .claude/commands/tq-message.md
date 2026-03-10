---
name: tq-message
description: Write a tq task completion summary to the configured messaging service. Called automatically by tq on-stop hooks.
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message)
---

Arguments: $ARGUMENTS

You have just completed a tq task. Parse the arguments to get the task hash and queue file:
- First argument: task hash (8-char string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a .yaml file)

## Steps

1. Write a 2-3 sentence summary of what you accomplished in this session. Be specific: mention what files were changed, what was fixed or built, and any notable outcome.

2. Send the summary:

```bash
tq-message --task "<first argument>" --queue "<second argument>" --message "<your summary here>"
```

Replace the placeholders with the actual hash, queue file path, and your written summary.

Do not explain what you are doing. Just write the summary and run the command.
