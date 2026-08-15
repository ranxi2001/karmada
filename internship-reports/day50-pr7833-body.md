**What type of PR is this?**

/kind feature
/kind api-change

**What this PR does / why we need it**:

`ResourceBinding.spec.components` records requested replicas, but Karmada does not persist or apply per-cluster component assignments. This change adds that producer-to-delivery path behind `MultiplePodTemplatesScheduling`.

The scheduler stores complete assignments for applicable multi-template workloads. Single-component `Divided` scheduling also keeps the legacy scalar result. The new `ReviseComponents` operation supports the configuration API, Lua, webhooks, and the built-in FlinkDeployment customization. Work delivery applies persisted assignments and fails closed when a changed multi-component result has no revision hook.

**Which issue(s) this PR fixes**:

Part of #7492

**Special notes for your reviewer**:

- Depends on #7837. This branch is based directly on `76589a9d5`, the current #7837 head. Review this PR's residual as `76589a9d5...98535c541`.
- PR2 covers result production, interpreter support, Work delivery, Flink customization, and `RequiredBy` ownership. It excludes scale detection, incremental estimation, rescheduling planning, and failed-result retention.
- Validation: `make verify`, focused race tests across the scheduler, detector, binding delivery, interpreter, CLI, and configuration webhook packages, and base E2E package compilation passed. No separate local live E2E run was performed.
- Codex assisted with implementation, tests, and review; I reviewed the final diff and validation results.

**Does this PR introduce a user-facing change?**:

```release-note
API Change: Added the `ReviseComponents` interpreter operation. With `MultiplePodTemplatesScheduling` enabled, Karmada persists per-component assignments and applies them during Work delivery.
```
