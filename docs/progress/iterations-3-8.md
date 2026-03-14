# Iterations 3-8: Direct Improvements by Lead

Date: 2026-03-14

## Iteration Focus Areas

| Iteration | Focus | Files Improved |
|-----------|-------|----------------|
| 3 | Bottom 3 rewrite | tq-reply.md, chrome-integration.md, review.md |
| 4 | Next bottom tier | install.md, init.md, setup-telegram.md |
| 5 | Mid-tier polish | todo.md, tq-message.md, schedule.md |
| 6 | Upper-mid improvements | jobs.md, converse.md, health.md |
| 7 | Top-tier polish | pause.md, unschedule.md, SKILL.md |
| 8 | Reference polish | SKILL.md, cron-expressions.md, session-naming.md |

## Key Changes

### Iteration 3
- **tq-reply.md**: Complete rewrite — added argument-hint, simplified slug detection to read `.tq-converse.md` marker file with tmux fallback, consolidated steps 3+4 into single "Save and send" step
- **chrome-integration.md**: Full restructure — added Overview section, When Chrome Is Needed table, Troubleshooting table, Related section
- **review.md**: Added argument-hint `[--fix]`, priority-ordered checklist table, Read tool for rules files, auto-fix option

### Iteration 4
- **install.md**: Added argument-hint `[--check]`, check-only mode, summary table format, symlink integrity verification
- **init.md**: Added `--refresh` flag, condition table for directory collection, project type detection table, summary table
- **setup-telegram.md**: Added permission verification in step 0, summary table in step 6

### Iteration 5
- **todo.md**: Condensed step 1 (3 sub-items → concise prose), added structured summary table in step 6
- **tq-message.md**: Added binary validation step, strict argument format validation, summary rules table
- **schedule.md**: Referenced cron-expressions.md instead of inline mapping, added /pause to Related footer

### Iteration 6
- **jobs.md**: Added prefix collision avoidance (`/<name>\.yaml`), `test` tool for file existence, "sweep" label for status-check
- **converse.md**: Added subcommand dispatch table, post-execution verification for start/spawn, `tmux` tool
- **health.md**: Replaced verbose check 5/6 with structured tables, log rotation warning

### Iteration 7-8
- **pause.md**: Fixed grep pattern for prefix safety, concise Related footer
- **unschedule.md**: Added `ls` tool, required argument hint
- **SKILL.md**: Added troubleshooting table, concise reference links, queue creation hint
