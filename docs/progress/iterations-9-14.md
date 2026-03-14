# Iterations 9-14: Command & Skill File Improvements

Date: 2026-03-14

## Iteration Focus Areas

| Iteration | Focus | Bottom 3 Improved |
|-----------|-------|-------------------|
| 9 | Cross-reference consistency | health.md, review.md, unschedule.md + cron-expressions.md, session-naming.md |
| 10 | Error handling completeness | init.md, todo.md, health.md |
| 11 | Argument validation | pause.md, schedule.md, setup-telegram.md + health.md, todo.md, tq-message.md |
| 12 | LLM executability (step numbering) | pause.md, schedule.md, unschedule.md |
| 13 | Tool permission scoping | setup-telegram.md, tq-reply.md, todo.md |
| 14 | Output format standardization | converse.md, pause.md, init.md |

## Before/After Scores (Weighted Composite)

Scoring criteria weights: Triggering 30%, Instruction Quality 25%, Completeness 20%, Convention 15%, Conciseness 10%.

| File | Before (It8) | After (It14) | Delta | Iterations Touched |
|------|-------------|-------------|-------|-------------------|
| converse.md | 78 | 82 | +4 | 14 |
| health.md | 72 | 80 | +8 | 9, 10, 11 |
| init.md | 71 | 79 | +8 | 10, 14 |
| install.md | 79 | 79 | 0 | (untouched) |
| jobs.md | 78 | 78 | 0 | (untouched) |
| pause.md | 68 | 79 | +11 | 11, 12, 14 |
| review.md | 73 | 76 | +3 | 9 |
| schedule.md | 72 | 79 | +7 | 11, 12 |
| setup-telegram.md | 76 | 80 | +4 | 11, 13 |
| todo.md | 74 | 79 | +5 | 10, 11, 13 |
| tq-message.md | 77 | 79 | +2 | 11 |
| tq-reply.md | 72 | 78 | +6 | 13 |
| unschedule.md | 69 | 77 | +8 | 9, 12 |
| SKILL.md | 82 | 82 | 0 | (untouched) |
| chrome-integration.md | 74 | 74 | 0 | (untouched) |
| cron-expressions.md | 71 | 74 | +3 | 9 |
| session-naming.md | 72 | 75 | +3 | 9 |

## Specific Changes by Iteration

### Iteration 9: Cross-reference consistency

**Problem**: Navigation rings were incomplete. Several commands referenced by others had no Related footer linking back, creating dead ends.

**Changes**:
- **health.md**: Added `Related:` footer linking to `/install`, `/converse`, `/setup-telegram`, `/init`, `/jobs` -- the 5 commands that reference health.
- **review.md**: Extended Related footer from 2 links to 4 (added `/todo`, `/converse`).
- **unschedule.md**: Added `/pause` to Related footer (pause already linked to unschedule, creating bidirectional link).
- **cron-expressions.md**: Added `## Related` section linking to SKILL.md, session-naming.md, and all cron-related commands.
- **session-naming.md**: Added `## Related` section linking to SKILL.md, chrome-integration.md, cron-expressions.md, and relevant commands.

**Impact**: All 13 commands now form complete navigation rings. All 3 reference files now cross-reference each other and link back to SKILL.md.

### Iteration 10: Error handling completeness

**Problem**: Some commands lacked explicit "stop" directives for failure conditions, leaving Claude to improvise error handling.

**Changes**:
- **init.md**: Added stop directive when all paths fail validation ("No valid directories to scan."). Added stop on workspace map write failure.
- **todo.md**: Added stop directive when `pwd` fails. Added stop on queue file write failure.
- **health.md**: Added explicit instruction "Never stop on individual check failures -- run all checks and report aggregate results." This documents the intentional design choice that health should always run all checks.

**Impact**: Every command now has explicit stop/continue semantics for every failure path.

### Iteration 11: Argument validation

**Problem**: `argument-hint` values were inconsistent -- some quoted, some not; some used `<>` for optional args that were actually optional.

