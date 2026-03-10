---
plan: thoughts/shared/plans/2026-03-09-named-task-yaml-parser.md
started: 2026-03-09
status: complete
---

# Implementation Progress: named-task-yaml-parser

**Plan**: thoughts/shared/plans/2026-03-09-named-task-yaml-parser.md
**Started**: 2026-03-09

---

## Phase 1

**Completed**: 2026-03-09
**Status**: COMPLETE
**Commits**: ceadbc1
**Tests**: PASS

### Summary
Fixed the hand-rolled YAML parser in `scripts/tq` to correctly handle tasks where `name:` appears before `prompt:`. The root cause was that the regex `r'^  - prompt:\s*(.*)'` only matched when `prompt` was the first key in a list item (2-space + list marker), but not the 4-space continuation form used when `name:` comes first. The fix adds a `current_name` tracking variable that resets on each new list item, captures the `name:` value when present, includes it in the task tuple and JSON output, and uses it for tmux session/window naming when available (falling back to the existing prompt-word-based naming for unnamed tasks). The `--prompt` mode 2-tuple was also updated to a 3-tuple to match the new iteration.

### Manual Test Results
- `shellcheck scripts/tq` — no errors
- `bash scripts/tq tests/fixtures/named-tasks.yaml` — 3 [spawned] lines confirmed
- `tmux ls` confirmed sessions: `tq-review-auth-*`, `tq-update-docs-*`, `tq-echo-unnamed-task-*`
