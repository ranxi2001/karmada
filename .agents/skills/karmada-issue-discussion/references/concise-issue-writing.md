# Concise Karmada Issue And Comment Writing

Use this reference when drafting Karmada issues, issue comments, PR comments, or review summaries. Select the artifact type first; do not force every investigation into one generic long template.

## Evidence Snapshot

The 2026-07-14 sample removes hidden HTML comments and empty bodies. Counts are reviewer-visible words.

| Author | Issue sample | Median words | Interpretation |
| --- | ---: | ---: | --- |
| `RainbowMango` | 20 recent issues | 196.5 | Umbrella and flake issues raise the median |
| `zhzhuang-zju` | 20 recent issues | 158 | Recent bug issues median 318 words |
| `FAUST-BENCHOU` | 3 authored issues | 74 | Small, mostly documentation bugs |
| `hzxuzhonghu` | 7 authored issues | 71 | Small qualitative sample |

The examples describe project style but are not a license to leave required fields empty. Full methodology and representative links are in `internship-reports/day16-karmada-upstream-writing-style.md`.

## Soft Budgets

- Enhancement or question: aim for 80-250 visible words.
- Reproducible bug: aim for 120-400 visible words, excluding irreducible logs or manifests.
- Focused flake issue with causal evidence: aim for 150-350 visible words before linked logs/tables.
- Ordinary issue/PR comment: aim for 40-180 visible words; a high-risk review finding may use up to about 250.
- Above 400 words for an issue or 250 for a comment: perform a compression pass and state the long-form reason.

These are review triggers. A source-backed RCA, proposal, or umbrella tracker may be longer when the structure remains scan-first.

## Choose A Type-Specific Shape

### Enhancement

```md
**What would you like to be added**:

<one concrete capability and first-phase scope>

**Why is this needed**:

<user impact or missing invariant>
```

### Bug

Use the repository bug template. Put the minimal failing scenario first, then expected behavior, reproduction, the smallest decisive log/source link, and environment fields that affect the result. Label an unproven cause as a hypothesis.

### Flake

Use the repository flake template. At `E0-E2`, report the job/test, first hard failure, artifact link, and next diagnostic step. At `E3`, add the shortest timestamp/code chain that proves the cause and link the full table/diagram.

### Proposal Or Umbrella

Start with goal and first-phase boundary, then a checklist of independent work items and acceptance criteria. Keep design details in a proposal document; keep the tracker readable as status changes.

### Comment Or Review

```md
I verified <scenario> at `<sha>`.

- Observation: <result>
- Evidence: <test, log, or code path>
- Impact: <bounded behavior>

Suggested next step: <one action or question>.
```

Omit any line that adds no information. Do not begin with a generic recap of the full thread.

## Remove By Default

- A restatement of the issue body or prior comments.
- Full raw logs when the first failure plus an artifact link is sufficient.
- Every command attempted during debugging; keep only decisive reproduction/validation.
- Background biographies, contributor reputation, or bot/AI conclusions.
- Multiple related links without a one-line relevance statement.
- Broad promises to implement work that has not been agreed or assigned.

## Compression Pass

- Lead with the outcome, impact, or exact question.
- Keep one evidence item per material claim.
- Move chronology and failed paths to local reports unless they change upstream decisions.
- Use a table only for three or more comparable cases or a real timestamp chain.
- End with one requested decision or next action.

Measure visible size with:

```bash
python3 .agents/skills/karmada-issue-discussion/scripts/draft_metrics.py <draft.md> --limit 250
```
