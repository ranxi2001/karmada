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

When component scale rescheduling fails, Karmada must preserve the accepted component result and existing Work.

This change calls the #7835 planner only for component scale on the current accepted target. Success commits the complete desired `TargetCluster.Components` result through the existing scheduler patch; any error returns before that patch. Before updating Work, the binding controllers compare replicas extracted from the current source with the accepted snapshot. Mismatched or incomparable replicas wait, while equal replicas continue through the existing `ensureWork` path without workload rewriting.

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

- Scope: the guard applies to default-scheduler multi-template bindings with an accepted snapshot. Other scheduler, feature-off, single-template, and missing-snapshot paths keep existing behavior; failover and requirements provenance remain out of scope.
- Review the residual diff as `e19a318eb...c8146e039`; the preceding commits are the stacked #7830 and #7835 dependencies.
- Tests: the affected package race tests passed. The base E2E package compiled and passed changed-path lint; live multi-cluster E2E was not run locally.
- AI assistance: Codex helped inspect the scheduler and Work update paths and draft the implementation and tests; I reviewed the final diff and validation results.

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
`karmada-scheduler`: Failed multi-template component scale rescheduling now preserves the accepted component result and existing Work until the new replicas are accepted.
```
