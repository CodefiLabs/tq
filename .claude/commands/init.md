---
name: init
description: Configure workspace dirs and catalog projects
tags: tq, setup, init, workspaces, catalog, projects, scan
allowed-tools: Bash(find), Bash(ls), Bash(mkdir), Bash(test), Read, Write
argument-hint: "[dir1 dir2 ...] or [--refresh]"
---

Arguments: $ARGUMENTS

Initialize tq workspace configuration and build a project catalog.

## 1. Check existing config

Read `~/.tq/config/workspaces.yaml`. If it exists, show the current `scan_dirs`.

If `$ARGUMENTS` is `--refresh`, skip to step 4 (re-scan with existing dirs).

## 2. Collect workspace directories

| Condition | Action |
|-----------|--------|
| `$ARGUMENTS` has paths | Use those paths |
| No config, no args | Ask user; suggest `~/Sites`, `~/Projects`, `~/code` |
| Config exists, no args | Show current dirs, ask to keep or replace |

Resolve all paths to absolute (expand `~`). Always include `~/.tq/workspace`.

Validate each with `test -d`. If missing, ask: create it or skip it? If all paths are invalid after validation, stop: "No valid directories to scan."

## 3. Write config

```bash
mkdir -p ~/.tq/config ~/.tq/workspace
```

Write `~/.tq/config/workspaces.yaml`:
```yaml
# tq workspace directories — machine-local config.
# Re-run /init --refresh to rebuild the project map.
scan_dirs:
  - /absolute/path/one
  - /absolute/path/two
```

## 4. Scan for projects

For each dir in `scan_dirs`, find git repos (max 4 levels):
```bash
find /absolute/path -maxdepth 4 -name ".git" -type d 2>/dev/null | sed 's|/.git$||' | sort
```

Detect type by marker file:

| Marker | Type |
|--------|------|
| `artisan` or `composer.json` | laravel |
| `package.json` | node |
| `Cargo.toml` | rust |
| `go.mod` | go |
| `pyproject.toml` or `requirements.txt` | python |
| `Gemfile` | ruby |
| none of above | unknown |

## 5. Write workspace map

Write `~/.tq/workspace-map.md` — markdown table (project, path, type), sorted by name. Include generation date and scan dirs at top. If the write fails, stop: "Failed to write workspace map — check permissions on `~/.tq/`."

## 6. Report

Show a summary table:

| Item | Value |
|------|-------|
| Dirs scanned | `<count>` |
| Projects found | `<count>` (by type breakdown) |
| Config | `~/.tq/config/workspaces.yaml` |
| Workspace map | `~/.tq/workspace-map.md` |

Warn if any dir yielded zero repos.

Related: `/install` for binaries, `/health` for diagnostics, `/todo` for creating queues.
