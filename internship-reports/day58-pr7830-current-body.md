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

Multi-template workloads keep the scalar replica fields at zero, so component replica changes do not trigger rescheduling.

With `MultiplePodTemplatesScheduling` enabled, this PR compares desired component replicas with the scheduled snapshot by name for multi-component workloads with one scheduled target. Replica changes trigger the existing `ScaleSchedule` path. Reordered entries are treated as equal; missing snapshots and component-set changes retain the existing behavior.

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

Part of #7895

**Special notes for your reviewer**:
<!--
Such as a test report of this PR.
-->

- This PR only adds the rescheduling trigger. Incremental estimation and failure-safe Work propagation remain in #7835 and #7841.
- Validation: `go test -race -count=1 -p=4 ./pkg/util ./pkg/scheduler` and `golangci-lint run --concurrency=4 ./pkg/util ./pkg/scheduler` passed with Go 1.26.9. Full `make test` and live E2E were not run locally.
- AI assistance: implementation, test updates, and this description were prepared with Codex assistance.

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
