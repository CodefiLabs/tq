# Vibeathon-Style Scoring Results — Iteration 2

**Date:** 2026-03-14
**Rubric:** vibeathon-hybrid-v1 (adapted from app-vibeathon-us AI Judge)
**Judge:** claude-opus-4-6

## Methodology Comparison

| Dimension | Iteration 1 (Simple) | Iteration 2 (Vibeathon) |
|-----------|----------------------|-------------------------|
| Scale | 0-10 | 0-100 |
| Criteria | 7 flat dimensions | 5 weighted criteria |
| Perspectives | None | 3 (User, LLM, System) |
| Evidence | Subjective impression | Cited impact items (+5 to -5) |
| Formula | Weighted sum | Hybrid: sqrt normalization + confidence regression |
| Anti-inflation | None (all scores 8-9) | Enforced: median must be 60-70 |
| Score spread (post-improve) | 1.0 pt (8.0-9.0) | 21.8 pts (55.5-77.3) |

## Score Comparison Table

| File | Simple (0-10) | Simple % | Vibeathon (0-100) | Delta | Rank Change |
|------|---------------|----------|-------------------|-------|-------------|
| **SKILL.md** | 9.0 | 90% | **77.3** | -12.7 | #1 → #1 |
| **pause.md** | 9.0 | 90% | **75.4** | -14.6 | #1 → #2 |
| **setup-telegram.md** | 8.5 | 85% | **74.2** | -10.8 | #5 → #3 |
| **converse.md** | 8.5 | 85% | **73.7** | -11.3 | #5 → #4 |
| **health.md** | 8.5 | 85% | **73.0** | -12.0 | #5 → #5 |
| **unschedule.md** | 9.0 | 90% | **72.3** | -17.7 | #1 → #6 |
| **jobs.md** | 9.0 | 90% | **72.0** | -18.0 | #1 → #7 |
| **schedule.md** | 9.0 | 90% | **71.4** | -18.6 | #1 → #8 |
| **todo.md** | 8.5 | 85% | **67.5** | -17.5 | #5 → #9 |
| **init.md** | 8.5 | 85% | **66.6** | -18.4 | #5 → #10 |
| **review.md** | 8.5 | 85% | **65.6** | -19.4 | #5 → #11 |
| **tq-message.md** | 8.5 | 85% | **64.6** | -20.4 | #5 → #12 |
| **install.md** | 8.0 | 80% | **63.4** | -16.6 | #14 → #13 |
| **tq-reply.md** | 8.5 | 85% | **55.5** | -29.5 | #5 → #14 |
| | | | | | |
| **Average** | 8.6 | 86% | **69.4** | -16.6 | |
| **Median** | 8.5 | 85% | **71.7** | -13.3 | |

## Distribution Analysis

**Simple rubric distribution (Iteration 1 post-improve):**
```
8.0 ████ (1 file)
8.5 ████████████████████████████████████ (9 files)
9.0 ████████████████████ (5 files, including SKILL.md)
```
Nearly everything clustered at 8.5. The rubric couldn't differentiate.

**Vibeathon distribution (Iteration 2):**
```
50-59 ██ (1 file: tq-reply)
60-69 ██████████████████████ (6 files)
70-79 ██████████████████████████████████ (7 files)
80+   (0 files)
```
Clear separation into tiers.

## What the Vibeathon Approach Revealed

### 1. tq-reply.md: 8.5 → 55.5 (biggest drop, -29.5)
The simple rubric said "good" because it had frontmatter and named steps. The vibeathon approach found:
- **Missing argument-hint** (-2 System): only command in batch 2 without it
- **Slug detection may not match registry approach** (-2 LLM): iterates session dirs for `current-slug` files, but `anti-patterns.md` documents registry.json as the canonical source
- **Empty REPLY_TO passed to --reply-to flag** (-1 LLM): if `reply-to-msg-id` file doesn't exist, passes empty string
- **No tmux guard** (-2 LLM): assumes it's running inside tmux but doesn't check
- Net impact on Completeness criterion: 0 → score of 50 (exactly average)

### 2. tq-message.md: 8.5 → 64.6 (drop of -20.4)
- **Single-quote variable expansion bug** (-1 System, -1 Convention): `'$SUMMARY'` in bash won't expand
- **No mid-task guard** (-2 LLM): can be invoked before task completes
- **No binary-missing check** (-1 LLM): doesn't verify `tq-message` is on PATH
- However, instruction quality scored **83** — the summary-writing instructions with concrete example are exceptional

