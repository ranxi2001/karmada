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

## A Flake Census Must End In A Fix-Candidate Decision

- Pattern: Counting unrelated CI failures and proving they are flakes does not identify which failures can be eliminated by a useful code change.
- Seen in: Karmada Day 27, where an initial 23-run/29-job census documented #7697 thoroughly but left Remedy status cleanup behind an unnecessary “wait for another reproduction” gate and did not inspect a migration test's one-shot read across two asynchronous status streams.
- Miss symptom: The report is dominated by run counts and rerun evidence, while the reader still cannot tell which cluster is ready for a PR, already fixed, blocked on RCA, or unsuitable for a code fix.
- Review check: For every flake cluster, state prevalence, supported-workflow reachability, E0-E4 level, the exact causal edge a patch would cut, minimum files/tests, and the missing evidence that blocks implementation.
- Evidence to gather: Cross-run occurrences, first hard failures, source-level no-self-heal chain, existing or closed fixes, current base behavior, and a counterfactual regression plan.
- Test or fix cue: End the census with `READY / DONE / NEEDS_RCA / NO_FIX`. A same-SHA green rerun must not demote a repeated E3 defect; conversely, repeated terminal symptoms without a common causal edge must not be turned into timeout, generic retry, or defensive-nesting PRs.

## Matrix Version Labels Must Be Bound To Runtime Roles

- Pattern: The same version string can name a member cluster, host Kind cluster, embedded control-plane API server, component branch, or dependency image in different workflows; grouping failures by the displayed version alone can merge opposite compatibility directions.
- Seen in: Karmada Day 50 scheduled E2E scan, where ordinary `v1.30.0` set `CLUSTER_VERSION` for member clusters while compatibility `v1.30.0` set `KARMADA_APISERVER_VERSION`. The former rejected `Complete=True` without `SuccessCriteriaMet=True`; the latter rejected that condition on a NonIndexed Job without `successPolicy`.
- Miss symptom: Identical E2E timeout and matrix label are reported as one root cause, leading to a proposed unconditional field or condition change that fixes one matrix and breaks the other.
- Review check: Before clustering by version, map every matrix axis and environment variable to the concrete runtime process/image it controls, then record all independently versioned peers in the request path.
- Evidence to gather: Workflow YAML, setup-script defaults, checked-out branch SHA, container image/`inspect.json`, component startup version logs, and the first rejecting component's exact error.
- Test or fix cue: Build role-labeled cases such as `old member -> new API server` and `new member -> old API server`. Require the proposed compatibility contract and regression tests to satisfy both directions before authorizing a fix PR.

## Aggregated Terminal Status Must Satisfy Cross-Field Validation

- Pattern: Adding a newly required terminal condition can fix one API validation error while the aggregated object still violates another invariant across counters, timestamps, and conditions.
- Seen in: `karmada-io/karmada#7846`, where synthesizing `FailureTarget=True` fixed `Failed=True` validation for one member but `failed member + active member` still produced `Active>0 + Failed=True`.
- Miss symptom: Unit tests compare the expected condition slice and pass, but a real API server rejects the complete status object.
- Review check: For every synthesized terminal condition, enumerate mixed member states and validate the whole aggregate against the target API server's cross-field rules.
- Evidence to gather: Aggregation code, upstream validation/strategy gates, old and new full status objects, and normal mixed-member timelines.
- Test or fix cue: Cover `failed + active`, `failed + missing status`, and mixed-version members; use API validation or envtest instead of condition-only object equality.

## API-Allocated Field Fixes Must Audit Sibling Allocation Paths

- Pattern: Removing one control-plane-allocated field before cross-cluster propagation can leave another field on the same resource that uses the same member-side allocator and fails under the same collision.
- Seen in: `karmada-io/karmada#7824`, where pruning `spec.ports[*].nodePort` fixed ordinary NodePort collisions but left `spec.healthCheckNodePort` on `LoadBalancer + externalTrafficPolicy: Local` Services.
- Miss symptom: The patch matches the field named in the issue and its happy-path test passes, but a sibling Service mode still sends a nonzero requested port to every member.
- Review check: Starting from the member API server's allocation transaction, enumerate every field it reserves, every resource mode that enables each allocator, and the create-versus-update retention contract.
- Evidence to gather: Defaulting, mode predicates, exact allocation calls for zero and nonzero requests, collision errors, propagation pruning, member-observed field retention, and supported version behavior.
- Test or fix cue: Exercise each sibling field through the real allocator with a preoccupied value. On create, prune control-plane allocations that must be member-local; on update, preserve the member's immutable allocation through the existing retain path.

## Regression Tests Must Distinguish Old And New Behavior

