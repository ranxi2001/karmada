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

For multi-template workloads, the scalar replica fields remain zero, so `IsBindingReplicasChanged` cannot detect component scale-up or scale-down. As a result, an existing Binding does not re-enter the scheduler when component replicas change.

With `MultiplePodTemplatesScheduling` enabled, this change compares the desired `spec.components` replicas with the scheduler-accepted `spec.clusters[0].components` snapshot by component name. Scale-up and scale-down enter the existing `ScaleSchedule` path, while equal snapshots, including reordered entries, keep the existing behavior.

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

- Scope: this PR only triggers rescheduling. Incremental estimation and failure-safe Work propagation remain in #7835 and #7841.
- Missing or incomparable accepted component snapshots do not select a fallback policy in this PR; the existing behavior is preserved.
- Tests: `go test -race -count=1 ./pkg/util -run '^TestIsBindingReplicasChanged$'`, `go test -race -count=1 ./pkg/scheduler -run '^(TestDoScheduleBinding|TestDoScheduleClusterBinding)$'`, and `go test -count=1 ./pkg/util ./pkg/scheduler` passed. Full `make test` and live E2E were not run.
- AI assistance: Codex helped inspect the scheduling path and draft the implementation and tests; I reviewed the final diff and validation results.

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
`karmada-scheduler`: Multi-template workloads are rescheduled when component replicas change.
```
