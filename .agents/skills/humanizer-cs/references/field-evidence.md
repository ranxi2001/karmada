# Field evidence

Load this reference when deciding how much context to repeat, whether to add a review label, or how strongly to normalize an unfamiliar project's artifact shape.

## Evidence boundary

The historical corpus v1 contains 687 de-identified derived records from 88 public threads in eight mature projects. It samples closed issues, merged pull requests, and closed unmerged pull requests from 2019, 2021, 2023, and 2025. It stores source URLs and lexical features, not bodies or usernames; the URLs remain traceable to public authors.

Treat the corpus as a false-positive guard, not a voice template:

- accepted work is not automatically good prose;
- common wording is not automatically correct;
- rare wording is not automatically artificial;
- GitHub-only behavior does not represent Gerrit, mailing lists, Trac, or chat;
- project rules and the supplied evidence still outrank corpus patterns.

## Calibrated rules

### Preserve native structure

Keep project templates, checklists, release-note blocks, issue-closing syntax, and slash commands. Do not replace them with a generic structure merely because the generic version is shorter.

### Match context depth to the artifact

Issue and pull-request bodies should carry enough anchors to be inspected without reconstructing the author's environment. Prefer supplied commands, paths, symbols, issue links, observed output, and explicit validation boundaries.

Inline comments already point to a diff location. For a local naming, syntax, documentation, or test request, one sentence or a focused question can be complete. Add trigger and consequence when the risk is not visible locally; never invent them to fill a review template.

Review replies are incremental. State only the new decision, code change, evidence, or unresolved disagreement. Repeat a symbol, SHA, or command when it disambiguates the update, not to make the reply look standalone.

Engineering summaries are status indexes. Use locators, exact states, blockers,
and next owners; do not turn each row into a full task report.

### Calibrate intent without imposing syntax

Use severity labels when the target project uses them or when a reader could otherwise mistake a blocker for a preference. Do not add `blocking:`, `nit:`, or `suggestion:` mechanically.

Preserve legitimate questions and uncertainty. A direct question is more trustworthy than a fabricated finding when reachability or impact is not established.

Preserve prior-art relationships. If another issue, PR, or discussion partially
overlaps the current work, name the relationship and next useful action instead
of rewriting it as either duplicate or unrelated.

Courtesy is compatible with directness, but it is not a required wrapper. In a direct reply, retain or add at most one natural acknowledgment when it recognizes the preceding contribution; remove it when it delays the technical update. A new finding can start with the behavior or question.

## Traceability

The methodology, aggregate counts, manual-audit links, limitations, source index, and rebuilding command live in the public repository's `docs/corpus-v1.md` and `research/corpus-v1/` directories.