- Pattern: A changed assertion can describe the desired end state while still passing against the old implementation, so it cannot prove the reported bug was fixed.
- Seen in: `karmada-io/karmada#7824`, where replacing cross-cluster NodePort equality with `nodePort > 0` passes both propagated fixed ports and member allocation when no collision exists.
- Miss symptom: CI is green, but the test never creates the conflict or state transition that made the old path fail.
- Review check: Run the proposed regression mentally or mechanically against the base revision and identify the exact assertion that must fail there.
- Evidence to gather: Original user trigger, allocator/state preconditions, base-versus-head result, and final controller/application condition.
- Test or fix cue: Force the collision or stale state, assert the user-visible recovery, and retain a baseline control; do not treat a happy-path invariant shared by both implementations as regression coverage.

## Recovery-Event Fixes Must Prove Semantic Equality And Termination

- Pattern: Expanding an update predicate can restore a dropped recovery event while also enqueueing representation-only changes or creating a controller feedback loop.
- Seen in: Karmada Day 27 Remedy fix, where `RemedyActions: [] -> [TrafficControl]` had to enqueue, but `nil` and `[]` both represented the same empty action set.
- Miss symptom: A new `reflect.DeepEqual` field check makes the regression pass, yet nil/empty, ordering, or duplicate differences trigger unnecessary reconciles; the test proves the first enqueue but not the final no-op.
- Review check: Identify whether the watched field is a list, set, map, or ordered sequence; use its semantic equality and trace `status write -> watch event -> enqueue -> reconcile` until no further write occurs.
- Evidence to gather: Field producer and normalization, API serialization shape, old/new informer objects, status helper equality, downstream write condition, and queue length after the terminal state.
- Test or fix cue: Pair the changed-state regression with a semantically equal final-state no-op case, including nil/empty when relevant. In the sequence diagram, show both the compensation reconcile and the event that terminates without another write.

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

## Clean Rebuilds Must Preserve Verifiable Prior Authorship

- Pattern: A stale PR can contain a valid core patch inside merge commits, unrelated files, DCO failures, or compile-breaking edits; rebuilding from current master is sometimes safer than rebasing, but history cleanup must not erase the original contributor.
- Seen in: `karmada-io/karmada#5425` and replacement PR `#7791`. Bharath's signed historical commit contains the correct six-line scheduler fix, while the current PR head has polluted merge ancestry, unrelated content, bot authorship, and a CRB typo.
- Miss symptom: A replacement PR reproduces the earlier implementation under only the new contributor's authorship, or blindly cherry-picks the polluted commit to retain credit.
- Review check: Compare the old PR's current and historical patches, authors, author emails, sign-off trailers, review-guided design changes, and current-base applicability. Separate unchanged prior code from new adaptation and tests.
- Evidence to gather: The exact signed historical commit, file/hunk identity, original review discussion, current head parents, unrelated ancestry, DCO correspondence, and patch/range diff against the clean rebuild.
- Test or fix cue: Rebuild only the proven patch on current master, retain its verifiable author and real sign-off, add the current committer's sign-off when appropriate, put new work in a separately authored commit, and credit the original PR in the new PR body. Never invent a sign-off or attribute materially changed code to the prior author.

## Eligibility And Capacity Must Change Before Selection

- Pattern: A scheduler fix that changes eligibility or allocatable capacity only during final assignment is too late when scoring, spread selection, or overflow tiering has already planned against the old capacity.
- Seen in: `karmada-io/karmada#6863`, where an unhealthy existing primary looked able to satisfy all replicas during overflow tiering, then its scale-up capacity was zeroed during assignment and the scheduler returned `Unschedulable` before trying a healthy overflow tier.
- Miss symptom: The local assignment unit test passes, but a full scheduling path either selects the wrong cluster set or fails before a fallback group is evaluated. A separate policy success reason, such as explicit taint toleration, may also be silently overwritten.
- Review check: Trace each eligibility and capacity value from filter result through score, group/spread selection, tier budgeting, assignment, and retry. List every reason a candidate can pass filtering and preserve distinctions that carry user intent.
- Evidence to gather: The stage that first computes capacity, all downstream consumers, fallback/error short-circuits, policy exceptions, previous assignments, and one full-path counterexample with a healthy alternative.
- Test or fix cue: Make policy-aware effective capacity visible before every planning consumer, preserve already-assigned replicas separately from new capacity, and test existing-but-ineligible, explicitly allowed, fallback-tier, and fresh-recalculation paths.

## Fresh Operations Must Enumerate Every Retained Decision

- Pattern: An operation described as `Fresh`, `Full`, or "complete recalculation" may reset the previous output while another persisted cursor, selected group, cache entry, or status field still constrains the new candidate space.
- Seen in: `karmada-io/karmada#5070` and proposal PR `#7662`, where explicit WorkloadRebalancer rescheduling resets dynamic replica assignment but retains `status.schedulerObservingAffinityName`, so a recovered earlier top-level `clusterAffinities` term is never reconsidered.
- Miss symptom: Tests prove that a trigger was written, a Fresh enum was selected, or scheduling completed, but never seed a later observed group and verify which earlier candidates are visible. Documentation then treats "new replica distribution" as "new scheduling context."
- Review check: Enumerate every input derived from the previous decision across spec, status, annotations, caches, queues, and controller-owned resources. For each, state `reset`, `retained`, `recomputed`, or `out of scope`, and name the component that owns it.
- Evidence to gather: The trigger path, outer candidate-selection loop, inner assignment mode, persisted status/cursor fields, field ownership, supported policy matrix, official user-facing promise, and one production lifecycle that distinguishes resetting output from resetting search context.
- Test or fix cue: Start from a non-initial cursor, restore an earlier candidate, trigger the alleged Fresh operation, and assert both candidate visibility and final output for every symmetric resource path. Keep scheduler-selected failback separate from caller-selected safe migration, and require a new explicit contract before changing retained state.

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

