# tq Patches: Conditional Chrome + Reliable Summary Delivery

## Overview

Two targeted patches to `scripts/tq` and `scripts/tq-message`:

1. **Conditional Chrome** — Add `--no-chrome` flag so Telegram-originated tasks skip Chrome/browser tools
2. **Reliable Summary Delivery** — Replace `sleep 45` with file-based handshake + polling for summary messages

## Current State Analysis

- `scripts/tq` (lines 325-335): Every launcher unconditionally opens Chrome Profile 5 and passes `--chrome` to Claude
- `scripts/tq-message` (lines 299-313): Summary mode uses `sleep 45` hoping Claude finishes the `/tq-message` slash command in time
- `scripts/tq-telegram-poll` (line 127): Calls `tq --prompt "$MSG"` with no way to skip Chrome
- `.claude/commands/tq-message.md`: Slash command calls `tq-message --message` directly

### Key Discoveries:
- `--chrome` is NOT auth — auth is the OAuth token from keychain into `CLAUDE_CODE_OAUTH_KEY`. `--chrome` enables browser automation tools.
- The launcher Chrome block is at `scripts/tq:325-335` in the Python heredoc
- The arg parser is at `scripts/tq:14-25`
- The `TQ_NOTIFY` export is at `scripts/tq:341`
- The summary-mode block is at `scripts/tq-message:299-313`
- The slash command `allowed-tools: Bash(tq-message)` restricts Bash to only tq-message commands — the handshake file write must happen inside `tq-message`, not in the slash command

## Desired End State

1. `tq ~/.tq/queues/morning.yaml` works identically to today (Chrome opens, `--chrome` passed)
2. `tq --no-chrome --prompt "..."` skips Chrome entirely — no `open -a Chrome`, no `--chrome` flag
3. `tq-telegram-poll` automatically uses `--no-chrome`
4. Summary messages are delivered reliably via file-based handshake with 90s timeout + direct-send fallback
5. No duplicate messages (handshake file is consumed by whichever delivery path fires first)

### Verification:
- Run `tq --no-chrome --prompt "echo hello"` — verify generated `.launch.py` has no Chrome references
- Run `tq --prompt "echo hello"` — verify generated `.launch.py` still has Chrome
- Trigger summary delivery — verify handshake file `/tmp/tq-summary-<hash>.txt` is created and consumed

## What We're NOT Doing

- Not changing the default behavior (Chrome remains default for queue files)
- Not adding per-task `chrome:` YAML key (opt-out flag is sufficient)
- Not changing auth/OAuth handling
- Not modifying the on-stop.sh hook generation
- Not adding tests (though the YAML parser changes are zero — only launcher generation changes)

## Implementation Approach

Two independent patches, each touching different parts of the codebase. Can be implemented sequentially (Phase 1 then Phase 2) with manual testing between phases.

---

## Phase 1: Conditional Chrome (`--no-chrome` flag)

### Overview
Add `CHROME=1` variable, `--no-chrome` flag, export `TQ_CHROME` env var, and conditionally generate Chrome code in the Python launcher.

### Changes Required:

#### 1. Add `CHROME` variable initialization
**File**: `scripts/tq`
**Location**: Line 12, after `NOTIFY=""`
**Change**: Add `CHROME=1` to the variable block

```bash
NOTIFY=""
CHROME=1
```

#### 2. Add `--no-chrome` case to arg parser
**File**: `scripts/tq`
**Location**: Lines 14-25, in the `while/case` block
**Change**: Add case before the `--) shift; break ;;` line

```bash
    --no-chrome) CHROME=0; shift ;;
```

#### 3. Export `TQ_CHROME` for the Python parser
**File**: `scripts/tq`
**Location**: Line 341, next to `export TQ_NOTIFY="$NOTIFY"`
**Change**: Add export

```bash
export TQ_NOTIFY="$NOTIFY"
export TQ_CHROME="$CHROME"
```

#### 4. Conditionally generate Chrome code in the Python launcher
**File**: `scripts/tq`
**Location**: Lines 325-335 (inside the PYEOF heredoc)
**Change**: Replace the unconditional Chrome block with conditional logic

Current code (lines 325-335):
```python
        f.write('import shutil, subprocess, time\n')
        f.write('prompt = open(prompt_file).read()\n')
        f.write('# Open Chrome with Profile 5 (halbotkirchner@gmail.com) before connecting\n')
        f.write('subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])\n')
        f.write('time.sleep(2)\n')
        f.write('# Use reattach-to-user-namespace if available (macOS tmux keychain fix)\n')
        f.write('reattach = shutil.which("reattach-to-user-namespace")\n')
        f.write('if reattach:\n')
        f.write("    os.execvp(reattach, [reattach, 'claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])\n")
        f.write('else:\n')
        f.write("    os.execvp('claude', ['claude', '--settings', settings_file, '--dangerously-skip-permissions', '--chrome', prompt])\n")
```

