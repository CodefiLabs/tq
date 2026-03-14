# Auto-Improve Learnings

Inspired by [Karpathy's auto-research pattern](https://github.com/karpathy/auto-research).
Accumulated insights from autonomous skill/command improvement iterations.

## Scoring Rubrics

### Iteration 1 Rubric (0-10 scale)

Simple dimension-weighted rubric. See git history for original tables.

### Iteration 2 Rubric (Vibeathon-style, 0-100 scale)

Adapted from the AI Judge in [app-vibeathon-us](~/Sites/codefi/app-vibeathon-us).
Full rubric: [docs/vibeathon-scoring-rubric.md](vibeathon-scoring-rubric.md).

5 weighted criteria evaluated through 3 perspectives (User, LLM, System),
scored with impact items (+5 to -5), confidence-adjusted hybrid formula.

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

### Iteration 2 — 2026-03-14 (Vibeathon-style scoring)

Applied multi-criteria, multi-perspective scoring adapted from the vibeathon AI judge.
5 parallel agents scored and improved all 17 files simultaneously.

**Before/After Scores (0-100 weighted composite):**

| File | Before | After | Delta | Top Impact Item |
|------|--------|-------|-------|-----------------|
| install.md | 67.9 | 78.0 | +10.1 | +5 Complete 7-binary verification list |
| review.md | 65.7 | 76.8 | +11.1 | +5 Fixed step ordering (staged check first) |
| converse.md | 74.1 | 81.3 | +7.2 | +5 Pre-flight check for tq-converse installation |
| pause.md | 78.2 | 83.6 | +5.4 | +3 Show-before-remove safety step |
| unschedule.md | 74.2 | 83.2 | +9.0 | +3 Fixed grep pattern preventing prefix collisions |
| jobs.md | 67.9 | 81.0 | +13.1 | +3 Orphaned cron entry detection |
| schedule.md | 68.1 | 80.8 | +12.7 | +3 Fixed broken step numbering (was 1,2,2b,3) |
| todo.md | 67.7 | 80.2 | +12.5 | +3 Eliminated reset TTL duplication via cross-ref |
| init.md | 73.7 | 78.5 | +4.9 | +2 Directory existence validation |
| health.md | 73.5 | 82.8 | +9.3 | +5 Conversation mode + workspace config checks |
| setup-telegram.md | 59.3 | 79.7 | +20.4 | +5 Existing config detection + chmod 600 |
| tq-message.md | 68.0 | 80.6 | +12.6 | +3 Telegram 3500-char limit + quoting fix |
| tq-reply.md | 54.2 | 71.0 | +16.8 | +3 Eliminated duplicate placeholder pattern |
| SKILL.md | 73.1 | 85.0 | +11.9 | +5 Reset modes table + background scripts |
| cron-expressions.md | 82.1 | 86.6 | +4.5 | +3 Clarified auto vs manual crontab management |
| session-naming.md | 80.1 | 89.2 | +9.1 | +5 Fixed missing tq- prefix (LLM-critical) |
| chrome-integration.md | 30.5 | 72.8 | +42.3 | +5 Full rewrite from 4-line stub to reference |

**Average: 68.1 → 80.6 (+12.5 pts, +18% improvement)**

**Score distribution after iteration 2:**
- 85-90: 2 files (session-naming, cron-expressions) — strong references
- 80-85: 8 files — solid commands
- 75-80: 4 files — good with room to grow
- 70-75: 3 files (init, tq-reply, chrome-integration) — still needs work

**Learnings accumulated (iteration 2):**

10. **Multi-perspective scoring catches different bugs** -- User perspective found discoverability gaps (missing tags), LLM perspective found instruction ambiguity (broken step numbering), System perspective found security violations (missing chmod 600).
11. **grep patterns across cron-touching commands had a systemic bug** -- `tq.*name.yaml` would match `morning` when searching for `morning-review`. Fixed to `tq.*/name\.yaml` with path separator across unschedule, schedule, and todo.
12. **Cross-references form navigation rings** -- Adding `Related: /schedule, /jobs, /unschedule` footers to all cron commands created a discoverable loop. Users of any one command can find the others.
13. **"and stop" after error conditions prevents LLM runaway** -- Without explicit "and stop", Claude may continue past an error (e.g., queue file missing) and attempt later steps anyway.
14. **Vibeathon confidence adjustment is useful** -- Files with sparse evidence (chrome-integration had only 4 impact items) correctly got pulled toward 50. Files with rich evidence (session-naming had 18 items) got scores that reflected actual quality.
15. **setup-telegram was the worst-scoring command** -- Security violations (no chmod 600), no overwrite protection on config, and no binary validation. Multi-perspective scoring surfaced all three independently.
16. **Technical accuracy in references is higher-leverage than prose quality** -- session-naming.md had beautiful formatting but was producing wrong session names (missing tq- prefix). The formatting score didn't help if the content was wrong.
17. **tq-reply remains the lowest-scoring command** -- Its inline slug detection loop is a code smell that scoring can't fix. Needs a `tq-converse detect-slug` subcommand to simplify.

### Iterations 3-8 — 2026-03-14 (Lead-driven targeted rewrites)

Focused on bottom-up rewrites of the weakest files, then progressive polish upward.
See [docs/progress/iterations-3-8.md](progress/iterations-3-8.md) for details.

**Key changes**: tq-reply.md complete rewrite (marker file detection), chrome-integration.md restructure (tables, troubleshooting), review.md (--fix flag, priority table), install.md (--check mode), init.md (--refresh flag), SKILL.md troubleshooting table.

### Iterations 9-14 — 2026-03-14 (Systematic cross-cutting improvements)

6 themed iterations run by a parallel agent. See [docs/progress/iterations-9-14.md](progress/iterations-9-14.md).

| Iteration | Theme | Impact |
|-----------|-------|--------|
| 9 | Cross-reference consistency | All 17 files now form complete navigation rings |
| 10 | Error handling completeness | Every command has explicit stop/continue semantics |
| 11 | Argument validation | All argument-hint values quoted, consistent `[]`/`<>` |
| 12 | LLM executability | All 13 commands use `## N. Title` heading format |
| 13 | Tool permission scoping | No command has unused tool permissions |
| 14 | Output format standardization | 11 of 13 commands have table-format output |

**Learnings accumulated (iterations 9-14):**

18. **Navigation rings need auditing from both directions** -- checking A→B is not enough; B→A must also exist.
19. **"Stop" vs "continue" must be explicit** -- LLMs will guess at error handling. Even "never stop" (health.md) is valuable.
20. **Argument-hint quoting compounds** -- one unquoted file sets a bad pattern. Fix all at once.
21. **`## N. Title` H2 headings beat numbered bold items** -- LLMs treat H2s as structural boundaries.
22. **Tool permission bloat is a security concern** -- unused tools can lead to unexpected behavior.
23. **Output tables create user expectation consistency** -- predictable output format across all commands.

### Iterations 15-22 — 2026-03-14 (Final polish and ceiling push)

8 themed iterations run by a parallel agent. See [docs/progress/iterations-15-22.md](progress/iterations-15-22.md).

| Iteration | Theme | Impact |
|-----------|-------|--------|
| 15 | Trigger phrase coverage | SKILL.md gained 20+ natural phrasings |
| 16 | Security & permissions | Token masking, python3 tool added |
| 17 | System perspective | Fixed macOS `grep -oP` bug (GNU-only) |
| 18 | Edge case handling | Converse/tq-message gained edge case sections |
| 19 | Progressive disclosure | Schedule TTL table simplified |
| 20 | Word count optimization | SKILL.md queue inference condensed |
| 21 | Heading consistency | All commands use `## N.` format |
| 22 | Ceiling test | Tags, tools, error stops for 7 files |

**Learnings accumulated (iterations 15-22):**

24. **`grep -oP` is GNU-only** -- critical macOS bug. Use `sed -n 's/.../p'` for portable extraction.
25. **allowed-tools must match every bash command used** -- `grep` in pipes needs `Bash(grep)`, `python3` needs `Bash(python3)`.
26. **Trigger phrases compound value** -- 20+ natural phrasings cover the long tail of user intent.
27. **Heading format consistency reduces cognitive friction** -- standardize across all files.
28. **Edge case coverage is the highest-ROI improvement** -- 2-3 lines prevent entire failure modes.
29. **Security notes earn high impact scores** -- one "never echo token in full" line is +3 impact.
30. **allowed-tools gaps cause silent failures** -- Claude works around missing permissions poorly.
31. **Strong files yield diminishing returns** -- focus iterations on weakest files for maximum impact.

## Cumulative Score Trajectory

| Stage | Average Score | Method |
|-------|--------------|--------|
| Pre-iteration 1 | 5.4/10 | Simple 0-10 rubric |
| Post-iteration 1 | 8.6/10 | Simple 0-10 rubric |
| Post-iteration 2 | 80.6/100 | Vibeathon rubric |
| Post-iteration 8 | ~82/100 | Vibeathon rubric (estimated) |
| Post-iteration 14 | ~83/100 | Vibeathon rubric (agent scored) |
| Post-iteration 22 | 81.1/100 | Vibeathon rubric (agent scored) |

**Note**: Score averages from different agents aren't directly comparable due to calibration differences. The key metric is within-agent delta, not absolute score.

## Final Score Distribution (Iteration 22)

| Range | Files | Names |
|-------|-------|-------|
| 85-90 | 3 | SKILL.md (88), health.md (87), setup-telegram.md (85), install.md (85) |
| 80-84 | 6 | converse.md (84), schedule.md (83), review.md (82), tq-reply.md (82), todo.md (81), session-naming.md (81) |
| 78-80 | 5 | pause.md (80), unschedule.md (80), tq-message.md (80), cron-expressions.md (80), init.md (79) |
| 74-77 | 2 | jobs.md (78), chrome-integration.md (74) |

**Total improvements made**: 120+ individual edits across 17 files over 22 iterations.