## Embedded REST Overrides Must Cover Every Exposed Verb

- Pattern: Overriding one method on a wrapper that embeds a generic REST store does not automatically affect other promoted methods; an alternate verb can keep calling the embedded receiver and bypass wrapper-specific validation.
- Seen in: `karmada-io/karmada#7779`, where `REST.Delete` enforced Cluster deletion protection but promoted `Store.DeleteCollection` called `Store.Delete` directly.
- Miss symptom: Single-object tests pass and the wrapper appears to own deletion, while collection, bulk, status, proxy, or subresource operations still use an unmodified embedded implementation.
- Review check: Enumerate the storage interfaces and routes actually exposed by the wrapper, then trace each supported verb to the concrete receiver that performs validation and mutation. Do not assume Go method calls dynamically return to an outer embedding type.
- Evidence to gather: Generated client interfaces, REST interface assertions, API installer route registration, promoted method sets, concrete method receivers, and every single-versus-collection test path.
- Test or fix cue: Add an explicit wrapper method for each verb that needs the invariant, pass the same validation into the generic implementation, and test through the public operation rather than only the validator helper. For non-atomic collection APIs, select one protected target so a failed request cannot leave ambiguous partial mutation.

## Strict Timestamp Gates Need a Persisted-Precision Barrier

- Pattern: An E2E can perform two logically ordered actions in the same persisted timestamp unit; after API serialization truncates precision, a strict `After`/`>` gate observes equal times and treats the second action as not pending.
- Seen in: the #5070 WorkloadRebalancer A -> B -> A regression, where `metav1.Time` round-trips at RFC3339 second precision and `RescheduleRequired` requires `trigger > lastScheduledTime`.
- Miss symptom: The workflow is correct in source order but flakes or times out because creation/update timestamps are equal after persistence; increasing the overall timeout does not change the causal ordering.
- Review check: Read the type's JSON precision and the consumer comparison. For every strict timestamp transition, prove the producer timestamp is later after an API round trip, not merely later in process execution.
- Evidence to gather: Persisted timestamps from both objects, serialization behavior, comparison operator, server/defaulting source of each time, and the generation/resource-version state proving the earlier transition has settled.
- Test or fix cue: Add a bounded clock-tick barrier immediately before creating the later timestamped object, then wait for `observedGeneration == generation` or another source-backed settlement signal. Keep the barrier local to the causal transition; do not replace it with a fixed sleep or inflate unrelated timeouts.

## Related Work Must Separate Shared Mechanism From Accepted Solution

- Pattern: Two bugs can share a stale-cache or retry mechanism without inheriting the same accepted fix; a prior thread may end with a mitigation or caller contract rather than a merged implementation.
- Seen in: `karmada-io/karmada#6858`, closed by documentation PR `#7632` after broad status-update proposals remained unmerged, and `#7776/#7777`, which expose a new remediation caller that can violate the documented convergence requirement.
- Miss symptom: A review says the current patch "follows the solution from #6858" after reading only one option comment, or reads the current PR conversation while missing the linked issue's substantive maintainer reply.
- Review check: Follow the earlier thread through closure and classify each link as same symptom, same root-cause class, mitigation, caller contract, rejected option, or accepted implementation. Keep confirmation of the bug separate from approval of the patch.
- Evidence to gather: Root-cause comment, competing proposals and tradeoffs, closing comment/PR, merged versus abandoned changes, current caller event order, and the latest linked issue and PR replies.
- Test or fix cue: Cite prior art with one relevance sentence that states both support and limit, then prove the current caller-specific convergence edge independently.

## Served Legacy Versions Can Erase Hub-Only Fields On Main And Status Writes

- Pattern: When a still-served legacy API version cannot represent fields in the storage version, lossy conversion can erase those fields during legacy read-modify-write; a status subresource is not automatically safe if storage decodes the existing object into the request version before copying its old spec.
- Seen in: Karmada #7492 API branch review, where `v1alpha1` remains served, `v1alpha2` is storage, and the legacy projection omits both `spec.components` and `spec.clusters[].components`.
- Miss symptom: A conversion unit test intentionally proves round-trip loss but is treated as harmless legacy projection, or reviewers assume `/status` preserves hub-only spec merely because the status strategy copies the old object.
- Review check: Inspect the final installed CRD, including kustomize/Helm patches; enumerate served/storage versions, conversion strategy, old-version schemas and clients, main/subresource admission rules, and the storage codec's decoder/encoder versions.
- Evidence to gather: Rendered CRD, conversion functions and tests, generated legacy clients, webhook routes, API-server update/status strategy source, and a real API-server main/status round-trip.
- Test or fix cue: Create a storage-version object with hub-only fields, then exercise legacy main and status updates. Require an explicit preservation or rejection contract at admission/storage boundaries; do not infer safety from typed conversion tests or status strategy in isolation.

