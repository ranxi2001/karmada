# Artifact contracts

Use the target repository's template first. These shapes supply missing reasoning; they are not replacement templates.

## Issue

An issue should remain valid if the proposed implementation changes.

### Bug

```text
Observable behavior
Minimal reproduction
Expected behavior or contract
Impact and affected boundary
Relevant environment
Confirmed evidence and open hypotheses
```

Lead with what a user, caller, controller, test, or operator can observe. Keep the root cause separate unless the source path or a counterfactual confirms it. Include only environment fields that affect reproduction.

Preserve the target issue template. Add a generic section only when it supplies decision-relevant information that the template does not already capture.

If evidence is static or mock-only, keep the artifact as a question or contract
clarification until a production path, public API contract, or accepted test
contract is established.

### Enhancement or design question

```text
Missing capability or decision
User or maintainer impact
First-phase boundary
Credible alternatives
Exact decision requested
```

Do not preselect an implementation when the project has not accepted the contract.

## Pull request

The body is an index to the issue, diff, tests, and risks. It is not an implementation diary.

```text
Problem or old observable behavior
New contract-level behavior
Issue relationship
Validation evidence
Compatibility, non-goal, or residual risk
Required release note or disclosure
```

Use exact commands only when they help reviewers understand coverage. State results and skipped tiers separately. Avoid dynamic check counts and file-by-file narration that the diff already provides.

For larger changes, point reviewers to the first decision-relevant diff area,
test, or compatibility boundary. Do not paste local investigation logs when a
locator and validation summary is enough.

Keep project-native checklists, release-note blocks, bot commands, ticket syntax, and hidden template comments. A short local fix may need only a compact body; a contract or compatibility change may need alternatives and residual risk. Do not normalize both to the same length.

Example:

```markdown
The controller returned success after a transient API timeout, so the work was not retried.

This change preserves the error from `syncTarget` and adds a regression test for the timeout path. It does not change retries for terminal validation errors.

Tests: `go test ./pkg/controller/...` (pass)

Fixes #123.
```

## Review comment

A finding must let the author verify the concern without guessing at the reviewer's intent.

```text
Optional severity or intent label
Affected location
Trigger or execution path
Concrete consequence
Evidence or confidence
Smallest correction direction or missing test
```

Use `blocking`, `non-blocking`, `question`, `suggestion`, or the repository's established labels. Do not make every comment sound mandatory.

Labels are optional unless project convention or ambiguity requires one. Inline comments already carry a diff location: a local syntax, naming, documentation, or test request may be one sentence or a focused question. Use the full trigger-consequence-evidence shape when the risk is not obvious from the location. Never invent downstream impact merely to complete the shape.

Address the code:

```markdown
blocking: this drops the retry signal when `Update` returns a transient error.

`Reconcile` receives `nil`, so the queue forgets the item and the desired state can remain stale until another event arrives. Please return the error here and cover the timeout path in the controller test.
```

Do not address the person:

```text
You clearly did not consider retries here.
```

If the evidence supports only a question, ask it. Do not manufacture a finding to sound decisive.

Before returning a non-trivial comment, check whether it can be understood if
the author sees only the changed line plus the comment. Add trigger, state
transition, consequence, or test direction when the local diff does not already
carry that context.

## Review reply

First verify that project policy permits AI assistance for replies.

Treat the reply as an increment to the visible thread. A direct reply may start with one brief, context-specific acknowledgment; answer the actual request immediately after it. The following slots are optional and should not become a checklist:

```text
Optional acknowledgment
Decision or direct answer
What changed and where, if applicable
Validation evidence
Remaining disagreement or question
```

Do not restate the original finding or surrounding code unless the reference is needed to disambiguate the new state.

Example:

```markdown
Fixed in `abc1234`: `Reconcile` now returns the transient error, and `TestReconcileRetriesUpdateTimeout` covers the queue retry path. `go test ./pkg/controller/...` passes.
```

Do not write generic replies such as "Thank you for the insightful feedback. I have carefully addressed your concern." If no change was made, explain the technical reason and invite a decision on the specific disagreement. See [comment communication](comment-communication.md) for the no-post gate and thread-specific cadence.

## Discussion comment

For issue or proposal discussion, use only the parts that move the decision:

```text
Current conclusion or disagreement
Evidence that changes the decision
One focused unresolved question or next action by default
```

Do not recap the full thread unless the user explicitly needs a synthesis. A new discussion starts with the behavior or decision; a follow-up mentions only the new state. See [comment communication](comment-communication.md) for direct-reply versus inline guidance.

When referencing prior art, classify the relationship instead of flattening it:
same symptom, same root cause, partial overlap, superseded, already fixed, or
separate problem. An active assignee or open PR usually means the better action
is review or test feedback, not a duplicate issue.

For flakes, preserve evidence level: one failure plus a green rerun supports
nondeterminism, not root cause. Ask for log sections, operation names, repeated
patterns, or counterfactual evidence before recommending merge or retry logic.

## Engineering summary

For weekly reports, manager updates, project summaries, and internship status,
use [engineering summaries](engineering-summaries.md).

```text
Result or state
Object and locator
Evidence
Value, risk, or blocker
Next action or owner
```

Do not treat PR or issue numbers as outcomes by themselves. Preserve the
difference between submitted, reviewed, merged, accepted, blocked, and not
pursued.
