---
name: init
description: Initialize tq for this machine — configure workspace directories and catalog all projects. Like `claude /init` but for tq. Re-run anytime to refresh the project map.
tags: tq, setup, init, workspaces
allowed-tools: Bash, Read, Write
---

Arguments: $ARGUMENTS

Initialize tq for this machine by configuring which directories contain your projects, then scanning them to build a project catalog that tq uses when helping you craft queue tasks.

## Step 1 — Read existing workspaces config

```bash
cat ~/.tq/config/workspaces.yaml 2>/dev/null || echo "(none)"
```

If it exists, show the current `scan_dirs` list to the user.

## Step 2 — Confirm or collect workspace directories

If no config exists, tell the user:

> tq needs to know which directories contain your projects so it can suggest `cwd:` values when you create queue tasks. What directories should tq scan for projects?
>
> Common choices: `~/Sites`, `~/Projects`, `~/code`, `~/.tq/workspace`

If `$ARGUMENTS` contains directory paths, use those directly — skip asking.

If a config already exists and `$ARGUMENTS` is empty, ask:
> Your current scan directories are: [list]. Press Enter to keep them, or type new ones to replace.

Resolve all paths to absolute (expand `~`).

Always include `~/.tq/workspace` in the list unless the user explicitly excludes it. Create it if it doesn't exist:

```bash
mkdir -p ~/.tq/workspace
```

## Step 3 — Write workspaces config

Write `~/.tq/config/workspaces.yaml`:

```bash
mkdir -p ~/.tq/config
```

Format:
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

Collect all project paths into a list. For each project, detect its type by checking for key files:

```bash
# Run for each project path
ls /project/path/package.json /project/path/Cargo.toml /project/path/artisan \
   /project/path/composer.json /project/path/requirements.txt /project/path/pyproject.toml \
   /project/path/go.mod /project/path/Gemfile 2>/dev/null | head -1
```

Type mapping:
- `package.json` → `node`
- `Cargo.toml` → `rust`
- `artisan` or `composer.json` → `laravel`
- `requirements.txt` or `pyproject.toml` → `python`
- `go.mod` → `go`
- `Gemfile` → `ruby`
- none of the above → `unknown`

Project name = basename of the path.

## Step 5 — Write workspace map

Write `~/.tq/workspace-map.md`:

```markdown
# tq Workspace Map

Generated: <YYYY-MM-DD>
Scan dirs: <comma-separated list>

Use these paths as `cwd:` values in your queue YAML files.

| project | path | type |
|---------|------|------|
| myapp | /Users/kk/Sites/startups/myapp | node |
| api-server | /Users/kk/Sites/api-server | python |
```

Sort rows alphabetically by project name.

## Step 6 — Summary

Tell the user:

> **tq initialized.**
>
> Scanned N directories, found X projects.
>
> Config: `~/.tq/config/workspaces.yaml`
> Project map: `~/.tq/workspace-map.md`
>
> tq now knows about your projects. When you use `/todo` or create queue files, reference any project by its path shown above as `cwd:`.
>
> Re-run `/init` anytime to refresh after adding new projects.

If no projects were found in a scan directory, warn:
> No git repositories found in `/path` — is this the right directory?