## Cache Timing Evidence Does Not Assign Freshness Ownership

- Pattern: A test can expose a real cross-informer ordering window without proving that the consumer where the symptom appears must bypass its cache or guarantee one-attempt convergence.
- Seen in: the offline mentor review of `karmada-io/karmada#7791`. The E2E cache barrier established that recovered Cluster state was visible before testing the scheduler's affinity-cursor reset; removing it led the review toward direct Cluster API reads and a request-scoped snapshot that expanded scheduler responsibility.
- Miss symptom: A reviewer treats a deterministic test barrier as a hidden product defect, then adds direct API reads, cache validation, retries, or snapshots to the consumer without first establishing that freshness belongs to that component's contract.
- Review check: Separate three questions: whether the ordering is reachable, whether the product promises automatic convergence for that ordering, and which component owns state freshness or retry. A yes to the first does not answer the other two.
- Evidence to gather: The component's established inputs and outputs, authoritative-state and cache owners, API/user guarantee, existing retrigger path, maintainer direction, and whether an operational or manual retry is acceptable.
- Test or fix cue: Use a bounded synchronization step to establish the precondition for the narrow behavior under test. Keep the production change at the owned state transition unless the contract explicitly requires automatic convergence; if it does, fix the owner or protocol rather than silently turning a cache consumer into the freshness owner.

## Numbered Event Sequences Make Race Reviews Auditable

- Pattern: A race explanation is easier to verify when each numbered step contains one actor and one state transition, followed by a one-sentence invariant and an explicit next action.
- Seen in: the maintainer confirmation on `karmada-io/karmada#7776`, which reconstructs eight steps from the Remedy status write through stale-cache equality, ignored `RemedyActions` update, and permanent non-convergence before promising a separate PR review.
- Miss symptom: A dense paragraph mixes API writes, cache delivery, reconcile order, and event filtering, so readers cannot identify which transition is proven or whether agreement covers the problem or the solution.
- Review check: Ask whether the sequence exposes producer, authoritative state, cache observation, consumer decision, recovery event, and terminal state; label uncertainty at the exact step.
- Evidence to gather: Actor/function per step, state source, ordering evidence, event-filter decision, recovery path, violated invariant, and reviewer stance.
- Test or fix cue: Write `stance -> numbered sequence -> race/invariant -> next action`; use a compact sequence diagram only when it reduces cognitive load further.

## Accept Operational Tradeoffs With Frequency And Unit-Cost Bounds

- Pattern: A reviewer can accept extra events, retries, or no-op reconciliations when the correctness benefit is clear and the operational cost is bounded by both low trigger frequency and low per-trigger work.
- Seen in: `karmada-io/karmada#7777`, where `zhzhuang-zju` explicitly acknowledged that watching `RemedyActions` may enqueue additional no-op reconciliations, then accepted the solution because Remedy mutations are infrequent and remediation reconciliation is lightweight.
- Miss symptom: A review either blocks every extra reconcile as a generic performance risk or dismisses it with "should be fine" without identifying workload frequency, fan-out, or unit cost.
- Review check: Name the downside first, then evaluate trigger frequency, objects affected per trigger, work per reconcile, queue coalescing/rate limiting, loop termination, and the correctness or convergence benefit gained.
- Evidence to gather: Event producers, expected mutation rate, fan-out cardinality, reconcile reads/writes, idempotence and no-op behavior, self-trigger potential, and any production scale or benchmark evidence needed for the risk level.
- Test or fix cue: State `cost -> frequency/unit-cost bounds -> decision`. Add filtering, batching, metrics, or a scale test only when the trigger is frequent, fan-out is broad, work is heavy, or termination is uncertain.

## Positive Overall Verdict Must Precede A Non-Blocking Tradeoff

- Pattern: When the implementation direction is sound and the only remaining concern is non-blocking, the upstream comment must state that overall verdict before presenting the cost or evidence gap.
- Seen in: The initial review draft for `karmada-io/karmada#7800`, which agreed with the indexed waiting store but opened directly with retained-memory growth.
- Miss symptom: The author sees criticism first and reasonably reads the reviewer as opposing the approach, even though the private review conclusion is that the behavior and performance improvement are correct.
- Review check: Before drafting, classify the overall stance and finding severity separately. If the stance is positive, name the verified benefit; if the concern is non-blocking, say so explicitly before its evidence.
- Evidence to gather: Proven behavior preserved, measured benefit, bounded downside, finding severity, and the smallest follow-up needed to evaluate the tradeoff.
- Test or fix cue: Write `verified benefit -> explicit non-blocking boundary -> concrete cost evidence -> smallest question`. Keep findings-first ordering for internal reports when useful, but do not let it misstate the upstream verdict.

