# Day 41: PR #7810 Published Upstream Review Comment

- Target: [`karmada-io/karmada#7810`](https://github.com/karmada-io/karmada/pull/7810)
- Review surface: top-level PR comment
- Reviewed head: `31bef8d37e6505cb333026ec86b00d8ea3172339`
- Status: **published** at [`issuecomment-5178016994`](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994)
- Published at: `2026-08-04T10:53:52Z`

## Published English Comment

Thanks for validating the observed 10 ms case. I think time-based coalescing can be a useful best-effort optimization, but the current implementation has a correctness gap beyond the window-size limitation discussed in #7805.

`AddAfter` is not trailing-edge debounce: client-go keeps the earliest `readyAt`. It also delays only this event producer; an immediate cluster requeue or `AddRateLimited` shares the same key and can make it runnable sooner.

A more serious sequence is:

1. scheduler A delays an RB update until `t0+D`;
2. before that deadline, the RB becomes `SchedulingSuspended` or changes `schedulerName`;
3. `FilteringResourceEventHandler` emits delete, but `onResourceBindingDelete` does not cancel the delayed key;
4. `doScheduleBinding` reloads the RB without rechecking either condition, so scheduler A can still patch it.

The scope is also broader than described: application failover/taint eviction and Descheduler mutate `RB.spec.clusters`, while WorkloadRebalancer updates `rescheduleTriggeredAt`; these scheduling paths receive `D`, while `PriorityBasedScheduling` silently ignores the flag.

Could we treat this as best-effort coalescing rather than `Fixes #7805`, add a dequeue-time eligibility guard, and limit the delay to detector-owned replica/placement changes? I also think fake-clock coverage should include the fixed-window boundary, fast-path bypass, ownership/suspension transitions, failover/descheduler/rebalance latency, and both queue modes.
