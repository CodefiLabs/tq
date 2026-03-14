---
name: install
description: Install tq scripts to PATH via symlinks
tags: tq, install, setup, path, symlinks, binaries
allowed-tools: Bash(bash), Bash(which), Bash(ls), Bash(git)
argument-hint: "[--check]"
---

Arguments: $ARGUMENTS

Install all tq CLI tools by running the install script. If `$ARGUMENTS` contains `--check`, only verify installation without running the installer.

## 1. Locate install script

```bash
git rev-parse --show-toplevel 2>/dev/null
```

If not in a git repo, stop: "Run this from the tq repository."

```bash
ls "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
```

If missing, stop: "Install script not found at `scripts/tq-install.sh`."

## 2. Run installer (skip if `--check`)

```bash
bash "$(git rev-parse --show-toplevel)/scripts/tq-install.sh"
```

If it exits non-zero, report the error output and stop.

## 3. Verify all 7 binaries

```bash
MISSING=0
for BIN in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
  if which "$BIN" >/dev/null 2>&1; then
    echo "OK: $BIN -> $(which "$BIN")"
  else
    echo "MISSING: $BIN"
    MISSING=$((MISSING + 1))
  fi
done
```

## 4. Verify symlink integrity

```bash
ls -la "$(which tq 2>/dev/null)" 2>/dev/null
```

Confirm the symlink points to the tq repository's `scripts/` directory.

## 5. Report

Display a summary table:

| Binary | Status | Path |
|--------|--------|------|
| tq | OK | /opt/homebrew/bin/tq -> .../scripts/tq |
| ... | ... | ... |

If any binaries are missing, suggest checking `$PATH` includes `/opt/homebrew/bin` or the `TQ_INSTALL_DIR` used during install.

Related: `/health` for full system diagnostics, `/setup-telegram` for Telegram, `/init` for workspace setup.
