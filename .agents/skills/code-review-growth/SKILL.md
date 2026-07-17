---
name: code-review-growth
description: Use when reviewing pull requests, code diffs, maintainer or bot review comments, CI-related code changes, flake root-cause analyses, or post-review misses to produce high-signal findings, verify behavioral risks, check test coverage, and update a reusable review pattern library from real review experience.
---

# Code Review Growth

## Purpose

Use this skill to make code review repeatable and cumulative. It complements repo-specific skills: use the repo skill for branch rules, posting gates, and project commands; use this skill for review reasoning and learning from misses.

## Review Workflow

1. For community scans or target selection, apply the Contribution Value Gate before downloading full artifacts or reading the complete diff. If the user explicitly requests one PR, explain a low-value classification and keep depth proportional.
2. Gather the exact review surface.
   - Read the PR body, linked issue, changed files, relevant surrounding code, CI state, and prior discussion.
   - After a delayed review, rebase, or base-branch advancement, compare every changed file against the current base and overlapping merged PRs. Distinguish a change that was unrelated when proposed from one that was originally relevant but is now redundant.
   - On GitHub PRs, read both conversation comments and line review comments. Issue comments alone miss review threads:

```bash
gh api repos/OWNER/REPO/issues/PR_NUMBER/comments --paginate
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments --paginate
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews --paginate
```

3. Build a change model.
   - State the intended behavior in one sentence.
   - Map entry points, call chain, data flow, side effects, and external contracts.
   - Compare the PR description against the actual diff; treat mismatches as review leads.

4. Classify risk surfaces before looking for findings.
   - Correctness: wrong result, missed state transition, bad default, lost error.
   - Control flow: early return, abort, panic/recover, timeout/cancel, retry, cleanup.
   - Concurrency and lifecycle: races, goroutine leaks, watch/reconnect, stale caches.
   - Security and resource use: auth boundary, path traversal, cardinality, memory/CPU growth.
   - API and compatibility: user-visible behavior, upgrade path, generated artifacts.
   - Observability: metric scope, label cardinality, logging signal, health/readiness semantics.
   - Tests: whether the changed behavior has positive, negative, and boundary coverage.

5. Trace non-happy paths explicitly.
   - For each modified entry point, check normal success, invalid input, auth failure, not-found/unmatched route, size limit, timeout, cancellation, panic, partial failure, and cleanup.
   - For middleware, controllers, schedulers, and retries, reason about who wraps whom and which code still runs after an early exit or panic.

6. Validate before posting.
   - Prefer local tests, targeted reproduction, source-level proof, logs, or CI artifacts.
   - Separate confirmed findings from questions and speculative concerns.
   - If a finding depends on an untested path, suggest a focused regression test.
   - For flakes, apply the evidence and stop gates below; a green rerun is classification evidence, not root-cause proof.

7. Write review comments as standalone findings.
   - Treat the line anchor as location, not explanation. State the current behavior or claim in plain language before challenging it.
   - Lead with one concrete scenario or counterexample, explain the resulting impact or inference gap, and end with the smallest credible change or test.
   - When disputing a conclusion, explicitly separate the **signal** (what the observation proves) from the **claim** (what the code or text concludes) and name the missing evidence bridge.
   - Translate domain terms into their role before listing symbols or functions. A list such as UID/generation/resourceVersion or `handleErr`/`Forget` does not explain why it matters by itself.
   - Use polite forms such as `Could ...?` only for the requested action. Politeness does not replace the causal explanation that precedes it.
   - Apply the Review Visualization Gate below before turning a multi-actor, branching, or temporal argument into another prose paragraph.
   - Avoid style nits unless they block maintainability, correctness, or project conventions.

8. Close the learning loop.
   - When a maintainer or later review reveals a missed reusable pattern, update `references/review-patterns.md`.
   - Keep each pattern short: symptom, review check, evidence to gather, and test/fix cue.
   - Do not edit upstream-facing topic branches only to store learning notes; update local learning branches or internship records.

## Contribution Value Gate

Production reachability and contribution value are separate gates. Before spending substantial review tokens or recommending a task, determine:

