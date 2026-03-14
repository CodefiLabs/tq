# Auto-Improve: 20 Iterations on feature/auto-improve-skills

Starting point: post-iteration-1 (commit 882fa59)

## Final Scores (0-100 weighted composite, vibeathon rubric)

| # | File | Baseline | Final | Delta | Key Improvements |
|---|------|----------|-------|-------|-----------------|
| 1 | converse.md | 82.1 | 88.5 | +6.4 | Pre-flight check, cross-references, "and stop" |
| 2 | pause.md | 80.9 | 88.0 | +7.1 | Show-before-remove, fixed grep prefix collision, cross-refs |
| 3 | unschedule.md | 80.9 | 88.0 | +7.1 | Show-before-remove, fixed grep, cross-refs |
| 4 | SKILL.md | 78.9 | 90.5 | +11.6 | Reset modes table, background scripts, portable paths, v1.5.0 |
| 5 | health.md | 78.7 | 89.5 | +10.8 | 7 binary checks, conversation mode, config check, log expansion |
| 6 | session-naming.md | 78.0 | 87.0 | +9.0 | Added tq- prefix to queue mode, fixed examples |
| 7 | jobs.md | 77.7 | 86.0 | +8.3 | Orphaned cron detection, cross-references |
| 8 | init.md | 75.2 | 83.5 | +8.3 | Directory validation, cross-references |
| 9 | tq-message.md | 75.0 | 85.0 | +10.0 | Fixed quoting (heredoc), 3500 char limit |
| 10 | review.md | 74.7 | 86.5 | +11.8 | argument-hint, staged-first order, hardcoded path check |
| 11 | cron-expressions.md | 73.0 | 86.0 | +13.0 | Auto vs manual section, portable paths, fixed grep |
| 12 | install.md | 71.8 | 85.5 | +13.7 | argument-hint, 7-binary check loop, git rev-parse error |
| 13 | schedule.md | 71.6 | 86.0 | +14.4 | Fixed step numbering (1-8), portable paths, cross-refs |
| 14 | todo.md | 70.4 | 84.0 | +13.6 | Deduplicated schedule logic via cross-ref, portable paths |
| 15 | setup-telegram.md | 69.5 | 86.0 | +16.5 | Pre-flight, overwrite protection, chmod 600, retry logic |
| 16 | tq-reply.md | 64.0 | 84.0 | +20.0 | argument-hint, tmux fallback detection, conditional --reply-to |
| 17 | chrome-integration.md | 43.8 | 80.0 | +36.2 | Full rewrite: profiles, troubleshooting table, profile finder |

**Average: 73.4 → 86.1 (+12.7 pts, +17.3% improvement)**

## Score Distribution

- 90-100: 1 file (SKILL.md) — exceptional
- 85-89: 11 files — strong
- 80-84: 5 files — solid

## Iteration Summary

| Iter | Focus | Files Changed | Key Improvement |
|------|-------|---------------|-----------------|
| 1 | chrome-integration.md rewrite | 1 | Full rewrite from 4-line stub to useful reference |
| 2 | tq-reply.md slug detection | 1 | Tmux fallback, conditional --reply-to, argument-hint |
| 3 | setup-telegram.md security | 1 | chmod 600, overwrite protection, pre-flight, retry |
| 4 | Systemic: portable paths | 5 | `$(command -v tq)` replaces `/opt/homebrew/bin/tq` |
| 5 | todo.md dedup | 1 | Cross-ref to /schedule instead of duplicating logic |
| 6 | Cron commands: cross-refs + grep | 3 | `/<name>\.yaml` grep, Related: footers |
| 7 | install.md + review.md | 2 | argument-hint, reordered steps, hardcoded path check |
| 8 | health.md expansion | 1 | 7-binary check, conversation mode, config, permissions |
| 9 | tq-message.md quoting | 1 | Heredoc temp file, 3500 char limit |
| 10 | init.md validation | 1 | Directory existence check, cross-refs |
| 11 | converse.md pre-flight | 1 | Installation check, cross-refs |
| 12 | SKILL.md enrichment | 1 | Reset modes table, background scripts, v1.5.0 |
| 13 | session-naming.md prefix | 1 | tq- prefix in queue mode sessions + examples |
| 14 | cron-expressions.md auto/manual | 1 | Auto vs manual crontab management section |
| 15 | Error handling consistency | 0 | Verified "and stop" present on all error paths |
| 16-17 | Description + allowed-tools | 2 | Trimmed descriptions, added Bash(command) |
| 18-20 | Final scoring + documentation | 1 | Progress doc, final re-scoring |

## Learnings (new, iterations 2-20)

10. **Stub reference files are a liability** — chrome-integration.md scored 43.8 (worst file) because it was 4 lines with no actionable content. A stub is worse than no file — it creates false confidence.
11. **Conditional flag omission prevents silent errors** — tq-reply was passing empty `--reply-to ""` to tq-message. Omitting the flag entirely when no reply context exists is more robust.
12. **Cross-reference rings create discoverability loops** — Adding `Related:` footers to all cron commands (/schedule, /pause, /unschedule, /jobs, /todo) means a user of any one command discovers all the others.
13. **grep `/<name>\.yaml` prevents prefix collisions** — `tq.*morning.yaml` matches both `morning.yaml` and `morning-review.yaml`. Using path separator + escaped dot (`/<name>\.yaml`) prevents false matches.
14. **Pre-flight binary checks catch "works on my machine" bugs** — converse.md and setup-telegram.md both assumed binaries were installed. A 1-line `command -v` check saves debugging time.
15. **Deduplication via cross-reference is higher leverage than deduplication via deletion** — todo.md's schedule logic was copy-pasted from schedule.md. Replacing with "Follow the same steps as `/schedule`" eliminates drift and halves the file.
16. **Heredoc quoting is the only safe pattern for arbitrary content** — tq-message's `--message "<SUMMARY>"` breaks if the summary contains quotes, backticks, or dollar signs. Heredoc to temp file handles all characters safely.
17. **Config permission checks are cheap security wins** — `chmod 600` on message.yaml and checking permissions in /health costs 2 lines each but prevents credential exposure.
18. **Auto vs manual scheduling needs explicit documentation** — tq-cron-sync and /schedule both modify crontab. Without documenting which takes precedence, users get confused when changes are overwritten.
19. **7 binaries, not 1** — health.md was only checking `tq`. Checking all 7 binaries catches partial installs where the symlink script failed mid-run.
20. **Diminishing returns after ~85** — Files scoring 85+ have incremental improvement opportunities (a word choice here, a formatting tweak there). The rubric correctly reflects this: scores above 85 require exceptional, not just good, execution.
