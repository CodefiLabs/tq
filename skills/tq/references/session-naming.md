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

## Edge Cases

| Input | Session Base | Reason |
|-------|-------------|--------|
| 1-word prompt: `deploy` | `deploy` | Uses the single word as-is |
| 2-word prompt: `fix bug` | `fix-bug` | Uses both words (fewer than 3) |
| Empty prompt | (empty string) | Produces `tq--<epoch>` — malformed; avoid empty prompts |
| Special chars: `fix "the" bug!` | `fix-the-bug-` | Quotes and punctuation replaced with `-` |
| Very long name field | Truncated to 20 chars | `cut -c1-20` limits length |

## Notes

- The epoch suffix prevents collision when the same prompt is re-queued after a reset
- tmux session names must not contain `.` or `:` -- the character replacement handles this
- The `-` separator between base and epoch is always present; if the base ends with `-`, strip it first to avoid `--`
- The `tail -c 6` approach for epoch suffix always produces 6 digits since Unix timestamps are 10+ digits

## Conversation Mode Session Names

Conversation sessions use a slug-based naming scheme with no epoch suffix:

| Type | Pattern | Example |
|------|---------|---------|
| Orchestrator | `tq-orchestrator` (fixed) | `tq-orchestrator` |
| Child session | `tq-conv-<slug>` | `tq-conv-fix-auth` |
| Child window | `<slug>` | `fix-auth` |

Slugs are short kebab-case names (2-4 words) chosen by the orchestrator Claude when creating a new conversation. Examples: `fix-auth-bug`, `refactor-api`, `update-docs`.

Since there is no epoch suffix, conversation session names are unique by slug. Starting a session with an already-active slug reuses the existing session.
