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

## Certificate Renewal Must Preserve Persisted Identity Inputs

- Pattern: A renewal command must treat the existing certificate as persisted identity state; rebuilding SANs only from current flags, nodes, DNS, or the execution host can silently remove endpoints that were valid when the certificate was first issued.
- Seen in: `karmada-io/karmada#7697`, where rotate reused the install-time config builder and therefore recomputed apiserver SANs from current control-plane nodes plus the current machine's externally queried Internet IP.
- Miss symptom: The operator replays every explicit installation flag, but running recovery from another machine or without the original Internet-IP lookup produces a renewed certificate that no longer verifies an existing endpoint.
- Review check: Classify every certificate subject/SAN input as explicit, auto-discovered, persisted, or environment-derived. Compare old and new identities and ask whether renewal can remove an old DNS/IP value without an explicit removal request.
- Evidence to gather: Existing leaf certificate subject/SANs, original and current flags, auto-discovery/network calls, current topology, execution-host identity, and the endpoint clients actually use.
- Test or fix cue: Preserve the existing SAN set or reject reductions before mutation; add remote-execution and discovery-failure tests. Do not make disaster recovery depend on an unbounded third-party identity lookup.

## CA Equality Is Not Cluster Identity

- Pattern: Matching trust roots proves that two credentials are in the same trust domain, not that a local artifact belongs to the selected cluster; organizations may intentionally reuse one CA across multiple clusters.
- Seen in: `karmada-io/karmada#7697`, where local kubeconfig refresh compared only CA DER before retaining its server endpoint and embedding credentials from the remotely selected cluster.
- Miss symptom: With clusters A and B sharing a CA, rotating B can rewrite a kubeconfig that still points to A. If both client certificates carry the same privileged CN/O, the mixed file may authenticate successfully and hide the target error.
- Review check: List independent remote and local selectors, then identify a target-specific stable identity beyond the issuer, such as an existing client public key, cluster UID, or persisted installation ID.
- Evidence to gather: Local endpoint and client certificate/key, target Secret certificate/key, CA reuse contract, client-auth subject mapping, and mutation ordering on mismatch.
- Test or fix cue: Compare a stable target-specific identity before any local or remote mutation. For key-preserving renewal, client public-key equality survives normal renewals and partial-failure reruns; test same CA with different cluster keys and endpoints.

## Local Artifacts Must Be Bound To The Remote Target Before Refresh

- Pattern: A command can select remote state through one kubeconfig/context while separately using a default local data path, so rewriting a local config without proving identity can mix credentials from two clusters.
- Seen in: `karmada-io/karmada#7697`, where rotating remote cluster B could otherwise preserve cluster A's local API server URL while embedding B's CA and admin credentials.
- Miss symptom: Both the remote Secret update and local file write are individually valid, but the resulting local kubeconfig combines an endpoint from one control plane with trust/client material from another.
- Review check: For commands that read remote state and refresh local artifacts, list every independent selector (remote kubeconfig/context, namespace, data path, filename) and identify the stable cluster identity checked before mutation.
- Evidence to gather: Selected remote CA or cluster ID, local artifact endpoint and embedded/referenced CA, path defaults, and the ordering of local/remote writes on mismatch.
- Test or fix cue: Compare a target-specific stable identity such as the existing client public key or a persisted installation ID before rewriting; CA DER is sufficient only when the contract guarantees one CA per cluster. Fail before any mutation on mismatch and add a two-cluster regression with shared CA but different keys/endpoints.

## Long-Running Operations Need A Deletion Path, Not Only A Cancel Field

