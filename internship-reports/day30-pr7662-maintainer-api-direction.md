# Day 30：PR #7662 维护者提出的 API 收敛方向

## 先说人话

这次维护者不是在批准原 proposal，而是在要求作者大幅删减：`WorkloadRebalancer` 不要变成一套“万能迁移系统”，只保留“请调度器重新计算一次”的职责，并增加一个“保留正常副本”的选项。

先看一个 10 副本的例子：

```text
member1：分配 6 个副本，其中 4 个 available（可正常提供服务）
member2：分配 4 个副本，其中 4 个 available
```

两种行为的区别是：

- 完整重调度：把 10 个副本全部重新计算，最终位置可能整体变化。
- 保留 available 副本：member1 的 4 个和 member2 的 4 个不动，只重新安排剩下 2 个不可用副本。

执行过程也从旧方案的“多个 controller 共同修改副本分配”变成：

```text
用户创建 WorkloadRebalancer
        ↓
WorkloadRebalancer controller 只写一条“重调度请求”
        ↓
调度器（karmada-scheduler）读取请求和行为选项
        ↓
只有调度器修改 Binding.spec.clusters
```

这样做的直接好处是：不会再出现 WorkloadRebalancer controller 和 scheduler 同时修改副本位置、互相覆盖的问题。

但 #5070 还差最后一条明确约定。可以把 `schedulerObservingAffinityName` 理解为调度器夹在 affinity 组列表里的“上次阅读书签”：

```text
优先组 A 暂时故障 -> 工作负载退到组 B
组 A 后来恢复 -> 用户触发“完整重调度”
```

用户期望重新从 A 开始选择；当前代码却仍可能从书签 B 开始。维护者说完整重调度应“彻底丢弃旧调度结果”，按这个意思应该把书签也忘掉，但他还没有明确写出要忽略或清空 `schedulerObservingAffinityName`。

因此当前结论是：API 方向已经清楚，#5070 也获得了较强的产品语义支持；但作者尚未提交新版 proposal，我们现在不应直接写代码。先等作者落稿，再检查“完整重调度是否真的从 affinity 组 A 重新开始”。

另外，`SafeMigration` 不是被解决，而是被移出 #7662。以后如果单独设计安全迁移，目标副本先就绪、源副本后删除、finalizer、持久化状态和并发 ownership 仍然需要重新回答。

## 证据快照

