# Review Pattern Library

Keep entries concise and evidence-oriented. Add a new entry only when a real review, maintainer comment, CI failure, or postmortem exposes a reusable lesson.

## Entry Format

- Pattern:
- Seen in:
- Miss symptom:
- Review check:
- Evidence to gather:
- Test or fix cue:

## Gin Middleware Metrics Must Wrap Early Exits And Recovery

- Pattern: Request metrics implemented after `c.Next()` must be registered outside middleware that can abort, recover, or otherwise short-circuit the request lifecycle.
- Seen in: `volcano-sh/agentcube#400`, PicoD Prometheus metrics review.
- Miss symptom: 413 body-size rejections or recovered 500 panics are returned to clients but not counted in HTTP request metrics.
- Review check: Write the middleware order as a stack. Ask whether `metrics` executes for normal return, `Abort()`, and panic + `gin.Recovery()`.
- Evidence to gather: Current `engine.Use(...)` order, middleware source, and a test route or request that triggers the non-happy path.
- Test or fix cue: Register metrics before `gin.Recovery()` and before body-size/auth limiters that should be observed; add tests asserting 413 and recovered 500 metrics.

## Prometheus Labels Need Bounded Cardinality

- Pattern: Labels derived from user-controlled raw paths, IDs, names, or error strings can create unbounded time series.
- Seen in: `volcano-sh/agentcube#400`, unmatched route path fallback.
- Miss symptom: `c.FullPath()` is empty and code falls back to `c.Request.URL.Path`, causing one label value per arbitrary 404 path.
- Review check: For every metric label, classify whether values are from a bounded enum, route template, status code, method, or untrusted raw input.
- Evidence to gather: Metric definitions, label extraction code, and route behavior for unmatched or dynamic paths.
- Test or fix cue: Use route templates such as `/api/files/*path` or fixed fallbacks like `unmatched`; test unmatched routes do not emit raw paths.

## Metric Name And Help Must Match Measurement Window

- Pattern: A metric can be technically correct but semantically misleading if the code increments it around a broader or narrower window than the name implies.
- Seen in: `volcano-sh/agentcube#400`, `picod_active_executions` counted the whole execute handler, including validation.
- Miss symptom: Name says active command executions, but the gauge includes JSON parsing, validation, and setup.
- Review check: Compare metric name/help text against the exact increment/decrement scope.
- Evidence to gather: Metric help string and surrounding code for `Inc()`, `Dec()`, counters, and status labels.
- Test or fix cue: Either narrow the instrumentation window or rename/help-text the metric to describe handler requests.

## Duration Tests Should Avoid Strictly Positive Timing Assumptions

- Pattern: Tests for elapsed time, histogram sample sums, or latency values can be flaky if they require a strictly positive duration for very fast code paths.
- Seen in: `volcano-sh/agentcube#400`, `picod_http_request_duration_seconds` test asserted `SampleSum > 0`.
- Miss symptom: The observed sample count is correct, but the duration sum can be zero on very fast paths or coarse timer resolution.
- Review check: For metrics tests, assert that a sample was observed and that sums are non-negative unless the code deliberately sleeps or controls time.
- Evidence to gather: Histogram assertions, timer source, and whether the tested path has guaranteed non-zero work.
- Test or fix cue: Prefer `SampleCount > 0` plus `SampleSum >= 0`, or inject/control time when a positive duration is the actual contract.

## CI Failure Classification Before Code Changes

- Pattern: A failed check after a mechanical or unrelated PR change is not automatically evidence that the PR broke code.
- Seen in: Karmada Ubuntu runner upgrade PR and estimator/FlinkDeployment e2e investigations.
- Miss symptom: A long e2e job fails in unrelated cleanup/control-plane code while narrower jobs and other matrix versions pass.
- Review check: Compare failing path against the diff, other matrix results, rerun behavior, logs, and artifacts before changing code.
- Evidence to gather: Failed job URL, head SHA, failing test path, logs around first error, related artifacts, and prior flake issues.
- Test or fix cue: Classify as code issue, fork environment difference, missing history/tag, CI flake, or upstream-only gate; rerun or isolate before patching unrelated code.
