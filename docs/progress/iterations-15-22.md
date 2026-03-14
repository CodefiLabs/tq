# Iterations 15-22: Scoring and Improvement Summary

## Iteration Focus Areas

| Iteration | Focus | Files Improved |
|-----------|-------|----------------|
| 15 | Trigger phrase coverage | SKILL.md, review.md, init.md |
| 16 | Security and permissions | setup-telegram.md, health.md, tq-reply.md |
| 17 | System perspective (valid bash, correct paths) | tq-reply.md, setup-telegram.md |
| 18 | Edge case handling | converse.md, tq-message.md |
| 19 | Progressive disclosure | schedule.md, session-naming.md |
| 20 | Word count optimization | SKILL.md, session-naming.md |
| 21 | Heading/formatting consistency | setup-telegram.md, todo.md |
| 22 | Ceiling test (micro-optimizations) | install.md, health.md, schedule.md, pause.md, unschedule.md, todo.md, converse.md |

## Changes by File

### SKILL.md (skills/tq/SKILL.md)
- **Iteration 15**: Added 20+ new trigger phrases covering natural phrasings: "check queue status", "background claude sessions", "headless claude", "automate claude tasks", "list conversations", "stop conversation", "stop session", "clear task state", "send telegram message", "reply via telegram", "what's running", "what tasks are done", "pause schedule", "resume schedule", "remove from cron", "unschedule queue", "lint tq scripts", "review tq changes", "configure workspaces", "workspace setup". Also added keyword triggers: "cron job", "tmux session", "queue file", "queue yaml".
- **Iteration 20**: Condensed "Queue Name Inference" section (removed bullet list, made single sentence). Renamed "Reset" to "Resetting State" for clarity.
- **Iteration 22**: Bumped version from 1.3.0 to 1.4.0.
- **Score**: 72 -> 88