## Cumulative Allocation Does Not Bound Retained Heap

- Pattern: A hot-path optimization can sharply reduce `alloc_space` while secondary indexes retain substantially more heap for the lifetime of queued or cached objects; cumulative allocation and post-GC live memory answer different capacity questions.
- Seen in: `karmada-io/karmada#7800`, where query CPU/allocation improved substantially, but a high-cardinality `(GVK,name) -> Set[ClusterWideKey]` index initially retained about 40.56 MB for 24,564 waiting objects versus about 3.15 MB for the old key-only map. The author confirmed the attribution and changed shared indexes to stable candidate pointers plus compact name slices, reducing locally measured full-store retained delta to about 17.98 MiB and the name index to about 3.19 MiB.
- Miss symptom: A review treats lower per-operation B/op or an `alloc_space` profile as proof that the new cache/index has a small steady-state footprint, especially when every unique key creates its own map/set bucket.
- Review check: Separate transient query allocation from post-GC retained heap. Estimate or measure outer-map entries, per-bucket allocations, duplicated keys, pointers, label snapshots, and cardinality distribution at the PR's claimed scale.
- Evidence to gather: Same-scale forced-GC `HeapAlloc`/`inuse_space`, independent-process repeats, fixture liveness via `runtime.KeepAlive`, nil-payload controls, selectively removed-index attribution, and production-relevant name/namespace/GVK cardinalities.
- Test or fix cue: Compare `old retained -> new retained -> component attribution`, then ask for the smallest bound or representation change. After an update, rerun the identical workload and verify lookup, update, deletion, and concurrency semantics before closing the finding.

## A Renamed Behavior Must Still Observe The User Story's State

- Pattern: Replacing an ambiguous runtime signal with a cleaner desired-state term can make an API sound more precise while removing the only data that distinguishes the reported problem; the new mode may then duplicate existing reconciliation rather than add behavior.
- Seen in: `karmada-io/karmada#7662`, where `PreserveScheduled` avoids treating every unavailable replica as movable but cannot identify replicas already assigned in `Binding.spec.clusters` that remain Pending inside a member cluster.
- Miss symptom: The proposal says it will reschedule a deficit caused by long-running Pending replicas, but computes the deficit only as `desired - assigned`; `assigned == desired` makes the operation a no-op, while `assigned < desired` already triggers the existing Steady scale-up and retry path.
- Review check: Map `user story -> real producer state -> persisted field -> existing trigger/retry -> proposed branch`. Give one example where desired, assigned, ready, and available counts differ, then verify the proposed field changes in that example.
- Evidence to gather: Field ownership and semantics, member/reflected status, scheduler assignment inputs, existing change predicates, retry classification, partial-result persistence, and a full-path case that distinguishes the new mode from current behavior.
- Test or fix cue: Require a regression where all desired replicas are assigned but the intended movable subset is not running. If the proposed signal cannot identify that subset, either define a source-backed signal and ownership contract or narrow the user story; do not add a public mode that only replays an existing reconcile path.

## A Selector Does Not Define Ownership Or A Scheduling Unit

- Pattern: A label selector narrows a candidate set, but it does not prove that each matched Pod belongs to the current workload lifecycle or define how a component-level count maps to the scheduler's placement unit.
- Seen in: `karmada-io/karmada#7662`, where a maintainer proposed adding selectors to `GetComponents` and `UnschedulableReplicasRequest` so scheduler-estimator could support workloads beyond Deployment. The existing Deployment path additionally selects the current ReplicaSet and filters Pod `ControllerRef` by UID, while current multi-component workloads bypass replica division and scalar `dynamicScaleUp`.
- Miss symptom: A proposal concludes that any workload exposing a selector is generically supported, but old rollout Pods, another controller's same-label Pods, or heterogeneous component replicas can enter the count without a defined owner/lifecycle check or placement/revision mapping.
- Review check: Trace `workload -> selector producer -> matched objects -> owner/lifecycle verifier -> counted component -> placement unit -> revision writer`. Require an explicit contract at every arrow; do not treat label equality as ownership or a component replica as a top-level workload replica.
- Evidence to gather: Selector source and mutation rules, member-side owner references and UIDs, rollout/current-generation discriminator, component identity, Binding placement representation, supported workload/strategy matrix, and the controller that can revise the selected unit.
- Test or fix cue: Cover overlapping labels, old/new rollout objects, and a multi-component workload with only one component unschedulable. Either verify ownership and map the component to an executable placement unit, or narrow the first version to workload kinds whose existing replica contract already provides both.

## A Fixture Counterfactual Is Not The Terminal Flake Counterfactual

