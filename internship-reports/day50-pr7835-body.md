**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

When a multi-template workload scales, estimating the complete desired component set against its current target double-counts replicas that the cluster has already accepted. This change adds name-keyed component comparison and scale-estimation planning based on the accepted per-component snapshot.

For a pure scale-up, the planner estimates only the positive component delta on the current target. Pure scale-down skips the estimator, while candidates without an accepted snapshot and other unsupported shapes retain the existing full-desired estimation fallback. The predicate and planner are intentionally not wired into the scheduler entry point in this PR, so this slice does not change production scheduling behavior.

**Which issue(s) this PR fixes**:

Part of #7492

**Special notes for your reviewer**:

- Depends on #7837. This branch is based directly on `76589a9d5`, the current #7837 head. Review this PR's residual as `76589a9d5...782232b7d`.
- Scope: this planner is for replica-count changes with a stable component set and resource requirements. Scheduler activation, unsupported-change rejection, and failure-safe result retention remain for the next stacked PR.
- Validation: `make verify`, `go test -race -count=1 ./pkg/util ./pkg/scheduler/core`, and `git diff --check a957f64d5..782232b7d` passed. No separate local live E2E run was performed because this slice is not connected to the production scheduler path.
- Codex assisted with implementation, tests, review, and PR drafting; I reviewed the final diff and validation results.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
