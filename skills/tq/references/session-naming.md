# tq Session Naming Reference

## Algorithm

Given a prompt string, derive a tmux session name and window name as follows:

### Session Name
1. Take the first 3 words of the prompt
2. Lowercase everything
3. Replace any non-`[a-z0-9]` character with `-`
4. Strip trailing `-` characters
5. Truncate to 20 characters
6. Append `-<epoch-suffix>` (last 6 digits of Unix epoch)

### Window Name
1. Take the first 2 words of the prompt
2. Same lowercasing and character replacement as above
3. Truncate to 15 characters (no epoch suffix)

## Examples

| Prompt | Session | Window |
|--------|---------|--------|
| `fix the login bug in auth service` | `fix-the-login-<epoch>` | `fix-the` |
| `write unit tests for payment module` | `write-unit-tests-<epoch>` | `write-unit` |
| `Refactor Auth Module` | `refactor-auth-module-<epoch>` | `refactor-auth` |
| `check LinkedIn saved posts` | `check-linkedin-saved-<epoch>` | `check-linkedin` |

## Bash Implementation

```bash
EPOCH_SUFFIX="$(date +%s | tail -c 6)"
SESSION_BASE="$(echo "$PROMPT" | awk '{print $1" "$2" "$3}' \
  | tr '[:upper:]' '[:lower:]' \
  | tr -cs 'a-z0-9' '-' \
  | sed 's/-*$//' \
  | cut -c1-20)"
SESSION="${SESSION_BASE}-${EPOCH_SUFFIX}"
WINDOW="$(echo "$PROMPT" | awk '{print $1" "$2}' \
  | tr '[:upper:]' '[:lower:]' \
  | tr -cs 'a-z0-9' '-' \
  | sed 's/-*$//' \
  | cut -c1-15)"
```

## Notes

- Epoch suffix prevents collision when the same prompt is re-queued after a reset
- tmux session names must not contain `.` or `:` — the character replacement handles this
- The `-` separator between base and epoch is always present; if the base ends with `-`, it gets stripped first to avoid `--`

## Conversation Mode Session Names

Conversation sessions use a different naming scheme — slug-based, no epoch suffix:

| Type | Pattern | Example |
|------|---------|---------|
| Orchestrator | `tq-orchestrator` (fixed) | `tq-orchestrator` |
| Child session | `tq-conv-<slug>` | `tq-conv-fix-auth` |
| Child window | `<slug>` | `fix-auth` |

Slugs are short kebab-case names (2-4 words) chosen by the orchestrator Claude when a
new conversation is created. Examples: `fix-auth-bug`, `refactor-api`, `update-docs`.

Since there is no epoch suffix, conversation session names are unique by slug. Starting
a session with an already-active slug will reuse the existing session.
