# PR4 draft: reschedule scaled multi-component workloads

Proposed title:

```text
feat: reschedule scaled multi-component workloads
```

Proposed body:

````md
**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

Multi-template workloads did not re-enter scheduling when component replicas changed, and a failed reschedule could allow the updated source configuration to reach member clusters.

This change routes component replica changes through scheduling using the last accepted per-component result. While the accepted target is available, pure scale-up estimates only the positive replica delta on that target and pure scale-down skips estimation. If no cluster fits or the transition is unsupported, the accepted result and existing Work remain unchanged. The FlinkDeployment E2E scenario now covers scale-up, scale-down, failed-update retention, requirements rejection, and recovery.

**Which issue(s) this PR fixes**:

Fixes #7492

**Special notes for your reviewer**:

- Depends on #7830, #7833, and #7835; all build on the API change in #7837. Review this PR's integrated residual as `ea8782509...40d82879f`.
- Rollout order: update the API/CRD first, then the binding controller, then the scheduler. Otherwise keep `MultiplePodTemplatesScheduling` disabled until both runtime components are updated.
- A healthy accepted target is not changed solely because of scale-up; a missing or terminating target can use the existing failover path.
- Validation: `go test -race -count=1 ./pkg/util ./pkg/controllers/binding ./pkg/scheduler ./pkg/scheduler/core ./pkg/scheduler/metrics`; `go test -count=1 ./test/e2e/suites/base -run '^$'`; `make verify`. The Flink E2E compiles locally but was not run against a live multi-cluster environment.
- Codex assisted with implementation, tests, review, and PR drafting; I reviewed the final diff and validation results.

**Does this PR introduce a user-facing change?**:

```release-note
`karmada-scheduler`: With `MultiplePodTemplatesScheduling` enabled, component replica changes now trigger rescheduling on the accepted target; scale-up estimates only added replicas, scale-down skips estimation, and failed rescheduling keeps the previously accepted member-cluster configuration.
```
````
