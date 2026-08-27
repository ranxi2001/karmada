# PR #7830 Rebuilt Draft

## Title

`feat: validate component scheduling results in bindings`

## Body

**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

#7837 adds per-component replica assignments to `TargetCluster`. This PR validates the persisted results on both `ResourceBinding` and `ClusterResourceBinding`: component names must belong to `spec.components`, duplicates within a target cluster are rejected, and component results copied into `requiredBy` are checked as well.

When `MultiplePodTemplatesScheduling` is disabled, existing component results may remain unchanged, be reordered, or be removed, but they cannot be introduced or modified.

`work.karmada.io/v1alpha1` cannot represent these fields. A v1alpha1 main-resource or `/status` update is therefore rejected only when the stored v1alpha2 binding contains component data; bindings without component data remain writable through v1alpha1.

This branch is temporarily stacked on #7837 and a minimal compile follow-up so PR CI can run. Those base commits will be rebased out after #7837 merges.

**Which issue(s) this PR fixes**:

Part of #7492

**Special notes for your reviewer**:

- The v1alpha1 guard uses an uncached v1alpha2 read because admission objects have already been projected through the lossy served version, including `/status` updates.
- This change does not produce component scheduling results or change delivery behavior.
- Repository verification, focused race tests for the changed webhook packages, and base E2E package compilation passed locally.
- Codex assisted with implementation and test drafting; the final diff and validation evidence were reviewed before submission.

**Does this PR introduce a user-facing change?**:

```release-note
API Change: Component scheduling results in ResourceBinding and ClusterResourceBinding are now validated; v1alpha1 writes that would discard v1alpha2 component data are rejected.
```
