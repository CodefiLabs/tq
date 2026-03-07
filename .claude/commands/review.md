---
description: Review staged changes before committing
---
0. Run shellcheck first: `shellcheck scripts/tq scripts/tq-install.sh`
   Fix any warnings before reviewing the checklist below.

Review the staged changes (git diff --staged) for:
1. Bugs or logic errors in bash/python
2. macOS-specific compatibility (sed -i '' syntax, security CLI, tmux)
3. Violations of naming, security, or anti-pattern rules in `CLAUDE.md` and `.claude/rules/` (`anti-patterns.md`, `naming.md`, `security.md`)
4. Security issues — especially anything that could leak OAuth tokens or commit .tq/ dirs
Summarize findings and suggest fixes.
