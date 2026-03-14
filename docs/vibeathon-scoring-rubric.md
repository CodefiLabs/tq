# Vibeathon-Style Scoring Rubric for Commands & Skills

Adapted from the AI Judge in [app-vibeathon-us](~/Sites/codefi/app-vibeathon-us).

## Criteria (weighted, 0-100 each)

| Criterion | Weight | What It Measures |
|-----------|--------|------------------|
| **Triggering & Discovery** | 30% | Will the command/skill surface when needed? Is the description specific, <60 chars, scannable in `/help`? Are trigger phrases comprehensive? |
| **Instruction Quality** | 25% | Can Claude reliably execute the instructions? Are steps unambiguous, imperative, and ordered? |
| **Completeness & Error Handling** | 20% | Does it handle missing args, edge cases, invalid input, network failures? |
| **Convention Adherence** | 15% | Follows tq naming (CLAUDE.md rules), formatting patterns, cross-references related commands? |
| **Conciseness & UX** | 10% | Lean body, no duplication with CLAUDE.md, progressive disclosure, good formatting? |

## Perspectives (evaluate each criterion through all 3)

| Perspective | Lens |
|-------------|------|
| **User** | Would a human find this via `/help`, understand what it does, know what args to pass? |
| **LLM** | Can Claude parse the frontmatter, follow steps in order, handle ambiguous input? |
| **System** | Are tool permissions correct? Paths valid? Commands exist? No security issues? |

## Impact Items (evidence-based scoring)

Each observation is tagged with an impact score:

| Impact | Meaning | Example |
|--------|---------|---------|
| +5 | Exceptional | Comprehensive trigger phrases covering 5+ natural phrasings |
| +3 | High | Clear error handling with actionable fallback |
| +2 | Medium | Proper cross-reference to related command |
| +1 | Low | Consistent formatting with sibling commands |
| -1 | Minor | Slightly verbose description (55-60 chars) |
| -2 | Medium | Missing argument-hint |
| -3 | High | Vague trigger that could misfire on unrelated prompts |
| -5 | Critical | Incorrect tool permission (allows destructive ops not needed) |

## Hybrid Scoring Formula

```
Step 1: Net impact per criterion
  net_impact = sum(positive_items) + sum(negative_items)
  total_items = count(all_items)

Step 2: Normalize and scale to 0-100
  normalized = net_impact / sqrt(total_items)
  raw_score = 50 + (normalized * 8.0)
  clamped = clamp(raw_score, 0, 100)

Step 3: Confidence adjustment (regression toward 50 when evidence sparse)
  evidence_density = total_items / 15   # 15 items = full confidence for a command
  confidence = clamp(evidence_density, 0, 1)
  deviation = clamped - 50
  final_score = round(50 + (deviation * (0.75 + 0.25 * confidence)))
```

## Target Score Distribution

| Range | Meaning | Expected % |
|-------|---------|------------|
| 90-100 | Exceptional — model for other projects | 5-10% |
| 75-89 | Strong — minor polish possible | 30-40% |
| 55-74 | Average — clear improvement opportunities | 30-40% |
| 35-54 | Below average — significant gaps | 10-20% |
| 0-34 | Needs major rewrite | 0-5% |

Score inflation is failure. If everything clusters 80-90, the rubric isn't discriminating.

## Weighted Composite

```
composite = sum(criterion_score * criterion_weight * criterion_confidence) /
            sum(criterion_weight * criterion_confidence)
```

## Command-Specific Checks

- [ ] `name:` matches filename (sans .md)
- [ ] `description:` < 60 chars, imperative verb, shown in `/help`
- [ ] `tags:` includes "tq" plus 2-3 domain tags
- [ ] `allowed-tools:` scoped to minimum needed (no wildcards)
- [ ] `argument-hint:` present if command accepts arguments
- [ ] Steps are numbered, imperative, sequenced correctly
- [ ] Error handling for missing/invalid arguments
- [ ] Cross-references related commands where appropriate

## Skill-Specific Checks

- [ ] Third-person trigger description with 5+ concrete phrases
- [ ] Body under 2000 words; details in `references/`
- [ ] All referenced files exist
- [ ] Commands table is complete (all 13 commands listed)
- [ ] No duplication of CLAUDE.md content
- [ ] Version field present and meaningful