- Pattern: Making a fixture violate a new readiness or lifecycle assertion proves that the fixture was unstable, but it does not prove that the instability caused the original later API error.
- Seen in: `karmada-io/karmada#7795`, where removing the BusyBox command made the focused E2E fail an `IsPodReady` lifecycle assertion after metrics readiness, while the retained CI symptom was a later `PodMetrics NotFound`. Maintainer reproduction and same-manifest polling found no post-success 404.
- Miss symptom: A `fixed pass -> reverse fail -> restored pass` sequence is labeled terminal E4 even though the reverse variant stops before the original consumer and returns a different error.
- Review check: Compare object, state layer, transition, consumer, terminal error, and recovery point between the CI failure and reverse test. Treat every mismatch as an explicit evidence boundary, not as a harmless earlier assertion.
- Evidence to gather: Exact terminal stderr and timestamp, the reverse test's first failing line and error, component-internal samples for the proposed edge, same-manifest falsification, and any controlled mechanism reproduction with its differences from production timing.
- Test or fix cue: Label the earlier result `fixture invariant proven` and keep the terminal cause at its prior level. Upgrade only after reproducing the original terminal symptom or capturing the missing internal state; otherwise narrow the PR claim or reclassify it as fixture cleanup.

## Heap Ordering Does Not Cover Partial Batch Admission

- Pattern: A priority heap can be locally correct while a producer moves candidates into it one at a time and signals a consumer after each insertion; an outer producer lock does not create a batch barrier when `Pop` uses a different lock.
- Seen in: `karmada-io/karmada#7802`, where `backoffQ` and `unschedulableBindings` flush under `prioritySchedulingQueue.lock`, but each `activeQ.Push` signals the serial scheduler worker and `prioritySchedulingQueue.Pop` bypasses that outer lock.
- Miss symptom: Comparator tests and tests that preload every candidate pass, so the review concludes strict priority is preserved across readmission. The opposite overclaim is that the worker drains the whole batch in admission order, even though the sole worker must complete an outer-lock path before a second `Pop`; that cannot happen before the flush releases the lock, whether or not the worker blocks in wall-clock time.
- Review check: Enumerate the source store order, eligibility rule, batch-collection point, lock held by each transition, signal point, consumer lock, worker count, and every lock the consumer must reacquire after one item. Compare both legal event orders: `first push -> pop -> remaining pushes` and `all pushes -> priority pop`.
- Evidence to gather: Exact comparator keys, timer cutoffs, producer and consumer goroutines, lock order, condition-variable behavior, post-pop retry/forget path, external requeue loops, existing test seams, official ordering contract, and production traces needed to estimate frequency.
- Test or fix cue: Use a fake clock for eligibility and a wrapper around the real active queue that pauses after its first delegated push. Test equal expiry, staggered-but-simultaneously-eligible expiry, and a full-batch control. For map-backed stores, assert `first popped == actual first pushed`; do not make a particular unspecified map order a pass condition. Report reachability, frequency, contract, and bounded blast radius separately.

## AddAfter On One Producer Is Not A Queue-Wide Not-Before Barrier

- Pattern: Calling `AddAfter` from one event handler delays only that producer's insertion; another `Add`, retry, already-ready item, or processing item for the same key can still make the consumer run before the intended window.
- Seen in: `karmada-io/karmada#7810`, where ResourceBinding update events used `AddAfter`, while cluster requeues used immediate `Add` and scheduler failures used `AddRateLimited` on the same legacy workqueue key.
- Miss symptom: A PR describes the delay as debounce or settling time, tests only the new branch, and assumes every scheduling attempt now waits for the configured duration.
- Review check: Enumerate every producer for the key, the base queue's dirty/processing sets, delayed-entry deduplication, retry deadlines, consumer count, and whether any path enforces a common not-before at dequeue.
- Evidence to gather: Delaying-queue deadline replacement rule, immediate and rate-limited producers, already queued/processing behavior, fake-clock interleavings, leader restart behavior, and the exact guarantee claimed to users.
- Test or fix cue: If the contract requires a quiet period, maintain shared per-key deadline state and recheck it at dequeue. Otherwise name and document the feature as best-effort fixed-window coalescing, then test boundary misses and fast-path bypass explicitly.

## Long-Lived Queue Keys Must Revalidate Current Ownership At Consumption

- Pattern: A queue key can remain valid as an identifier while the current object becomes suspended, deleted, reassigned, or otherwise ineligible; admission-time filtering cannot protect a delayed or retried consumer.
- Seen in: `karmada-io/karmada#7810`, where the informer filter rejected a ResourceBinding after `schedulerName` or scheduling suspension changed, but the delete handler did not cancel the delayed key and `doScheduleBinding` did not recheck eligibility after its lister read.
- Miss symptom: The event filter appears to enforce ownership, yet a stale delayed key lets the former owner run an algorithm or patch status/spec after handoff.
- Review check: For every queue whose entries can outlive one event turn, map `filter/admit -> enqueue -> ownership change -> cancel/delete -> dequeue -> authoritative re-read -> mutation` and identify where current eligibility is revalidated.
- Evidence to gather: Filter transition behavior, delete-handler effects, queue cancellation capability, key payload, lister/API read, ownership and suspension fields, and all writes after dequeue.
- Test or fix cue: Revalidate ownership, suspension, deletion, and other mutation gates after reading the current object and before side effects. Use a fake clock to retain a key, change eligibility, advance time, and assert no algorithm call or patch occurs.

