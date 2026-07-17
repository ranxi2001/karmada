---
name: fix-e2e-flakes
description: Turn a source-proven Karmada E2E flake into an aligned reproduction, minimal causal fix, E4 validation, clean fork branch, CI classification, and reviewer-ready preflight. Use when an E2E failure already has logs and source-level RCA, or when implementing or reviewing a /kind flake fix. Do not use for E0-E2 guesses, generic timeout or retry patches, mock-only scenarios, or ordinary deterministic code failures.
---

# Fix E2E Flakes

Convert a proven intermittent failure into the smallest change that removes its causal edge. Keep the observed failure, deterministic reproduction, code fix, diagram, and validation at the same abstraction level.

## Prerequisites

1. Use `e2e-root-cause-analysis` to collect logs, correlate objects and timestamps, trace the source path, and reach a source-backed cause.
2. Use the E0-E4 evidence levels defined by `code-review-growth`:
   - E0-E1: symptom or correlation only. Stop; do not patch.
   - E2: plausible mechanism. Improve diagnostics or design the next experiment only.
   - E3: source-backed cause. Implementation may begin.
   - E4: the regression test fails without the causal fix and passes with it.
3. For Karmada branches, commits, fork CI, and upstream text, follow `karmada-pr-management` and `karmada-push-ci-check`.

Do not classify a deterministic product-code failure as a flake merely because CI exposed it. Exclude synthetic invalid-input cases unless repository contracts or real production evidence show that the input is reachable.

## Alignment Contract

Before editing code, write one row that binds all artifacts to one transition:

| Dimension | Required identity |
| --- | --- |
| Object | Same kind, namespace/name, generation or lifecycle instance |
| State layer | Same API object, informer cache, member-cluster object, or reflected status |
| Transition | Same old state, triggering event, and new state |
| Consumer | Same predicate, handler, controller branch, or assertion |
| Failure | Same missed wake-up, stale read, premature assertion, race, or terminal mismatch |
| Recovery | Same event or invariant whose observation proves the fix |

Reject a proposed reproduction that merely resembles the symptom. For example, a fake invalid value does not reproduce a missed cache event, and a longer timeout does not reproduce a stale-status assertion.

## Workflow

### 1. Establish Relevance and Ownership

- Confirm the failure is intermittent across equivalent revisions or is a timing/order-dependent failure in one run.
- Search open issues and PRs for the exact component, test name, error, and proposed causal cut.
- Check active assignees and maintainer direction before investing in a duplicate fix.
- Identify the writer of each relevant field and the consumer that failed to observe it.

### 2. Prove the Cause Backwards

Start at the final failed assertion and trace backwards through:

1. the last consumer read;
2. cache or API state at that time;
3. the event or write expected to advance the state;
4. filtering, enqueueing, reconciliation, and status persistence;
5. the earliest divergence between a passing and failing path.

Record timestamped log evidence and exact source locations. State competing explanations and the evidence that rules them out. Do not begin implementation below E3.

### 3. Draw One Comparable Sequence

Create a project-local Mermaid sequence diagram with the same actors and message labels in three colored regions:

- observed failure;
- deterministic reproduction;
- fixed path.

The reproduction region must exercise the same causal edge as the observed failure. The fixed region must show both recovery and the final no-op or terminal condition, so a new loop or event storm is visible. Keep the `.mmd` source and rendered PNG or SVG together.

### 4. Freeze Scope Before Code

List:

- the exact branch name and upstream base SHA;
- files that may change and why each is required;
- files and APIs that must not change;
- the narrow regression command and broader validation command;
- the expected failure before the fix and expected pass after it.

If implementation needs a new shared abstraction, API change, generated code, broad timeout increase, or unrelated refactor, stop and re-evaluate the design.

### 5. Reproduce the Exact Edge

Prefer a deterministic test that constructs the observed old state, triggering event, and new state, then checks the failed consumer outcome.

- Run the test against the unfixed code and preserve the failure output.
- Avoid arbitrary sleeps, random timing, network dependence, and invented invalid inputs.
- If a full deterministic reproduction is impractical, combine the original CI trace with a source-level regression of the exact missed transition. Record which environment-dependent part remains unreproduced.
- For test-synchronization flakes, exercise the real lifecycle and wait for the exact state consumed by the assertion; do not replace the workflow with mocks.

### 6. Apply the Smallest Causal Fix

Change the earliest owned decision that loses or observes the transition incorrectly.

- Controller event loss: compare every field owned by the downstream reconciliation decision, enqueue the relevant update, and prove equal final state is ignored.
- Cache/API races: wait on the authoritative consumer-visible invariant, not an unrelated proxy state.
- Test synchronization: use a bounded poll for the exact object and lifecycle instance, then retain the original semantic assertions.
- Retry behavior: repair the state or event dependency before adding retries.

Do not use a generic sleep, broader timeout, unconditional retry, or defensive nesting as the primary fix. A timeout change is acceptable only when the documented contract itself requires a longer bound and evidence rules out a missing event or stale read.

### 7. Reach E4

Validate in this order:

1. regression test fails on the clean base or with only the test patch;
2. regression test passes with the fix;
3. temporarily reverse the causal production hunk and confirm the same test fails;
4. restore the fix and rerun the focused package;
5. run formatting, `git diff --check`, and the relevant broader verification;
6. run the real E2E workflow when locally available; otherwise use fork push CI and disclose the boundary.

Do not weaken assertions to obtain E4. The failure without the production hunk must identify the same causal edge.

### 8. Falsify Regressions

Review the diff as an adversary:

- Could the new event cause an infinite reconciliation loop or event storm?
- Does nil versus empty state create one extra event, and does it terminate?
- Can an older lifecycle instance satisfy the wait?
- Is the watched field written by the component assumed in the RCA?
- Does the fix hide a deterministic product error as a test flake?
- Are unrelated fields, components, or generated artifacts changed?

Add or retain a final-state no-op test for controller event changes. For waits, require identity plus the terminal condition, not only a non-empty status.

### 9. Isolate, Push, and Review

- Create one clean topic branch from the recorded `upstream/master` SHA per independent fix.
- Keep internship reports and local skills on `intern`.
- Produce one focused, signed-off commit and verify the merge-base and file list.
- Push to the personal fork and classify every failed job as code issue, fork-environment difference, or known/new CI flake.
- Review the fork diff against the alignment contract before drafting upstream text.
- Obtain explicit user confirmation for the exact upstream target and English text before opening or commenting on a PR or issue.

## Required Handoff

Leave enough evidence for another reviewer to falsify the fix without chat context:

- run URL, job, test, timestamps, and object identity;
- E3 causal chain with source paths;
- alignment-contract row;
- observed/reproduction/fixed sequence diagram and rendered asset;
- scoped file and no-change lists;
- baseline failure and patched-pass commands;
- E4 reverse-patch result;
- branch, commit SHA, fork CI result, and remaining validation gap;
- concise reviewer-facing explanation of why the change is causal rather than probabilistic.

Treat the skill itself as incomplete until it has been forward-tested on a real flake fix and its gates prevented at least one plausible but misaligned patch.
