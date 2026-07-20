I think the effective capacity for new replicas needs to be decided before cluster selection, while preserving the existing `ClusterTolerations` behavior.

For an already-targeted non-Ready cluster, two policy states matter. If its health taint is not tolerated, `TaintToleration.Filter` retains the cluster only so its existing replicas can remain until taint-manager handles eviction. This is the #6861 case, so its new-replica capacity should be 0. If the health taint is explicitly tolerated, the policy intentionally keeps the cluster eligible, but this unconditional Ready check still sets its new capacity to 0 and overrides that policy choice.

The check is also too late for current `master`: `SelectClusters` computes `AvailableReplicas`, and overflow tiering consumes it before `dynamicScaleUp`. In a focused assignment/overflow regression, primary A had 4 existing + 10 estimated replicas, healthy overflow B had 10, and the desired count was 12. Tier 0 budgeted all 12 to A; `dynamicScaleUp` then reduced A's new capacity to 0 and returned `Unschedulable`, so B was never tried.

```mermaid
flowchart TB
    subgraph CURRENT["Current PR ordering"]
        direction LR
        C_FILTER["Filter<br/>existing A is retained"]:::current --> C_AVAILABLE["SelectClusters<br/>A appears to hold 4 + 10"]:::current --> C_TIER["Overflow tier 0<br/>budgets all 12 to A"]:::current --> C_LATE["dynamicScaleUp<br/>sets A new capacity to 0"]:::late --> C_FAIL["Risk: Unschedulable<br/>healthy B is not tried"]:::risk
    end

    subgraph REQUIRED["Required invariant"]
        direction LR
        P_POLICY{"Health taint<br/>explicitly tolerated?"}:::decision
        P_POLICY -->|Yes| P_KEEP["New capacity = estimator result<br/>policy choice preserved"]:::unchanged
        P_POLICY -->|No| P_ZERO["New capacity = 0<br/>existing replicas preserved"]:::changed
        P_KEEP --> P_AVAILABLE["Compute AvailableReplicas<br/>before selection"]:::changed
        P_ZERO --> P_AVAILABLE
        P_AVAILABLE --> P_RESULT["Tiering sees the correct<br/>remaining demand"]:::changed
    end

    CURRENT ~~~ REQUIRED

    classDef current fill:#f5f5f5,stroke:#666666,color:#262626;
    classDef unchanged fill:#dae8fc,stroke:#6c8ebf,color:#172554;
    classDef decision fill:#fff2cc,stroke:#d6b656,color:#713f12;
    classDef changed fill:#d5e8d4,stroke:#82b366,color:#14532d,stroke-width:2px;
    classDef late fill:#fff2cc,stroke:#d6b656,color:#713f12,stroke-width:2px;
    classDef risk fill:#f8cecc,stroke:#b85450,color:#7f1d1d,stroke-dasharray:6 4;
```

Could we compute this policy-aware new-replica capacity before selection and carry it through tiering and assignment? Please cover the `filter -> selection/tiering -> assignment` path for an existing untolerated cluster, an explicitly tolerated health taint, and a healthy overflow fallback. `dynamicFreshScale` also bypasses the current check; please apply the same invariant there, or confirm with maintainers that Fresh rescheduling is intentionally outside this PR's scope.
