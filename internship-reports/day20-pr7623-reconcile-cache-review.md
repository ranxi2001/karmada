# Day 20 - PR #7623 Reconcile Cache Review

日期：2026-07-15

PR：[#7623 fix: update cached scale target when scale target reference changes](https://github.com/karmada-io/karmada/pull/7623)

Issue：[#7622 CronFederatedHPA repeatedly stops cron executors after changing scale target](https://github.com/karmada-io/karmada/issues/7622)

Review commit：`793f47dbfeb9f55a98e151af0b3c10f52e9b6c34`

## Review 定位

#7623 是 #7622 的窄范围 bug fix，不是 #7621 / #7662 安全重调度提案的一部分。它要修复的现象成立：`CronFHPAScaleTargetRefUpdates()` 如果只比较而不刷新缓存，以后的每次 reconcile 都会继续把同一次 target change 当成新变化，并停止现有 cron executors。

因此 review 不需要扩大到新 API 或架构设计。真正需要验证的是一个 controller 事务边界：新的 target 何时可以被视为已经成功应用。PR 当前在比较函数中立即提交缓存，但后面的 executor rebuild 和 status reconciliation 仍可能失败。

当前建议只发一条阻塞性 finding，定位到新增缓存赋值。三个 AI bot thread 不应代替这个 finding：

- Copilot 的 data race 判断不成立；该 helper 已由 `scaleTargetLock` 的写锁保护。
- Gemini 的 map cleanup 是已有 lifecycle gap，PR 更新已有 key 并未引入无界 key 增长，可另行讨论。
- 测试名是否更具体只是 nit，不能覆盖失败恢复路径。

## 阻塞性 Finding

PR 在 [`cronfederatedhpa_handler.go:77`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_handler.go#L77-L79) 检测到 target 变化后，立即把新 target 写入 `cronFHPAScaleTargetMap`。之后 reconcile 才停止旧 executor、创建新 executor 并写 rule history：

- [`cronfederatedhpa_controller.go:90`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_controller.go#L90-L103)
- [`cronfederatedhpa_controller.go:133`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_controller.go#L133-L150)
- [`cronfederatedhpa_controller.go:186`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_controller.go#L186-L188)

如果第一次 reconcile 在 `Status().Update` 处遇到瞬时错误，状态链变成：

```text
target changed
  -> cache advances to the new target
  -> replacement executor is inserted
  -> Status().Update fails
  -> reconcile is retried
  -> target comparison now reports unchanged
  -> identical existing executor causes processCronRule to return early
  -> the error retry does not retry the failed rule-history write
  -> retry returns success and the queue forgets the item
```

后续 job 也不能补齐缺失的 history record；执行历史更新在找不到对应 rule history 时直接返回：[`cronfederatedhpa_job.go:299`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_job.go#L299-L302)。controller 还使用 `GenerationChangedPredicate`，status-only update 不会自然触发一次修复 reconcile。后续新的 spec generation 或 controller restart 可能重新触发初始化，因此不能把影响写成永久不可恢复。

## E4 复现

在 PR head 的隔离 worktree 中加入临时 controller test：

1. 在 cache 中预置旧 target。
2. fake client 中的 CronFHPA 对象使用新 target 和一条合法 cron rule。
3. interceptor 令第一次 status subresource update 返回注入错误。
4. 连续调用两次 `Reconcile()`。

PR head 上结果：

```text
reconcile #1: injected status update failure
reconcile #2: nil
status update calls: 1
ExecutionHistories: empty
```

只移除 PR 新增的 cache assignment 后重复测试，第二次 reconcile 会再次执行 status update，调用数变为 `2`。这证明 finding 由新增缓存提交时机触发，而不是 fake client 或旧 controller 行为造成的相关性。

## Production Reachability 边界

故障注入只证明“如果第一次 `Status().Update` 失败，当前 retry 路径会留下不完整状态”，不能单独证明真实集群已经发生过这个问题。

本例不是任意构造的不可达错误：`Status().Update` 是真实 Kubernetes API 写边界，调用者显式处理其 error；Cron job 也会独立读取同一个 CronFHPA，并通过 `UpdateStatus` 写 `ExecutionHistories`：[`cronfederatedhpa_job.go:94`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_job.go#L94-L106) 和 [`cronfederatedhpa_job.go:305`](https://github.com/karmada-io/karmada/blob/793f47dbfeb9f55a98e151af0b3c10f52e9b6c34/pkg/controllers/cronfederatedhpa/cronfederatedhpa_job.go#L305-L312)。因此 conflict、API timeout 或 server/transport error 都是该接口允许出现的生产触发条件，而不是 fake client 独有状态。

当前没有线上日志或 CI artifact 证明该顺序实际发生过，准确分类应是 **reachable latent correctness bug**，不是 observed production incident。它仍可作为 blocking review finding，因为 controller 的 error retry 必须正确处理常规 API 写失败；但 review 文案必须公开说明证据来自 fault injection，不能暗示已观察到真实事故。

现有临时测试注入的是通用 error，因此它只负责证明 error branch 和 cache commit 的因果关系。更强的 upstream regression 应使用 `apierrors.NewConflict`，或通过 stale `resourceVersion` / 并发 status writer 产生真实 conflict；不能因为任意 mock error 能触发分支，就反向宣称每一种具体生产故障都已被复现。

完整包测试也通过：

```text
go test ./pkg/controllers/cronfederatedhpa -count=1
ok karmada.io/karmada/pkg/controllers/cronfederatedhpa 0.227s
```

临时 worktree 和 defect-assertion test 已删除，没有修改 upstream branch。

## 已发布 Upstream Review

已作为新增缓存赋值处的 line comment 发布，使用 `COMMENTED` review 并保持 thread unresolved。它是 blocking correctness finding，但不需要用 `REQUEST_CHANGES` review state 表达：

> Thanks for addressing the repeated target-change detection. One concern: this updates the cache too early, because the cache acts as the marker that the target change has already been handled.
>
> Suppose the target changes from A to B:
>
> 1. This line stores B in the cache.
> 2. `Reconcile` creates the new executor.
> 3. `updateRuleHistory` fails and `Reconcile` is retried.
> 4. The retry compares B with cached B and treats the target as unchanged.
> 5. `processCronRule` sees the existing executor and returns without retrying the failed status update.
>
> The retry then succeeds while `ExecutionHistories` remains empty. I reproduced this by making the first `Status().Update` fail; the second `Reconcile` returned `nil` and made no second status update.
>
> Could we update the cache only after all rules and status updates succeed, and add a regression test for this retry path?

用户确认 exact target 和正文后，已发布：[#7623 discussion_r3584185187](https://github.com/karmada-io/karmada/pull/7623#discussion_r3584185187)。GitHub 回读确认 comment `3584185187` 由 `ranxi2001` 发布到 head `793f47dbf`、`cronfederatedhpa_handler.go` 右侧第 78 行，关联 review `4700504249` 的状态为 `COMMENTED`，正文与本地稿一致。

## 当前状态

截至 2026-07-15，PR 仍为 open，head 未变，17 个 checks 全部 success，mergeable 但 `mergeable_state=blocked`。请求的真人 reviewer 是 `jwcesign` 和 `zhzhuang-zju`；当前新增了本次 `COMMENTED` review，但仍没有 maintainer LGTM 或 approve。
