#### Which jobs are flaking:

- `CI Workflow / e2e test (v1.34.0)`
- First observed in #7697 on run https://github.com/karmada-io/karmada/actions/runs/28499042349, job https://github.com/karmada-io/karmada/actions/runs/28499042349/job/84472927003, head SHA `152ab454265ac683f55f04a166e9de9aedaad94c`.
- Observed again on the master push after #7728 was merged: run https://github.com/karmada-io/karmada/actions/runs/28998390044, job https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911, head SHA `3d4d14d746de507164abf40c1017b1f2b0e47e3a`.
- The #7697 occurrence passed after re-triggering CI with an empty commit, so this looks like an e2e timing flake rather than a regression from #7697.
- The #7728 occurrence is an independent signal: #7728 only updated GitHub runner labels, its PR CI passed before merge, and the FlinkDeployment failure appeared only in the post-merge master push run.

#### Which test(s) are flaking:

The first observed failure was:

```text
[EstimatorAssumption] ResourceQuota plugin assumption testing
[It] FlinkDeployment should be unschedulable when assumed workloads exhaust ResourceQuota
```

The later master push failure was:

```text
[EstimatorAssumption] NodeResource plugin assumption testing
[It] FlinkDeployment should be unschedulable when assumed workloads exhaust cluster resources
```

Both failures timed out in `WaitResourceBindingFitWith` while waiting for `FlinkDeployment` ResourceBindings:

```text
[FAILED] Timed out after 420.000s.
In [It] at: test/e2e/framework/resourcebinding.go:47
test/e2e/suites/base/estimator_test.go:350
```

The latest occurrence timed out at the same helper:

```text
[FAILED] Timed out after 420.001s.
In [It] at: test/e2e/framework/resourcebinding.go:47
```

This is probably not limited to one `It` block. Several e2e suites create and delete the same `flinkdeployments.flink.apache.org` CRD:

- `test/e2e/suites/base/estimator_test.go`
- `test/e2e/suites/base/schedule_multi_template_test.go`
- `test/e2e/suites/base/federatedresourcequota_test.go`

#### Reason for failure:

The scheduler log from the first failed job shows that the ResourceBinding was rejected by the APIEnablement plugin because `member1` did not report the `FlinkDeployment` API:

```text
Cluster(member1) not fit as missing API(flink.apache.org/v1beta1, kind=FlinkDeployment)
ResourceBinding(karmadatest-6cw8j/flinkdeployment-5fc2b-flinkdeployment) scheduled to clusters []
0/3 clusters are available: 1 cluster(s) did not have the API resource, 2 cluster(s) did not match the placement cluster affinity constraint.
```

The later master push failure has the same shape. The test created and propagated the `FlinkDeployment` CRD, then repeatedly failed to find the expected `ResourceBinding` objects before timing out:

```text
Failed to get ResourceBinding(karmadatest-cdn7t/flinkdeployment-czxhf-flinkdeployment), err: resourcebindings.work.karmada.io "flinkdeployment-czxhf-flinkdeployment" not found
Failed to get ResourceBinding(karmadatest-cdn7t/flinkdeployment-62qpd-flinkdeployment), err: resourcebindings.work.karmada.io "flinkdeployment-62qpd-flinkdeployment" not found
Failed to get ResourceBinding(karmadatest-cdn7t/flinkdeployment-zxmgw-flinkdeployment), err: resourcebindings.work.karmada.io "flinkdeployment-zxmgw-flinkdeployment" not found
Failed to get ResourceBinding(karmadatest-cdn7t/flinkdeployment-8v7jl-flinkdeployment), err: resourcebindings.work.karmada.io "flinkdeployment-8v7jl-flinkdeployment" not found
Failed to get ResourceBinding(karmadatest-cdn7t/flinkdeployment-tm6gt-flinkdeployment), err: resourcebindings.work.karmada.io "flinkdeployment-tm6gt-flinkdeployment" not found
```

The current FlinkDeployment e2e cleanup path only waits for the source CRD to disappear from the Karmada control plane. CRD propagation/removal to member clusters and the `Cluster.Status.APIEnablements` collection are asynchronous.

I ran a local diagnostic that simulated the old cleanup boundary:

