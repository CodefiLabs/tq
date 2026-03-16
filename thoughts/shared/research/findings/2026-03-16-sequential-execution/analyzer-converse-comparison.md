# tq-converse Execution Model — Analysis

Source file: `/Users/kk/Sites/codefi/tq/scripts/tq-converse`

---

## 1. How Child Sessions Are Spawned (`spawn` subcommand)

Lines 399–508.

The `spawn` subcommand takes a `<slug>` plus optional `--cwd`, `--desc`, and `--msg-id` flags.

**Steps in order:**

1. Derives the tmux session name as `tq-conv-<slug>` (line 421).
2. Checks for an already-running session via `tmux has-session`; exits 0 without error if it exists (lines 424–427). This is idempotency — spawn is a no-op if the session is live.
3. Creates `~/.tq/conversations/sessions/<slug>/` with subdirectories `inbox/`, `outbox/`, `hooks/` (line 431).
4. Writes `.tq-converse.md` into that directory — the instruction document Claude will read on first start (lines 434–455). It embeds the slug and the `current-slug` marker file path.
5. Writes `current-slug` marker file (line 458) so the `/tq-reply` slash command can identify which session is responding.
6. Calls `write_session_settings` (line 462) which writes `settings.json` and two hook scripts:
   - `hooks/on-stop.sh` — calls `tq-converse update-status <slug> stopped` when the Claude session terminates (lines 175–192).
   - `hooks/on-notification.sh` — logs notifications to stdout (lines 196–203).
7. Registers the session in `registry.json` via `registry_op set` with fields: `description`, `tmux`, `cwd`, `conv_dir`, `created`, `last_active`, `status=active` (lines 469–481).
8. Optionally calls `registry_op track-msg` to map the triggering Telegram message ID to this slug (lines 484–487).
9. Creates the working directory if it does not exist (line 489).
10. Starts a new detached tmux session (`tmux new-session -d -s "$CHILD_SESSION" -n "$SLUG"`) (line 491).
11. Calls `inject_auth` (line 493), which writes `export CLAUDE_CODE_OAUTH_KEY='...'` into the tmux pane via `send-keys` (lines 153–162).
12. Sends `cd '<cwd>'` into the pane (line 495).
13. Sends `claude --settings '<settings_file>' --dangerously-skip-permissions` (lines 497–498).
14. Sleeps 3 seconds, then sends a one-line primer: `Read <path>/.tq-converse.md — those are your instructions. Acknowledge with 'ready'.` (lines 500–502).

Each child session is independent. No parent-child process relationship exists between sessions — they are all peers under tmux. The 3-second sleep is a fixed delay, not a readiness check.

---

## 2. How Messages Are Routed to Sessions (`route` subcommand)

Lines 513–552.

The `route` subcommand takes `<slug>` and `<message>` (all remaining positional args joined as `$*`).

**Steps:**

1. Derives `CHILD_SESSION="tq-conv-<slug>"` (line 523).
2. Checks the session is live with `tmux has-session`; errors and exits 1 if not (lines 525–528).
3. Logs the message to `~/.tq/conversations/sessions/<slug>/inbox/<YYYYMMDD-HHMMSS>.txt` (lines 533–534).
4. Updates `last_active` field in the registry (line 537).
5. Writes the message to a temp file via `printf '%s'` (lines 540–541).
6. Injects the message into the tmux pane using `tmux load-buffer <tmpfile>` + `tmux paste-buffer -t <session>:<window>` + `sleep 0.2` + `tmux send-keys ... Enter` (lines 543–546). This avoids quoting issues with special characters.
7. Deletes the temp file (line 548).

There is no feedback mechanism in `route` itself — the command fires and returns `"Routed to <slug>"`. The child session's Claude processes the message asynchronously at its own pace. There is no acknowledgement, no polling, no blocking wait.

The `send` subcommand (lines 557–581) uses the same `load-buffer` / `paste-buffer` pattern to deliver messages to the orchestrator session at `tq-orchestrator:orchestrator`, with no structural difference from `route`.

---

## 3. Registry Operations

Lines 15–117 (`ensure_registry`, `registry_op`).

**Storage format:** A single flat JSON file at `~/.tq/conversations/registry.json` with two top-level keys:
- `sessions` — map of `slug → session metadata object`
- `messages` — map of `telegram_msg_id → slug`

**`ensure_registry`** (lines 15–19): creates the file with empty `{"sessions":{},"messages":{}}` if it does not exist.

**`registry_op`** (lines 21–117): all registry operations go through a single embedded Python script executed via a mktemp temp file. Operations:

