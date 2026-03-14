---
name: init
description: Configure workspace dirs and catalog projects
tags: tq, setup, init, workspaces
allowed-tools: Bash(cat), Bash(find), Bash(ls), Bash(mkdir), Bash(test), Read, Write
argument-hint: [workspace-dirs...]
---

Arguments: $ARGUMENTS

Initialize tq by configuring workspace directories and scanning them to build a project catalog for queue task creation.

## Step 1 — Read existing workspaces config

Read `~/.tq/config/workspaces.yaml`. If it exists, show the current `scan_dirs` list.

## Step 2 — Confirm or collect workspace directories

- If `$ARGUMENTS` contains directory paths, use those directly.
- If no config exists and no arguments, ask the user which directories to scan (suggest `~/Sites`, `~/Projects`, `~/code`, `~/.tq/workspace`).
- If config exists and no arguments, show current dirs and ask to keep or replace.

Resolve all paths to absolute (expand `~`). Always include `~/.tq/workspace` unless explicitly excluded. Create it with `mkdir -p` if needed.

Validate each directory exists (`test -d`). If a directory does not exist, warn the user and ask whether to create it or skip it.

## Step 3 — Write workspaces config

Run `mkdir -p ~/.tq/config`, then write `~/.tq/config/workspaces.yaml`:

```yaml
# tq workspace directories — machine-local config.
# Edit this file, then re-run /init to refresh the project map.
scan_dirs:
  - /absolute/path/one
  - /absolute/path/two
```

## Step 4 — Scan for projects

For each directory in `scan_dirs`, find git repositories (max 4 levels deep):
```bash
find /absolute/path -maxdepth 4 -name ".git" -type d 2>/dev/null | sed 's|/.git$||' | sort
```

Detect project type by checking for marker files (`package.json` -> node, `Cargo.toml` -> rust, `artisan`/`composer.json` -> laravel, `requirements.txt`/`pyproject.toml` -> python, `go.mod` -> go, `Gemfile` -> ruby, otherwise `unknown`). Project name = basename of path.

## Step 5 — Write workspace map

Write `~/.tq/workspace-map.md` with a markdown table (columns: project, path, type), sorted alphabetically by project name. Include generation date and scan dirs at the top.

## Step 6 — Summary

Report: number of directories scanned, projects found, paths to config and workspace map. Note that `workspace-map.md` is always overwritten (not merged) on each run. Warn if any scan directory yielded zero git repositories.

Related: `/install` to ensure tq binaries are on PATH, `/health` to verify the full system, `/todo` to create queue tasks using the workspace map.
