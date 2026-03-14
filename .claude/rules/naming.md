# Naming Conventions

## Bash Variables

ALL_CAPS for all shell variables, no exceptions:

```bash
QUEUE_FILE    STATE_DIR    QUEUE_BASENAME
SESSION_BASE  EPOCH_SUFFIX WIN_IDX
PARSE_OUTPUT  PARSE_SCRIPT FIRST_LINE
```

## Bash Files

- Executable CLI scripts: `kebab-case`, no extension — `tq`
- Installer scripts: `kebab-case.sh` — `tq-install.sh`
- Shebang: always `#!/usr/bin/env bash` (never `#!/bin/bash`)

## Python Variables (embedded)

snake_case throughout:

```python
queue_file   state_dir    sessions_dir
prompt_file  block_lines  safe_first_line
launcher_file  stop_hook  captured_env
```

No CONSTANT_CAPS in Python — all variables are lowercase even for paths and constants.

## Generated Artifacts

All keyed by 8-char SHA-256 digest of the prompt content:

| Artifact | Pattern | Example |
|----------|---------|---------|
| Task state file | `<hash>` (no extension) | `a1b2c3d4` |
| Prompt file | `<hash>.prompt` | `a1b2c3d4.prompt` |
| Launcher script | `<hash>.launch.py` | `a1b2c3d4.launch.py` |

## tmux Session and Window Names

### Queue Mode
- Session: `tq-<first-3-words-slug>-<last-6-digits-of-epoch>` — e.g., `tq-fix-the-login-451234`
- Window: `<first-2-words-slug>` truncated to 15 chars — e.g., `fix-the`
- Slugification: lowercase, replace non-alphanumeric with `-`, strip leading/trailing dashes

### Conversation Mode
- Orchestrator session: `tq-orchestrator` (fixed name, always exactly this)
- Child sessions: `tq-conv-<slug>` — e.g., `tq-conv-fix-auth`, `tq-conv-refactor-payments`
- Window name: same as slug — e.g., `fix-auth`
- Slugs: short kebab-case, 2-4 words, chosen by the orchestrator — e.g., `fix-auth-bug`, `update-docs`

## Queue and State Directories

- Queue files: `~/.tq/queues/<name>.yaml` — e.g., `morning.yaml`
- Task state dir: `<queue-dir>/.tq/<queue-basename>/` — e.g., `.tq/morning/`
- Session dir: `~/.tq/sessions/<hash>/` — e.g., `~/.tq/sessions/a1b2c3d4/`

## Conversation Directories

- Conversation root: `~/.tq/conversations/`
- Registry: `~/.tq/conversations/registry.json`
- Orchestrator: `~/.tq/conversations/orchestrator/`
- Session dirs: `~/.tq/conversations/sessions/<slug>/` — e.g., `sessions/fix-auth/`
- Inbox/outbox: `sessions/<slug>/inbox/`, `sessions/<slug>/outbox/`
- Message files: `<YYYYMMDD-HHMMSS>.txt` — timestamped plaintext

## Documentation Files

- Claude skill definitions: `SKILL.md` (UPPER.md)
- Reference docs: `kebab-case.md` — `cron-expressions.md`, `session-naming.md`
