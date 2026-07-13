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
- Test or fix cue: Classify as code issue, fork environment difference, missing history/tag, CI flake, or upstream-only gate; rerun or isolate before patching unrelated code. A green rerun proves nondeterminism only, not root cause or patch correctness.

## Flake Fixes Require A Source-Level Causal Timeline

- Pattern: Flake classification evidence and fix evidence are different; a timing experiment can suggest a race while still describing the wrong consumer, state direction, or retry behavior.
- Seen in: `karmada-io/karmada#7719` and PR `#7732`, where the proposed cleanup barrier was valid but the original explanation needed maintainer logs and scheduler queue tracing to establish the real 420-second failure chain.
- Miss symptom: A rerun turns green and a local experiment exposes stale state, so a wait is added without proving which state the consumer reads, why one bad observation becomes terminal, or why the later recovery event does not self-heal.
- Review check: Build a timestamped sequence from producer through authoritative/member state, reflected cache/status, consumer decision, retry/`Forget`, recovery event, and event-filter/requeue behavior. Read helper implementations; do not infer observed state from names.
- Evidence to gather: First hard-failure logs, controller create/delete timestamps, cache/status collection timestamps, consumer plugin input, error classification, queue transition, update-event predicates, and count of later enqueue/schedule attempts.
- Test or fix cue: Require an `E3` code-backed Mermaid timeline before patch design and an `E4` reproduction, regression, or observable baseline-versus-patch counterfactual when feasible. A reasoned counterfactual is design evidence, not causal validation. The patch must name the exact causal edge it cuts; otherwise add diagnostics and keep the proposal labeled as a hypothesis.

## Verify Assertion-Control-Flow Comments Before Patching

- Pattern: AI review comments about assertion helpers can be false when they assume ordinary Go control flow instead of framework-specific retry/fail semantics.
- Seen in: `karmada-io/karmada#7732`, Gemini comment on `gomega.Eventually(func(g gomega.Gomega) ...)`.
- Miss symptom: Reviewer claims a failed `g.Expect(err).NotTo(HaveOccurred())` continues to a nil dereference, but Gomega's passed-in `Gomega` failure aborts the current poll and retries.
- Review check: For assertion/retry frameworks, confirm whether failures return, panic, call `FailNow`, or are intercepted by the framework before accepting a panic/control-flow finding.
- Evidence to gather: Framework docs or vendored source plus a focused temporary test with side effects after the disputed assertion.
- Test or fix cue: In Gomega, `Eventually` callbacks that take `gomega.Gomega` retry after assertion failure; returning `(bool, error)` is still a clear style, but not necessarily a nil-panic fix.

## Per-Item Skip Conditions Must Not Stop Aggregate Collection

- Pattern: A helper can use a sentinel such as `nil` to mean “exclude this item,” while its caller incorrectly treats the sentinel as a reason to stop processing all later items.
- Seen in: `karmada-io/karmada#7757`, cluster resource modeling stopped at the first saturated node.
- Miss symptom: Aggregate output depends on input iteration order and silently omits valid items after one locally unusable item.
- Review check: For loops that build summaries from caches or collections, classify every `break`, `return`, and sentinel result as item-local or collection-global; remember informer/map iteration may be unordered.
- Evidence to gather: Helper contract/logging, mutations before the sentinel return, collection ordering guarantees, and a case with an invalid/saturated item before a valid item.
- Test or fix cue: Use `continue` for item-local exclusion; add order-invariance tests with the skipped item before and after valid items.

## Cleanup Absence Is Meaningful Only After Presence

- Pattern: In eventually consistent tests, an initial `NotFound` does not prove cleanup succeeded unless the test first observed that the resource was created.
- Seen in: `karmada-io/karmada#7692`, ClusterResourceBinding e2e propagation and cleanup race.
- Miss symptom: Cleanup passes while propagation is still in flight, and the delayed controller action creates the resource after the test has moved on.
- Review check: For every create-then-delete flow, verify the test establishes `requested -> observed present -> delete requested -> observed absent`, rather than only `requested -> observed absent`.
- Evidence to gather: Controller and test timestamps around source deletion, derived object creation, Work deletion, and the first successful absence poll.
- Test or fix cue: Add a bounded presence barrier before cleanup, then retain the disappearance barrier; use failure artifacts to confirm the ordering rather than relying only on a green rerun.

## A Fresh Read Can Still Return State From The Previous Lifecycle

- Pattern: Polling the API again proves read freshness, not semantic freshness; reflected status can still describe a previous object lifecycle when names are reused.
- Seen in: `karmada-io/karmada#7719` and PR `#7732`, where the next FlinkDeployment case briefly accepted the prior CRD's `APIEnabled` status before the new member CRD existed.
- Miss symptom: A wait returns true immediately, a later controller refresh changes the same status, and the consumer makes a one-shot decision from the stale value that is never retried.
- Review check: Identify the state layer being read and prove that the value is correlated to the current UID, generation, resource version, or an observed old-state-disappeared then new-state-present transition.
- Evidence to gather: Object identities and lifecycle timestamps, authoritative/member state, reflected status updates, consumer decision input, and requeue/event-filter behavior.
- Test or fix cue: Test both the target alone and `predecessor -> target`; use a lifecycle-aware barrier rather than only polling a boolean condition or increasing its timeout.

## Certificate Private Keys May Have Non-TLS Consumers

- Pattern: A file named after a TLS certificate may also be reused as a JWT, ServiceAccount, or application signing key, so rotating the leaf key can invalidate credentials outside the X.509 trust chain.
- Seen in: `karmada-io/karmada#7697`, where `karmada.key` is both a leaf key and the kube-apiserver/kube-controller-manager ServiceAccount signing key.
- Miss symptom: CA certificates remain unchanged and TLS leaf verification looks correct, but existing tokens fail after restart or during a rolling update because old and new replicas trust different signing keys.
- Review check: Search every consumer of each rotated private-key path, including process flags, mounted Secrets, JWT signing, service-account controllers, webhooks, and sidecars; do not infer usage only from the filename.
- Evidence to gather: Key-generation path, all command-line flags referencing the key, verifier key sets, rollout order, token lifetime, and whether old/new verification overlap exists.
- Test or fix cue: Preserve the shared signing key when only renewing its certificate, or design explicit old/new verification overlap; add a regression test for pre-rotation tokens and mixed-version replicas.

## Local Artifacts Must Be Bound To The Remote Target Before Refresh

- Pattern: A command can select remote state through one kubeconfig/context while separately using a default local data path, so rewriting a local config without proving identity can mix credentials from two clusters.
- Seen in: `karmada-io/karmada#7697`, where rotating remote cluster B could otherwise preserve cluster A's local API server URL while embedding B's CA and admin credentials.
- Miss symptom: Both the remote Secret update and local file write are individually valid, but the resulting local kubeconfig combines an endpoint from one control plane with trust/client material from another.
- Review check: For commands that read remote state and refresh local artifacts, list every independent selector (remote kubeconfig/context, namespace, data path, filename) and identify the stable cluster identity checked before mutation.
- Evidence to gather: Selected remote CA or cluster ID, local artifact endpoint and embedded/referenced CA, path defaults, and the ordering of local/remote writes on mismatch.
- Test or fix cue: Compare a stable identity such as parsed CA DER before rewriting, fail before any local or remote mutation on mismatch, and add a two-cluster regression test asserting both states remain unchanged.