1. Create `flinkdeployments.flink.apache.org` on the Karmada control plane.
2. Propagate the CRD to two member clusters.
3. Wait until the member CRDs exist and `Cluster.Status.APIEnablements` reports `FlinkDeployment`.
4. Delete the `ClusterPropagationPolicy`.
5. Delete the source CRD from the control plane.
6. Wait only for the control-plane CRD to disappear, which is what the old cleanup waited for.
7. Poll member CRDs and `Cluster.Status.APIEnablements`.

The diagnostic showed that the old cleanup can return before member-cluster CRD and APIEnablement state has converged:

```text
control-plane CRD disappeared after 1s

after 00s: APIEnablements still reported FlinkDeployment and member CRDs still existed
after 01s: APIEnablements still reported FlinkDeployment; one member CRD was gone
after 02s: member CRDs were gone, but APIEnablements still reported FlinkDeployment
after 03s: member CRDs were gone, but APIEnablements still reported FlinkDeployment
after 04s: APIEnablements also converged
```

This gives a plausible race:

1. A previous FlinkDeployment e2e deletes the CRD and returns after the control-plane CRD disappears.
2. `Cluster.Status.APIEnablements` can still report `FlinkDeployment` from the previous CRD for a short time.
3. The next FlinkDeployment e2e starts and `WaitCRDPresentOnClusters()` can pass on that stale enabled status instead of a fresh status update for the newly propagated CRD.
4. The scheduler can then observe the member cluster as missing `flink.apache.org/v1beta1/FlinkDeployment`, causing the ResourceBinding to remain unscheduled until the test times out.

So the cleanup should wait for all state that later tests depend on:

- the source CRD has disappeared from the Karmada control plane;
- the propagated CRD has disappeared from member clusters;
- `Cluster.Status.APIEnablements` no longer reports `FlinkDeployment` as enabled.

This follows the same synchronization-barrier idea as #7692, but for the FlinkDeployment CRD/APIEnablements cleanup path.

#### Anything else we need to know:

Additional CI evidence:

- The first failure in #7697 was followed by an empty trigger commit [`93eaf7e57515c959fe30fa2aba387ce10029046d`](https://github.com/ranxi2001/karmada/commit/93eaf7e57515c959fe30fa2aba387ce10029046d), whose commit stats are `files=0`, `additions=0`, and `deletions=0`.
- The re-triggered upstream PR CI run https://github.com/karmada-io/karmada/actions/runs/28762872757 passed `lint`, `codegen`, `compile`, `unit test`, `e2e v1.34.0`, `e2e v1.35.0`, and `e2e v1.36.1`.
- Before #7728 was merged, its PR CI run https://github.com/karmada-io/karmada/actions/runs/28915976137 passed after an empty trigger commit [`de3b6be675bbf8ad12f91052f7d0fb53c5b592a5`](https://github.com/ranxi2001/karmada/commit/de3b6be675bbf8ad12f91052f7d0fb53c5b592a5), whose commit stats are also `files=0`, `additions=0`, and `deletions=0`.
- The same FlinkDeployment timeout then appeared in the post-merge master push run https://github.com/karmada-io/karmada/actions/runs/28998390044, job https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911.

I tested a small e2e-only candidate fix that waits for member-cluster CRD disappearance and for `Cluster.Status.APIEnablements` to stop reporting `FlinkDeployment` during cleanup.

Validation branch:

- Branch: [ranxi2001/karmada@test/estimator-flink-crd-flake](https://github.com/ranxi2001/karmada/tree/test/estimator-flink-crd-flake)
- Commit: [f2e7c434bad6d4a970265af79a157afb61e6182e](https://github.com/ranxi2001/karmada/commit/f2e7c434bad6d4a970265af79a157afb61e6182e)

Local validation:

- `git diff --check`
- `go test ./test/e2e/suites/base -run '^$' -count=0`

Fork push CI:

- [CI run 28774018375](https://github.com/ranxi2001/karmada/actions/runs/28774018375): passed
- Jobs: `lint`, `codegen`, `compile`, `unit test`, `e2e v1.34.0`, `e2e v1.35.0`, and `e2e v1.36.1` all passed.

I can send this as a focused e2e flake fix if this issue direction makes sense.
