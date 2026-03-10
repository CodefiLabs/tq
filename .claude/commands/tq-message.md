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

1. Write a rich, specific summary of what you accomplished. Structure it as:
   - **Lead sentence**: what was done + specific output (e.g. "Wrote a 106-line guide at docs/demo-video-tips.md")
   - **Numbered list** of what was built/covered/fixed (3-6 items), each with a brief description after an em dash
   - Keep it tight — no filler like "I successfully..." or "In this session..."

   Example format:
   ```
   Wrote a 106-line demo video guide at docs/demo-video-tips.md in app-vibeathon-us. The guide covers:
   1. Why the video matters — frames it as judges' main window into the project
   2. What judges look for — 5 evaluation lenses with concrete criteria
   3. Video structure — a 5-minute template: Hook → Live Demo → Technical Walk → Close
   4. Do This / Avoid This — actionable dos/don'ts from judging criteria
   5. Recording tips — tools, formats, audio quality, the 100MB upload limit
   6. Uploading — platform flow including the code-first requirement and S3 upload
   ```

2. Send the summary:

```bash
tq-message --task "<first argument>" --queue "<second argument>" --message "<your summary here>"
```

Replace the placeholders with the actual hash, queue file path, and your written summary.

Do not explain what you are doing. Just write the summary and run the command.
