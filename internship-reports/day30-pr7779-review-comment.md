This only protects single-object deletion. Because `REST` embeds `*genericregistry.Store`, it still promotes `Store.DeleteCollection` and implements `rest.CollectionDeleter`. The API installer therefore exposes collection DELETE for `/clusters`, and `Store.DeleteCollection` calls `e.Delete` with a `*Store` receiver. That call cannot return to the outer `REST.Delete` override, so `validateDeletionProtection` is skipped.

```mermaid
flowchart TB
    subgraph CURRENT["Current PR behavior"]
        direction LR
        C_SINGLE["Single DELETE"]:::current --> C_REST["REST.Delete"]:::changed --> C_VALIDATE["Protection validator"]:::changed --> C_FORBID["Forbidden"]:::changed
        C_COLLECTION["Collection DELETE"]:::current --> C_PROMOTED["Promoted Store.DeleteCollection"]:::current --> C_STORE["Store.Delete"]:::risk --> C_DELETED["Risk: protected Cluster deleted"]:::risk
    end
    subgraph REQUIRED["Required collection path"]
        direction LR
        P_COLLECTION["Collection DELETE"]:::unchanged --> P_REST["REST.DeleteCollection (new)"]:::new --> P_VALIDATE["Compose protection + request validation"]:::new --> P_STORE["Store.DeleteCollection"]:::unchanged --> P_FORBID["Forbidden for protected item"]:::new
    end
    CURRENT ~~~ REQUIRED
    classDef current fill:#f5f5f5,stroke:#666666,color:#262626;
    classDef unchanged fill:#dae8fc,stroke:#6c8ebf,color:#172554;
    classDef changed fill:#d5e8d4,stroke:#82b366,color:#14532d,stroke-width:2px;
    classDef new fill:#d9ead3,stroke:#38761d,color:#14532d,stroke-width:2px;
    classDef risk fill:#f8cecc,stroke:#b85450,color:#7f1d1d,stroke-dasharray:6 4;
```

This is a supported client path: `ClusterInterface` exposes `DeleteCollection`, so a label selector matching a protected Cluster can still delete it. Could we override `REST.DeleteCollection` and pass the same composed validator to `r.Store.DeleteCollection`? Please add a regression whose selector matches only a protected Cluster, then assert the request is rejected and the Cluster remains; using one match also avoids the API's documented non-atomic partial-deletion behavior.
