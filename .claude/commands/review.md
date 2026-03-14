---
name: review
description: Lint and review staged changes before commit
tags: tq, review, lint, shellcheck, code-quality, pre-commit, staged
allowed-tools: Bash(shellcheck), Bash(git), Bash(ls), Bash(which), Read
argument-hint: "[--fix]"
---

Arguments: $ARGUMENTS

Review staged changes for correctness, style, and security before committing.

## 1. Check prerequisites

```bash
git diff --staged --stat
```

If nothing is staged, report "No staged changes to review." and stop.

Check shellcheck availability:
```bash
which shellcheck 2>/dev/null || echo "MISSING"
```

## 2. Lint bash scripts

If shellcheck is available, lint all scripts in `scripts/`:
```bash
ls scripts/tq* 2>/dev/null | xargs shellcheck -S warning 2>&1 || true
```

Report any shellcheck warnings or errors. Do not stop — continue to step 3.

## 3. Read the staged diff

```bash
git diff --staged
```

## 4. Review against tq rules

Check every changed file against these criteria (in priority order):

| Priority | Check | Example Violation |
|----------|-------|-------------------|
| Critical | No credential leaks — no OAuth tokens, `.tq/` dirs, `message.yaml` | `git add .tq/morning/` |
| Critical | Hash stability — `hashlib.sha256` logic unchanged | Changed slice from `[:8]` to `[:12]` |
| High | macOS BSD `sed -i ''` (not GNU `sed -i`) | `sed -i 's/foo/bar/'` |
| High | Shebang `#!/usr/bin/env bash` in all scripts | `#!/bin/bash` |
| High | `set -euo pipefail` in every bash script | Missing `-u` flag |
| Medium | Temp files cleaned via `trap ... EXIT` | `mktemp` without `trap` |
| Medium | Naming: ALL_CAPS bash vars, snake_case Python vars | `myVar` in bash |
| Low | `os.execvp()` not replaced with `subprocess.run()` in launchers | subprocess call in launcher |

Also read `.claude/rules/anti-patterns.md` and `.claude/rules/security.md` for the full rule set.

## 5. Report findings

For each issue found, report:
- **File** and **line number**
- **Severity**: Critical / High / Medium / Low
- **Description** and **suggested fix**

If `$ARGUMENTS` contains `--fix`, apply the suggested fixes automatically (stage them but do not commit).

If no issues found, confirm: "All staged changes pass review."

Related: `/health` for system diagnostics, `/install` to update binaries, `/todo` for queue management, `/converse` for conversation sessions.
