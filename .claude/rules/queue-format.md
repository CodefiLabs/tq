# Queue File Format

Queue files are YAML files passed to `tq` as the first argument.

## Required Top-Level Keys

- `cwd` — working directory for all tasks (string, absolute path recommended)
- `tasks` — array of task objects

## Optional Top-Level Keys

- `schedule` — cron expression for automatic scheduling via `tq-cron-sync` (string)
- `reset` — when to automatically clear task state so tasks re-run (string, see Reset Modes below)
- `message` — notification config block (see Queue-Level Messaging below)

## Task Object Keys

- `prompt` — the Claude prompt to run (string, required)
- `name` — optional human-readable label for tmux session naming (string)

## Reset Modes

Add `reset:` to control when task state is cleared so tasks re-run automatically.

| Value | Behaviour |
|-------|-----------|
| `daily` | Clears all task state once per calendar day (on first run of the day) |
| `weekly` | Clears once per ISO week (Monday–Sunday) |
| `hourly` | Clears once per hour |
| `always` | Clears on every `tq` run |
| `on-complete` | Per-task: deletes state after each task finishes (task re-runs next time) |

```yaml
reset: daily
schedule: "0 9 * * *"
cwd: /Users/kk/Sites/myproject
tasks:
  - prompt: "Summarize yesterday's git activity into docs/daily-standup.md"
```

Queue-level resets (`daily`, `weekly`, `hourly`, `always`) clear state **before** task evaluation, so all tasks re-run on that run. They also clear `.queue-notified` so the completion notification fires fresh. A `.last_reset` dotfile in the state dir tracks the last reset period.

## Automatic Scheduling

Add `schedule:` with a raw cron expression to have `tq-cron-sync` manage the crontab entry automatically. No manual `crontab -e` needed.

```yaml
schedule: "0 9 * * *"
cwd: /Users/kk/Sites/myproject
tasks:
  - name: morning-review
    prompt: "Review yesterday's commits and summarize in docs/daily.md"
```

`tq-cron-sync` scans `~/.tq/queues/*.yaml` every 20 minutes and syncs crontab:
- Queues with `schedule:` get a run entry + a `*/30 * * * *` status-check entry
- Removing `schedule:` or deleting the queue file removes the crontab entries on the next sync
- Changing `schedule:` updates the crontab entry on the next sync

Use an LLM to translate natural language ("daily at 9am") to cron expressions ("0 9 * * *").

## Queue-Level Messaging

Add an optional `message:` block at the top level to configure notifications for this queue.
Overrides `~/.tq/config/message.yaml` global config.

```yaml
message:
  service: telegram       # which service (telegram | slack)
  content: summary        # summary | status | details | log (default: summary)
  chat_id: "-100123456"  # override global chat_id for this queue
```

**Content types:**
- `summary` — Claude writes a 2-3 sentence digest of what it accomplished (requires live session)
- `status` — task name, done/failed, duration (no Claude required)
- `details` — prompt first line, status, duration, hash (no Claude required)
- `log` — last 200 lines of tmux pane scrollback (no Claude required)

**Global credentials** go in `~/.tq/config/message.yaml` — never in queue files (queue files may be shared).

## Minimal Example

```yaml
cwd: /Users/kk/Sites/startups/myproject
tasks:
  - prompt: "Review the code in src/main.py and suggest improvements"
```

## Multi-Task Example

```yaml
cwd: /Users/kk/Sites/startups/myproject
tasks:
  - name: review-auth
    prompt: "Review the authentication module in src/auth.py for security issues"
  - name: update-readme
    prompt: "Update README.md to reflect the latest API changes"
  - name: add-tests
    prompt: "Add unit tests for the User model in tests/test_user.py"
```

## Multi-Line Prompts (Block Scalar)

Use YAML block scalars for multi-line prompts:

```yaml
tasks:
  - name: complex-task
    prompt: |
      Review the entire src/ directory and:
      1. Identify any security vulnerabilities
      2. Suggest performance improvements
      3. Check for consistent error handling
      Write findings to docs/review-2026.md
```

## Task Identity

Each task's identity is derived from `SHA-256(prompt)[:8]`. This means:
- Tasks are idempotent — re-running the same prompt skips already-completed tasks
- Editing a prompt creates a new task identity (old state is orphaned, not deleted)
- Task identity is stable across re-runs of the same queue file

## Do Not

- Do not add top-level keys other than `cwd`, `tasks`, `schedule`, `reset`, and `message` — others are ignored
- Do not use YAML anchors — the embedded Python parser does not support them
- Do not leave `cwd` blank — tasks will run in an undefined directory
