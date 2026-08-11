# Engineering summaries

Use this reference for weekly reports, manager-facing status, project summaries,
release summaries, and internship progress updates.

## Boundary

Rewrite supplied status evidence. Do not discover work, render or send email,
choose recipients, disclose private identity, publish portfolio text, or infer
maintainer decisions.

Repository privacy, employment, authorship, and disclosure rules outrank this
generic summary shape.

## Status truth

Keep reporter-owned completion separate from external acceptance:

- `done`: the reporter finished the local work or the change is merged,
  accepted, sent, or published by the owning process.
- `submitted`, `open`, or `waiting review`: the reporter has handed off work,
  but a maintainer, reviewer, manager, or release process still owns the next
  decision.
- `blocked`: the next action requires a named external decision, missing
  evidence, credentials, environment, or approval.
- `not pursued`: another issue, PR, or owner already covers the work, or the
  candidate failed a contribution-value gate.

Do not count an open PR, proposed issue, draft email, or green local check as an
accepted outcome unless the source evidence says it was accepted.

## Shape

Prefer rows or bullets that a manager can scan in 15 seconds:

```text
Result or state
Object and locator
Evidence
Value, risk, or blocker
Next action or owner
```

Start with the result or state, then name the project/component and locator.
Use PR and issue numbers as locators, not as achievements by themselves.

Good:

```text
- AI Agent Book PR #439: submitted and validated; waiting for maintainer review.
  Risk: merge timing is outside my control.
```

Weak:

```text
- Did lots of AI Agent Book work, including #439. Progress is good.
```

## Evidence and wording

- Bind numbers to an object: `2 PRs merged`, `4 review comments addressed`,
  `57 tests passed`, not `many` or `a lot`.
- Name the project, component, operation, or artifact behind a technical
  learning. Avoid empty phrases such as "learned a lot" or "improved quality".
- Preserve established terms such as CI, E2E, PR Review, Feature Proposal
  Review, mTLS, CRD, and project names.
- Report validation as observed: local command, CI job, reviewer approval,
  merge, release, or explicit skipped tier.
- Mention blockers only when they change ownership, timing, risk, or next
  action.

## Chinese summaries

For Chinese manager-facing text, keep English project terms and technical
locators when they are the stable names in source evidence. Use compact status
phrases such as `已提交`, `已合入`, `等待 maintainer review`, `本地验证通过`,
`未继续实现`, and `需要审批`.
