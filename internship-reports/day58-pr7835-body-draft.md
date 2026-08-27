**What type of PR is this?**

<!--
Add one of the following kinds:
/kind bug
/kind feature
/kind documentation
/kind cleanup

Optionally add one or more of the following kinds if applicable:
/kind api-change
/kind deprecation
/kind failing-test
/kind flake
/kind regression

-->

/kind feature

**What this PR does / why we need it**:

Estimating the complete desired component set during multi-template workload rescheduling can double-count replicas already running on the accepted target. This change adds a calculation-only planner based on the accepted `TargetCluster.Components` snapshot.

Pure scale-up sends only each component's positive replica delta to the estimator. Pure scale-down returns internal evidence that the accepted target remains usable without calling the estimator. Mixed directions, equal or incomparable snapshots, missing or partial results, and candidates other than the single accepted target are rejected without falling back to full desired estimation.

**Which issue(s) this PR fixes**:
<!--
*Automatically closes linked issue when PR is merged.
Usage: `Fixes #<issue number>`, or `Fixes (paste link of issue)`.*
-->

<!--
*Optionally link to the umbrella issue if this PR resolves part of it.
Usage: `Part of #<issue number>`, or `Part of (paste link of issue)`.*
Part of #
-->

Part of #7492

**Special notes for your reviewer**:
<!--
Such as a test report of this PR.
-->

- Scope: this PR only defines component-scale estimation. Production routing and failure-safe result retention are added by #7841.
- Review the residual diff as `e3e9d4e9f...e19a318eb`; the preceding commits are the stacked #7830 dependency.
- Tests: `go test -race -count=1 ./pkg/scheduler/core` passed. Full `make test` and live E2E were not run for this calculation-only slice.
- AI assistance: Codex helped inspect the estimation path and draft the implementation and tests; I reviewed the final diff and validation results.

**Does this PR introduce a user-facing change?**:
<!--
If no, just write "NONE" in the release-note block below.
If yes, a release note is required.
Some brief examples of release notes:
1. `karmada-controller-manager`: Fixed the issue that xxx
2. `karmada-scheduler`: The deprecated flag `--xxx` now has been removed. Users of this flag should xxx.
3. `API Change`: Introduced `spec.<field>` to the PropagationPolicy API for xxx.
-->

```release-note
NONE
```
