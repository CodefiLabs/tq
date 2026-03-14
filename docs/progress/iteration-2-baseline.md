# Iteration 2 Baseline Snapshot

Captured: 2026-03-14

This document contains the complete contents of all 17 files from `.claude/commands/` (13 files) and `skills/tq/` (SKILL.md + 3 reference files) as they exist at the start of iteration 2.

---

## Table of Contents

### Commands (13 files)
1. [converse.md](#converse)
2. [health.md](#health)
3. [init.md](#init)
4. [install.md](#install)
5. [jobs.md](#jobs)
6. [pause.md](#pause)
7. [review.md](#review)
8. [schedule.md](#schedule)
9. [setup-telegram.md](#setup-telegram)
10. [todo.md](#todo)
11. [tq-message.md](#tq-message)
12. [tq-reply.md](#tq-reply)
13. [unschedule.md](#unschedule)

### Skill Files (4 files)
14. [SKILL.md](#skill)
15. [references/chrome-integration.md](#chrome-integration)
16. [references/cron-expressions.md](#cron-expressions)
17. [references/session-naming.md](#session-naming)

---

<a id="converse"></a>
## 1. `.claude/commands/converse.md`

```markdown
---
name: converse
description: Manage Telegram conversation sessions
tags: tq, telegram, conversation, orchestrator
allowed-tools: Bash(tq-converse), Bash(which)
argument-hint: "[start|stop|status|list|spawn <slug>]"
---

Arguments: $ARGUMENTS

Manage Telegram conversation sessions via `tq-converse`.

1. Verify `tq-converse` is installed:
   ```bash
   which tq-converse
   ```
   If missing, suggest running `/install` first and stop.

2. Parse the arguments according to these subcommands:
   - No arguments or `start`: start the orchestrator (`tq-converse start`)
   - `stop`: stop the orchestrator (`tq-converse stop`)
   - `stop <slug>`: stop a specific conversation session (`tq-converse stop <slug>`)
   - `status`: show all session statuses (`tq-converse status`)
   - `list`: list active conversation slugs (`tq-converse list`)
   - `spawn <slug> [--cwd <dir>] [--desc <desc>]`: create a new child session (`tq-converse spawn <slug> ...`)

3. If the arguments do not match any subcommand above, report the available subcommands and stop.

4. Run the corresponding command. If it exits non-zero, report the error output.

5. Display the command output to the user.

Related: `/setup-telegram` to configure Telegram bot, `/pause` and `/schedule` for queue scheduling.
```

---

<a id="health"></a>
## 2. `.claude/commands/health.md`

```markdown
---
name: health
description: Verify tq binaries, cron, queues, and logs
tags: tq, health, status, diagnostics
allowed-tools: Bash(ls), Bash(which), Bash(crontab), Bash(tmux), Bash(tail), Bash(tq), Bash(tq-converse), Bash(cat), Bash(grep), Bash(test), Bash(launchctl)
argument-hint: [queue-name]
---

Arguments: $ARGUMENTS

Run all checks below, then summarize with a pass/warn/fail status for each. If `$ARGUMENTS` names a specific queue, focus checks 3-6 on that queue only.

## 1. Binary check

Verify all tq binaries exist and are executable:
```bash
for BIN in tq tq-converse tq-message tq-telegram-poll tq-telegram-watchdog tq-cron-sync tq-setup; do
  which "$BIN" 2>/dev/null && echo "$BIN: pass" || echo "$BIN: FAIL"
done
```
Fail: suggest `/install`.

## 2. Cron jobs check

Run `crontab -l 2>/dev/null | grep tq`. Warn if no tq cron jobs found. Flag any queue that has a `schedule:` key in its YAML but no corresponding crontab entry.

## 3. Queue inventory

List `~/.tq/queues/*.yaml`. For each queue, run `tq --status ~/.tq/queues/<name>.yaml` and summarize: total tasks, done/running/pending counts. Warn if any queue has 0 tasks or only pending tasks with no cron schedule. Warn if no queue files exist and suggest `/todo` to create one.

## 4. Zombie session check

For any task with `status=running` in state files, verify the tmux session is alive with `tmux has-session -t "<session>"`. Flag running-state tasks whose session is dead.

## 5. Log check

Run `tail -50 ~/.tq/logs/tq.log`. Surface lines containing `error`, `Error`, `failed`, or `Exit code`. Warn if log file is missing but cron jobs are configured.

## 6. Conversation mode check

Verify conversation infrastructure:
- Orchestrator session alive: `tmux has-session -t tq-orchestrator 2>/dev/null`
- Registry exists and is valid JSON: `test -f ~/.tq/conversations/registry.json && python3 -c "import json; json.load(open('$HOME/.tq/conversations/registry.json'))"`
- Telegram config exists: `test -f ~/.tq/config/message.yaml`
- Telegram poll running: check crontab for `tq-telegram-poll` or launchd for `com.tq.telegram-poll`

Pass if all present and valid. Warn if telegram config missing (suggest `/setup-telegram`). Warn if orchestrator is down but conversations are registered (suggest `/converse start`).

## 7. Config check

Verify workspace config:
- `~/.tq/config/workspaces.yaml` exists (suggest `/init` if missing)
- `~/.tq/workspace-map.md` exists and is not stale (warn if older than 30 days)

## Output format

Print a summary table:

```
SYSTEM CHECK          STATUS   NOTES
--------------------  -------  ----------------------------------------
tq binaries           pass     7/7 on PATH
cron jobs             pass     2 jobs registered
queues found          pass     3 queues (morning, refactor, cleanup)
morning queue         pass     5 done, 0 running, 0 pending
zombie sessions       pass     none
recent log errors     pass     no errors in last 50 lines
conversation mode     pass     orchestrator running, 2 active sessions
workspace config      pass     32 projects cataloged
```

Then show per-queue `tq --status` output beneath.
```

---

<a id="init"></a>
## 3. `.claude/commands/init.md`

```markdown
---
name: init
description: Configure workspace dirs and catalog projects
tags: tq, setup, init, workspaces
allowed-tools: Bash(cat), Bash(find), Bash(ls), Bash(mkdir), Bash(test), Read, Write
argument-hint: [workspace-dirs...]
---

Arguments: $ARGUMENTS

Initialize tq by configuring workspace directories and scanning them to build a project catalog for queue task creation.

## Step 1 -- Read existing workspaces config

Read `~/.tq/config/workspaces.yaml`. If it exists, show the current `scan_dirs` list.

## Step 2 -- Confirm or collect workspace directories

- If `$ARGUMENTS` contains directory paths, use those directly.
- If no config exists and no arguments, ask the user which directories to scan (suggest `~/Sites`, `~/Projects`, `~/code`, `~/.tq/workspace`).
- If config exists and no arguments, show current dirs and ask to keep or replace.

Resolve all paths to absolute (expand `~`). Always include `~/.tq/workspace` unless explicitly excluded. Create it with `mkdir -p` if needed.

Validate each directory exists (`test -d`). If a directory does not exist, warn the user and ask whether to create it or skip it.

## Step 3 -- Write workspaces config

Run `mkdir -p ~/.tq/config`, then write `~/.tq/config/workspaces.yaml`:

```yaml
# tq workspace directories -- machine-local config.
# Edit this file, then re-run /init to refresh the project map.
scan_dirs:
  - /absolute/path/one
  - /absolute/path/two
```

## Step 4 -- Scan for projects

For each directory in `scan_dirs`, find git repositories (max 4 levels deep):
```bash
find /absolute/path -maxdepth 4 -name ".git" -type d 2>/dev/null | sed 's|/.git$||' | sort
```

Detect project type by checking for marker files (`package.json` -> node, `Cargo.toml` -> rust, `artisan`/`composer.json` -> laravel, `requirements.txt`/`pyproject.toml` -> python, `go.mod` -> go, `Gemfile` -> ruby, otherwise `unknown`). Project name = basename of path.

## Step 5 -- Write workspace map

Write `~/.tq/workspace-map.md` with a markdown table (columns: project, path, type), sorted alphabetically by project name. Include generation date and scan dirs at the top.

## Step 6 -- Summary

Report: number of directories scanned, projects found, paths to config and workspace map. Warn if any scan directory yielded zero git repositories.

Suggest next steps:
- Re-run `/init` after adding new projects
- Run `/install` to ensure tq binaries are on PATH
- Run `/health` to verify the full system is operational
```

---

<a id="install"></a>
## 4. `.claude/commands/install.md`

```markdown
---
name: install
description: Install tq scripts to PATH via symlinks
tags: tq, install, setup, path
allowed-tools: Bash(bash), Bash(which), Bash(ls)
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
```

---

<a id="jobs"></a>
## 5. `.claude/commands/jobs.md`

```markdown
---
name: jobs
description: List scheduled tq cron jobs and queue status
tags: tq, cron, schedule, queue, status
allowed-tools: Bash(crontab), Bash(tq), Bash(ls)
argument-hint: [queue-name]
---

List all scheduled tq cron jobs with their queue status. Accepts optional filter like "show morning jobs" or "what's scheduled for refactor".

Arguments: $ARGUMENTS

## Steps

1. **Read crontab and filter**:
   ```bash
   crontab -l 2>/dev/null | grep '/tq ' || true
   ```
   If no tq lines found, say "No tq cron jobs scheduled." and suggest `/todo <task> every morning` or `/schedule <queue> <time>`. Stop.

2. **If `$ARGUMENTS` names a specific queue**, filter to lines matching that queue filename only.

3. **Display a table** with one row per cron line:

   | Queue | Action | Schedule | Human | Path |
   |-------|--------|----------|-------|------|
   | morning | run | `0 9 * * *` | daily at 9am | `~/.tq/queues/morning.yaml` |
   | morning | status-check | `*/30 * * * *` | every 30 min | `~/.tq/queues/morning.yaml` |

   - **Action**: `run` for `tq <queue>`, `status-check` for `tq --status <queue>`
   - **Human**: plain-English translation of the cron expression

4. **Show queue state** for each unique queue found:
   ```bash
   tq --status ~/.tq/queues/<name>.yaml 2>/dev/null
   ```
   If the queue file no longer exists, warn: "Queue file missing -- cron entry is orphaned. Run `/unschedule <name>` to clean up."

5. If `$ARGUMENTS` filter matched no queues, say so and list the queue names that do exist.

Related: `/schedule` to add/update, `/unschedule` to remove, `/todo` to create queues.
```

---

<a id="pause"></a>
## 6. `.claude/commands/pause.md`

```markdown
---
name: pause
description: Pause a tq queue's cron run schedule
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
argument-hint: <queue-name>
---

Pause a tq queue's cron schedule by removing the run line while keeping the status-check sweep. Accept natural language like "pause the weekday queue" or "pause morning".

Arguments: $ARGUMENTS

## Steps

1. **Infer the queue name** from `$ARGUMENTS` (e.g. "the weekday queue" -> `weekday`, "morning" -> `morning`).
   If no queue name is given, list tq run lines from the crontab and ask which to pause.

2. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

3. **Find the tq run line** for this queue (the `tq` run line, NOT `tq --status`).
   If not found, say "No active schedule found for `<name>` queue." and stop.

4. **Show the line** that will be removed before removing it.

5. **Remove only the tq run line**, keeping the `tq --status` sweep:
   ```bash
   (crontab -l 2>/dev/null | grep -v "^[^#]*tq [^-].*<name>.yaml") | crontab -
   ```
   The `tq --status` line is kept so state continues to be maintained.

6. **Verify** the line was actually removed:
   ```bash
   crontab -l 2>/dev/null | grep "<name>.yaml" || echo "(none)"
   ```

7. **Confirm**: Show what was removed and note that `tq --status` is still running.

Related: `/schedule <name>` to resume, `/unschedule <name>` to fully remove, `/jobs` to see all scheduled queues.
```

---

<a id="review"></a>
## 7. `.claude/commands/review.md`

```markdown
---
name: review
description: Lint and review staged changes before commit
tags: tq, review, lint, code-quality
allowed-tools: Bash(shellcheck), Bash(git:*), Bash(ls)
---

Review staged changes for correctness, style, and security before committing.

1. Check for staged changes first:
   ```bash
   git diff --staged --stat
   ```
   If nothing is staged, report that and stop.

2. Run shellcheck on all bash scripts in `scripts/` (auto-discover, do not hardcode the list):
   ```bash
   ls scripts/tq* | xargs shellcheck
   ```
   If shellcheck is not installed, warn and skip this step.
   Report any warnings before proceeding.

3. Show the staged diff:
   ```bash
   git diff --staged
   ```

4. Review the diff against this checklist:
   - Bugs or logic errors in bash/python
   - macOS compatibility: `sed -i ''` syntax (not GNU `sed -i`), `security` CLI, tmux commands
   - Violations of rules in `.claude/rules/` (`anti-patterns.md`, `naming.md`, `security.md`)
   - Security: anything that could leak OAuth tokens, commit `.tq/` dirs, or expose credentials
   - Hash stability: no changes to `hashlib.sha256` hashing logic
   - Shebang correctness: all scripts use `#!/usr/bin/env bash`
   - Strict mode: all scripts use `set -euo pipefail`
   - Temp files cleaned via `trap ... EXIT`

5. Summarize findings as a numbered list. For each issue, state the file, line, and suggested fix. If no issues found, confirm the changes look clean.
```

---

<a id="schedule"></a>
## 8. `.claude/commands/schedule.md`

```markdown
---
name: schedule
description: Add or update cron schedule for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [queue-name] [schedule]
---

Add or update a cron schedule for a tq queue. Accepts natural language like "run the morning queue every day at 9am" or "schedule refactor every weekday at 6pm".

Arguments: $ARGUMENTS

## Steps

1. **Parse the request** from `$ARGUMENTS`:
   - Infer queue name (e.g. "the morning queue" -> `morning`, "refactor" -> `refactor`)
   - Translate schedule to cron expression:
     - "every day at 9am" -> `0 9 * * *`
     - "every weekday at 6pm" -> `0 18 * * 1-5`
     - "every hour" -> `0 * * * *`
     - "every 4 hours" -> `0 */4 * * *`
     - "every monday at 8am" -> `0 8 * * 1`
   - If a raw cron expression is given (5 space-separated fields), use it directly
   - If no queue name given, list `~/.tq/queues/*.yaml` and ask which to schedule
   - If no schedule given, ask: "What schedule? (e.g. 'every day at 9am')"

2. **Validate the queue file exists**:
   ```bash
   ls ~/.tq/queues/<name>.yaml
   ```
   If missing, say "Queue `<name>` not found. Run `/todo <task description>` to create it first." and stop.

3. **Compute `reset:` TTL** based on the cron interval:

   | Cron pattern | Interval | TTL |
   |---|---|---|
   | `*/N` in hour field | N hours | `floor(N * 0.5)`h |
   | Comma-list in hour field | smallest gap | `floor(min_gap * 0.5)`h |
   | Single hour, one day-of-week | 168h | `3d` |
   | Single hour, any other | 24h | `12h` |

   Minimum: `1h`. Read the queue file. If `reset:` already exists with a named value (`daily`, `weekly`, `on-complete`, etc.), skip -- do not overwrite. Otherwise insert or replace `reset:` before `cwd:`.

4. **Ensure log dir exists**:
   ```bash
   mkdir -p ~/.tq/logs
   ```

5. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo ""
   ```

6. **Build two cron lines**:
   ```
   <cron-expression> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   */30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
   ```

7. **Merge into crontab** (remove existing lines for this queue first, match on `/<name>\.yaml`):
   ```bash
   (crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; echo "<line1>"; echo "<line2>") | crontab -
   ```

8. **Confirm**: Show the two new crontab lines and their plain-English meaning. If replacing an existing schedule, note what changed.

Related: `/jobs` to verify, `/unschedule <name>` to remove, `/todo` to create queues.
```

---

<a id="setup-telegram"></a>
## 9. `.claude/commands/setup-telegram.md`

```markdown
---
name: setup-telegram
description: Configure Telegram bot and notifications
tags: tq, setup, telegram, notify, conversation
allowed-tools: Bash(curl), Bash(mkdir), Bash(chmod), Bash(cat), Bash(test), Bash(python3), Bash(tq-setup), Bash(tq-telegram-watchdog), Bash(crontab), Write, Read
argument-hint: [bot-token]
---

Arguments: $ARGUMENTS

Guide the user through Telegram notification setup interactively. If `$ARGUMENTS` contains a bot token, skip step 1.

## Step 0 -- Check existing config

Read `~/.tq/config/message.yaml` if it exists. If present, show the current `telegram.bot_token` (masked: first 5 chars + `...`) and `telegram.user_id`. Ask the user whether to reconfigure or keep the existing setup. If keeping, skip to step 5.

## Step 1 -- Get bot token

Instruct the user to create a bot via @BotFather in Telegram (`/newbot`), then paste the token. Wait for input.

Validate the token format matches `\d+:[A-Za-z0-9_-]{35,}`. If invalid, show the expected format (`123456:ABCdef...`) and ask again.

## Step 2 -- Discover user ID

Ask the user to send any message to their new bot, then confirm. Run:
```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates?offset=0&limit=10&timeout=0"
```
Parse the JSON response with:
```bash
python3 -c "import sys,json; r=json.loads(sys.stdin.read()); print(r['result'][0]['message']['from']['id'] if r.get('result') else '')"
```
Extract `from.id` from the first message. If no messages found, ask the user to send a message to the bot and retry (up to 3 attempts). If still empty after retries, ask the user to paste their numeric user ID manually.

## Step 3 -- Content type

Ask which notification type to use on task completion:
- `status` -- task name, done/failed, duration (default)
- `summary` -- Claude writes a 2-3 sentence digest (requires live session)

Default to `status` if unspecified.

## Step 4 -- Test and write config

1. Send a test message via the Telegram API:
   ```bash
   curl -s -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
     -d chat_id="<USER_ID>" -d text="tq setup test -- Telegram notifications are working."
   ```
   Parse the response to check `"ok":true`. If it fails, report the error message from the API response and stop.

2. On success, run `mkdir -p ~/.tq ~/.tq/workspace ~/.tq/logs ~/.tq/config` and write `~/.tq/config/message.yaml`:

   ```yaml
   default_service: telegram
   content: <CONTENT_TYPE>

   telegram:
     bot_token: "<TOKEN>"
     user_id: "<USER_ID>"
   ```

3. Restrict file permissions (config contains the bot token):
   ```bash
   chmod 600 ~/.tq/config/message.yaml
   ```

## Step 5 -- Install Telegram polling

Install the polling cron entry via the watchdog (preferred) or manually:

```bash
tq-telegram-watchdog
```

If `tq-telegram-watchdog` is not on PATH, fall back to manual cron installation:
```bash
mkdir -p ~/.tq/logs
(crontab -l 2>/dev/null | grep -v "tq-telegram-poll"; echo "* * * * * /opt/homebrew/bin/tq-telegram-poll >> ~/.tq/logs/tq-telegram.log 2>&1") | crontab -
```

Verify the cron entry was installed:
```bash
crontab -l 2>/dev/null | grep tq-telegram-poll
```

## Step 6 -- Summary

Report:
- Config path: `~/.tq/config/message.yaml` (permissions: 600)
- Polling: active via cron or launchd
- Test message: sent successfully

Suggest next steps:
- Run `/converse start` to launch conversation mode via Telegram
- Run `/health` to verify the full system
```

---

<a id="todo"></a>
## 10. `.claude/commands/todo.md`

```markdown
---
name: todo
description: Add tasks to a tq queue with optional scheduling
tags: tq, queue, tasks, schedule, tmux
allowed-tools: Bash(pwd), Bash(cat), Bash(ls), Bash(mkdir), Bash(crontab), Read, Write
argument-hint: [task description] [schedule]
---

Add task(s) to a tq queue file. Optionally schedule the queue via cron. Accepts natural language like "review auth module every morning" or "add tests to the refactor queue".

Arguments: $ARGUMENTS

## Step 1 -- Capture CWD and workspace context

1. Run `pwd` and store as `TASK_CWD`.
2. Read `~/.tq/workspace-map.md`. If missing, warn "No workspace map found -- run `/init` to set one up." but continue.
3. Use the workspace map to resolve project names in `$ARGUMENTS` (e.g. "fix bug in samson" -> look up samson's path as `TASK_CWD`). Continue even if project is unlisted.

## Step 2 -- Parse the request

If no arguments provided, list existing queues (`ls ~/.tq/queues/*.yaml 2>/dev/null`) and stop.

From `$ARGUMENTS`, extract:
- **Task prompt(s)**: the work to do
- **Schedule** (optional): time/frequency language ("every morning", "daily at 9am", "weekly on mondays")
- **Queue name** (optional): if explicitly stated ("add to the refactor queue")

Queue name inference (if not explicit):
- From schedule keyword: "every morning" -> `morning`, "daily" -> `daily`, "weekday" -> `weekday`, "weekly" -> `weekly`, "hourly" -> `hourly`
- No schedule: use basename of `TASK_CWD`

## Step 3 -- Read or create queue

```bash
mkdir -p ~/.tq/queues
```

Read `~/.tq/queues/<name>.yaml` if it exists. Note whether this is a new or existing file.

## Step 4 -- Write the updated queue YAML

Merge tasks into existing queue (never remove existing tasks, dedup by exact prompt text). Always include `cwd:` at top.

Write to `~/.tq/queues/<name>.yaml`. If existing queue has a different `cwd:`, warn the user and ask which to keep before writing.

Format must follow queue-format rules: required keys `cwd` and `tasks`, optional `schedule`, `reset`, `message`.

## Step 5 -- Schedule (if schedule language detected)

If no schedule language in `$ARGUMENTS`, skip to Step 6.

Translate to cron expression (e.g. "every morning" -> `0 9 * * *`, "every weekday" -> `0 9 * * 1-5`, "nightly" -> `0 22 * * *`).

Install cron entries (match on exact queue filename to avoid clobbering other queues):
```bash
mkdir -p ~/.tq/logs
(crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml"; \
  echo "<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

Compute `reset:` TTL using the same rules as `/schedule` (see step 3 there). Insert before `cwd:` unless `reset:` already exists with a named value.

## Step 6 -- Confirm

Show:
- Queue file path and full contents
- `cwd` for task execution
- Cron schedule in plain English, or "Not scheduled -- run manually with `tq ~/.tq/queues/<name>.yaml`"

Related: `/schedule` to change schedule, `/jobs` to list all cron jobs, `/unschedule` to remove schedule.
```

---

<a id="tq-message"></a>
## 11. `.claude/commands/tq-message.md`

```markdown
---
name: tq-message
description: Send task completion summary via messaging service
tags: tq, notify, message, summary, telegram
allowed-tools: Bash(tq-message)
argument-hint: <task-hash> <queue-file>
---

Arguments: $ARGUMENTS

## 1. Parse arguments

Extract from `$ARGUMENTS`:
- **First**: task hash (8-char hex, e.g. `a1b2c3d4`)
- **Second**: queue file path (absolute path to `.yaml`)

If either is missing or malformed (hash not 8 hex chars, path not ending in `.yaml`), stop and report which argument is invalid.

## 2. Write summary

Write a rich, specific summary of what was accomplished:
- **Lead sentence**: state what was done + specific output (e.g. "Wrote a 106-line guide at docs/demo-video-tips.md")
- **Numbered list**: 3-6 items of what was built/covered/fixed, each with a brief description after an em dash
- Keep under 3500 characters (Telegram limit is 4096; leave room for prefix)
- No filler ("I successfully...", "In this session...")

Example:
```
Wrote a 106-line demo video guide at docs/demo-video-tips.md. The guide covers:
1. Why the video matters -- frames it as judges' main window into the project
2. What judges look for -- 5 evaluation lenses with concrete criteria
3. Video structure -- a 5-minute template: Hook > Live Demo > Technical Walk > Close
4. Do This / Avoid This -- actionable dos/don'ts from judging criteria
5. Recording tips -- tools, formats, audio quality, the 100MB upload limit
```

## 3. Send via tq-message

Store the summary in a variable and pass it:

```bash
SUMMARY='<your summary text here>'
tq-message --task "<TASK_HASH>" --queue "<QUEUE_FILE>" --message "$SUMMARY"
```

If `tq-message` exits non-zero, report the error output.

Do not explain what you are doing. Write the summary and run the command.

> Related: `/tq-reply` (conversation mode replies), `/converse` (manage sessions)
```

---

<a id="tq-reply"></a>
## 12. `.claude/commands/tq-reply.md`

```markdown
---
name: tq-reply
description: Reply to Telegram user from conversation session
tags: tq, telegram, conversation, reply
allowed-tools: Bash(tq-message),Bash(tq-converse),Bash(cat),Bash(mkdir),Bash(date)
---

Arguments: $ARGUMENTS

No arguments needed -- the conversation slug is auto-detected from the current tmux session.

## 1. Detect conversation slug

Find which conversation this Claude instance belongs to by matching the tmux session name against registered slugs:

```bash
SLUG=""
for DIR in "$HOME/.tq/conversations/sessions"/*/; do
  [[ -f "$DIR/current-slug" ]] || continue
  CANDIDATE="$(cat "$DIR/current-slug")"
  SESSION="tq-conv-${CANDIDATE}"
  if tmux display-message -p '#{session_name}' 2>/dev/null | grep -qF "$SESSION"; then
    SLUG="$CANDIDATE"
    break
  fi
done
echo "Slug: $SLUG"
```

If SLUG is empty, stop and report: "Could not detect conversation slug. This command must run inside a `tq-conv-*` tmux session."

## 2. Write the response

Write a concise, Telegram-friendly response based on what was just accomplished or answered:
- Lead with the answer or result
- Use Telegram Markdown (`*bold*`, `_italic_`, `` `code` ``)
- Keep under 3500 characters (Telegram limit is 4096; slug prefix takes space)
- No filler ("I successfully...", "Sure, I can...")

Store the response text mentally -- it will be used in steps 3 and 4.

## 3. Look up reply-to ID and save to outbox

```bash
SLUG_DIR="$HOME/.tq/conversations/sessions/$SLUG"
REPLY_TO=""
if [[ -f "$SLUG_DIR/reply-to-msg-id" ]]; then
  REPLY_TO="$(cat "$SLUG_DIR/reply-to-msg-id")"
fi

mkdir -p "$SLUG_DIR/outbox"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
```

Write the response text to `$SLUG_DIR/outbox/${TIMESTAMP}.txt` for audit.

## 4. Send via tq-message

```bash
echo "$SLUG" > "$HOME/.tq/conversations/latest-reply-slug"
RESPONSE='<response text here>'
tq-message --message "[$SLUG] $RESPONSE" --reply-to "$REPLY_TO"
```

If `tq-message` exits non-zero, report the error.

Do not explain what you are doing. Write the response and run the commands.

> Related: `/tq-message` (queue task summaries), `/converse` (manage sessions)
```

---

<a id="unschedule"></a>
## 13. `.claude/commands/unschedule.md`

```markdown
---
name: unschedule
description: Remove cron schedule for a tq queue
tags: tq, cron, schedule, queue
allowed-tools: Bash(crontab)
argument-hint: [queue-name]
---

Remove all cron lines (both run and status-check) for a tq queue. Accepts natural language like "unschedule the weekday queue" or "remove morning from cron".

Arguments: $ARGUMENTS

## Steps

1. **Infer the queue name** from `$ARGUMENTS` (e.g. "the weekday queue" -> `weekday`, "morning" -> `morning`).
   If no queue name given, list all tq cron lines (`crontab -l 2>/dev/null | grep '/tq '`) and ask which to remove.

2. **Read current crontab**:
   ```bash
   crontab -l 2>/dev/null || echo "(no crontab)"
   ```

3. **Find matching tq lines** for this queue. Match the exact queue filename to avoid false positives (e.g. "morning" must not remove "morning-review"):
   ```bash
   crontab -l 2>/dev/null | grep "tq.*/<name>\.yaml"
   ```
   If none found, say "No cron schedule found for `<name>` queue." and stop.

4. **Show what will be removed** and the lines being kept. Then remove:
   ```bash
   (crontab -l 2>/dev/null | grep -v "tq.*/<name>\.yaml") | crontab -
   ```

5. **Confirm removal**. Note that the queue file (`~/.tq/queues/<name>.yaml`) and task state are untouched -- only the cron schedule was removed.

Related: `/schedule <name>` to reschedule, `/jobs` to verify removal.
```

---

<a id="skill"></a>
## 14. `skills/tq/SKILL.md`

```markdown
---
name: tq
description: >
  This skill should be used when the user asks to "add to queue", "run queue", "queue these tasks",
  "schedule with tq", "tq status", "check task queue", "create a tq queue", "set up cron for tq",
  "run claude in background", "batch prompts in tmux", "start a conversation", "start conversation mode",
  "converse via telegram", "telegram conversation mode", "telegram bot", "message routing",
  "route a message", "spawn a session", "orchestrator", "reset tasks", "reset queue",
  "notify on completion", "tq notification", "tq health", "check tq health", "tq setup",
  "setup telegram bot", "tq install", or wants to manage Claude prompts running
  in tmux sessions via the tq CLI tool. Triggers on phrases like "queue", "tq", "task queue",
  "tmux queue", "scheduled claude tasks", "conversation mode", "telegram chat", "converse",
  "telegram session", "poll telegram", "tq-converse", "tq-message", "task notification".
version: 1.3.0
---

# tq -- Claude Task Queue Runner

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/tq`

Installed to PATH via `/install`: `/opt/homebrew/bin/tq`

## Overview

tq manages Claude Code sessions via tmux in two modes:

1. **Queue mode** -- batch prompts into YAML queue files, spawn each as an independent tmux session. Idempotent: re-running `tq` skips `done` and live `running` tasks.
2. **Conversation mode** -- maintain persistent interactive Claude Code sessions orchestrated via Telegram. An orchestrator routes messages to the right conversation, spawning new sessions or resuming existing ones.

## Queue File Format

Location: `~/.tq/queues/<name>.yaml`

```yaml
schedule: "0 9 * * *"              # optional -- auto-managed crontab via tq-cron-sync
reset: daily                        # optional -- daily|weekly|hourly|always|on-complete
cwd: /path/to/working/directory     # where claude runs for each task
message:                            # optional -- notification config
  service: telegram
  content: summary                  # summary|status|details|log
tasks:
  - name: review-auth               # optional -- used for session naming
    prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```

Queue files are read-only -- tq never modifies them.

### Reset Modes

Reset controls when task state is cleared so tasks re-run:

| Mode | Behavior |
|------|----------|
| `daily` | Clear once per calendar day |
| `weekly` | Clear once per ISO week |
| `hourly` | Clear once per hour |
| `always` | Clear on every `tq` run |
| `on-complete` | Per-task: delete state after task finishes |

## State

State dir: `<queue-dir>/.tq/<queue-basename>/` (e.g., `~/.tq/queues/.tq/morning/`)
One file per task, named by 8-char SHA-256 of the prompt:

```
status=running
session=tq-fix-the-login-451234
window=fix-the
prompt=fix the login bug in auth service
started=2026-03-05T10:00:00
```

Statuses: `pending` -> `running` -> `done`

## Commands

| Command | Purpose |
|---------|---------|
| `/todo <natural language>` | Create/update queue and optionally schedule |
| `/schedule <natural language>` | Add/update cron schedule for a queue |
| `/pause <queue>` | Remove run line, keep status-check (resume with `/schedule`) |
| `/unschedule <queue>` | Remove all cron lines for a queue |
| `/jobs [filter]` | List all scheduled tq cron jobs |
| `/health [queue]` | Run system-wide diagnostics |
| `/install` | Symlink tq binaries to PATH |
| `/init` | Configure workspace directories and build project catalog |
| `/review` | Lint and review staged changes before commit |
| `/converse [start\|stop\|status\|list]` | Manage conversation orchestrator and sessions |
| `/tq-reply` | Send response back to Telegram (conversation mode) |
| `/tq-message` | Write and send task completion summary |
| `/setup-telegram` | Configure Telegram bot token and notifications |

## CLI Usage

```bash
tq <queue.yaml>           # spawn pending tasks in tmux; skip running/done
tq --status <queue.yaml>  # print status table; flip dead sessions to done
```

## Cron Scheduling

Add `schedule:` to any queue YAML and `tq-cron-sync` auto-manages crontab (runs every 20 min, scans `~/.tq/queues/*.yaml`). Each scheduled queue gets two cron lines:

```cron
<schedule> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
```

The `tq --status` line runs every 30 min to reap dead sessions and flip their state to `done`.

See `references/cron-expressions.md` for natural language to cron mapping.

## Queue Name Inference

When using `/todo` without an explicit queue name:

- Schedule keyword present -> derive from it: "every morning" -> `morning`, "daily" -> `daily`, "weekly" -> `weekly`
- No schedule -> use `basename` of current working directory

## Reset

- One task: delete its state file from `.tq/<queue-basename>/`
- Entire queue: `rm -rf ~/.tq/queues/.tq/<queue-basename>/`

## Conversation Mode

Start the orchestrator via `tq-converse start` or send `/converse` from Telegram.

The orchestrator routes incoming Telegram messages using 3-tier routing:

1. **Reply threading** -- Telegram reply to a known message routes to that session automatically
2. **Slug prefix** -- `#slug message` routes to the named session
3. **Orchestrator fallback** -- new topic triggers the orchestrator to spawn a new session with a descriptive slug

Each conversation is a persistent Claude Code interactive session in its own tmux window.
Child sessions use `/tq-reply` to send responses back to Telegram as threaded replies.

### Key CLI commands

```bash
tq-converse start                         # start orchestrator
tq-converse spawn <slug> --cwd <dir>      # create new conversation session
tq-converse route <slug> <message>        # send message to a session
tq-converse list                          # list active sessions
tq-converse status                        # show all session statuses
tq-converse stop [<slug>]                 # stop session or orchestrator
```

## Background Scripts

| Script | Purpose |
|--------|---------|
| `tq-cron-sync` | Scans `~/.tq/queues/*.yaml` every 20 min, syncs `schedule:` to crontab |
| `tq-telegram-poll` | Long-polls Telegram, routes messages via 3-tier routing |
| `tq-telegram-watchdog` | Ensures poll cron entry exists |
| `tq-message` | Sends notifications (Telegram/Slack) on task completion |

## Additional Resources

- **`references/session-naming.md`** -- session/window name generation algorithm and examples
- **`references/cron-expressions.md`** -- natural language to cron expression mapping table
- **`references/chrome-integration.md`** -- Chrome `--chrome` flag, profile setup, and browser configuration
```

---

<a id="chrome-integration"></a>
## 15. `skills/tq/references/chrome-integration.md`

```markdown
# tq Chrome Integration Reference

## How `--chrome` Works

When a queue task runs, tq generates a `.launch.py` launcher script. If Chrome integration is enabled, the launcher:

1. Opens Chrome with the configured profile directory before connecting
2. Passes `--chrome` to the `claude` CLI, which connects to the Chrome browser extension
3. Claude can then interact with web pages through the browser

The `--chrome` flag is added to the `claude` CLI args in the generated launcher:

```python
# In the generated .launch.py:
subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])
time.sleep(2)
os.execvp('claude', ['claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])
```

## Default Profile

tq uses **Chrome Profile 5** (`--profile-directory=Profile 5`) which corresponds to halbotkirchner@gmail.com. This is hardcoded in the `scripts/tq` launcher generation (line ~396).

To find which Chrome profile directory maps to which account:

```bash
# List all Chrome profiles and their email addresses
for d in ~/Library/Application\ Support/Google/Chrome/Profile*/; do
  python3 -c "import json; p=json.load(open('$d/Preferences')); print('$(basename $d):', p.get('account_info',[{}])[0].get('email','unknown'))" 2>/dev/null
done
```

## Multiple Chrome Profiles

To use a different Chrome profile for specific tasks, modify the `--profile-directory` argument in the generated launcher. Currently, this requires editing `scripts/tq` directly (the profile is not configurable per-queue).

For running isolated browser extension sessions across profiles without conflicts, use the `chrome-devtools` MCP with the `--isolated` flag.

## Setting the Browser Display Name

The Claude browser extension stores its display name as `bridgeDisplayName` in `chrome.storage.local`. This name identifies the browser in Claude's connected browsers list.

To set or change it:

1. Open Chrome with the target profile
2. Right-click the Claude extension icon in the toolbar and select **Options**
3. Look for the browser name / display name field and set it
4. The name persists in the extension's local storage

## When Chrome Is Used

Chrome integration is used when tasks need to interact with web pages (e.g., scraping, form filling, visual verification). Most queue tasks that only modify code do not need Chrome.

The `--chrome` flag is controlled in the launcher generation section of `scripts/tq` (~line 396-403).
```

---

<a id="cron-expressions"></a>
## 16. `skills/tq/references/cron-expressions.md`

```markdown
# tq Cron Expression Reference

## Natural Language to Cron Mapping

| Natural Language | Cron Expression | Notes |
|-----------------|-----------------|-------|
| "every morning" / "daily at 9am" | `0 9 * * *` | Default morning time |
| "every night" / "nightly" | `0 22 * * *` | 10pm |
| "every weekday" | `0 9 * * 1-5` | Mon-Fri at 9am |
| "every weekday at 6pm" | `0 18 * * 1-5` | Mon-Fri at 6pm |
| "every monday" / "weekly on mondays" | `0 9 * * 1` | 9am Monday |
| "every monday at 8am" | `0 8 * * 1` | 8am Monday |
| "every hour" / "hourly" | `0 * * * *` | Top of each hour |
| "every 4 hours" | `0 */4 * * *` | Every 4 hours |
| "every 30 minutes" | `*/30 * * * *` | Every 30 min |
| "every 15 minutes" | `*/15 * * * *` | Every 15 min |
| "twice daily" / "morning and evening" | `0 9,18 * * *` | 9am and 6pm |
| "daily" | `0 9 * * *` | Default to 9am |
| "weekly" | `0 9 * * 1` | Default to Monday 9am |
| "first of the month" | `0 9 1 * *` | 9am on the 1st |

## Day-of-Week Numbers

| Number | Day |
|--------|-----|
| 0 or 7 | Sunday |
| 1 | Monday |
| 2 | Tuesday |
| 3 | Wednesday |
| 4 | Thursday |
| 5 | Friday |
| 6 | Saturday |

## Standard tq Crontab Block

Every scheduled queue gets two cron lines:

```cron
# Run queue (spawn pending tasks)
<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1

# Status sweep (reap dead sessions every 30 min)
*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1
```

## Automatic Crontab Management

`tq-cron-sync` runs every 20 minutes and scans `~/.tq/queues/*.yaml` for `schedule:` keys. It automatically adds, updates, or removes crontab entries. No manual `crontab -e` needed.

### Manual Override (if needed)

Replace existing lines for the same queue by filtering out old entries before appending new ones:

```bash
(crontab -l 2>/dev/null | grep -v "tq.*<name>.yaml"; \
  echo "<cron> /opt/homebrew/bin/tq ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1"; \
  echo "*/30 * * * * /opt/homebrew/bin/tq --status ~/.tq/queues/<name>.yaml >> ~/.tq/logs/tq.log 2>&1") | crontab -
```

The `grep -v` removes all existing lines referencing this queue before appending new ones, preventing duplicates.

## Queue Name to Schedule Name Inference

When no queue name is given, infer from the schedule keyword:

| Schedule keyword | Queue name |
|-----------------|------------|
| "morning" / "9am" | `morning` |
| "daily" | `daily` |
| "weekday" / "weekdays" | `weekday` |
| "weekly" / "monday" | `weekly` |
| "hourly" / "every hour" | `hourly` |
| "nightly" / "night" | `nightly` |
| no schedule | `basename` of current working directory |
```

---

<a id="session-naming"></a>
## 17. `skills/tq/references/session-naming.md`

```markdown
# tq Session Naming Reference

## Algorithm

Given a task, derive a tmux session name and window name. The YAML `name` field takes priority over prompt-derived words.

### Source Text

1. If the task has a `name:` field in the YAML, use that as the full source text
2. Otherwise, use the first line of the prompt

### Session Name

1. If using `name:` field: take the full field value. If using prompt: take the first 3 words
2. Lowercase everything
3. Replace any non-`[a-z0-9]` character with `-`
4. Strip leading and trailing `-` characters
5. Truncate to 20 characters
6. Prepend `tq-` and append `-<epoch-suffix>` (last 6 digits of Unix epoch)

Result: `tq-<base>-<epoch>`

### Window Name

1. If using `name:` field: take the full field value. If using prompt: take the first 2 words
2. Apply the same lowercasing, character replacement, and dash stripping as above
3. Truncate to 15 characters (no prefix, no epoch suffix)

## Examples

### Without `name:` field (prompt-derived)

| Prompt | Session | Window |
|--------|---------|--------|
| `fix the login bug in auth service` | `tq-fix-the-login-451234` | `fix-the` |
| `write unit tests for payment module` | `tq-write-unit-tests-451234` | `write-unit` |
| `Refactor Auth Module` | `tq-refactor-auth-module-451234` | `refactor-auth` |

### With `name:` field

| Name Field | Session | Window |
|------------|---------|--------|
| `review-auth` | `tq-review-auth-451234` | `review-auth` |
| `Update Readme` | `tq-update-readme-451234` | `update-readme` |

## Bash Implementation

```bash
EPOCH_SUFFIX="$(date +%s | tail -c 6)"

# With name field:
if [[ -n "$TASK_NAME_FIELD" ]]; then
  SESSION_BASE="$(echo "$TASK_NAME_FIELD" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-20)"
  WINDOW="$(echo "$TASK_NAME_FIELD" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-15)"
else
  # Without name field (prompt-derived):
  SESSION_BASE="$(echo "$FIRST_LINE" | awk '{print $1" "$2" "$3}' | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-20)"
  WINDOW="$(echo "$FIRST_LINE" | awk '{print $1" "$2}' | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-*//' | sed 's/-*$//' | cut -c1-15)"
fi

SESSION="tq-${SESSION_BASE}-${EPOCH_SUFFIX}"
```

## Notes

- The epoch suffix prevents collision when the same prompt is re-queued after a reset
- tmux session names must not contain `.` or `:` -- the character replacement handles this
- The `-` separator between base and epoch is always present; if the base ends with `-`, strip it first to avoid `--`

## Conversation Mode Session Names

Conversation sessions use a slug-based naming scheme with no epoch suffix:

| Type | Pattern | Example |
|------|---------|---------|
| Orchestrator | `tq-orchestrator` (fixed) | `tq-orchestrator` |
| Child session | `tq-conv-<slug>` | `tq-conv-fix-auth` |
| Child window | `<slug>` | `fix-auth` |

Slugs are short kebab-case names (2-4 words) chosen by the orchestrator Claude when creating a new conversation. Examples: `fix-auth-bug`, `refactor-api`, `update-docs`.

Since there is no epoch suffix, conversation session names are unique by slug. Starting a session with an already-active slug reuses the existing session.
```