## A Final Readiness Error Does Not Localize The Whole Create Duration

- Pattern: A long cluster-create call can end with a short bounded readiness error even though the elapsed time also includes earlier provider work and failure cleanup; the final message identifies the terminal gate, not where the whole duration was spent.
- Seen in: `karmada-io/karmada#7795`, where a namespace E2E spent `23m33s` in kind v0.32.0 `Create` and ended at the `30s` cgroup-ready log gate, while the same path also contained image/network operations, `docker run`, and automatic cluster deletion without one enclosing timeout.
- Miss symptom: The RCA calls the failure a 23-minute readiness timeout, assigns all delay to `docker run`, or claims the dynamic cluster triggered runner collapse even though control-plane health errors began before cluster creation.
- Review check: Expand the provider path through rollback, compare the first environmental degradation timestamp with the alleged trigger, and separate the proven terminal mechanism from any physical infrastructure cause.
- Evidence to gather: Per-phase provider timestamps, failed-node journal and inspect output, host dockerd/container-runtime logs, disk and inode state, I/O/PSI metrics, kernel OOM/block events, and synchronized symptoms from independent control-plane stores.
- Test or fix cue: Keep the physical cause at `E2` when failed-node or host evidence is absent. A same-SHA green rerun upgrades nondeterminism to `E1` only; it does not justify changing unrelated PR code or naming a root cause.

## Workflow Event Filters Do Not Bound Bot Rerun Capabilities

- Pattern: A workflow that listens only to `push` and `pull_request` cannot be started directly by an issue comment, but a trusted project bot may still accept `/retest` and call the GitHub Actions rerun API for the existing run.
- Seen in: `karmada-io/karmada#7795`, where the author's untrusted `/retest` was rejected, while maintainer `zhzhuang-zju` posted the same command and `karmada-bot` started `run_attempt: 2` four seconds later with only the failed v1.35 job executing again.
- Miss symptom: An RCA reads only the workflow `on:` block and concludes that `/retest` cannot affect a GitHub Actions check, then recommends a manual Actions click as the only valid path.
- Review check: Separate direct workflow event creation from an integration's rerun permission. Correlate the accepted command with the existing run's attempt, `triggering_actor`, start time, and new failed-job ID.
- Evidence to gather: Exact comment actor/time and bot response, run `run_attempt`/`run_started_at`/`triggering_actor`, per-attempt job IDs and timestamps, and whether successful jobs were retained or actually rerun.
- Test or fix cue: Do not infer bot capability from workflow YAML alone. State account trust, command acceptance, and rerun mechanics as separate claims; verify the resulting Actions state before prescribing a trigger path.

## Adding A Slice Or Map Can Break Comparable Callers

- Pattern: Adding a slice, map, or function field to a public Go struct makes the entire struct non-comparable, so generic equality and set helpers constrained by `comparable` can fail outside the API package even when code generation and narrow compile jobs pass.
- Seen in: `karmada-io/karmada#7837`, where adding `TargetCluster.Components []TargetComponent` left `test/helper/scheduler.go` calling `slices.Contains`; lint, unit, CLI, Operator, and base E2E jobs failed with `TargetCluster does not satisfy comparable` while codegen and the narrower compile job passed.
- Miss symptom: Review checks the type, conversion, generated clients, CRDs, and API package compilation but does not search for map keys, `==`, `slices.Contains`, `maps` usage, generic constraints, or test helpers that consume the changed struct.
- Review check: For every newly non-comparable field, search all direct and aliased uses of the enclosing type, then classify each equality caller by intended semantics: exact ordered representation, order-insensitive keyed collection, or domain-specific identity.
- Evidence to gather: Exact field/type diff, compiler errors across the full consumer graph, generic function constraints, schema list semantics, serialization normalization, and existing equality tests for duplicates, order, and nil versus empty collections.
- Test or fix cue: First reproduce the compile failure in the smallest consumer package. Use `ContainsFunc` plus an explicit equality function for the minimal repair; only introduce indexing, multiset matching, duplicate rejection, or nil/empty normalization when the API contract defines those semantics. Rerun the helper package and representative caller packages before broad CI.

## Accepted-Result Migrations Need Provenance And A Recovery Door

- Pattern: A generation acknowledged by an older controller proves only that the old behavior completed; it does not prove that newly introduced result fields or input identities were persisted. A migration must distinguish states that can be reconstructed from the old contract from states that require a new full operation.
- Seen in: `karmada-io/karmada#7492`, where pre-upgrade multi-component bindings could have no component snapshot or a complete snapshot without the new accepted-requirements hash.
- Miss symptom: The new controller either trusts every `generation == observedGeneration` object and silently invents accepted data, or freezes every old object with no automatic or user-triggered recovery path.
- Review check: Enumerate every persisted shape produced by each predecessor version, state exactly what old success proves for Duplicated versus Divided scheduling, and identify a bounded recovery action for every unprovable state.
- Evidence to gather: Old routing behavior, result schema by version, success/status invariants, placement strategy, feature-gate default, and whether an explicit full reschedule can preserve the previous result on failure.
- Test or fix cue: Auto-backfill only states proven by the old contract; otherwise fail closed and provide an explicit full recalculation that atomically establishes the new snapshot and identities. Test both upgrade shapes and success/failure recovery.