| Operation | Arguments | Effect |
|-----------|-----------|--------|
| `list` | — | Prints `slug\tstatus\ttmux\tdesc` for all sessions |
| `get` | slug | Prints JSON for one session; exits 1 if not found |
| `set` | slug, json | Writes or overwrites the full session record |
| `update-field` | slug, field, value | Updates one field in an existing session record |
| `remove` | slug | Deletes the session record and all its message mappings |
| `track-msg` | slug, msg_id | Adds `msg_id → slug` to the messages map |
| `lookup-msg` | msg_id | Returns the slug for a message ID; exits 1 if not found |
| `dump` | — | Pretty-prints the full registry JSON |
| `slugs` | — | Prints all slugs |
| `active-slugs` | — | Prints slugs where status == "active" |
| `summary` | — | Prints `slug\tdescription\tcwd` for active sessions (used by `list` command) |

Session status values in use: `active` (set at spawn), `stopped` (set by on-stop.sh hook or explicit `stop` command), `dead` (set transiently during `status` display when tmux session is gone but registry still shows active).

---

## 4. Sequential / Chaining Logic

There is none.

Each child session runs independently in its own tmux session. There is no concept of task ordering, prerequisites, or chaining between sessions. The orchestrator does not wait for one session to finish before spawning or routing to another. All child sessions are alive simultaneously and process messages as they arrive.

The only sequencing within a single interaction is:
- Within `spawn`: a 3-second `sleep` after starting `claude` before sending the primer instruction (line 500). This is a hardcoded wait, not coordination logic.
- Within `route`: a 0.2-second `sleep` between `paste-buffer` and `send-keys Enter` (line 545), which is also just a timing buffer.

---

## 5. Relationship Between Orchestrator and Child Sessions

The orchestrator (`tq-orchestrator` tmux session) is a peer Claude Code session, not a process supervisor. It does not spawn children via fork/exec, does not hold file descriptors to them, and does not receive their output.

The relationship is mediated entirely through `tq-converse` CLI invocations that the orchestrator's Claude is instructed to run as bash commands:

- Orchestrator calls `tq-converse list` or `tq-converse registry` to read state.
- Orchestrator calls `tq-converse spawn <slug> ...` to create a child.
- Orchestrator calls `tq-converse route <slug> <message>` to forward a user message.
- Orchestrator calls `tq-converse track-msg <slug> <msg-id>` to maintain Telegram threading.

The orchestrator is told explicitly (lines 331, 341): "Do NOT use /tq-reply to confirm routing or spawning — the child session will reply directly."

Children communicate back to the user via `/tq-reply` (a `.claude/commands/` slash command), which calls `tq-message --reply-to` to send to Telegram. Children do not communicate back to the orchestrator — there is no return channel. The orchestrator is a dispatcher, not a supervisor.

The orchestrator's Claude is AI-powered and makes routing decisions itself (which session to route to, whether to spawn a new one). The `spawn` decision is not automated by code — it is driven by the orchestrator's LLM judgment.

---

## 6. Session Completion Detection

Completion is detected via a **stop hook**, not polling.

When `write_session_settings` runs (lines 167–231), it writes `hooks/on-stop.sh` which contains:

```bash
tq-converse update-status "$SLUG" stopped
```

This hook is registered in `settings.json` under the `Stop` hook event (lines 205–229). Claude Code fires the `Stop` hook when the Claude session ends (either normally via `/exit` or via process termination).

The hook calls `tq-converse update-status <slug> stopped`, which translates to `registry_op update-field <slug> status stopped` (lines 705–713), writing the new status to `registry.json`.

There is a secondary detection path in the `status` command (lines 625–655): when displaying session status, if the registry shows `status=active` but `tmux has-session` returns non-zero, the status display shows `dead` and updates the registry to `stopped` (lines 647–649). This is a lazy reconciliation on `tq-converse status` invocation, not a background monitor.

For the orchestrator session itself, the same `write_session_settings` is called with an empty slug (line 368), so the on-stop.sh hook logs a message but skips the registry update (lines 183–185 check `if [[ -n "$SLUG" ]]`).

There is no polling loop, no background watchdog, and no callback from child to orchestrator when work is complete. Completion is registered passively via the Stop hook or discovered lazily via `status`.

---

## Summary: Queue Mode vs Conversation Mode

| Dimension | Queue Mode (`tq`) | Conversation Mode (`tq-converse`) |
|-----------|-------------------|-----------------------------------|
| Session identity | SHA-256 hash of prompt | User-chosen kebab-case slug |
| Session lifetime | Fire-and-forget; runs once to completion | Persistent; receives multiple messages |
| Sequencing | No — all tasks spawned independently | No — all child sessions run in parallel |
| State storage | Per-task flat file at `<queue-dir>/.tq/<queue-basename>/<hash>` | Registry JSON at `~/.tq/conversations/registry.json` |
| Message input | Prompt file loaded at session start | Live injection via `tmux load-buffer` + `paste-buffer` |
| Completion detection | `on-stop.sh` writes `status=done` to task state file | `on-stop.sh` calls `tq-converse update-status stopped` |
| Orchestration | None — `tq` script itself loops over tasks | Orchestrator Claude session routes messages via CLI |
| Reply channel | `tq-message` at task end (optional) | `/tq-reply` slash command inside child session |
