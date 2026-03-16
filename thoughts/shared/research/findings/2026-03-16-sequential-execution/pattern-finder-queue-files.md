# Queue File Patterns — Pattern Finder Report
Date: 2026-03-16

## 1. Real-World Queue Files Found

### ~/.tq/queues/*.yaml
**No files found.** The directory `~/.tq/queues/` is empty — no live queue files exist on this machine at the time of this scan.

### tests/fixtures/named-tasks.yaml
The only committed YAML fixture in the project:

```yaml
cwd: /tmp
tasks:
  - name: review-auth
    prompt: "Review the authentication module in src/auth.py for security issues"
  - name: update-docs
    prompt: "Update README.md to reflect the latest API changes"
  - prompt: "echo unnamed task check"
```

File: `/Users/kk/Sites/codefi/tq/tests/fixtures/named-tasks.yaml`

This fixture demonstrates: named tasks alongside an unnamed task; double-quoted inline prompts; `cwd` at top level.

---

## 2. Queue-Level Keys Actually Used in Practice

Drawn from the fixture file, README examples, SKILL.md reference, and rule documentation.

### Keys present in the committed fixture
- `cwd` — top-level string, absolute path (`/tmp` in fixture)
- `tasks` — array of task objects

### Keys present in README/docs examples (not in fixture)
- `schedule` — cron string e.g. `"0 9 * * *"`, `"30 7 * * 1-5"`, `"0 8 * * *"`
- `reset` — string values: `daily`, `weekly`, `hourly`, `always`, `on-complete`; one plan doc shows a proposed (unimplemented) `12h` TTL form
- `message` — sub-block with nested keys `service`, `content`, `chat_id`

### Keys never used in actual files
All optional keys (`schedule`, `reset`, `message`) appear only in documentation examples and test scaffolding in plan docs, not in any committed queue file or fixture.

---

## 3. Task Structure Patterns

All task patterns are sourced from the committed fixture and README/docs examples.

### Pattern A: Named task with double-quoted inline prompt
```yaml
- name: review-auth
  prompt: "Review the authentication module in src/auth.py for security issues"
```
Source: `tests/fixtures/named-tasks.yaml:2-3`

### Pattern B: Unnamed task with double-quoted inline prompt
```yaml
- prompt: "echo unnamed task check"
```
Source: `tests/fixtures/named-tasks.yaml:7`

### Pattern C: Unquoted inline prompt (bare string)
```yaml
- prompt: fix the login bug in the auth service
- prompt: write unit tests for the payment module
```
Source: `README.md` Quick Start example

### Pattern D: Block literal prompt (`|`) — preserves line breaks
```yaml
- prompt: |
    Review the README and update it to reflect
    the current API endpoints and authentication flow
```
Source: `README.md` Quick Start example; also shown in `.claude/rules/queue-format.md`

### Pattern E: Block folded prompt (`>`) — newlines become spaces
```yaml
- prompt: >
    Refactor the authentication service to use JWT tokens
    instead of session cookies, updating all dependent endpoints.
```
Source: `README.md` queue format section

### Pattern F: Named task with block literal prompt
```yaml
- name: complex-task
  prompt: |
    Review the entire src/ directory and:
    1. Identify any security vulnerabilities
    2. Suggest performance improvements
    3. Check for consistent error handling
    Write findings to docs/review-2026.md
```
Source: `.claude/rules/queue-format.md` multi-line example

### Pattern G: Named task with unquoted inline prompt
```yaml
- name: morning-review
  prompt: "Review yesterday's commits and summarize in docs/daily.md"
```
Source: `.claude/rules/queue-format.md` automatic scheduling example; `skills/tq/SKILL.md`

---

## 4. Full Queue File Patterns (Composite Examples)

### Minimal (cwd + tasks, no options)
```yaml
cwd: /Users/yourname/projects/myapp
tasks:
  - prompt: fix the login bug in auth service
```
Source: `README.md`, `.claude/rules/queue-format.md`