1. **Workflow relevance**: Does the trigger occur during supported, ordinary use? Deliberately invalid values, manual corruption, mock-only errors, and extreme scheduler/configuration constructions default to low value without evidence from real workloads.
2. **Material outcome**: Does the patch prevent security exposure, data loss/corruption, process-wide unavailability, broken compatibility, or a persistent wrong result? Trace framework recovery and retries; a recovered panic and a returned error may enter the same queue path and leave the same object stuck.
3. **Prevalence and ownership**: Look for repeated incidents, ordinary-path source evidence, user demand, or maintainer direction. `Observed once under a constructed input`, green CI, no assignee, and no human review do not establish priority.
4. **Root-cause leverage**: Prefer fixing the existing validation, contract, ownership, or state-transition boundary. Downgrade symptom wrappers that only improve logs, and fixes that add defensive branches while preserving the bad final state.
5. **Complexity cost**: Do not grow nested validation, guards, retry states, or tests for unsupported inputs merely because a mock can reach them. The implementation and maintenance cost must be proportionate to production impact.

Classify the target before deep review:

- **PRIORITIZE**: normal workflow or material security, integrity, availability, compatibility, repeated-incident, or maintainer-priority impact.
- **LIGHTWEIGHT**: narrow but real hygiene with a small boundary fix; review briefly only when it does not displace strategic work.
- **SKIP**: mock-only, deliberately invalid/unsupported, extreme unobserved state, self-healing/no final-outcome change, or defensive complexity greater than likely benefit.

It is valid to return `no worthwhile candidate`. When a target is `SKIP`, stop after a compact reason instead of fetching full JSON, reading every file, running fault injection, or inventing more edge cases. Explicit user requests for that exact PR override the stop, but not the evidence labels or proportionality requirement.

The classification governs our attention, not whether another contributor's patch may merge. A correct low-complexity hygiene fix does not warrant a discouraging review comment merely because we would not choose it. Lack of a company production incident is not a technical blocker. Comment only when there is a specific defect or cost: disproportionate defensive complexity, wrong behavior/contract, regression risk, missing material evidence for a strong impact claim, or conflict with maintainer direction.

## Review Comment Comprehension Gate

A technically correct comment still fails review quality when the author needs the reviewer's private investigation, local report, or follow-up chat to understand it. Before posting a non-trivial comment, hide that private context and verify that a reader with only the diff and thread can answer:

1. What exact behavior, sentence, or conclusion is under review?
2. What concrete input, event order, or counterexample exposes the problem?
3. What does the current evidence prove, and what stronger claim does it not prove?
4. Why does that distinction matter to behavior, diagnosis, compatibility, or maintenance?
5. What is the smallest requested change, and how would it close the gap?

Use this compact structure without requiring literal labels:

- **Observation**: quote or paraphrase the current behavior.
- **Counterexample or failure**: give one concrete case that produces the same signal or bad outcome.
- **Reasoning**: connect the example to the impact or missing evidence.
- **Action**: request a specific wording, code, or test change.

For inference-boundary comments, make the contrast explicit: `signal = one grep match; claim = no runtime retry`, or `signal = fast return; claim = stale previous-lifecycle state`. Do not make the author infer this distinction from a list of implementation terms.

If the author says the comment is hard to understand, treat that as a review-quality defect. Rewrite from the concrete observation and one plain-language counterexample before adding more references or jargon. A link can support the explanation, but it cannot carry context that the comment itself omits.

## Review Visualization Gate

Use a visualization when it makes the disputed relationship materially easier to understand, not merely because a comment is technical. Default to a compact inline Mermaid diagram when the explanation contains any of these:

- three or more actors, state layers, or dependent transitions;
- ordering, retry, cleanup, race, or recovery behavior;
- one signal with multiple plausible causes;
- a current-versus-proposed flow whose invariant is hard to scan in prose.

Use `flowchart` for branching causes or decision logic, `sequenceDiagram` for actor order and retries, and `stateDiagram-v2` for lifecycle transitions. Keep a review diagram focused on one question and usually 4-10 nodes. Follow `project-mermaid` for source grounding, labels, and syntax validation.

For a PR proposal that changes nodes within the same flow, preserve the node order and labels across current/proposed views. Keep unchanged/current nodes neutral, accent changed or new nodes, use amber for open questions and red only for material risk, and repeat those meanings in labels or line styles.

Structure a visual review comment as:

