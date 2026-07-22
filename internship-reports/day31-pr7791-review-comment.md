# PR #7791 Review Comment Draft

Target: `test/e2e/suites/base/clusteraffinities_test.go`, line 149 in head `1117aa6e20a37f3c9b69598ea3732510dd52cc74`.

Status: not posted upstream; superseded by the request-scoped authoritative snapshot fix amended into current head `8992dabd62`; retained only as review evidence.

```text
Could we handle this without relying on the test-only cache barrier?

After member1 is restored in the API, the WorkloadRebalancer update can reach the scheduler before its Cluster informer observes member1's label update. The new path then starts from group1 against stale cache, falls back successfully to group2, and advances LastScheduledTime, so the one-shot request is considered complete.

When member1's Cluster event arrives later, enqueueAffectedBindings checks only SchedulerObservedAffinityName, which is still group2. Because member1 matches group1 rather than group2, this event does not requeue the Binding, and the workload never fails back even though the user created the WorkloadRebalancer after restoring member1.

The member2 label round trip here waits for the scheduler cache and avoids exactly this valid informer ordering, but users do not have that barrier. I reproduced the sequence in a focused scheduler test: the fallback consumed RescheduleTriggeredAt, and the later cluster1 event left the scheduling queue empty.

Please make the request converge under either informer order and cover the delayed Cluster-cache path with a deterministic test.
```

Visible words: 169.
