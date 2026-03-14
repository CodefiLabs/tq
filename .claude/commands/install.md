---
name: install
description: Install tq scripts to PATH via symlinks
tags: tq, install, setup, path
allowed-tools: Bash(bash), Bash(which), Bash(ls)
---

Install the tq CLI tools by running the install script and verifying the result.

1. Run the install script:
   ```bash
   bash "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
   ```

2. If the script exits non-zero, report the error output and stop.

3. Verify installation succeeded by checking each expected binary:
   ```bash
   which tq && which tq-converse && which tq-message && which tq-telegram-poll
   ```

4. Confirm the symlink target is correct:
   ```bash
   ls -la "$(which tq)"
   ```

5. Report the install location and which scripts were linked. If any binary is missing from PATH, warn the user.
