# Testing

## Current State

**No tests exist.** Coverage is 0%. This severely limits AI effectiveness — core logic
(the YAML parser, idempotency state machine, dead-session detection, hash-based task identity)
is entirely unverified. Make conservative, targeted edits and test manually with a real
queue file until a test suite exists.

## Recommended Frameworks

- **Bash scripts** (`tq`, `tq-install.sh`): `bats-core` (Bash Automated Testing System)
  - Install: `brew install bats-core`
  - Test files live in `tests/` with `.bats` extension
- **Python YAML parser**: `pytest`
  - The embedded Python in `scripts/tq` should be extracted to a testable module first

## Priority Test Targets (in order)

1. **Custom YAML parser** — the hand-rolled regex parser in `scripts/tq` handles inline prompts,
   block-literal (`|`), block-folded (`>`), quoted strings, and multi-line prompts. Edge cases:
   prompts with single quotes, prompts with special characters, empty tasks list, missing `cwd`.

2. **Idempotency state machine** — given a state file with `status=done`, tq must skip.
   Given `status=running` with a live tmux session, tq must skip.
   Given `status=running` with a dead session, tq must flip to `done` and skip.
   Given no state file, tq must spawn.

3. **Dead session detection** — both `tq` (run mode) and `tq --status` detect stale `running` state
   by checking `tmux has-session`. Test with a mocked tmux that returns non-zero.

4. **Hash stability** — `hashlib.sha256(prompt.encode()).hexdigest()[:8]` must be deterministic.
   The same prompt must always produce the same 8-char hash across runs.

## Test Fixtures

Queue YAML files are the natural fixture format. Sample fixtures to create:

```yaml
# tests/fixtures/simple.yaml
cwd: /tmp
tasks:
  - prompt: fix the login bug
```

```yaml
# tests/fixtures/multiline.yaml
tasks:
  - prompt: |
      Write unit tests for
      the payment module
  - prompt: >
      Refactor the auth
      service for clarity
```

5. **Conversation registry operations** — `tq-converse` registry subcommands:
   set/get/remove sessions, track-msg/lookup-msg message ID mapping,
   update-status. Test with a temp registry.json file.

6. **3-tier message routing** — `tq-telegram-poll` routing logic:
   reply_to matches registry → Tier 1, #slug prefix → Tier 2, fallback → Tier 3.
   Test with mock `tq-converse` and a pre-populated registry.

7. **tq-message reply threading** — `--reply-to` flag correctly adds
   `reply_to_message_id` to the Telegram API call. Test with mock curl.

## What NOT to Test

- macOS keychain reads (mock `security` CLI instead)
- tmux session spawning in CI (mock `tmux` instead)
- `claude` CLI invocation (the launcher is generated; test the generation, not execution)
- Orchestrator Claude's routing decisions (these are AI-powered and non-deterministic)