- Pattern: A controller that performs durable side effects over multiple reconciles must define direct deletion semantics; a `spec.cancel` state machine is bypassed when the operation object is deleted.
- Seen in: `karmada-io/karmada#7662`, proposed `WorkloadRebalancer` SafeMigration lifecycle.
- Miss symptom: Deleting the operation after target-open or partial source commit removes the only reconciliation intent while shared resources retain partial side effects.
- Review check: Trace `deletionTimestamp`, finalizer installation/removal, watch predicates, NotFound handling, TTL cleanup, owner references, and the terminal path when rollback cannot converge.
- Evidence to gather: First side effect, operation-object predicate/delete handling, ownership of mutated resources, durable operation identity, and whether another controller can complete or undo the work.
- Test or fix cue: Add the finalizer before the first side effect, treat deletion as latched cancellation, stop new work, converge to a defined safe state, and test deletion before and after partial commit.

## Target-First State Must Survive Other Desired-State Writers

- Pattern: A make-before-break controller cannot claim source preservation merely by writing a temporary over-assigned desired state when a scheduler or another controller is also authorized to normalize that state.
- Seen in: `karmada-io/karmada#7662`, where adding target replicas to `Binding.spec.clusters` requeues scheduling and can trigger scale-down before target readiness.
- Miss symptom: `EnsureTarget` succeeds, but a concurrent scheduler recomputes the cluster assignment or a binding controller immediately reduces source replicas, breaking the target-ready barrier.
- Review check: Build an effect graph for every writer of the shared spec, then test the intermediate state against Duplicated, static, dynamic, Fresh/Steady, eligibility changes, failover, and retry paths.
- Evidence to gather: Update-event predicates, assignment branch for over/under-allocation, merge/update conflict semantics, existing eviction or suspension primitives, and exact before/after replica distributions.
- Test or fix cue: Choose one authoritative migration state or an explicit scheduler exclusion, and assert that source desired/ready capacity cannot decrease from target-open through the stable window.

## Derived Caches Must Commit After Reconcile Success

- Pattern: A controller cache used to detect desired-state changes is a commit marker; advancing it before all dependent side effects succeed can turn an error retry into a false no-op.
- Seen in: `karmada-io/karmada#7623`, where the CronFederatedHPA target cache advanced before executor rebuild and rule-history status update completed.
- Miss symptom: The first reconcile mutates some in-memory state and then fails; the retry reports success because the cached desired state now looks unchanged, leaving status or other side effects incomplete.
- Review check: For every in-memory fingerprint, last-seen value, or derived-state cache write, identify which operations it suppresses on the next reconcile and whether every earlier return after the write is safe.
- Evidence to gather: Cache lock and lifecycle, mutation order, retry behavior, partial side effects before each error, early-return conditions, watch predicates, and whether a later event can repair the incomplete state.
- Test or fix cue: Commit the cache only after the full reconcile transaction succeeds, or make every partial step independently retryable; inject a failure after the cache candidate is computed and assert the next reconcile retries all incomplete work.

## Fault Injection Does Not Prove Production Reachability

- Pattern: A fake client, mock, or manually constructed state proves what code does if a trigger occurs; it does not prove that a real producer can emit the trigger or that supported operations can reach the state.
- Seen in: `karmada-io/karmada#7623` review, where an injected status-update error proved the retry defect but needed separate reachability classification.
- Miss symptom: A review calls an arbitrary mocked error or impossible object state a production bug and asks for a fix without identifying how a real system reaches it.
- Review check: Name the production producer, its interface contract, the reachable preconditions, and the recovery behavior before assigning bug severity or blocking a PR.
- Evidence to gather: Real logs or reproduction when available; otherwise exact error contracts, validation and locking rules, concurrent writers, retry/resync/restart paths, and the persistence of user-visible impact.
- Test or fix cue: Inject only errors or states the real boundary permits. Label code-proven but unobserved cases as reachable latent bugs; keep unproven cases as questions or evidence gaps.

## Reachable Edge Cases Are Not Automatically Valuable