1. one sentence stating the finding or inference gap;
2. the smallest Mermaid diagram that exposes the relationship;
3. one sentence stating the evidence boundary and requested action.

Do not force Mermaid onto a single condition or one-step fix. Do not make the diagram the only explanation: retain a prose conclusion for accessibility, label hypotheses as hypotheses, and cite the code/log evidence for consequential arrows. When a diagram synthesizes meeting, log, experiment, or research evidence, state what the source supports, what it does not establish, and its provenance limits. If a prose comment keeps growing because it narrates arrows or event order, stop compressing sentences and draw the relationship.

## Evidence Model

Label every material claim by what actually supports it. Pick evidence for the claim being made; there is no universal source ranking.

- `OBS`: timestamped logs, a failing test, a controlled reproduction, or another direct observation of what happened.
- `CODE`: exact-SHA source and branch behavior, proving what the implementation can or will do for stated inputs.
- `DOC`: the version-matched public contract or documented semantics.
- `MAINTAINER`: project direction, acceptance criteria, or a review decision; this does not replace technical proof.
- `INFERENCE`: an unproven connection between facts. Keep it visibly labeled until supported.

Match the claim to sufficient evidence:

| Claim | Minimum evidence |
| --- | --- |
| An exact commit passed a check | Exact-SHA CI result or complete local command result |
| A failure is nondeterministic | Same-SHA rerun or repeated independent observations (`E1`) |
| A failure path is reachable in production | An observed occurrence, or `CODE`/`DOC` identifying a real producer or interface contract that can produce the trigger under reachable preconditions |
| This is the root cause | `OBS` + `CODE` completing the causal chain (`E3`) |
| This patch removes the cause | Controlled baseline-versus-patch evidence or a regression counterfactual (`E4`) |
| This direction is acceptable upstream | Explicit `MAINTAINER` evidence |

A test passing proves only its assertions on that run. Check whether the test would fail with the patch reverted or the disputed edge restored. Agent, reviewer, and maintainer conclusions remain claims until their supporting evidence is inspected; role changes coordination priority, not technical truth.

## Production Reachability Gate

Apply this gate before calling an unobserved scenario a bug or posting it as a blocking review finding:

1. Define the exact trigger, including input, error, timing, concurrency, and prior state.
2. Identify its real producer. Use either an observed occurrence or `CODE`/`DOC` proving that a production component or interface may produce it. An arbitrary mock return is not a producer.
3. Prove the preconditions are reachable through supported operations. Do not rely on states forbidden by validation, locking, ownership, or controller ordering.
4. Trace retry, resync, restart, later events, and cleanup to determine whether the system remains wrong or self-heals within its contract.
5. Run a counterfactual test only after reachability is established, and inject an error or state that the real boundary is allowed to produce.
6. Classify the result accurately:
   - **Observed bug**: the trigger and impact occurred in logs, CI, or a realistic end-to-end reproduction.
   - **Reachable latent bug**: source or contract evidence proves the trigger can occur, and a focused test proves the bad outcome, but no real occurrence has been observed.
   - **Hypothetical scenario**: only a synthetic test or imagined ordering creates the trigger; production reachability is unproven.

Fault injection proves conditional control flow, not production reachability. A reachable latent bug may still block when the trigger is a routine external failure mode and the impact violates a correctness or safety invariant. If reachability is unproven, write a question or evidence gap and request a realistic test; do not present it as a confirmed bug. If reachability is proven, still apply the Contribution Value Gate: `can happen` does not imply `worth implementing or deeply reviewing`.

## Flake Root-Cause Gate

Treat flake classification and patch authorization as separate decisions. Use these evidence levels:

- `E0 Symptom`: a timeout, failure message, or failed job.
- `E1 Nondeterminism`: the same SHA passes on rerun or after an empty commit. This supports flake classification only.
- `E2 Hypothesis`: an experiment exposes a timing or state window. Label the explanation as a hypothesis, not root cause.
- `E3 Causal chain`: timestamped logs and source branches connect the producer, reflected cache/status, consumer decision, queue/retry behavior, recovery event, and terminal stuck state. Only this level supports the term root cause and patch design.
- `E4 Causal validation`: a controlled reproduction, regression test, or observable baseline-versus-patch counterfactual shows that the patch cuts the proven causal edge. A reasoned counterfactual alone is patch design, not validation.