## Split Result And Status Writes Need Durable Provenance

- Pattern: Reading the generation returned by a successful result patch protects only the current process call; a crash or status conflict loses that in-memory fact, so the next reconcile needs persisted evidence that the result belongs to the current scheduling input.
- Seen in: `karmada-io/karmada#7492`, where the main binding patch could succeed, the status patch could fail, and a later ordinary Divided reconcile could erase or fail to acknowledge the accepted component result.
- Miss symptom: A retry infers success from `generation > observedGeneration`, or uses only the patch response generation, then either trusts an unrelated detector update or reruns scheduling and clears a correct result on `FitError`.
- Review check: Number `input read -> result write -> concurrent update -> status write -> retry`, then ask which facts survive process death and which write prevents a newer trigger from being consumed.
- Evidence to gather: Atomic result metadata, normalized input digest, predicted and returned generation, resource-version preconditions on main and status patches, and the retry path for token-current versus token-stale states.
- Test or fix cue: Persist a result-generation token and a normalized accepted-input digest with the result, use resource-version CAS for both writes, and test crash, conflict, config-only update, rollback, and a genuinely changed scheduling input.

## Additional-Capacity Estimates Do Not Prove Full Replacement Capacity

- Pattern: An estimator request for only the positive replica delta answers whether extra capacity exists beside the accepted workload; it cannot validate a replacement result whose existing replicas have changed requirements or whose accepted baseline is unknown.
- Seen in: `karmada-io/karmada#7492`, where estimating `newReplicas - acceptedReplicas` would undercount a simultaneous CPU, node-claim, or priority-class change on the existing replicas.
- Miss symptom: A patch labels every replica increase as incremental and reuses the old count even when component names, requirements, placement, or the accepted result identity changed.
- Review check: Separate count delta from per-replica requirements and prove that every unchanged replica in the proposed result still has the requirements represented by the accepted baseline.
- Evidence to gather: Name-keyed accepted replicas, accepted requirements identity, scale direction, placement identity, estimator accounting model, and behavior when the target remains healthy but cannot fit the delta.
- Test or fix cue: Use delta estimation only for same-name, one-direction replica changes with matching accepted requirements; use full scheduling for an explicit recovery, and preserve the old result if either path fails.

## ResourceVersion Is A Trigger, Not Semantic Freshness Proof

- Pattern: A changed source `resourceVersion` says that some write occurred, but it does not say whether scheduler-relevant fields changed; equality can prove an exact referenced source, while inequality requires semantic comparison at the owning boundary.
- Seen in: `karmada-io/karmada#7492`, where the binding controller must allow image-only updates but must not deliver a source whose component replicas or requirements are newer than the binding's accepted scheduling input.
- Miss symptom: A controller freezes every resource-version change, blocking unrelated configuration delivery, or ignores the version difference and copies a newer CPU/node requirement before scheduling accepts it.
- Review check: Identify the fields owned by scheduling, the component that interprets them, and which non-scheduling source changes are allowed to flow independently.
- Evidence to gather: Referenced UID and resource version, interpreted component replicas and requirements, accepted input hash, pending-result state, and event ordering between source, detector, scheduler, and delivery controller.
- Test or fix cue: Check UID first; accept an exact resource-version match; otherwise compare normalized scheduler inputs through the existing interpreter. Freeze the entire delivery only while those inputs are pending, and test a same-update config plus scale failure.

## Stacked PR Rewrites Can Orphan Contract Owners

- Pattern: After one PR in a dependent stack is force-pushed, rebased, or narrowed, an old integration branch can still contain its removed code while no current reviewable PR owns that invariant. Green integration checks and old patch-equivalence claims do not repair the ownership gap.
- Seen in: `karmada-io/karmada#7492`, where result validation remained in the stale history of `#7841` after current `#7830` was rebuilt as interpreter plus Work delivery and `#7833` remained producer-only.
- Miss symptom: A stack inventory lists API, producer, consumer, and activation PRs, sees the validation files somewhere in the cumulative diff, and concludes the contract is covered without mapping it to a current exact head and mergeable dependency.
- Review check: For every required invariant, name one current PR owner and verify the code in that PR's actual base-to-head diff. Recompute each residual after every history rewrite, then compare PR-body dependency and patch-equivalence claims with current patch identities.
- Evidence to gather: Exact bases and heads, commit ancestry, patch IDs or residual diffs, current and stale file lists, feature-gate default, merge/rollout order, and the design or API contract that requires each invariant.
- Test or fix cue: Restore an orphaned invariant in a narrow owner-aligned follow-up or the nearest current owner, rebuild the integration branch from current heads, update the PR body, and keep activation disabled until every required owner is present in the deployable stack.
