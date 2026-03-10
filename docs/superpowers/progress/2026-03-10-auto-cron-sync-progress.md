---
plan: docs/superpowers/plans/2026-03-10-auto-cron-sync.md
started: 2026-03-10T00:00:00Z
status: in_progress
---

# Implementation Progress: auto-cron-sync

**Plan**: docs/superpowers/plans/2026-03-10-auto-cron-sync.md
**Started**: 2026-03-10

---

## Chunk 1: Create `scripts/tq-cron-sync`

**Completed**: 2026-03-10
**Status**: COMPLETE
**Commits**: 4451c62
**Tests**: PASS

### Summary
Created `scripts/tq-cron-sync` (92 lines), a new Bash script that scans `~/.tq/queues/*.yaml` for `schedule:` keys using embedded Python via a temp file, strips all `# tq-managed:` lines from the existing crontab, and rebuilds them fresh on every run. Each scheduled queue gets a run entry (using the queue's own cron expression) and a `*/30 * * * *` status-check entry; a self-watcher entry (`*/20 * * * *` by default, configurable via `--interval`) is always appended. A broken symlink for `tq` at `/opt/homebrew/bin/tq` was fixed to point to `codefi/tq/scripts/tq`. All six smoke test scenarios passed.

---
