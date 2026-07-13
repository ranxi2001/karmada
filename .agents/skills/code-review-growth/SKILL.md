---
name: code-review-growth
description: Use when reviewing pull requests, code diffs, maintainer or bot review comments, CI-related code changes, flake root-cause analyses, or post-review misses to produce high-signal findings, verify behavioral risks, check test coverage, and update a reusable review pattern library from real review experience.
---

# Code Review Growth

## Purpose

Use this skill to make code review repeatable and cumulative. It complements repo-specific skills: use the repo skill for branch rules, posting gates, and project commands; use this skill for review reasoning and learning from misses.

## Review Workflow

1. Gather the exact review surface.
   - Read the PR body, linked issue, changed files, relevant surrounding code, CI state, and prior discussion.
   - On GitHub PRs, read both conversation comments and line review comments. Issue comments alone miss review threads:

```bash
gh api repos/OWNER/REPO/issues/PR_NUMBER/comments --paginate
gh api repos/OWNER/REPO/pulls/PR_NUMBER/comments --paginate
gh api repos/OWNER/REPO/pulls/PR_NUMBER/reviews --paginate
```

2. Build a change model.
   - State the intended behavior in one sentence.
   - Map entry points, call chain, data flow, side effects, and external contracts.
   - Compare the PR description against the actual diff; treat mismatches as review leads.

3. Classify risk surfaces before looking for findings.
   - Correctness: wrong result, missed state transition, bad default, lost error.
   - Control flow: early return, abort, panic/recover, timeout/cancel, retry, cleanup.
   - Concurrency and lifecycle: races, goroutine leaks, watch/reconnect, stale caches.
   - Security and resource use: auth boundary, path traversal, cardinality, memory/CPU growth.
   - API and compatibility: user-visible behavior, upgrade path, generated artifacts.
   - Observability: metric scope, label cardinality, logging signal, health/readiness semantics.
   - Tests: whether the changed behavior has positive, negative, and boundary coverage.

4. Trace non-happy paths explicitly.
   - For each modified entry point, check normal success, invalid input, auth failure, not-found/unmatched route, size limit, timeout, cancellation, panic, partial failure, and cleanup.
   - For middleware, controllers, schedulers, and retries, reason about who wraps whom and which code still runs after an early exit or panic.

5. Validate before posting.
   - Prefer local tests, targeted reproduction, source-level proof, logs, or CI artifacts.
   - Separate confirmed findings from questions and speculative concerns.
   - If a finding depends on an untested path, suggest a focused regression test.
   - For flakes, apply the evidence and stop gates below; a green rerun is classification evidence, not root-cause proof.

6. Write review comments as findings.
   - Lead with the impact and concrete failing scenario.
   - Include file/line context, why the code behaves that way, and the smallest credible fix or test.
   - Avoid style nits unless they block maintainability, correctness, or project conventions.

7. Close the learning loop.
   - When a maintainer or later review reveals a missed reusable pattern, update `references/review-patterns.md`.
   - Keep each pattern short: symptom, review check, evidence to gather, and test/fix cue.
   - Do not edit upstream-facing topic branches only to store learning notes; update local learning branches or internship records.

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
| This is the root cause | `OBS` + `CODE` completing the causal chain (`E3`) |
| This patch removes the cause | Controlled baseline-versus-patch evidence or a regression counterfactual (`E4`) |
| This direction is acceptable upstream | Explicit `MAINTAINER` evidence |

A test passing proves only its assertions on that run. Check whether the test would fail with the patch reverted or the disputed edge restored. Agent, reviewer, and maintainer conclusions remain claims until their supporting evidence is inspected; role changes coordination priority, not technical truth.

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