### 3. Scheduling family (pause/unschedule/jobs/schedule): All dropped from 9.0
The simple rubric gave these the highest score, but vibeathon differentiated:
- **pause.md (75.4)**: Best of the group — NL inference examples, 7-step workflow with verification
- **schedule.md (71.4)**: Worst of the group — longest at 68 lines, hardcoded `/opt/homebrew` path, TTL formula requires Claude math with no code block

### 4. install.md and review.md: Still at the bottom
Both still missing argument-hint (even though Iteration 1 flagged this). The vibeathon scoring quantifies the penalty: -2 per missing hint, affecting the 30%-weighted Triggering criterion.

## Per-Criterion Heatmap

| File | Triggering (30%) | Instruction (25%) | Completeness (20%) | Convention (15%) | Conciseness (10%) |
|------|-------------------|--------------------|---------------------|-------------------|---------------------|
| SKILL.md | **80** | **85** | 72 | 71 | 68 |
| pause.md | 74 | 76 | 74 | **79** | 71 |
| setup-telegram.md | 76 | **81** | **76** | 65 | 63 |
| converse.md | **78** | 72 | 73 | 71 | 67 |
| health.md | **77** | **78** | 67 | 70 | 61 |
| unschedule.md | 76 | 69 | 72 | 73 | 71 |
| jobs.md | 74 | 70 | 68 | **79** | 68 |
| schedule.md | 73 | 75 | 68 | 70 | 60 |
| todo.md | 72 | 73 | 57 | 65 | 60 |
| init.md | 65 | 72 | 61 | 63 | 68 |
| review.md | 60 | 72 | 60 | 67 | 65 |
| tq-message.md | 62 | **83** | 47 | 63 | 72 |
| install.md | 64 | 68 | 55 | 63 | 67 |
| tq-reply.md | 53 | 63 | **50** | 57 | 57 |

**Criterion averages:**
- Triggering: 70.3 (best overall — argument-hint fix in Iter 1 paid off)
- Instruction Quality: 74.1 (highest — commands have good step-by-step structure)
- Completeness: 64.3 (weakest — error handling is the biggest gap)
- Convention: 68.3 (moderate — cross-references are good, minor formatting issues)
- Conciseness: 65.6 (moderate — some commands are verbose)

## Key Insight: Completeness is the Weakest Criterion

The simple rubric had "Error handling" as a single 1-point dimension. The vibeathon approach weights it at 20% and evaluates it through 3 perspectives, revealing it's the #1 improvement opportunity:

| Completeness Score | Files | Pattern |
|-------------------|-------|---------|
| 47-50 | tq-message, tq-reply | Missing guards for invalid state (mid-task run, no tmux) |
| 55-61 | install, review, todo, init | Silently suppressed errors, no fallback on failure |
| 67-74 | schedule, health, jobs, unschedule, converse | Good coverage but missing one key edge case each |
| 74-76 | pause, setup-telegram, SKILL | Comprehensive with retry logic and validation |

## Recommendations for Iteration 3

**High-impact improvements (sorted by expected score lift):**

1. **Fix tq-reply.md slug detection** — align with registry.json approach, add tmux guard, handle empty REPLY_TO. Expected: 55 → 68.
2. **Fix tq-message.md single-quote bug** — change `'$SUMMARY'` to `"$SUMMARY"`, add binary-missing guard. Expected: 64 → 72.
3. **Add argument-hint to install.md and review.md** — simple one-line addition, 30% weight impact. Expected: +5 each.
4. **Add error handling guards across all commands** — check for binaries before invoking, validate tmux is running, handle curl/network failures.
5. **Remove hardcoded /opt/homebrew from schedule.md** — use `$(which tq)` or `command -v tq`.

## Conclusions

The vibeathon-style scoring revealed that the Iteration 1 "8.5 average" was inflated. The evidence-based approach produces:
- **Better discrimination**: 21.8-point spread vs 1.0-point spread
- **Actionable findings**: specific bugs (single-quote expansion, empty REPLY_TO) that the simple rubric missed entirely
- **Weighted priorities**: Triggering (30%) and Instruction Quality (25%) correctly dominate, while the simple rubric gave Error Handling only 10% weight
- **Confidence-adjusted scores**: commands with sparse evidence regress toward 50, preventing overconfident scoring of thin commands

The rubric in `docs/vibeathon-scoring-rubric.md` is validated and ready for future iterations.
