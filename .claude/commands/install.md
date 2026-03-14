---
name: install
description: Install tq scripts to PATH via symlinks
tags: tq, install, setup, path
allowed-tools: Bash(bash), Bash(command), Bash(ls)
argument-hint: (no arguments)
---

Install the tq CLI tools by running the install script and verifying the result.

1. Run the install script:
   ```bash
   bash "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
   ```
   If `git rev-parse` fails (not in a git repo), stop and report the error.

2. If the script exits non-zero, report the error output and stop.

3. Verify all 7 expected binaries are installed:
   ```bash
   for bin in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
     command -v "$bin" || echo "MISSING: $bin"
   done
   ```

4. Confirm the symlink target is correct:
   ```bash
   ls -la "$(command -v tq)"
   ```

5. Report the install location and which scripts were linked. If any binary is missing from PATH, warn the user and suggest checking `$PATH`.

Related: `/health`