- Pattern: A scenario may be source-proven or observed yet still be a poor contribution target when it requires deliberately invalid input, an extreme unobserved configuration, or a failure that framework recovery already maps to the same final state.
- Seen in: The 2026-07-17 Karmada scan initially ranked PRs `#7774` and `#7647` highly because they were reachable, green, and lacked human review. In `#7774`, controller-runtime recovered the nil panic and rate-limited the same reconcile while the invalid resource remained stuck; the patch mainly changed diagnostics. In `#7647`, the real trigger was an explicitly invalid `--etcd-pvc-size=abc`, making the fix narrow CLI hygiene.
- Miss symptom: A scan equates `observed bug`, test volume, green CI, no assignee, or no reviewer with project value, then spends full-diff and mock-analysis tokens on cases outside normal production workflows.
- Review check: Before deep analysis, classify trigger normality, prevalence, final outcome after recovery, root-cause leverage, maintainer demand, and the complexity added by the fix. Ask whether users are materially better off or only receive a different error/log for the same terminal state.
- Evidence to gather: Supported input/operation contract, real incident frequency, recovery/requeue behavior, process/data/availability impact, final state with and without the patch, and explicit maintainer priority.
- Test or fix cue: Mark narrow hygiene `LIGHTWEIGHT` and mock-only/extreme/no-outcome-change work `SKIP`; stop after a compact reason. Prefer an existing boundary fix over nested guards, and allow `no worthwhile candidate` rather than forcing a ranked list. Treat this as an attention decision, not an automatic merge veto: abstain from commenting on a small correct patch unless it adds disproportionate complexity, violates a contract, or overstates impact.

## Force-Pushed Rebases Need Patch Comparison, Not Head Comparison

- Pattern: Comparing `old-head..new-head` after a force-pushed rebase mixes base-branch advancement into the apparent PR delta even when the contributor patch is unchanged.
- Seen in: `karmada-io/karmada#7764`, where a patch-equivalent single commit moved to a newer `master` parent and a direct head diff misleadingly showed 22 changed files.
- Miss symptom: A reviewer attributes already-merged base commits to the author, reviews unrelated files, or assumes earlier findings were addressed because the head SHA changed.
- Review check: Inspect both parent SHAs, compare each `parent..head` patch, then run `git range-diff old^! new^!` and stable `git patch-id` before reviewing the incremental change.
- Evidence to gather: Old/new parent and head SHAs, range-diff result, patch IDs, PR REST changed-file list, and direct equality of the files under review.
- Test or fix cue: Mark `=` plus identical patch IDs as a patch-equivalent rebase; carry prior findings forward unchanged and wait for a real patch delta.

## Re-Audit Scope After The Base Branch Advances

- Pattern: A change can be relevant when proposed and later become redundant because another PR lands the same behavior in the base branch; current redundancy is not evidence that the original contribution was unrelated.
- Seen in: `karmada-io/karmada#7704`, where the original Node.js 20 cleanup legitimately included a FOSSA action upgrade, but Dependabot PR `#7713` merged that upgrade before human review. Rebasing then correctly removed `fossa.yml` and left only the `release.yml` tar replacement.
- Miss symptom: A delayed review calls a now-redundant file “outside scope” without naming the base change that absorbed it, or the contributor carries duplicate edits and stale PR-body/test claims after rebasing.
- Review check: Compare the PR's creation base, current base, and current head; search merged overlapping PRs by file, dependency, issue, and behavior; state whether the change was originally unrelated, independently duplicated, or made redundant by base advancement.
- Evidence to gather: Original and current base SHAs, original/current changed-file lists, the overlapping merged PR or commit, file-level patches, and the PR body/test text that may now be stale.
- Test or fix cue: Ask for a rebase, name the already-merged change, and state the expected residual diff. Afterward, verify the redundant patch disappeared, update the PR body and validation scope, preserve sign-off during history rewriting, and compare patch/tree identity across force-pushes.

## Prompt-Formatting Claims Need A Mechanism Chain