Replacement:
```python
        use_chrome = os.environ.get('TQ_CHROME', '1') == '1'

        f.write('import shutil, subprocess, time\n')
        f.write('prompt = open(prompt_file).read()\n')
        if use_chrome:
            f.write('# Open Chrome with Profile 5 (halbotkirchner@gmail.com) before connecting\n')
            f.write('subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--profile-directory=Profile 5"])\n')
            f.write('time.sleep(2)\n')

        # Build claude args
        claude_args = "['claude', '--settings', settings_file, '--dangerously-skip-permissions'"
        if use_chrome:
            claude_args += ", '--chrome'"
        claude_args += ", prompt]"

        f.write('# Use reattach-to-user-namespace if available (macOS tmux keychain fix)\n')
        f.write('reattach = shutil.which("reattach-to-user-namespace")\n')
        f.write('if reattach:\n')
        f.write("    os.execvp(reattach, [reattach, " + claude_args[1:] + ")\n")
        f.write('else:\n')
        f.write("    os.execvp('claude', " + claude_args + ")\n")
```

#### 5. Pass `--no-chrome` in tq-telegram-poll
**File**: `scripts/tq-telegram-poll`
**Location**: Line 127
**Change**: Add `--no-chrome` flag

Current:
```bash
    tq --prompt "$MSG"
```

Replacement:
```bash
    tq --no-chrome --prompt "$MSG"
```

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq` passes
- [ ] `shellcheck scripts/tq-telegram-poll` passes
- [ ] `bash scripts/tq --no-chrome --prompt "echo hello" --name test-no-chrome` runs without errors
- [ ] Generated `.launch.py` file does NOT contain `Chrome` or `--chrome` when `--no-chrome` used
- [ ] `bash scripts/tq --prompt "echo hello" --name test-with-chrome` still generates Chrome code in `.launch.py`

#### Manual Verification:
- [ ] `tq ~/.tq/queues/morning.yaml` still opens Chrome and passes `--chrome` (unchanged behavior)
- [ ] `tq --no-chrome --prompt "list files"` spawns tmux session without Chrome opening
- [ ] Send Telegram message, verify tmux session spawns without Chrome

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Reliable Summary Delivery (replace `sleep 45`)

### Overview
Replace the `sleep 45` approach with a file-based handshake: `tq-message` polls for a handshake file while the `/tq-message` slash command writes to it. The `tq-message` script also writes the handshake file itself when called with `--message`, so the slash command only needs `Bash(tq-message)` permissions.

### Design Decision: Avoiding Duplicate Messages

The slash command's `allowed-tools: Bash(tq-message)` prevents it from running arbitrary bash commands like `echo > /tmp/file`. Instead of expanding permissions, we have `tq-message` itself write the handshake file when called with `--message`. This means:

1. Polling parent (`tq-message` in summary mode) creates handshake path, polls for file
2. Claude's `/tq-message` slash command calls `tq-message --task HASH --queue FILE --message "summary"`
3. That `tq-message --message` invocation writes the handshake file AND delivers directly
4. The polling parent sees the file, reads `MESSAGE_TEXT`, but checks if already delivered

To avoid duplicates: the polling parent, upon finding the handshake file, reads it but does NOT deliver again — it just cleans up and exits. The direct `--message` invocation already delivered. If the poll times out (no file after 90s), THEN the polling parent delivers a fallback "details" message.

### Changes Required:

#### 1. Add handshake file write to `tq-message` when called with `--message`
**File**: `scripts/tq-message`
**Location**: Just before the final `deliver` call (before line 316)
**Change**: Write handshake file when `--message` was provided and we have a task hash

Add before `# Deliver message if we have one`:
```bash
# Write handshake file for summary polling (if applicable)
if [[ -n "$TASK_HASH" ]]; then
  echo "$MESSAGE_TEXT" > "/tmp/tq-summary-${TASK_HASH}.txt"
fi
```

#### 2. Replace summary-mode block with polling
**File**: `scripts/tq-message`
**Location**: Lines 299-313
**Change**: Replace `sleep 45` + `exit 0` with poll loop + fallback

Current code (lines 299-313):
```bash
# Summary mode with a live session: ask Claude to generate and send
if [[ "$CONTENT" == "summary" && -n "$SESSION" && -z "$MESSAGE_TEXT" ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    # Pass hash and queue path as arguments to the slash command
    tmux send-keys -t "$SESSION" "/tq-message ${TASK_HASH} ${QUEUE_FILE}" Enter
    # Give Claude time to summarize and call back tq-message --message
    sleep 45
    # Close the session
    tmux send-keys -t "$SESSION" "" Enter
    exit 0
  else
    # Session gone — fall back to details
    MESSAGE_TEXT="$(build_message "details" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "")"
  fi
fi
```

