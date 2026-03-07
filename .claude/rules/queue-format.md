# Queue File Format

Queue files are YAML files passed to `tq` as the first argument.

## Required Top-Level Keys

- `cwd` — working directory for all tasks (string, absolute path recommended)
- `tasks` — array of task objects

## Task Object Keys

- `prompt` — the Claude prompt to run (string, required)
- `name` — optional human-readable label for tmux session naming (string)

## Queue-Level Messaging

Add an optional `message:` block at the top level to configure notifications for this queue.
Overrides `~/.tq/message.yaml` global config.

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

**Global credentials** go in `~/.tq/message.yaml` — never in queue files (queue files may be shared).

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

- Do not add extra top-level keys — only `cwd` and `tasks` are processed
- Do not use YAML anchors — the embedded Python parser does not support them
- Do not leave `cwd` blank — tasks will run in an undefined directory
