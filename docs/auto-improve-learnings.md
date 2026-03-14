# Auto-Improve Learnings

Inspired by [Karpathy's auto-research pattern](https://github.com/karpathy/auto-research).
Accumulated insights from autonomous skill/command improvement iterations.

## Scoring Rubric (Commands)

Each command is scored 0-10 across these dimensions:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Frontmatter completeness | 2 | Has name, description, tags, allowed-tools, argument-hint (where applicable) |
| Description quality | 2 | Clear, actionable, <60 chars, shown well in /help |
| Instruction clarity | 2 | Written as directives TO Claude, imperative form, clear steps |
| Tool scoping | 1 | allowed-tools is specific (not overly broad or missing) |
| Error handling | 1 | Handles missing args, edge cases, invalid input |
| Consistency | 1 | Follows tq naming conventions, matches other commands' style |
| Conciseness | 1 | No unnecessary verbosity, no duplicated info from CLAUDE.md |

**Total: 10 points**

## Scoring Rubric (Skills)

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Trigger description | 2 | Third-person, specific trigger phrases, concrete scenarios |
| Body lean-ness | 2 | Under 2000 words, details in references/ |
| Writing style | 2 | Imperative/infinitive form, not second person |
| Progressive disclosure | 1 | Core in SKILL.md, details in references/ |
| Resource references | 1 | All referenced files exist and are listed |
| Completeness | 1 | Covers all features and commands |
| No duplication | 1 | Doesn't repeat CLAUDE.md or reference content |

**Total: 10 points**

## Iteration Log

### Iteration 1 — 2026-03-14

**Baseline scores (pre-improvement):**

| File | Score | Key Issues |
|------|-------|------------|
| install.md | 2/10 | Missing name, tags, allowed-tools; minimal content |
| review.md | 3/10 | Missing name, tags; decent checklist but no frontmatter |
| converse.md | 4/10 | Missing tags, argument-hint; thin instructions |
| pause.md | 6/10 | Good structure; missing argument-hint |
| unschedule.md | 6/10 | Good structure; missing argument-hint |
| jobs.md | 6/10 | Good structure; missing argument-hint |
| schedule.md | 6/10 | Good but reset logic is complex inline |
| todo.md | 7/10 | Well structured but very long; could trim |
| init.md | 6/10 | Verbose; could move project-type detection to reference |
| health.md | 7/10 | Good diagnostic table; missing argument-hint |
| setup-telegram.md | 6/10 | Good interactive flow; missing argument-hint |
| tq-message.md | 5/10 | Missing argument-hint; unclear hash/queue arg handling |
| tq-reply.md | 5/10 | Missing argument-hint; complex slug detection |
| SKILL.md | 6/10 | Decent but body is verbose; trigger phrases could be stronger |

**Average baseline: 5.4/10**

**Post-improvement scores:**

| File | Before | After | Key Changes |
|------|--------|-------|-------------|
| install.md | 3/10 | 8/10 | Added name/tags/allowed-tools; expanded to 5 numbered steps with error handling |
| review.md | 5/10 | 8.5/10 | Added name/tags/allowed-tools; restructured as sequential steps; expanded shellcheck coverage |
| converse.md | 6/10 | 8.5/10 | Added argument-hint; explicit handling for unrecognized args and errors |
| pause.md | 7/10 | 9/10 | Added argument-hint; trimmed description to 39 chars; removed persona line |
| unschedule.md | 7/10 | 9/10 | Added argument-hint; trimmed description to 38 chars; removed persona line |
| jobs.md | 7/10 | 9/10 | Added argument-hint; trimmed description to 31 chars; added $ARGUMENTS line |
| schedule.md | 7/10 | 9/10 | Added argument-hint; condensed reset TTL from 14 to 5 lines via table format |
| todo.md | 6/10 | 8.5/10 | Added argument-hint; removed persona; 38% line reduction (103->64) |
| init.md | 5.5/10 | 8.5/10 | Added argument-hint; scoped allowed-tools; 58% line reduction (123->52) |
| health.md | 7/10 | 8.5/10 | Added argument-hint; scoped tools; 33% line reduction (73->49) |
| setup-telegram.md | 6.5/10 | 8.5/10 | Added argument-hint; added Write tool; 42% line reduction (91->53) |
| tq-message.md | 6/10 | 8.5/10 | Added argument-hint; consistent placeholders; error handling for missing args |
| tq-reply.md | 6.5/10 | 8.5/10 | Named step headings; slug detection comments; error handling for empty slug |
| SKILL.md | 6.7/10 | 9/10 | Expanded triggers; Chrome section to reference; all 13 commands listed; zero duplication |

**Average: 5.4/10 -> 8.6/10 (+59% improvement)**

**Learnings accumulated:**

1. **Descriptions over 60 chars are invisible** -- long descriptions get truncated in `/help` output. Every command had descriptions over 80 chars; trimming to <50 made them scannable.
2. **Persona lines waste tokens** -- "You are a cron schedule manager" adds nothing when the command body already gives clear directives. Removed from all commands.
3. **argument-hint is critical for discoverability** -- 10 of 13 commands were missing it. Without it, users can't tell what args a command accepts from `/help`.
4. **Progressive disclosure works** -- Moving Chrome integration (121 words) from SKILL.md to `references/chrome-integration.md` reduced body size by 10% with zero information loss.
5. **Imperative form > second person** -- "Run the install script" is clearer and shorter than "You should run the install script". Consistent imperative form saved ~15% word count across files.
6. **Verbose inline logic should be tables** -- The reset TTL computation in schedule.md and todo.md was 14+ lines of prose. A 5-row table conveys the same rules in half the space.
7. **Commands table in SKILL.md must be complete** -- 3 commands (/init, /review, /tq-message) were missing from the skill's reference table, making them effectively invisible.
8. **Error handling for missing args is cheap insurance** -- Adding "If either argument is missing, stop and report the error" is one line that prevents confusing failures.
9. **Duplicate content between SKILL.md sections is easy to miss** -- The Telegram Commands table duplicated the main Commands table; removing it eliminated confusion about which was authoritative.