Replacement:
```bash
# Summary mode with a live session: ask Claude to write summary via slash command
if [[ "$CONTENT" == "summary" && -n "$SESSION" && -z "$MESSAGE_TEXT" ]]; then
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    HANDSHAKE_FILE="/tmp/tq-summary-${TASK_HASH}.txt"
    rm -f "$HANDSHAKE_FILE"

    # Tell Claude to generate summary (slash command calls tq-message --message which writes handshake file + delivers)
    tmux send-keys -t "$SESSION" "/tq-message ${TASK_HASH} ${QUEUE_FILE}" Enter

    # Poll for the handshake file (max 90 seconds, check every 3s)
    WAITED=0
    while [[ ! -f "$HANDSHAKE_FILE" && "$WAITED" -lt 90 ]]; do
      sleep 3
      WAITED=$(( WAITED + 3 ))
    done

    if [[ -f "$HANDSHAKE_FILE" ]]; then
      # Slash command already delivered the message — just clean up
      rm -f "$HANDSHAKE_FILE"
      exit 0
    else
      # Timed out — fall back to details
      MESSAGE_TEXT="$(build_message "details" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "")"
    fi
  else
    # Session gone — fall back to details
    MESSAGE_TEXT="$(build_message "details" "$TASK_HASH" "$STATE_FILE" "$PROMPT_FILE" "")"
  fi
fi
```

Key difference from the original spec: when the handshake file is found, we `exit 0` instead of re-delivering, because the `tq-message --message` invocation (from the slash command) already delivered the message. This avoids duplicate messages.

#### 3. Update the `/tq-message` slash command
**File**: `.claude/commands/tq-message.md`
**Change**: Minimal update — the slash command still calls `tq-message --message`, which now also writes the handshake file. Just clean up the instructions slightly.

Full replacement:
```markdown
---
name: tq-message
description: Write a tq task completion summary to the configured messaging service. Called automatically by tq on-stop hooks.
tags: tq, notify, message, summary
allowed-tools: Bash(tq-message)
---

Arguments: $ARGUMENTS

You have just completed a tq task. Parse the arguments to get the task hash and queue file:
- First argument: task hash (8-char string, e.g. `a1b2c3d4`)
- Second argument: queue file path (absolute path to a .yaml file)

## Steps

1. Write a 2-3 sentence summary of what you accomplished in this session. Be specific: mention what files were changed, what was fixed or built, and any notable outcome.

2. Send the summary:

```bash
tq-message --task "<first argument>" --queue "<second argument>" --message "<your summary here>"
```

Replace the placeholders with the actual hash, queue file path, and your written summary.

Do not explain what you are doing. Just write the summary and run the command.
```

### Success Criteria:

#### Automated Verification:
- [ ] `shellcheck scripts/tq-message` passes
- [ ] `tq-message --task abc12345 --queue /tmp/test.yaml --message "test summary"` writes `/tmp/tq-summary-abc12345.txt`
- [ ] The handshake file contains the message text

#### Manual Verification:
- [ ] Queue a task with `message: content: summary` — verify summary is delivered to Telegram
- [ ] Kill Claude session before summary completes — verify fallback to `details` message after 90s timeout
- [ ] Verify no duplicate messages when summary succeeds normally

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation.

---

## Testing Strategy

### Phase 1 Tests:
1. Generate a `.launch.py` with default flags, grep for `Chrome` and `--chrome` — should be present
2. Generate a `.launch.py` with `--no-chrome`, grep — should be absent
3. Run `tq-telegram-poll` in dry-run mental model — verify `--no-chrome` is in the command

### Phase 2 Tests:
1. Call `tq-message --task HASH --queue FILE --message "hello"` — verify `/tmp/tq-summary-HASH.txt` exists with "hello"
2. Simulate summary mode: create a tmux session, set content=summary, verify polling loop works
3. Verify timeout fallback: don't write handshake file, confirm details message after 90s

### Edge Cases:
- `--no-chrome` combined with `--status` (should be ignored — status mode doesn't spawn tasks)
- `--no-chrome` combined with queue file (should work — applies to all tasks in queue)
- Handshake file already exists from previous run (cleaned up by `rm -f` before polling)
- Multiple tasks completing simultaneously (each has unique hash, so separate handshake files)

## References

- `scripts/tq:14-25` — arg parser
- `scripts/tq:325-335` — Chrome launcher block in Python heredoc
- `scripts/tq:341` — `TQ_NOTIFY` export
- `scripts/tq-message:299-313` — summary mode block
- `scripts/tq-telegram-poll:127` — `tq --prompt` call
- `.claude/commands/tq-message.md` — slash command definition
