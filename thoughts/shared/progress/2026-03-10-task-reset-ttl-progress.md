---
plan: thoughts/shared/plans/2026-03-10-task-reset-ttl.md
started: 2026-03-10
status: in_progress
---

# Implementation Progress: task-reset-ttl

**Plan**: thoughts/shared/plans/2026-03-10-task-reset-ttl.md
**Started**: 2026-03-10

---

## Phase 1

**Completed**: 2026-03-10
**Status**: COMPLETE
**Commits**: 0ddfb2f, 5e36e3b
**Tests**: PASS

### Summary
All 5 changes from the plan were implemented in `scripts/tq`: (1) Python parser now extracts top-level `reset:` key into `reset_mode`. (2) `reset_mode` is included in every per-task JSON output line. (3) The `--prompt` mode tuple was updated from 3-tuple to 4-tuple to stay consistent. (4) The `on-stop.sh` generator now appends `echo "completed=$(date +%s)"` after marking `status=done`. (5) The `--status` dead-session flip also writes `completed=` timestamp. Additionally, `RESET_MODE` is extracted in the bash dispatch loop with a `shellcheck disable` comment since it is not yet consumed until Phase 2.

### Sub-Agents Used
- Direct implementation (no sub-agents needed)

---

## Phase 2

**Completed**: 2026-03-10
**Status**: COMPLETE
**Commits**: dee3a9b
**Tests**: PASS

### Summary
The TTL-based reset logic was added to the dispatch loop in `scripts/tq`. When a task has `status=done` and `RESET_MODE` is a duration string (not blank, not `on-complete`), the code now reads the `completed=` epoch from the state file, converts the duration to seconds via an inline `python3 -c` call (supporting `h`, `d`, `m` suffixes), and compares against `date +%s`. If the TTL has elapsed, the state file is deleted and the loop falls through to spawn logic showing `[reset] (TTL expired)`. If not yet expired — or if `COMPLETED` is missing — it shows `[done]` as before. The `# shellcheck disable=SC2034` comment added in Phase 1 was removed since `RESET_MODE` is now actively used.

---

## Phase 3

**Completed**: 2026-03-10
**Status**: COMPLETE
**Commits**: 26ba1d4
**Tests**: PASS

### Summary
Phase 3 implemented the `on-complete` reset mode in the `on-stop.sh` generator. Three changes were made: (1) `RESET_MODE=` is now assigned immediately after `STATE_FILE=` at the top of the stop script; (2) the mark-done block is now conditional — when `RESET_MODE == "on-complete"` it runs a no-op (`:`), deferring action until after tq-message; (3) a cleanup block appended after the tq-message section deletes the state file when `RESET_MODE == "on-complete"`. The tq-message block reads `$STATE_FILE` for the session name before the deletion block runs, so the session name is captured correctly. Shellcheck passes cleanly.

---

## Phase 4

**Completed**: 2026-03-10
**Status**: COMPLETE
**Commits**: 89c0e50
**Tests**: PASS

### Summary
Phase 4 adds automatic `reset:` TTL inference to both the `/schedule` and `/todo` commands. When either command writes a cron schedule to crontab, it now also computes a reset TTL at 50% of the minimum firing interval and inserts `reset: <N>h` (or `reset: 3d` for weekly) as the first line of the queue YAML. Both commands use identical inference rules. Neither command overwrites an existing `reset:` line, and `/todo` skips computation for one-off tasks. The `allowed-tools` list in `schedule.md` was extended to include `Read` and `Write`.

---
