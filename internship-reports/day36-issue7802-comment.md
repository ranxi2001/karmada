Thanks for raising this. I verified the mechanism on [current master (`ce2a7b869`)](https://github.com/karmada-io/karmada/commit/ce2a7b869477272202095282251afe490c38d525) using a fake clock and gated `ActiveQueue`.

- `activeQ` orders high before low when both are resident.
- With an earlier low backoff expiry, the worker can `Pop` low after the first `Push`, before an also-eligible high reaches `activeQ`. The unschedulable-map path has the same window.
- This is bounded: the sole worker can take at most one early binding per periodic flush, because it cannot begin a second `Pop` before that flush releases the outer lock. Thus continuous draining overstates the evidence.
- Capacity/quota release also has no direct binding requeue event, a separate wake-up gap.

This proves reachability, not production frequency. The [user guide](https://karmada.io/docs/userguide/scheduling/priority-scheduling/) promises strict priority during contention, while the [merged proposal](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/docs/proposals/scheduling/binding-priority-preemption/README.md#effect-of-priority-on-scheduling) says an unschedulable high-priority binding may not precede lower-priority work without preemption.

Could maintainers clarify whether priority covers only bindings simultaneously in `activeQ`, or all blocked bindings eligible for the same retry opportunity? I suggest settling that contract before coupling a fix to #7485; its tenant FIFO strategies address a different decision.