For every flake, trace this sequence before proposing a fix:

1. Identify the first hard failure, excluding later cleanup and control-plane fallout.
2. List actors and the exact create/update/delete/reconcile events.
3. Separate authoritative state from member state, caches, discovery results, and reflected status.
4. Find the consumer decision and the exact function/branch that turns stale state into failure.
5. Trace retry, backoff, `Forget`, requeue, and event filters such as generation, labels, status, or resource version.
6. Identify the recovery event and prove why it does or does not make the system self-heal.
7. State the invariant the patch establishes and the counterfactual timeline with that invariant present.

Build a timestamp/code evidence table and a Mermaid `sequenceDiagram`. Every causal arrow must cite a timestamped log or a `file:function/branch`; helper names and comments are not proof of what they observe. Mark unsupported arrows as hypotheses and continue investigating.

When an arrow lacks evidence, instrument or inspect each component boundary. Record the actor/function, input, output or decision, state source (authoritative API, member object, cache, or reflected status), timestamp, correlated object identity, and a freshness marker such as UID, generation, resource version, or lifecycle transition.

Also trace backward from the terminal symptom instead of only narrating forward:

```text
terminal symptom
<- last decision that prevented recovery
<- input used by that decision
<- producer of the reflected or cached state
<- authoritative state transition
```

For waits and eventually-consistent checks, define both the condition and why the observation belongs to the current lifecycle. A fresh API GET can still return stale reflected status. When names are reused, require old-state disappearance followed by the new transition, or correlate by UID/generation/resource version; a bare boolean such as `APIEnabled=true` is insufficient. If test pollution is plausible, compare the target alone with `predecessor -> target`, then narrow the predecessor set instead of only rerunning the target.

Stop under these conditions:

- At `E0` or `E1`, do not change product or test synchronization logic.
- At `E2`, add diagnostics or publish a clearly labeled hypothesis only; do not open a fix PR or claim root cause.
- Require `E3` before implementing a flake fix. Also seek `E4`; when controlled validation is objectively impractical, record why, the residual risk, and obtain maintainer direction before upstream posting.
- Do not use a longer timeout, `sleep`, retry, or generic wait as a substitute for RCA. Add a bounded wait only when source evidence proves the next consumer requires that exact missing invariant.
- Do not recommend `/lgtm` or `/approve` from green CI alone; verify that the patch closes the proven causal chain.

## Independent Falsification Pass

Use a fresh-context review for non-obvious, high-risk claims involving shared state, controllers, scheduler queues, certificates, authentication, cleanup, or flake RCA. Give the reviewer the raw artifact and the contract, but omit the prior conclusion, intended fix, and investigation narrative so they are not anchored.

Ask the reviewer to identify unsupported evidence edges, an alternative event order, hidden state coupling, recovery paths that may or may not self-heal, and whether the proposed regression would fail without the patch. Treat the response as data, not a verdict. Reconcile each point as one of: contract misread, valid and actionable, valid tradeoff, or noise. Record unresolved evidence gaps explicitly. Skip this pass for mechanical or low-risk edits.

## Focused Subroutines

### Middleware Metrics

For HTTP or Gin middleware instrumentation, draw the registration order and identify which middleware wraps which behavior.

Check at least these paths:

- Normal handler return.
- Middleware `Abort()` or early return before the metrics layer.
- Handler panic recovered by recovery middleware.
- Excluded endpoints such as `/metrics` and `/health`.
- Unmatched routes and dynamic route labels.

In Gin, post-`c.Next()` recording only runs if execution returns to that middleware frame. If `metrics` is registered after `gin.Recovery()`, a handler panic unwinds past `metrics` before `Recovery()` converts it to a 500, so recovered 500s are not counted. Register metrics before recovery, or implement equivalent panic-safe recording intentionally.

Expected regression tests:

- Oversized request returns 413 and records HTTP request count/duration.
- Panic route returns 500 through recovery and records HTTP request count/duration.
- Unmatched route uses a bounded label such as `unmatched`, not raw URL paths.

## Pattern Library

Read `references/review-patterns.md` when doing a non-trivial review, when investigating a missed finding, or when the PR touches HTTP middleware, metrics, CI flakes, controllers, schedulers, certificates, auth, or resource cleanup.
