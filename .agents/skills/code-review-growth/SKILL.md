---
name: code-review-growth
description: Use when reviewing pull requests, code diffs, maintainer or bot review comments, CI-related code changes, or post-review misses to produce high-signal findings, verify behavioral risks, check test coverage, and update a reusable review pattern library from real review experience.
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

6. Write review comments as findings.
   - Lead with the impact and concrete failing scenario.
   - Include file/line context, why the code behaves that way, and the smallest credible fix or test.
   - Avoid style nits unless they block maintainability, correctness, or project conventions.

7. Close the learning loop.
   - When a maintainer or later review reveals a missed reusable pattern, update `references/review-patterns.md`.
   - Keep each pattern short: symptom, review check, evidence to gather, and test/fix cue.
   - Do not edit upstream-facing topic branches only to store learning notes; update local learning branches or internship records.

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