- PR：[karmada-io/karmada#7662](https://github.com/karmada-io/karmada/pull/7662)
- 最新维护者 review：[RainbowMango review 4742653446](https://github.com/karmada-io/karmada/pull/7662#pullrequestreview-4742653446)
- Review 时间：2026-07-21 08:24:34 UTC / 16:24:34 CST
- PR head：`586f6fc3508eb0a504223898c0329a4bb8b4c57c`
- 当前 upstream 基线：`4926be09bc3546162a56faf92e7e3e96158d4bcd`
- 维护者权重：`RainbowMango` 是 PR assignee、Karmada member、根 OWNERS approver 和 `pkg/apis` approver。
- 当前状态：这是 `COMMENTED` 的建议方案，不是已批准 API。作者尚未回复或推送新 commit；PR 仍只有 2026-06-23 的一个 proposal commit，11 个 review threads 全部未解决。

## 维护者明确提出的方向

维护者反对把 `WorkloadRebalancer` 扩展成通用 strategy/executor framework。本 proposal 只聚焦一个场景：保留已经 available 的副本，仅重新调度不能工作的部分。

`SafeMigration` 明确不属于 `WorkloadRebalancer` 的职责。因此，当前 proposal 中下面这些内容都应删除：

- migration executor；
- `from` / `to`；
- `stableWindow` 和 in-flight units；
- cancellation 和 rollback；
- migration progress；
- 面向长事务扩展的状态机。

这里必须区分“移出范围”和“问题已解决”。如果将来单独提出 SafeMigration proposal，source preservation、finalizer、durable state、GracefulEviction 复用和并发 ownership 仍然是开放问题。

## 建议的 API

### WorkloadRebalancer 请求

```go
type WorkloadRebalancerSpec struct {
    Workloads []ObjectReference `json:"workloads"`
    Reschedule *RescheduleBehavior `json:"reschedule,omitempty"`
    TTLSecondsAfterFinished *int32 `json:"ttlSecondsAfterFinished,omitempty"`
}

type RescheduleBehavior struct {
    PreserveAvailableReplicas *bool `json:"preserveAvailableReplicas,omitempty"`
}
```

- `spec.reschedule=nil` 表示完整重调度，从而保留现有 WorkloadRebalancer 的默认行为。
- `preserveAvailableReplicas=true` 表示已经 available 的副本位置不动，只重新安排 unavailable 副本。
- `preserveAvailableReplicas` 默认是 `false`，因此未填写时仍是完整重调度。
- 旧 proposal 中 required strategy union 和无类型约束的 `runtime.RawExtension` 参数都会消失。

### Binding 上的调度请求

```go
type ResourceBindingSpec struct {
    Reschedule *Reschedule `json:"reschedule,omitempty"`
    RescheduleTriggeredAt *metav1.Time `json:"rescheduleTriggeredAt,omitempty"` // deprecated
}

type Reschedule struct {
    TriggeredAt metav1.Time `json:"triggeredAt"`
    Behavior *RescheduleBehavior `json:"behavior,omitempty"`
}
```

- 旧字段 `rescheduleTriggeredAt` 继续支持，但标记为 deprecated，并且永远表示完整重调度。
- 新旧请求同时存在时，scheduler 选择时间戳较新的请求。
- WorkloadRebalancer controller 以后只写新的 `spec.reschedule`。
- scheduler 读取行为并继续作为 `spec.clusters` 的唯一写入者，消除旧方案中的 assignment ownership 冲突。

## 这次方向解决了什么

先给结论：它解决的是 API 过度复杂和多写者冲突，没有解决 SafeMigration 本身。

| 问题 | 当前状态 | 通俗解释 |
| --- | --- | --- |
| required `strategy` 会破坏旧 WorkloadRebalancer | 方向已解决 | 新字段可选，不填写仍执行旧的完整重调度。 |
| `RawExtension` 让参数缺少类型约束 | 方向已解决 | 改成一个明确的布尔行为字段。 |
| controller 与 scheduler 都修改 placement | 当前范围内已解决 | controller 只“下单”，scheduler 负责真正分配。 |
| SafeMigration target-first 冲突 | 移出 #7662 | 删除这条流程，不在本 proposal 内修补。 |
| direct deletion、finalizer、cancel、持久化迁移状态 | 移出 #7662 | 单次调度请求不需要长事务机制；未来迁移 proposal 仍需设计。 |

## 仍未解决的技术边界

### 完整重调度与 #5070

维护者把完整重调度定义为“彻底丢弃之前的调度结果”。这为 #5070 提供了较强的产品语义证据：旧的 `schedulerObservingAffinityName` 不应继续把搜索范围限制在后面的顶层 affinity 组。

但是实现边界尚未写清：

- 当前 `rescheduleTriggeredAt` 只让 `pkg/scheduler/core/assignment.go` 进入 Fresh 副本分配模式；
- `pkg/scheduler/scheduler.go` 的外层 `clusterAffinities` 循环仍从 `status.schedulerObservingAffinityName` 开始；
- 新 proposal 必须明确 ResourceBinding 和 ClusterResourceBinding 是否都要忽略或重置这个“书签”。

因此 #5070 目前是“方向部分明确”，还不是“可以按最终 API 开始实现”。

### PreserveAvailableReplicas 的数据合同

“保留 available 副本”听起来简单，但 scheduler 必须知道哪个数字可信。新版 proposal 还需回答：

- available 到底指 `availableReplicas`、`readyReplicas`，还是 resource interpreter 提供的统一值；
- 每个 member cluster 的数据从哪里读取，如何证明它属于当前 workload generation；
- status 缺失、过期或大于 assigned replicas 时怎么办；
- 快照是在写入请求时取得，还是 scheduler 真正执行时取得；
- 支持哪些 workload 和调度策略：Deployment、自定义资源、Divided dynamic/static、Duplicated、多顶层 affinity 和 overflow；
- 一个副本虽然 available，但所在 cluster 已不再满足 policy 时，是否仍必须保留。

### 多个请求如何仲裁和确认

“使用较新的时间戳”只解决了最普通的情况，还没有定义：

- 两个请求时间戳相同但 behavior 不同；
- 只修改 behavior、不更新时间戳；
- 多个 WorkloadRebalancer 同时操作一个 Binding；
- scheduler 完成后，如何证明它应用的是哪一种 behavior。

现有 `lastScheduledTime` 只能表示调度完成时间，不能说明执行了哪个 behavior。当前 WorkloadRebalancer 的 `Successful` 也只代表请求已成功写入，不代表 scheduler 已经完成重调度。

此外，伪代码在 `apps/v1alpha1` 和 `work/v1alpha2` 两层都使用 `RescheduleBehavior`，但这个共享类型最终放在哪个 API package、CRD default/validation marker 如何定义，仍未确定。

## 与原始公司业务目标的关系

收窄后的设计不能完整满足 #7621 最初提出的这些目标：

- 跨集群迁移期间服务不中断；
- target ready 后才清理 source；
- 根据资源池水位自动均衡；
- CPU/内存比例保护；
- 防止工作负载来回振荡。

因此，如果作者接受维护者方向，PR 正文继续写 `Fixes #7621` 会夸大结果。更准确的说法应该是这个 PR 只提供一个重调度 primitive，并让 #7621 的 SafeMigration 和自动均衡目标继续保持开放。

我们已经发布的 `EnsureTarget` review 对当前 head `586f6fc` 仍然成立；但作者删除 SafeMigration 后，它会自然过期。此时不应再要求作者在收窄后的 proposal 内修复 target-first 流程。

## 下一步

不要基于当前 720 行旧 proposal 开始实现。先等作者接受维护者方向并推送精简版，然后只检查：

1. 完整重调度是否明确忽略或重置所有历史调度“书签”；
2. preserve-available 是否有权威、能证明 freshness 的状态来源；
3. scheduler strategy 和 affinity 支持矩阵是否明确；
4. 新旧请求仲裁和执行回执是否确定；
5. PR 是否停止把未交付的 SafeMigration 当作已经 `Fixes #7621`。
