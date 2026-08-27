To clarify how the new operation fits the existing component path: `Component` is the scheduler input extracted from the source object, while `TargetComponent` is the per-cluster replica assignment stored in `spec.clusters[*].components`. Commit 1 adds the inverse mapping from that logical assignment back to resource-specific fields; commit 2 invokes it while generating `Work`.

```mermaid
---
config:
  theme: base
  themeVariables:
    background: "#ffffff"
    fontFamily: "Arial"
  flowchart:
    curve: basis
    htmlLabels: true
---
flowchart TB
    subgraph INPUT["Existing extraction and scheduling"]
        direction TB
        SOURCE["Source workload<br/>e.g. FlinkDeployment"]:::existing
        COMPONENTS["GetComponents<br/>to Binding spec.components<br/>Component: replicas + requirements"]:::existing
        SCHED["Scheduler AssignReplicas<br/>supported multi-template placement<br/>existing after PR 7833"]:::existing
        TARGET[("Binding spec.clusters[].components<br/>TargetComponent: per-cluster replicas")]:::state

        SOURCE -->|resource-specific fields| COMPONENTS
        COMPONENTS -->|scheduling input| SCHED
        SCHED -->|per-cluster assignment| TARGET
    end

    subgraph DELIVERY["PR 7830 Work delivery"]
        direction TB
        CONSUMER["ensureWork calls reviseWorkloadReplicas<br/>select component, scalar, or fallback<br/>Commit 2 consumer"]:::commit2
        HAS_RESULT{"Component result<br/>present?"}:::commit2
        SCALAR["ReviseReplica<br/>existing scalar path"]:::existing
        REVISE["ReviseComponents dispatcher<br/>and resource-specific field patch<br/>Commit 1 capability"]:::commit1

        CONSUMER --> HAS_RESULT
        HAS_RESULT -->|no| SCALAR
        HAS_RESULT -->|yes, revision hook| REVISE
    end

    subgraph OUTPUT["Existing Work finalization"]
        direction TB
        OVERRIDE["ApplyOverridePolicies<br/>runs last"]:::existing
        WORK["Work manifest<br/>dispatched to member cluster"]:::external

        OVERRIDE -->|final desired object| WORK
    end

    INPUT -->|source template + persisted TargetComponent result| DELIVERY
    DELIVERY -->|replica-adjusted workload| OUTPUT

    classDef existing fill:#e8eef5,stroke:#61758a,color:#17202a;
    classDef commit1 fill:#d8f0df,stroke:#3f7d52,color:#173b24,stroke-width:2px;
    classDef commit2 fill:#d8edf0,stroke:#347985,color:#12363c,stroke-width:2px;
    classDef state fill:#fff2cc,stroke:#b7922d,color:#4d3b00;
    classDef external fill:#f5f5f5,stroke:#666666,color:#262626,stroke-dasharray:5 5;
```

No component result uses the existing scalar path. Without a `ReviseComponents` hook, delivery proceeds only when `GetComponents` returns the exact name/replica set; otherwise the controller emits no mismatched `Work`. `ApplyOverridePolicies` still runs last. The split therefore keeps the reusable capability separate from its production consumer.