### converse.md
- **Iteration 18**: Added edge case handling section (step 3): orchestrator already running, slug not found, spawn without slug, Telegram not configured.
- **Iteration 21**: Fixed step numbering (was duplicate ## 5, now correctly numbered 1-6).
- **Iteration 22**: Added `Bash(test)` to allowed-tools for config file existence check.
- **Score**: 70 -> 84

### health.md
- **Iteration 16**: Added `Bash(python3)` to allowed-tools (needed for registry JSON validation in step 6).
- **Iteration 22**: Added tags "check" and "verify" for better discoverability. Changed argument-hint format to `"[queue-name]"` (quoted).
- **Score**: 80 -> 87

### init.md
- **Iteration 15**: Added tags "projects" and "scan" for better trigger matching.
- **Score**: 75 -> 79

### install.md
- **Iteration 22**: Added tag "binaries" for discoverability.
- **Score**: 82 -> 85

### jobs.md
- No changes needed in iterations 15-22 (already strong).
- **Score**: 78 -> 78

### pause.md
- **Iteration 22**: Added `Bash(grep)` to allowed-tools (used in crontab grep -v operation).
- **Score**: 76 -> 80

### review.md
- **Iteration 15**: Added tags "pre-commit" and "staged" for better trigger matching.
- **Score**: 78 -> 82

### schedule.md
- **Iteration 19**: Simplified reset TTL table -- added explanatory sentence ("Rule: TTL = half the cron interval"), removed redundant "Interval" column, removed "Minimum: 1h" standalone sentence (now implicit).
- **Iteration 22**: Added `Bash(grep)` to allowed-tools. Added error handling for crontab update failure (step 7).
- **Score**: 76 -> 83

### setup-telegram.md
- **Iteration 16**: Added `Bash(ls)` to allowed-tools (used in step 0 for `ls -la`). Added `Bash(grep)` for crontab grep operations. Added security note: "Never echo or log the bot token in full."
- **Iteration 17**: Fixed curl-to-python3 pipe -- combined separate code blocks into single piped command. Removed unused `Bash(tq-setup)` from allowed-tools (cleaned up by other agent).
- **Iteration 21**: Standardized heading format from `## Step N --` to `## N.` to match all other commands.
- **Score**: 73 -> 85

### todo.md
- **Iteration 21**: Standardized heading format from `## Step N --` to `## N.` to match all other commands. Fixed "Step 6" reference to lowercase "step 6".
- **Iteration 22**: Added `Bash(grep)` to allowed-tools (used in crontab grep -v operations).
- **Score**: 75 -> 81

### tq-message.md
- **Iteration 18**: Added edge case handling: no arguments provided, missing messaging config (`~/.tq/config/message.yaml`). Added `Bash(test)` to allowed-tools.
- **Score**: 72 -> 80

### tq-reply.md
- **Iteration 16**: Added `Bash(sed)`, `Bash(echo)`, and `Write` to allowed-tools.
- **Iteration 17**: Fixed critical macOS bug -- replaced `grep -oP` (Perl regex, GNU only) with `sed -n` pattern extraction (BSD-compatible). Note: the other agent subsequently rewrote this file to use Read/Write tools instead of bash cat/echo, which also resolved the grep issue.
- **Score**: 65 -> 82

### unschedule.md
- **Iteration 22**: Added `Bash(grep)` to allowed-tools (used in crontab grep operations). Added error handling for crontab update failure.
- **Score**: 76 -> 80

### chrome-integration.md (references)
- No changes needed in iterations 15-22.
- **Score**: 74 -> 74

### cron-expressions.md (references)
- No changes needed in iterations 15-22 (already strong).
- **Score**: 80 -> 80

### session-naming.md (references)
- **Iteration 20**: Trimmed Notes section -- removed wordy explanations, kept essential points concise.
- **Score**: 78 -> 81

## Score Summary

| File | Before (it. 15) | After (it. 22) | Delta |
|------|-----------------|----------------|-------|
| SKILL.md | 72 | 88 | +16 |
| converse.md | 70 | 84 | +14 |
| health.md | 80 | 87 | +7 |
| init.md | 75 | 79 | +4 |
| install.md | 82 | 85 | +3 |
| jobs.md | 78 | 78 | 0 |
| pause.md | 76 | 80 | +4 |
| review.md | 78 | 82 | +4 |
| schedule.md | 76 | 83 | +7 |
| setup-telegram.md | 73 | 85 | +12 |
| todo.md | 75 | 81 | +6 |
| tq-message.md | 72 | 80 | +8 |
| tq-reply.md | 65 | 82 | +17 |
| unschedule.md | 76 | 80 | +4 |
| chrome-integration.md | 74 | 74 | 0 |
| cron-expressions.md | 80 | 80 | 0 |
| session-naming.md | 78 | 81 | +3 |
| **Average** | **75.3** | **81.1** | **+5.8** |

## Key Learnings

1. **`grep -oP` is a GNU extension** -- critical system-level bug on macOS where BSD grep does not support `-P` (Perl regex). Always use `sed -n 's/.../p'` for portable pattern extraction.

2. **allowed-tools must match every command used** -- commands using `grep` in piped crontab operations need `Bash(grep)` explicitly. `python3` for JSON validation needs `Bash(python3)`.

3. **Trigger phrases compound value** -- adding 20+ natural phrasings to SKILL.md covers the long tail of how users might express the same intent. Keywords like "cron job", "tmux session", "queue file" are high-value because they match partial/vague queries.

4. **Heading format consistency matters** -- `## N. Title` vs `## Step N -- Title` creates cognitive friction. Standardizing to `## N. Title` across all 13 commands makes the collection feel cohesive.

5. **Edge case coverage is the highest-ROI improvement** -- adding 2-3 lines for "what if no args", "what if config missing", "what if already running" prevents entire failure modes.

6. **Security notes earn high impact scores** -- a single "Never echo the bot token in full" line in setup-telegram.md is a +3 impact item.

7. **allowed-tools gaps cause silent failures** -- when Claude cannot use a tool it needs, the command silently fails or Claude works around it poorly. Auditing allowed-tools against every bash command in the body catches these.

8. **Files that were already strong (jobs.md, cron-expressions.md) yield diminishing returns** -- focus iterations on the weakest files for maximum improvement.
