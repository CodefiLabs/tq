---
name: review
description: Lint and review staged changes before commit
tags: tq, review, lint, code-quality
allowed-tools: Bash(shellcheck), Bash(git:*), Bash(ls)
---

Review staged changes for correctness, style, and security before committing.

1. Check for staged changes first:
   ```bash
   git diff --staged --stat
   ```
   If nothing is staged, report that and stop.

2. Run shellcheck on all bash scripts in `scripts/` (auto-discover, do not hardcode the list):
   ```bash
   ls scripts/tq* | xargs shellcheck
   ```
   If shellcheck is not installed, warn and skip this step.
   Report any warnings before proceeding.

3. Show the staged diff:
   ```bash
   git diff --staged
   ```

4. Review the diff against this checklist:
   - Bugs or logic errors in bash/python
   - macOS compatibility: `sed -i ''` syntax (not GNU `sed -i`), `security` CLI, tmux commands
   - Violations of rules in `.claude/rules/` (`anti-patterns.md`, `naming.md`, `security.md`)
   - Security: anything that could leak OAuth tokens, commit `.tq/` dirs, or expose credentials
   - Hash stability: no changes to `hashlib.sha256` hashing logic
   - Shebang correctness: all scripts use `#!/usr/bin/env bash`
   - Strict mode: all scripts use `set -euo pipefail`
   - Temp files cleaned via `trap ... EXIT`

5. Summarize findings as a numbered list. For each issue, state the file, line, and suggested fix. If no issues found, confirm the changes look clean.