**Changes**:
- **pause.md**: Changed `<queue-name>` (required syntax) to `"[queue-name]"` (optional, quoted) -- matches actual behavior where no arg prompts a selection.
- **schedule.md**: Added quotes: `[queue-name] [schedule]` -> `"[queue-name] [schedule]"`.
- **setup-telegram.md**: Added quotes: `[bot-token]` -> `"[bot-token]"`.
- **health.md**: Added quotes: `[queue-name]` -> `"[queue-name]"`.
- **todo.md**: Added quotes: `[task description] [schedule]` -> `"[task description] [schedule]"`.
- **tq-message.md**: Added quotes: `<task-hash> <queue-file>` -> `"<task-hash> <queue-file>"`.

**Convention established**: All argument-hint values are quoted strings. `[]` = optional, `<>` = required.

### Iteration 12: LLM executability (step numbering)

**Problem**: Three commands used `## Steps` with numbered bold items inside a single section instead of `## N. Title` heading format, making it harder for LLMs to track discrete execution steps.

**Changes**:
- **pause.md**: Converted from `## Steps` with 7 inline numbered items to 7 separate `## N. Title` sections. Added error stop in verification step.
- **schedule.md**: Converted from `## Steps` with 8 inline numbered items to 8 separate `## N. Title` sections. Added error stop in merge step.
- **unschedule.md**: Converted from `## Steps` with 5 inline numbered items to 5 separate `## N. Title` sections. Added error stop in remove step.

**Impact**: All 13 commands now use consistent `## N. Title` step format. Each step is a discrete H2 heading that an LLM can track independently.

### Iteration 13: Tool permission scoping

**Problem**: Some commands had allowed-tools that were either unused or redundant with Read/Write tools.

**Changes**:
- **setup-telegram.md**: Removed `Bash(tq-setup)` (never referenced in instructions), `Bash(cat)` (redundant with Read).
- **tq-reply.md**: Removed `Bash(tq-converse)` (unused), `Bash(cat)` (replaced with Read), `Bash(sed)` (replaced with Read + parsing), `Bash(echo)` (replaced with Write). Added `Read, Write`. Updated step 1 slug detection to use Read tool instead of bash cat/sed. Updated step 3 to use Read/Write instead of cat/echo.
- **todo.md**: Removed `Bash(cat)` (redundant with Read already in allowed-tools).

**Impact**: No command has unused tool permissions. Tool lists are minimal and specific.

### Iteration 14: Output format standardization

**Problem**: Some commands had vague output instructions ("Show command output to user") while others had detailed summary table templates.

**Changes**:
- **converse.md**: Replaced "Show command output to user" with a structured summary table template (Action, Result, Session, Active sessions).
- **pause.md**: Replaced "Show what was removed and note that `tq --status` is still running" with a structured summary table (Queue, Removed, Kept, Resume).
- **init.md**: Replaced "Show: dirs scanned, projects found..." list with a structured summary table (Dirs scanned, Projects found, Config, Workspace map).

**Impact**: 11 of 13 commands now have explicit table-format output. The 2 exceptions (tq-message, tq-reply) are appropriately different -- they produce output that gets sent externally rather than displayed to the user.

## Cumulative Learnings

1. **Navigation rings need auditing from both directions** -- checking that A links to B is not enough; B must also link back to A. The easiest way to audit is to build a link matrix.

2. **"Stop" vs "continue" must be explicit** -- LLMs will guess at error handling if not told. Even "never stop" (as in health.md) is valuable documentation.

3. **Argument-hint quoting is a convention detail that compounds** -- once one file is unquoted, a linter or future contributor may follow the wrong pattern. Fixing all at once establishes the standard.

4. **Step numbering format directly affects LLM parsing** -- `## N. Title` as H2 headings is significantly more parseable than numbered bold items inside a single `## Steps` section. The LLM treats H2s as structural boundaries.

5. **Tool permission bloat is a security and reliability concern** -- unused tools in allowed-tools can lead to unexpected behavior if the LLM decides to use them. The minimum viable set is always better.

6. **Output tables create user expectation consistency** -- when every command produces a similar summary table, users learn to scan for the key information in a predictable location.

## Files Not Touched

- **install.md** (79): Already well-structured with summary table, proper error handling, correct argument-hint.
- **jobs.md** (78): Good output table, proper error handling, correct cross-references.
- **SKILL.md** (82): Comprehensive trigger phrases, complete commands table, reference links.
- **chrome-integration.md** (74): Reference file with proper Related section already.
