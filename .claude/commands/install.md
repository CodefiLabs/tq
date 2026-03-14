---
name: install
description: Install tq scripts to PATH via symlinks
tags: tq, install, setup, path
allowed-tools: Bash(bash), Bash(which), Bash(ls)
argument-hint: (no arguments)
---

Install all tq CLI tools by running the install script and verifying the result.

1. Confirm this is a git repo and the install script exists:
   ```bash
   ls "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
   ```
   If either command fails, report the error and stop.

2. Run the install script:
   ```bash
   bash "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
   ```
   If it exits non-zero, report the error output and stop.

3. Verify installation by checking every expected binary:
   ```bash
   for BIN in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
     which "$BIN" 2>/dev/null || echo "MISSING: $BIN"
   done
   ```

4. Confirm at least one symlink target is correct:
   ```bash
   ls -la "$(which tq)"
   ```

5. Report the install location and which scripts were linked. If any binary is missing from PATH, warn the user.

Related: `/health` to verify full system status, `/setup-telegram` to configure Telegram integration.