### Multi-task with mixed named/unnamed and prompt styles
```yaml
cwd: /tmp
tasks:
  - name: review-auth
    prompt: "Review the authentication module in src/auth.py for security issues"
  - name: update-docs
    prompt: "Update README.md to reflect the latest API changes"
  - prompt: "echo unnamed task check"
```
Source: `tests/fixtures/named-tasks.yaml` (committed fixture — the only real file)

### With schedule and reset
```yaml
reset: daily
schedule: "0 9 * * *"
cwd: /Users/kk/Sites/myproject
tasks:
  - prompt: "Summarize yesterday's git activity into docs/daily-standup.md"
```
Source: `.claude/rules/queue-format.md`

### With message block
```yaml
cwd: /Users/yourname/projects/myapp
message:
  service: telegram
  content: summary
tasks:
  - prompt: refactor the auth module
```
Source: `README.md` notifications section

### Full composite (all optional keys present)
```yaml
schedule: "0 9 * * *"
reset: daily
cwd: /path/to/working/directory
message:
  service: telegram
  content: summary
tasks:
  - name: review-auth
    prompt: fix the login bug in auth service
  - prompt: write unit tests for payment module
```
Source: `skills/tq/SKILL.md` reference format

---

## 5. Parallel Execution Model as Demonstrated by Queue Files

The queue file structure **does not express any sequencing or dependency**. The tasks array is a flat list with no ordering fields, no `depends_on`, no `after`, no `parallel` flag.

The README Quick Start output shows all three tasks spawned in the same run with sequential epoch suffixes — implying they are launched in iteration order but run simultaneously:

```
[spawned] tq-fix-the-login-451234   -- fix the login bug in the auth service
[spawned] tq-write-unit-test-451235 -- write unit tests for the payment module
[spawned] tq-review-the-readme-451236 -- Review the README and update it to reflect
```

Source: `README.md:75-78`

The `--status` output confirms concurrent execution — two tasks show `running` while one is already `done`, all with start times one second apart:

```
done       tq-fix-the-login-451234     2026-03-06T09:01:02    fix the login bug...
running    tq-write-unit-test-451235   2026-03-06T09:01:03    write unit tests...
running    tq-review-the-readme-451236 2026-03-06T09:01:04    Review the README...
```

Source: `README.md:89-93`

The parser in `scripts/tq` iterates the tasks list and for each task either skips it (if state file says `done` or `running` with live session) or immediately spawns a new tmux session before moving to the next task. There is no wait, join, or barrier between spawns. Each task becomes an independent tmux session running `claude` in parallel.

---

## 6. Keys Parser Actually Reads (from scripts/tq)

The embedded Python parser in `scripts/tq` extracts these top-level keys by regex:

| Key | Regex | Line |
|-----|-------|------|
| `cwd` | `^cwd:\s*(.+)$` | ~156 |
| `reset` | `^reset:\s*(.+)$` | ~164 |
| task `name` | `^  - name:\s*(.*)` | ~210 |
| task `prompt` | `^(?:  - |    )prompt:\s*(.*)` | ~216 |

The `schedule` key is read by `tq-cron-sync`, not by `scripts/tq`. The `message` key is read by `tq-message`, not by the main parser.

---

## 7. Fixtures Proposed but Not Yet Created

The testing rules doc (`/.claude/rules/testing.md`) lists fixtures that are planned but do not exist on disk:

- `tests/fixtures/simple.yaml` — bare minimum cwd + single task
- `tests/fixtures/multiline.yaml` — block literal and block folded prompts

The `thoughts/shared/plans/2026-03-10-task-reset-ttl.md` proposes fixtures that also do not exist:
- `tests/fixtures/reset-ttl.yaml`
- `tests/fixtures/reset-on-complete.yaml`
- `tests/fixtures/no-reset.yaml`

Only `tests/fixtures/named-tasks.yaml` is committed.
