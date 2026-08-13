#### Which jobs are flaking:

- [Official v1.34.0 failure](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911) at `3d4d14d746de507164abf40c1017b1f2b0e47e3a`.
- [Fork v1.36.1 attempt-1 failure](https://github.com/ranxi2001/karmada/actions/runs/31573625648/job/94042457609) at `8770a193a7a0c6f20dd3a1ea3ac9ff979df2730f`.

#### Which test(s) are flaking:

Both jobs failed the same spec:

```text
[EstimatorAssumption] NodeResource plugin assumption testing
[It] FlinkDeployment should be unschedulable when assumed workloads exhaust cluster resources
```

`assertSingleTemplateDeploymentUnschedulable` timed out after 420 seconds because the 200m probe Deployment became schedulable instead of reaching `Scheduled=False`.

#### Reason for failure:

The spec stops creating FlinkDeployments at the first no-fit result and treats that result as proof that **its own** assumptions exhausted `member1`. The two runs show two different earlier specs that violated this isolation assumption and affected the same assertion.

| Run | Workload-producing spec | State left for the NodeResource spec | Result |
| --- | --- | --- | --- |
| Official v1.34.0 | `[propagation with taint and toleration testing] ... deployment with cluster tolerations testing` | `deploy-wbch9` was rescheduled during cleanup and refreshed a foreign scheduler assumption | The Flink loop stopped on a no-fit result that still included `deploy-wbch9`; after that foreign assumption expired, the probe scheduled successfully |
| Fork v1.36.1 attempt 1 | `[resource-status collection] ... PodDisruptionBudget collection testing ... pdb status collection testing` | `poddisruptionbudget-xw489` Deployment had no cleanup; only its PDB and policy were removed | The retained workload changed the capacity seen by the same NodeResource spec, so its first Flink no-fit did not prove that this spec's assumptions alone exhausted `member1` |

The official run provides the timestamped root-cause chain:

```mermaid
sequenceDiagram
    autonumber
    participant T as Taint/toleration spec
    participant A as Karmada API
    participant S as Scheduler
    participant C as Assumption cache
    participant N as NodeResource spec

    T->>A: 07:10:19.011 Create deploy-wbch9
    A->>S: Schedule to member1
    S->>A: Binding = {member1:3}
    T->>A: 07:10:24.030 Restore cluster taints
    A-)S: Queue cluster-change scheduling
    T->>A: 07:10:24.148 Delete Deployment
    S->>A: 07:10:24.239 Patch binding = {member1:3, member2:3, member3:3}
    S->>C: Record deploy-wbch9 assumption
    A-->>T: 07:10:24.346 ResourceBinding becomes NotFound
    N->>S: 07:15:22.998 Estimate last FlinkDeployment
    S->>C: Read assumptions including deploy-wbch9
    C-->>S: Foreign 30m CPU workload still present
    S-->>N: No fit, stop the Flink loop
    N->>S: 07:15:24.666 Estimate 200m probe
    S->>C: Read assumptions after inferred TTL boundary
    C-->>S: deploy-wbch9 no longer present
    S-->>N: Probe fits and becomes Scheduled=True
    N--xN: 07:22:24.642 Timeout waiting for Scheduled=False
```

The fork run identifies a separate producer for the same consumer failure:

```mermaid
sequenceDiagram
    autonumber
    participant P as PDB collection spec
    participant A as Karmada API
    participant M as member1 / estimator state
    participant N as NodeResource spec

    P->>A: 07:52:45.778 Create poddisruptionbudget-xw489 Deployment
    P->>A: Create matching PDB and PropagationPolicy
    P->>A: 07:53:06.559 Remove PropagationPolicy
    P->>A: 07:53:06.626 Remove PDB
    Note over P,A: No Deployment cleanup was registered
    A-)M: Retained workload remains part of available-capacity state
    N->>M: 08:12:18.447 Start sequential Flink estimates
    M-->>N: First Flink no-fit arrives under foreign workload capacity
    N->>M: 08:12:43.596 Estimate single-template 200m probe
    M-->>N: Probe does not reach Scheduled=False
    N--xN: 08:19:43.613 Timeout waiting for Scheduled=False
```

The first diagram is the primary E3 root-cause evidence. The second diagram identifies an independent cleanup omission and the same downstream failure. That run was later rerun, and GitHub now exposes the rerun's component artifact under the run-level artifact name; therefore the second branch is supporting evidence, not the timestamp anchor for a cache transition.

#### Anything else we need to know:

A spec that creates a schedulable workload must delete the source object and wait for its generated `ResourceBinding` to become NotFound before restoring shared cluster state or completing cleanup. This prevents a completed spec from changing the capacity assumptions observed by a later estimator spec.

The proposed fix is limited to E2E lifecycle isolation. It does not change scheduler or estimator behavior, cache TTL, retries, or test timeouts, and it does not claim to solve the general production delete/reschedule race.

- #7719 and #7732 use the same official CI run but fix the earlier Flink CRD/APIEnablements cleanup race, not these workload producers.
- #5382 isolates the PDB selector but does not delete the fixture Deployment.
