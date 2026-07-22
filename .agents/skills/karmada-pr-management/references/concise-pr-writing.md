# Concise Karmada PR Writing

Use this reference when drafting or shortening a Karmada PR body. The body is a reviewer index, not the complete engineering record.

## Evidence Snapshot

The 2026-07-14 sample removes hidden HTML comments, empty bodies, and automated cherry-pick PRs. Counts are reviewer-visible words and nonblank lines.

| Author | Sample | Median words | Median lines |
| --- | ---: | ---: | ---: |
| `RainbowMango` | 24 recent PRs | 80.5 | 13 |
| `zhzhuang-zju` | 23 recent PRs | 74 | 11 |
| `FAUST-BENCHOU` | 21 authored PRs | 38 | 9 |
| `hzxuzhonghu` | 1 Karmada PR | 104 | 21 |

The `hzxuzhonghu` PR sample is qualitative only. These examples describe local style; they do not make empty template fields or missing test evidence acceptable. Full methodology and representative links are in `internship-reports/day16-karmada-upstream-writing-style.md`.

## Soft Budgets

- Ordinary code, test, cleanup, or documentation PR: aim for 80-250 visible words and at most 30 nonblank lines.
- API, compatibility, security, or multi-component change: aim for 150-400 visible words and at most 45 nonblank lines.
- Above 400 words: perform a compression pass and state why the remaining detail must be in the body.
- Diff size alone is not a reason for a long body. Link the issue, proposal, or local evidence record instead of copying it.

These are review triggers, not hard correctness limits. Do not delete evidence required for a flake causal chain, compatibility contract, or security boundary merely to hit a number.

## Keep

1. One sentence stating the user or maintainer problem and the resulting behavior.
2. The exact `Fixes #N`, `Part of #N`, or `Refs #N` relationship.
3. At most three reviewer notes covering only material scope, compatibility, safety, or residual risk.
4. One compact validation line with the most relevant local commands and behavior-specific results. Do not cite fork CI unless the user explicitly requests it.
5. One sentence disclosing AI assistance and human validation.
6. A concrete release note, or `NONE`.

## Remove By Default

- File-by-file rationale tables already present in the diff or local preflight record.
- Complete test-case inventories; summarize behavior classes and give the main command.
- Chronological implementation or debugging diaries.
- Dynamic CI status, workflow counts, and Actions links that will become stale.
- Repeated scope/non-goal lists or implementation walkthroughs.
- Bot summaries, AI review output, and claims that merely restate the diff.
- Full RCA or proposal text when a stable linked issue/document can carry it.

## Long-Form Exceptions

- Proposal PR: keep the body to an executive summary and link the proposal document.
- Flake fix: summarize the first failure, proven causal edge, invariant, and validation; keep the full timestamp/code table and diagram in the linked issue when possible.
- API or compatibility migration: include the old/new contract and upgrade action, but move exhaustive field mappings to docs or the proposal.
- Security-sensitive change: retain the threat boundary and verification evidence even when the body exceeds the ordinary target.

## Compression Pass

Before requesting approval, ask:

- Can a reviewer state the problem, behavior change, risk, and validation after one screen?
- Does each paragraph change a review decision?
- Is any detail duplicated in the issue, proposal, diff, or local report?
- Are test claims tied to a concrete local command or behavior-specific result rather than a transient CI status?
- Would the body still be accurate next week?

Measure visible size with:

```bash
python3 .agents/skills/karmada-issue-discussion/scripts/draft_metrics.py <draft.md> --limit 250
```
