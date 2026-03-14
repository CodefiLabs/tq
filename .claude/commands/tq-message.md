---
name: tq-message
description: Send task completion summary via messaging service
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message)
argument-hint: [task-hash] [queue-file]
---

Arguments: $ARGUMENTS

Parse arguments immediately:
- First argument: task hash (8-char hex string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a `.yaml` file)

If either argument is missing or malformed, stop and report the error.

## Steps

1. Write a rich, specific summary of what was accomplished. Structure it as:
   - **Lead sentence**: state what was done + specific output (e.g. "Wrote a 106-line guide at docs/demo-video-tips.md")
   - **Numbered list**: 3-6 items of what was built/covered/fixed, each with a brief description after an em dash
   - Keep it tight. No filler like "I successfully..." or "In this session..."

   Example:
   ```
   Wrote a 106-line demo video guide at docs/demo-video-tips.md in app-vibeathon-us. The guide covers:
   1. Why the video matters — frames it as judges' main window into the project
   2. What judges look for — 5 evaluation lenses with concrete criteria
   3. Video structure — a 5-minute template: Hook > Live Demo > Technical Walk > Close
   4. Do This / Avoid This — actionable dos/don'ts from judging criteria
   5. Recording tips — tools, formats, audio quality, the 100MB upload limit
   6. Uploading — platform flow including the code-first requirement and S3 upload
   ```

2. Send the summary by running:

   ```bash
   tq-message --task "<TASK_HASH>" --queue "<QUEUE_FILE>" --message "<SUMMARY>"
   ```

   Replace `<TASK_HASH>`, `<QUEUE_FILE>`, and `<SUMMARY>` with the parsed arguments and written summary.

Do not explain what you are doing. Write the summary and run the command.
