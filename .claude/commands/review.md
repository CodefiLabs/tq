---
name: review
description: Lint and review staged changes before commit
tags: tq, review, lint, code-quality
allowed-tools: Bash(shellcheck), Bash(git:*)
argument-hint: (no arguments)
---

Review staged changes for correctness, style, and security before committing.

1. **Check for staged changes first**:
   ```bash
   git diff --staged --name-only
   ```
   If no files are staged, report that and stop.

2. **Run shellcheck** on all bash scripts in `scripts/`:
   ```bash
   shellcheck scripts/tq scripts/tq-converse scripts/tq-message scripts/tq-telegram-poll scripts/tq-telegram-watchdog scripts/tq-cron-sync scripts/tq-setup scripts/tq-install.sh
   ```
   Report any warnings before proceeding.

3. **Show the staged diff**:
   ```bash
   git diff --staged
   ```

4. **Review the diff** against this checklist:
   - Bugs or logic errors in bash/python
   - macOS compatibility: `sed -i ''` syntax, `security` CLI, tmux commands
   - Violations of rules in `.claude/rules/` (anti-patterns, naming, security)
   - Security: OAuth token leaks, `.tq/` dirs in git, credential exposure
   - Hash stability: no changes to `hashlib.sha256` hashing logic
   - Shebang correctness: `#!/usr/bin/env bash` (never `#!/bin/bash`)
   - Hardcoded paths: use `$(command -v tq)` not `/opt/homebrew/bin/tq`

5. **Summarize findings** as a numbered list. For each issue: file, line number, and suggested fix. If clean, confirm ready to commit.
