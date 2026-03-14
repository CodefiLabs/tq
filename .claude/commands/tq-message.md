---
name: tq-message
description: Send task completion summary via messaging
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message), Bash(cat), Bash(rm)
argument-hint: [task-hash] [queue-file]
---

Arguments: $ARGUMENTS

Parse arguments immediately:
- First argument: task hash (8-char hex string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a `.yaml` file)

If either argument is missing or malformed, stop and report the error.

## Steps

1. Write a rich, specific summary of what was accomplished. Structure it as:
   - **Lead sentence**: what was done + specific output (e.g. "Wrote a 106-line guide at docs/demo-video-tips.md")
   - **Numbered list**: 3-6 items of what was built/covered/fixed, each with a brief em dash description
   - No filler ("I successfully...", "In this session...")
   - Keep under 3500 characters (Telegram limit is 4096; slug prefix and metadata consume the rest)

   Example:
   ```
   Wrote a 106-line demo video guide at docs/demo-video-tips.md. The guide covers:
   1. Why the video matters — frames it as judges' main window into the project
   2. What judges look for — 5 evaluation lenses with concrete criteria
   3. Video structure — a 5-minute template: Hook > Live Demo > Technical Walk > Close
   ```

2. Write the summary to a temp file and send via heredoc to avoid quoting issues:

   ```bash
   MSG_TMPFILE=$(mktemp /tmp/tq-msg-XXXXXX)
   cat > "$MSG_TMPFILE" <<'MSGEOF'
   <SUMMARY>
   MSGEOF
   tq-message --task "<TASK_HASH>" --queue "<QUEUE_FILE>" --message "$(cat "$MSG_TMPFILE")"
   rm -f "$MSG_TMPFILE"
   ```

   Replace `<TASK_HASH>`, `<QUEUE_FILE>`, and `<SUMMARY>` with actual values.

Do not explain what you are doing. Write the summary and run the command.
