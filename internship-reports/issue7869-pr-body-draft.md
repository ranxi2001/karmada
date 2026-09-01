**What type of PR is this?**

/kind documentation

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

**What this PR does / why we need it**:

Stop maintaining version 1.16 and maintain version 1.19.

**Which issue(s) this PR fixes**:
<!--
*Automatically closes linked issue when PR is merged.
Usage: `Fixes #<issue number>`, or `Fixes (paste link of issue)`.*
-->
Part of #7869

<!--
*Optionally link to the umbrella issue if this PR resolves part of it.
Usage: `Part of #<issue number>`, or `Part of (paste link of issue)`.*
Part of #
-->

**Special notes for your reviewer**:
<!--
Such as a test report of this PR.
-->

- Tests: YAML, version-matrix, and README table assertions passed; `actionlint v1.7.12` passed for both scheduled workflows. The scheduled compatibility and image-scanning matrices were not run locally.
- AI assistance: Codex helped inspect prior release updates and prepare validation; I reviewed the diff and results.

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
