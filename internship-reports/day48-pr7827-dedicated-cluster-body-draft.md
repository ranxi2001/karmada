**What type of PR is this?**

/kind cleanup
/kind flake

**What this PR does / why we need it**:

The NodeResource `EstimatorAssumption` spec previously [hard-coded `member1` as its target](https://github.com/karmada-io/karmada/blob/09c08f405b2f0b53106b1947e08a82d4cc94de28/test/e2e/suites/base/estimator_test.go#L382-L407). That constraint works, but `member1` is shared by the base E2E suite, so workloads or estimator assumptions left by another spec can change when this spec observes capacity exhaustion.

This change [gives the spec a temporary Kind member cluster and a dedicated scheduler-estimator](https://github.com/karmada-io/karmada/blob/478fdcc8df0ac607a8b0d82adb5f3aafac57c756/test/e2e/suites/base/estimator_test.go#L397-L667). The serial spec waits for the scheduler to establish the dedicated estimator connection, verifies a successful `MaxAvailableComponentSets` request, and runs the assumption assertions only against that cluster. Cleanup is registered before cluster creation and join so partial setup failures also remove the temporary resources.

**Which issue(s) this PR fixes**:

Fixes #7826

**Special notes for your reviewer**:

- The final diff is limited to `test/e2e/suites/base/estimator_test.go`; it does not change scheduler, estimator, cache, TTL, retry, or timeout behavior.
- `go test -count=1 ./test/e2e/suites/base -run '^$'`, `go test -race -count=1 ./test/e2e/suites/base -run '^$'`, `go vet ./test/e2e/suites/base`, `PATH=/root/go/bin:$PATH make verify`, and `git diff --check` passed.
- A real multi-cluster E2E is not available locally; upstream PR CI remains the end-to-end validation boundary.
- Codex assisted with source analysis, implementation, validation, and drafting; I reviewed the change and results.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
