---
name: review
description: Lint and review staged changes before commit
tags: tq, review, lint, code-quality
allowed-tools: Bash(shellcheck), Bash(git:*)
---

Review staged changes for correctness, style, and security before committing.

1. Run shellcheck on all bash scripts in `scripts/`:
   ```bash
   shellcheck scripts/tq scripts/tq-converse scripts/tq-message scripts/tq-telegram-poll scripts/tq-telegram-watchdog scripts/tq-cron-sync scripts/tq-setup scripts/tq-install.sh
   ```
   Fix or report any warnings before proceeding.

2. Show the staged diff:
   ```bash
   git diff --staged
   ```

3. Review the diff against this checklist:
   - Bugs or logic errors in bash/python
   - macOS compatibility: `sed -i ''` syntax, `security` CLI, tmux commands
   - Violations of naming, security, or anti-pattern rules in `.claude/rules/` (`anti-patterns.md`, `naming.md`, `security.md`)
   - Security: anything that could leak OAuth tokens, commit `.tq/` dirs, or expose credentials
   - Hash stability: no changes to the `hashlib.sha256` hashing logic
   - Shebang correctness: all scripts use `#!/usr/bin/env bash`

4. If no files are staged, report that and stop.

5. Summarize findings as a numbered list. For each issue, state the file, line, and suggested fix.