- Pattern: A parser preserving whitespace proves representation, not by itself that formatting helps or harms model behavior; a prompt-quality review needs the semantic, transport, and model-sensitivity links.
- Seen in: `karmada-io/karmada#7764`, where a hard-wrap comment needed references after the author challenged an unsupported “artificial boundaries” claim.
- Miss symptom: A reviewer presents a prompt-style preference as a model-performance fact, or retreats to “needs an A/B test” without using existing standards and research.
- Review check: Establish whether the format change is meaning-preserving in the document grammar, whether the client preserves it into prompt context, whether primary literature shows models can be sensitive to equivalent formatting or separators, and whether official prompt corpora follow a consistent convention.
- Evidence to gather: The markup specification, exact client/reference-parser implementation, product context-loading documentation, peer-reviewed prompt-format sensitivity research, and AST-based counts from official repositories pinned to exact SHAs.
- Test or fix cue: Frame the result as a robustness mechanism (`may introduce accidental structure`), not a deterministic performance delta. Treat official corpus style as corroborating convention rather than normative specification, report counterexamples, and keep the recommendation non-blocking unless the product contract requires one format.

## Polite Review Questions Still Need Standalone Causal Context

- Pattern: `Could ...?` softens a request but does not explain it; a review comment must carry enough local context for the author to reconstruct the observation, counterexample, inference gap, and requested change without the reviewer's private notes.
- Seen in: `karmada-io/karmada#7764`, where the author explicitly found the fast-wait and single-log-hit comments hard to understand even though their technical evidence existed in the local review report.
- Miss symptom: The comment leads with an abstract conclusion such as “keep this as a hypothesis,” then lists lifecycle or queue terms. The reviewer sees the intended distinction, while the author cannot tell what concrete case contradicts the current text.
- Review check: With the local report and chat hidden, ask whether the author can state (1) the exact current claim, (2) one concrete counterexample, (3) what the observed signal actually proves, (4) the missing evidence, and (5) the smallest edit.
- Evidence to gather: The quoted code/text, one minimal alternative execution that produces the same signal, the direct behavioral consequence, and only the implementation terms needed to verify the distinction.
- Test or fix cue: Draft in `observation -> counterexample -> reasoning -> action` order. Put `Could ...?` at the action, translate jargon into its role, and treat an “I do not understand” reply as a reason to rewrite rather than repeat the same abstraction.

## Visualize Branching Or Temporal Review Arguments

- Pattern: When a review asks the author to compare multiple causes, actors, state layers, or event order, a compact diagram can remove more cognitive load than another explanatory paragraph.
- Seen in: `karmada-io/karmada#7764`, where fast-wait and retry comments described branching evidence boundaries in prose and the author still could not reconstruct the distinction. The Day 22 safe-rescheduling infographic is the positive precedent: its five-stage flow makes the current safety gap and target-first invariant scannable, restrained green emphasizes the proposed invariant while red marks the service-loss risk, and a bottom band separates supported direction from unapproved API, ownership, persistence, rollback, and implementation claims.
- Miss symptom: The comment accumulates lifecycle, queue, cache, retry, or timestamp terminology while the actual point is a small graph such as “one signal -> two possible causes” or “attempt -> queue decision -> retry/forget.”
- Review check: Ask whether the reader must track three or more nodes, a temporal order, competing causes, or current-versus-proposed behavior. If yes, compare a 4-10 node Mermaid diagram against prose before posting.
- Evidence to gather: Proven actors/states, arrow direction, branch conditions, synchronous versus asynchronous edges, which relationships remain hypotheses, and the source's approval/provenance boundary.
- Test or fix cue: Use one sentence of conclusion, the smallest inline Mermaid diagram, then one sentence of requested action. For a proposal change comparison, preserve node order and labels, keep unchanged/current nodes neutral, and color changed/new nodes while repeating the distinction in text or line style. For evidence synthesis, add compact `supports` / `does not establish` / source-limit text. Keep a prose summary for accessibility; do not use a diagram for a single local fact.
