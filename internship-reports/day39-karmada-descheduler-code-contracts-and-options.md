# Day 39：Karmada Descheduler 的任务调度本质、整任务重入队与方案对比

> 纠偏版本：2026-08-04
>
> 代码基线：`upstream/master@a5cf21eacf49373a6ebd57477ac49a52babdde49`
>
> 研究对象：Karmada scheduler、Descheduler、`ResourceBinding`、`ResourceInterpreter`、`GracefulEvictionTask`、ApplicationFailover、WorkloadRebalancer

## 先说人话

### 纠偏后的核心结论

上一版把问题建模成“如何把 Deployment 的副本算法扩展到更多 GVK”，因此过度关注 `readyReplicas`、副本标量和组件向量。这只能解释首版代码怎样工作，不能代表新的 Descheduler 必须继续沿用那套抽象。

这次从调度本质重新开始：

> 对千问、Job、MPIJob 等一次性任务，Karmada 的核心调度对象应当是“一个等待执行的整任务”。scheduler 负责把它从队列分配到一个集群；Descheduler 只在“已经分配、但尚未真正开始，并且当前放置长期不可行”时撤销这次放置，让同一个任务重新入队。一旦任务开始运行或进入终态，Descheduler 不再迁移它。

因此，本期不需要解决：

- 把 leader、worker 等组件分别搬到不同集群；
- 运行中任务 checkpoint、cutover 或 rollback；
- StatefulSet ordinal/PVC 的在线迁移；
- 把任意 workload 的内部结构压成统一副本标量；
- 扩展 `TargetCluster` 保存逐组件分配向量。

真正要解决的是五件事：

1. 把任意任务解释为统一生命周期：`Queued / Assigned / Running / Terminal / Unknown`；
2. 证明它“尚未启动，而且成员 kube-scheduler 长期无法放置”；如果策略只处理资源不足，还要另有结构化 diagnostics 证明具体原因；
3. 在动作前取得由 workload controller 协作的 admission fence，并按 revision 二次确认源任务，再撤销源集群放置，避免观察之后任务刚好启动；
4. 排除源集群、重新触发 scheduler，并用 `Running/Completed` 而不是默认 `Healthy` 确认新目标接管；
5. 持久保存尝试次数、排除历史和冷却时间，避免重启丢状态或任务在集群之间来回跳。

### 一个千问任务的具体例子

假设 `QwenJob/qwen-train-42` 需要 8 张 GPU，策略要求整任务只进入一个成员集群：

1. `ResourceBinding` 进入 scheduler 队列；scheduler 选择 `member-a`。
2. Binding controller 把任务下发到 `member-a`，所以 `Applied=true`。
3. `member-a` 实际只有 4 张可用 GPU，任务一直没有启动，状态持续为 `Pending / Unschedulable`。
4. 超过阈值后，Descheduler 认定“这次放置失败”，而不是认定“任务执行失败”。
5. action controller 用最新 revision 再确认一次，并取得 Operator/admission 层在任务启动前就建立的 fence；若 Operator 不提供这种协作，就只能接受 best-effort 的竞态窗口。事后才设置 Job `spec.suspend` 本身也可能与 Pod 启动竞态，不能冒充原子锁。
6. action controller 调用 `GracefulEvictCluster("member-a", ...)`：从当前放置移除 `member-a`，同时留下源集群排除记录。
7. Binding 更新重新进入 scheduler 队列；`ClusterEviction` 插件阻止本轮再次选择 `member-a`，scheduler 尝试 `member-b`。
8. `member-b` 接收任务并开始运行后，本次重调度结束。若任务很短、观测时已经成功完成，`Terminal + Completed` 也可作为接管成功；`Terminal + Failed` 不能。后续业务运行和对象清理由 Job/Operator/TTL controller 自己负责。

这里没有“搬 3 个 worker”或“把向量改成标量”。迁移单位始终是整个任务。

### “用完即弃用”需要区分两级队列和对象生命周期

你的直觉“Job 就是排队、运行、结束”是对的，但这里其实有两级队列：

1. **Karmada scheduler queue**：排队的是 `ResourceBinding`。scheduler 成功选择成员集群后就 `Forget` 该 queue item，不会把它留到 Job 跑完；
2. **member kube-scheduler queue**：下发后的 Job 创建 Pod，资源不够时是这些 Pod 在成员集群里保持 Pending。

Descheduler 要补的正是两级队列之间的恢复边：Binding 已经从第一级出队并被分配到 `member-a`，但第二级里的 Pod 长期排不上，于是撤销这次 assignment，让 Binding 回到第一级重新选集群。它不是新的任务执行器，也不需要理解 Deployment 的副本算法。

任务运行完成后，Pod 占用的执行资源会释放，Job 进入终态；这是批任务“用完即释放”的本质。但这不等于 Descheduler 必须删除 Kubernetes Job 对象：

- `Job.status` 的 `Complete/Failed` 表示任务进入终态；
- Job 对象是否保留由用户、上层 Operator 或 TTL-after-finished controller 决定；
- Karmada 甚至会从成员集群清除 `.spec.ttlSecondsAfterFinished`，建议在控制面执行 TTL 清理，避免成员集群提前删除后又被 Karmada 重建。

源码证据：[`RemoveJobTTLSeconds`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/resourceinterpreter/default/native/prune/prune.go#L142-L152)。

所以 Descheduler 的完成条件不是“等训练跑完几个小时”，而是“新放置已经被接受并开始运行；或者短任务已经成功完成；或者本轮重放置明确失败”。业务终态还用于把任务排除出后续 Descheduler 候选。scheduler 成功后 `Forget` queue item 的代码在 [`handleErr()/legacyHandleErr()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/scheduler.go#L939-L960)。

## 一、重新定义代码对象：Descheduler 操作的是调度状态，不是 controller 类型

### 1.1 五个必要对象

下面是逻辑模型，不代表必须新增一个大 CRD。当前 API 已经承载了其中大部分信息：

| 逻辑对象 | 需要回答的问题 | 当前 Karmada 对应位置 |
| --- | --- | --- |
| `SchedulingUnit` | 正在调度谁？ | `ResourceBinding.Spec.Resource` 的 GVK、namespace、name、UID |
| `Demand` | 整任务需要多少资源？ | `Replicas/ReplicaRequirements` 或 `Components`，由 `ResourceInterpreter` 提取 |
| `Placement` | 当前被分配到哪里？ | `ResourceBinding.Spec.Clusters` |
| `ExecutionState` | 未启动、运行中还是终态？ | `AggregatedStatusItem.Applied/Health/Status`，但目前缺统一任务生命周期解释 |
| `RetryMemory` | 哪个集群刚失败、何时可重试？ | `GracefulEvictionTasks` 能临时排除源集群；持久化 relocation attempt/cooldown 尚无统一合同。priority queue 的 attempts 只是进程内调度尝试，不能替代它 |

关键抽象是：`ResourceBinding` 才是 Karmada scheduler 排队和放置的单位。Job、MPIJob、QwenJob 只是这个调度单元引用的业务对象类型。

### 1.2 最小生命周期

```text
Queued
  | scheduler selects one cluster
  v
Assigned
  | applied, but not started and infeasible for too long
  +----------------------------------------------+
  | Descheduler revokes placement and requeues   |
  +----------------------------------------------+
  |
  | execution really starts
  v
Running
  | Job / Operator reports completion or failure
  v
Terminal
```

同时存在一个 fail-closed（信息不足就不动作）状态：`Unknown`。

Descheduler 只允许这一条回边：

```text
Assigned + NotStarted + SchedulerUnschedulableBeyondThreshold -> Queued
```

明确禁止自动执行：

- `Running -> Queued`：已经开始的任务不迁移；
- `Terminal -> Queued`：完成或失败后的重试属于任务策略，不属于 Descheduler；
- `Unknown -> Queued`：状态不可信时不猜测；
- `PartiallyRunning -> Queued`：只要任何执行单元已经开始，就按 Running 处理。

### 1.3 标量和组件向量什么时候才重要

它们不是 Descheduler 的通用前置条件，只在另外两类产品需求中重要：

- **部分副本重分配**：例如把 Deployment 在 `member-a` 的 5 个副本中的 2 个搬走；
- **组件跨集群拆分**：例如 leader 留在 `member-a`、workers 分配到 `member-b/c`。

本期千问/Job 路线明确采用“单任务、单目标集群、未启动才重排”，所以资源组件只用于 scheduler 判断哪个集群放得下，不能反过来要求 Descheduler 理解组件迁移。

## 二、源码事实：Karmada scheduler 本来就能调度 Job

### 2.1 scheduler 排队的是 Binding，但有默认和可选两条队列路径

无论启用哪条实现，scheduler 取出的都是 Binding key，而不是 Deployment 或 Job 对象：

- 默认 `PriorityBasedScheduling=false`，走 legacy rate-limiting workqueue；调度失败后调用 `AddRateLimited()`；
- 显式启用 Alpha feature gate 后，才走 priority scheduling queue；这条路径的 `QueuedBindingInfo` 保存 Binding key、priority、首次入队时间和 attempts，无可行集群进入 unschedulable queue，其他失败进入 backoff queue；
- 两条路径都能证明“Binding 事件 -> 入队 -> 调度失败后重试”，但 priority queue 的 attempts 是 scheduler 进程内的一次次调度尝试，不是跨 controller、跨重启的任务迁移历史。

源码证据：

- [`SchedulingQueue` 接口](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/internal/queue/scheduling_queue.go#L55-L70)
- [`QueuedBindingInfo`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/internal/queue/types.go#L23-L42)
- [`scheduleNext()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/scheduler.go#L354-L380)
- [`handleErr()` 和 `legacyHandleErr()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/scheduler.go#L939-L960)
- [`PriorityBasedScheduling` 默认关闭](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/features/features.go#L167-L176)

这说明“任务排队、尝试放置、失败后等待重试”不是需要 Descheduler 重新发明的机制。Descheduler 需要补的是：当 Binding 已经有放置结果，但成员集群中的任务仍未启动时，如何撤销旧结果并再次进入这条队列。

### 2.2 Job 的资源需求和终态已经能被解释

原生 `ResourceInterpreter` 已经支持 Job：

- `jobReplica()` 读取 `spec.parallelism`，并用 `spec.completions` 限制最大并行数；
- `GenerateReplicaRequirements()` 从 Pod template 提取单执行单元资源需求；
- `reflectJobStatus()` 反射 `active/succeeded/failed/conditions/startTime/completionTime`；其中 `startTime` 只是 Job controller 开始处理的时间，`active` 同时包含 Pending 和 Running Pod，二者不能单独证明业务任务已经真正运行；
- `aggregateJobStatus()` 聚合成员集群状态，并在 Job 已完成后停止继续覆盖终态。

源码证据：

- [`jobReplica()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/resourceinterpreter/default/native/replica.go#L94-L116)
- [`reflectJobStatus()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/resourceinterpreter/default/native/reflectstatus.go#L203-L230)
- [`aggregateJobStatus()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/resourceinterpreter/default/native/aggregatestatus.go#L252-L275)
- [Kubernetes `JobStatus` 对 `startTime` 和 `active` 的定义](https://github.com/kubernetes/api/blob/v0.36.2/batch/v1/types.go#L497-L521)

`genericScheduler.Schedule()` 的输入也是通用 `ResourceBindingSpec/Status`，不是 Deployment 对象：[`generic_scheduler.go#L71-L115`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/core/generic_scheduler.go#L71-L115)。

所以更准确的结论是：

> Job 调度已经存在；Job 的 Deschedule/requeue（撤销错误放置并重新入队）没有形成通用闭环。

### 2.3 现有 Descheduler 是一个特定恢复算法，不是 scheduler 的类型上限

当前 Descheduler 只过滤 `Deployment + Dynamic Divided`，再通过 member estimator 统计长期 Unschedulable Pod，最后减少 `TargetCluster.replicas`。

这些代码说明首版功能范围，不应该成为新任务方案必须适配的接口：

- [`supportedGVKs`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/descheduler/core/filter.go#L30-L49)
- [`Deployment -> current ReplicaSet -> Pods`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/estimator/server/replica/replica.go#L42-L97)
- [`clusters[i].replicas` 减法](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/descheduler/descheduler.go#L208-L249)

本报告不再提出“把 Job 适配进这三个旧接口”。新的 whole-workload mode（整任务模式）应拥有独立的 eligibility、observation 和 action 路径。

## 三、历史答案：Deployment-only 是首版纵向切片，不是任务调度的根本限制

### 3.1 能直接证明的事实

| 时间 | 代码/材料 | 能证明什么 |
| --- | --- | --- |
| 2021-09 | [Issue #697](https://github.com/karmada-io/karmada/issues/697)、[KEP-697](https://github.com/karmada-io/karmada/blob/8bbc60d02857c37c730c9caf7d36334a1cd9d7eb/docs/proposals/scheduling/697-descheduler/README.md) | 需求讨论很宽，但完整故事使用 Deployment，聚焦长期 Unschedulable Pod。 |
| 2022-02-23 | [estimator commit `90900309`](https://github.com/karmada-io/karmada/commit/90900309ca594342c7ea74ee9f9f47e6ec45dd75) | 首版 member 观察链只实现 Deployment -> ReplicaSet -> Pod。 |
| 2022-02-24 | [Descheduler commit `85d8a6cc`](https://github.com/karmada-io/karmada/commit/85d8a6ccf4f4f1e2c29ee2e66073e1081397c9f8) | 首版通过减少逐集群副本数修复放置。 |
| 2022-07/08 | [`RemoveCluster`](https://github.com/karmada-io/karmada/commit/dcbf8d2b963dcf4ffd0fd05f8937d74ba8412667)、[`GracefulEvictionTasks`](https://github.com/karmada-io/karmada/commit/89f9c96644975c0822ca782200ec6689b181569c)、[grace-eviction controller](https://github.com/karmada-io/karmada/commit/135efdb4a5d0f013a1de8e6b67347adc2f4b85df) | 首版合入约五个月后，整工作负载移除和优雅清理底座才陆续出现。 |
| 2022-08 | [Binding/Work Health](https://github.com/karmada-io/karmada/commit/c1794bf7e4598dcda3bf6908ec3c7490cc485793)、[health-aware eviction](https://github.com/karmada-io/karmada/commit/e90edb23a53b7c427cea106c27efa1e5fa984bfc) | 新目标健康后清理旧 Work 的反馈闭环开始形成。 |
| 2023-04 | [ApplicationFailover](https://github.com/karmada-io/karmada/commit/d06fe2b5b371d519419ba40ccda25c0db9892d73)、[`ClusterEviction` plugin](https://github.com/karmada-io/karmada/commit/80eab7bcb31e0c45f4dcc24c4d9033f746bcf4ed) | 首版约十四个月后，通用健康检测、源集群排除和整工作负载 failover 才形成可复用路径。 |

### 3.2 不能越界的解释

在已核查的 Issue、KEP、PR 和提交中，没有找到 maintainer 明确说：

- Job 或 CRD 不应该被 Descheduler 支持；
- Deployment 是架构上唯一安全的资源类型；
- 作者因为缺少 GracefulEviction 才选择 Deployment。

因此只能陈述边界，不能补写作者动机：

> 首版提交确实是一条 `Deployment -> ReplicaSet -> Pod -> replica subtraction` 的纵向切片；通用整工作负载移除、源集群排除和状态反馈基础设施是在之后陆续加入的。这个时间线说明今天已经具备重新设计 whole-workload mode 的条件，但不能证明首版作者“为什么”选择 Deployment，也不能把旧 scope 反推成今天的对象模型。

## 四、当前可复用的是动作原语，不是完整任务闭环

![Whole-workload descheduling and requeue flow](day39-karmada-descheduler-code-contract-breaks.png)

- canonical source：[Mermaid](day39-karmada-descheduler-code-contract-breaks.mmd)
- renderer：官方 `@mermaid-js/mermaid-cli 11.16.0`，白色背景 PNG
- 图中绿色接管完成分支是**建议目标行为**，不是当前 graceful-eviction controller 已经实现的 Job 生命周期语义。

### 4.1 可以复用的机械动作链

1. 新 whole-workload mode 读取 `ResourceBinding` 和成员状态，判定当前任务仍未启动且长期不可调度；这一步尚不存在。
2. 决策成立后调用 `binding.Spec.GracefulEvictCluster(source, options)`；helper 可以复用。
3. helper 从 `spec.clusters` 移除源集群，并把它写入 `spec.gracefulEvictionTasks`。
4. Binding spec generation 变化，scheduler informer 重新把 Binding 入队。
5. scheduler 的 `ClusterEviction` filter 拒绝 eviction task 中的源集群。
6. scheduler 选择新目标；Binding controller 创建新 Work。非 `Directly/Immediately` 模式下，旧 Work 暂时仍被视为存在。
7. 当前 graceful-eviction controller 在 scheduler 已观察本代、所有新目标状态 `Healthy` 后清除 task；普通 task（未设置 `SuppressDeletion`）到达 timeout 也会清除。随后 Binding controller 可删除旧 Work。这是现状，不是批任务需要的完成合同。

源码证据：

- [`GracefulEvictCluster()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/apis/work/v1alpha2/binding_types_helper.go#L153-L195)
- [Binding spec 更新重新入队](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/event_handler.go#L183-L218)
- [`ClusterEviction.Filter()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/framework/plugins/clustereviction/cluster_eviction.go#L49-L56)
- [旧 Work 保留规则](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/util/helper/binding.go#L190-L211)
- [eviction task 健康/超时判断](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/gracefuleviction/evictiontask.go#L67-L116)
- [orphan Work 清理](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/binding/binding_controller.go#L109-L165)

### 4.2 为什么不能只写 `RescheduleTriggeredAt`

`RescheduleTriggeredAt` 只让 scheduler 进入 Fresh（完全重算）模式，并不会把当前源集群从候选集移除。因此它可能再次选择同一个资源不足的集群。

`WorkloadRebalancer` 当前就是：找到 Binding，写入 `spec.rescheduleTriggeredAt`，API update 成功后便把该条目标记为 `RebalanceSuccessful`。这个 successful 表示“触发写入成功”，不是“新目标已经接管，更不是任务运行完成”。

源码证据：

- [`RescheduleTriggeredAt` 语义](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/apis/work/v1alpha2/binding_types.go#L151-L159)
- [Fresh 模式](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/core/assignment.go#L114-L122)
- [WorkloadRebalancer 写时间戳并立即记成功](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/workloadrebalancer/workloadrebalancer_controller.go#L189-L239)

所以自动恢复必须使用能排除源集群的 `GracefulEvictCluster` 或等价机制，不能只触发 Fresh。

### 4.3 一个必须修正的健康状态陷阱

整任务迁移动作已经存在，但任务完成语义不能直接照搬：

- `AggregatedStatusItem` 只有 `Applied`、三态 `Health` 和原始 `Status`，没有统一 `Running/Completed`；
- 对没有 `InterpretHealth` hook 的 GVK，`WorkStatusController` 会直接当作 `Healthy`；
- 默认 health handler 列表没有 Job；
- Job 的 `Complete/Failed` 只在 raw/aggregated status 中有专门逻辑。

这意味着：如果对 Job 机械调用现有 GracefulEviction，新 Job 对象刚创建就可能被当成 Healthy，graceful controller 随即清掉 eviction task 和源 Work。它没有证明新任务已经开始，更没有证明终态。

源码证据：

- [`AggregatedStatusItem`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/apis/work/v1alpha2/binding_types.go#L451-L476)
- [缺 health hook 时默认 Healthy](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/status/work_status_controller.go#L393-L410)
- [默认 health handler 列表](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/resourceinterpreter/default/native/healthy.go#L33-L44)

所以本期不仅要新增任务生命周期解释，还必须把它接入 eviction completion；只新增 `InterpretSchedulingState` 而继续沿用当前 `Healthy/timeout` 收尾，仍会误清源任务。

## 五、代码层面的五个真实问题

### B1：统一执行状态，而不是统一 controller 字段

Descheduler 至少需要一个规范化结果：

```go
// 概念接口，名称和 API 形态仍需社区讨论。
type SchedulingState struct {
    Phase              string // Queued, Assigned, Running, Terminal, Unknown
    Reason             string // SchedulerUnschedulable, Admitted, Completed, Failed, ...
    Started            bool
    Relocatable        bool
    ObservedGeneration int64
    TransitionTime     metav1.Time
}
```

核心只消费这个结果，不读取 `readyReplicas`、`active`、`jobId` 或某个 CRD 的私有 condition。

### B2：确认“未启动且不可调度”的证据来源

不同任务暴露的信息不同：

- Kubernetes Job 的 `Complete/Failed` condition 能证明终态，但 `startTime` 只是 Job controller 开始处理的时间，`active` 同时统计 Pending 和 Running Pod；顶层状态不能单独证明执行已经开始，也不直接包含 Pod 的 `PodScheduled=False/Unschedulable`；
- MPIJob、RayJob、QwenJob 等 CRD 可能由 Operator 在顶层 status 暴露 admission、running 和 failure reason；
- 若顶层 status 不提供资源不足原因，member observer 仍需沿 owner/selector 找到 Pod，但它只返回规范化状态，不再返回“应该减多少副本”。

因此 Pod ownership 是一种观察实现成本，不是调度对象的根本抽象。

### B3：把“观察后撤销”做成原子执行协议

本方案要求一个任务同一时刻只有一个有效执行目标，但 `NotStarted` 只是某一时刻的观察。Descheduler 判定之后、更新 Binding 或删除旧 Work 之前，源 Job 可能刚好开始运行，这是一处典型 TOCTOU（检查时与使用时不一致）竞态。

- Placement 必须约束 scheduler 只选择一个集群；
- 多组件 workload 可以把 components 作为整体资源需求参与过滤，但不能复制到多个目标；
- action 必须携带被观察对象的 UID、generation/resourceVersion 或等价 revision，并在撤销 placement 前重新确认；这是必要的陈旧状态检查，但单独校验父 Job revision 封不住子 Pod 独立启动；
- 强保证需要 workload controller/admission 在执行开始前就建立 lock；“任务初始保持 suspended，placement commit 后才 release”可以是 adapter 协议的一种实现，但事后才写 Job `spec.suspend` 仍可能撞上 Pod 启动，不能单独提供原子保证；
- `PurgeMode` 只决定 Work 清理时序，它本身不是 admission fence：直接删除可能中断刚启动的任务，保留两端又可能造成重复执行；
- 如果千问 Operator 没有执行前 admission lock 合同，本方案只能明确提供 best-effort，并承认存在中断或重复执行窗口，不能承诺“Running 绝不迁移”。

当前 multi-component scheduler 已明确“作为整体选择”，但选择多少个集群仍由 Placement 决定：[`pkg/scheduler/core/common.go#L42-L77`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/core/common.go#L42-L77)。

Job API 也明确说明：创建后从 `suspend=false` 改为 `true` 会删除 active Pods，所以它是中断动作而非无损锁：[`batch/v1 JobSpec.suspend`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/vendor/k8s.io/api/batch/v1/types.go#L440-L449)。

### B4：用任务生命周期确认新目标已经接管

当前 graceful-eviction controller 只读取 `Health`；对未设置 `SuppressDeletion` 的普通 task，timeout 会让 `assessSingleTask()` 返回 `nil`，也就是清除 task。它不会读取本报告提出的 `SchedulingState`。因此，方案 A/B 都还需要修改 graceful controller 或新增 relocation action controller，定义独立的 handoff contract：

- 新目标 `Running`，或短任务已经 `Terminal + Completed`：允许清 task，并按策略删除源 Work；
- 新目标 `Terminal + Failed`：不能视为接管成功；
- 新目标 `Unknown`、没有目标或 timeout：保留源/排除记录，或执行显式 rollback，不能沿用当前“超时即清 task”；
- completion 必须校验目标 revision，防止旧 status 为新一轮迁移错误背书。

可复用的是 `GracefulEvictCluster` helper、`ClusterEviction` filter 和 Work 清理机制；现有完成判断需要扩展，而不是原样复用。

### B5：保存失败记忆并保持 Binding 单一写入顺序

`GracefulEvictionTask` 在存在期间能排除源集群；task 清除后，源集群会重新成为候选。若资源条件没有变化，可能出现 `A -> B -> A` 抖动。

需要定义：

- per-workload/per-cluster cooldown；
- 最大 relocation attempts；
- 最近失败原因和时间；
- 谁是 `ResourceBinding.Spec.Clusters/GracefulEvictionTasks` 的动作 owner；
- 与 ApplicationFailover、cluster failover、用户手动重调度并发时的优先级和幂等键。

这些是控制器一致性问题，但仍不要求核心理解 Job 的内部 worker 拓扑。

## 六、多方案对比

四个方案都采用“整任务重新入队”，差别只在状态从哪里来、代码放在哪里。

### 方案 A：逐 GVK 内建生命周期规则

为 Job、MPIJob、QwenJob 等分别实现：

```text
raw status -> Started / Terminal / SchedulerUnschedulable / Relocatable
```

Descheduler core 可以复用 `GracefulEvictCluster` helper 和 `ClusterEviction` filter，但仍要实现 B3 的 fence/二次确认和 B4 的 lifecycle-aware completion。

优点：

- 最快做出 Job 或千问单类型试点；
- 不改 Binding API；
- 行为容易用具体 YAML 和 e2e 证明。

缺点：

- 每增加 GVK 都要发 Karmada core 版本；
- condition 名、generation 和时间逻辑容易散落；
- 不适合作为长期“全部任务”扩展机制。

定位：近期验证方案，不是最终抽象。

### 方案 B：ResourceInterpreter 提供任务调度状态（推荐）

给 `ResourceInterpreter` 增加类似 `InterpretSchedulingState` 的能力，或者扩展现有可配置解释器，使每个 workload 返回规范化生命周期和 relocatable 决策。

控制器职责：

```text
ResourceInterpreter:          解释业务对象 -> SchedulingState
Descheduler:                  阈值、预算、cooldown、是否发起撤销
Relocation action controller: fence/二次确认、排除源、生命周期接管确认、清理
scheduler:                    重新入队、过滤、打分、选择新集群
Job / Operator:               实际运行、admission fence 与业务终态
```

优点：

- 新 GVK 主要增加解释规则，不改 Descheduler 主循环；
- 对象类型差异停留在解释器，不进入 scheduler filter/score；
- 与 Karmada 现有 status reflection、health customization 和 component resource 路线一致；
- 可以明确 fail-closed：未注册规则或返回 Unknown 就不迁移。

缺点：

- 需要设计新 hook 的输入、返回值、版本兼容和 webhook/Lua 能力；
- 仅靠控制面 raw status 未必能知道 Pod 为什么 Pending；
- 需要补 Descheduler 对 `ResourceInterpreter` 的 wiring、RBAC 和 contract test。

定位：推荐的长期主线。

### 方案 C：member Pod observer 作为状态来源

把当前 estimator 从“统计 Deployment 不可调度副本数”改成“观察一个调度单元是否开始、是否被成员 kube-scheduler 长期判定为不可调度”。

概念响应：

```text
NotStarted=true
Unschedulable=true
Reason=SchedulerUnschedulable
ObservedAt=...
```

优点：

- 直接使用 kube-scheduler 的 Pod condition，对“当前无法放置”的证据更直接；
- 顶层 CRD status 不完整时仍可工作；
- 对千问类 Operator 没有良好状态字段的场景有价值。

缺点：

- 必须按 GVK/adapter 证明 owner/selector，不存在真正零配置的任意对象归属；
- 需要 member informer、动态 GVR、RBAC 和 revision 防串线；
- 跨控制面/member 的观测时效和错误处理更复杂。

Kubernetes 稳定的结构化证据是 Pod `PodScheduled=False, Reason=Unschedulable`；CPU/GPU 细节通常位于 `Message`，不是可依赖的稳定 reason。若产品必须区分 `InsufficientGPU`，需要另建结构化 scheduler diagnostics contract，不能直接从现有 condition 声称已经得到。

定位：方案 B 的 fallback observation，不建议单独成为主架构。

### 方案 D：扩展 ApplicationFailover 直接承担未启动任务恢复

现有 ApplicationFailover 已经具备：

- 按 `InterpretHealth` opt-in；
- 在 controller 进程内 map 记录首次观察到 unhealthy 的时间；
- 调用 `GracefulEvictCluster`；
- 更新 Binding 并发出事件。

源码证据：[`bindingFilter()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/applicationfailover/rb_application_failover_controller.go#L219-L242)、[`detectFailure()/evictBinding()`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/applicationfailover/rb_application_failover_controller.go#L89-L164)。

优点：

- 可以复用 tolerance/threshold 的检测模式和 whole-workload action helper；
- 新代码量可能少于改造旧 replica Descheduler；
- 已有 controller-runtime reconcile 和事件模型。

缺点：

- ApplicationFailover 的语义是“已运行应用变得不健康”，本场景是“任务从未被成功 admission”；
- 现有二值 Health 无法表达 Running/Terminal，直接复用会误判 Job；
- `workloadUnhealthyMap` 只保存进程内 first-unhealthy timestamp，controller 重启即丢失，不是 attempts/cooldown/history 的持久合同；
- 现有 filter 还要求 `Failover.Application`、`AggregatedStatus`、`InterpretHealth` 和 `PropagateDeps`，不能当作任意 Job 的通用入口；
- 把 pre-start scheduling recovery 塞进 runtime failover 会模糊组件责任。

源码证据：[`workloadUnhealthyMap`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/applicationfailover/common.go#L34-L85)。

定位：可提取 tolerance 检测模式和 eviction helper；持久重试状态需要另建 owner，不建议直接把本功能改名塞进 ApplicationFailover。

### 方案横向比较

| 方案 | 状态来源 | 新 GVK 成本 | 是否复用动作原语 | 主要风险 | 结论 |
| --- | --- | --- | --- | --- | --- |
| A 逐 GVK 内建 | control-plane raw status | 每类型改 core | 是 | 分支持续增长 | Job/千问试点 |
| B ResourceInterpreter | 可配置生命周期 hook | 主要加规则 | 是 | 新 hook 合同设计 | **推荐主线** |
| C member Pod observer | Pod condition + owner resolver | 每类型需归属规则 | 是 | informer/RBAC/时效 | B 的 fallback |
| D 扩 ApplicationFailover | Health + 进程内计时 | 中 | 是 | 责任边界、二值 Health、重启丢失计时 | 复用模式，不直接合并语义 |

被移出本期的旧方案：

- `TargetCluster` 组件向量重构；
- 运行中任务 delegated checkpoint/cutover；
- 把 Job 适配为 `readyReplicas` 标量；
- 为“任意 GVK”提供默认自动迁移。

这些没有被解决，而是因为“只迁移未启动整任务”的产品边界而不再构成本期前置条件。

## 七、推荐代码路线

### Phase 0：先固定状态和动作边界

必须先区分“eligibility 判定”和“执行期保证”。下面只回答某一快照是否允许发起动作：

```text
Move iff:
  optIn
  && singleTargetPlacement
  && Applied
  && Phase == Assigned
  && Started == false
  && Relocatable == true
  && Reason == SchedulerUnschedulable
  && UnschedulableDuration >= threshold
  && attempt < maxAttempts
  && source not in cooldown

Never move when:
  Running || Terminal || Unknown || PartiallyRunning
```

要把这个判定升级为“运行中的任务不会被误杀或重复”，action 还必须拿 observed revision 做二次确认，并取得在执行开始前就生效的源任务 admission fence。没有 workload controller 协作时只能提供 best-effort 语义。

### Phase 1：用 Kubernetes Job 做最小试点

选择 Job 的原因不是它像 Deployment，而是它最能验证任务队列模型：

- 资源需求和终态已有原生解释；真正 `Started` 仍需 Pod 或 Operator 提供可信证据；
- 任务是有限生命周期；
- Placement 可约束单集群；
- 状态侧仍需补 `NotStarted + SchedulerUnschedulable` 的可靠判定，动作侧还必须完成 B3/B4；
- 能明确测试“当前状态已 Running 就不发起动作”；端到端无误杀保证仍取决于执行前 fence。

试点可先使用方案 A 的内建状态规则，同时复用 `GracefulEvictCluster` helper 和 source exclusion，不复用 replica subtraction。试点必须同时实现 revision 二次确认和 lifecycle-aware completion；否则只证明“能搬”，没有证明“不会误杀或重复”。

### Phase 2：把状态解释提升为方案 B

当 Job 试点的状态矩阵稳定后：

- 抽取 `InterpretSchedulingState`；
- 把 Job 规则迁到内置 interpreter；
- 用一个真实千问/MPIJob CRD 验证可配置规则；
- 对缺 Pod 原因的类型接方案 C observer；
- 未注册、状态陈旧或冲突一律返回 Unknown。

### Phase 3：抽取共用 relocation engine

Descheduler 与 ApplicationFailover 都需要：

- threshold/toleration 的检测模式；
- `GracefulEvictCluster` options；
- source exclusion；
- cooldown/attempt；
- optimistic update 和事件。

应复用库或统一 action helper，但新增持久 relocation status，并保留两个决策 owner：

- Descheduler：pre-start placement infeasible；
- ApplicationFailover：runtime workload unhealthy。

这样保持 scheduler 简单：它只消费 Binding、资源需求、候选集和排除集，不理解 Job 的业务状态。

## 八、为什么千问场景更适合 Descheduler，而不是 WorkloadRebalancer

两者不是“谁都能触发 Fresh，所以任选一个”。它们代表两种入口：

| 维度 | Descheduler 目标语义 | 当前 WorkloadRebalancer |
| --- | --- | --- |
| 谁发起 | 系统持续观察后自动恢复 | 用户显式提交 workload 列表 |
| 触发条件 | Assigned 但 NotStarted，且长期 Unschedulable | 对象被列入 spec |
| 源集群处理 | 必须排除刚失败的源集群 | 只写 `rescheduleTriggeredAt`，源仍可能被选中 |
| 完成判定 | **目标合同**：观察新目标 Running/Completed；当前代码尚需补 | Binding update 成功即记 `RebalanceSuccessful` |
| 运行中保护 | **目标合同**：状态判断 + pre-start fence；revision 只防陈旧观察，无 fence 只能 best-effort | 不负责识别任务是否已开始 |
| 工作模式 | 周期检测、阈值、防抖、自动闭环 | 一次性命令对象 |

千问需要的是“任务被错误放置后自动回队”，而不是“用户再创建一个对象要求完全重算”。因此决策 owner 应在 Descheduler；WorkloadRebalancer 可以保留为人工强制重排入口，但不应承担自动发现和闭环。

## 九、千问场景的范围声明

### 本期支持

- workload 通过 `ResourceBinding` 被 Karmada 调度；
- 整任务只能选择一个成员集群；
- 顶层 status 或 member observer 能证明尚未启动；
- 能证明长期 Pending 的原因是不可调度，而不是镜像、配置、权限或业务初始化错误；
- 未启动任务允许删除并在其他集群重新创建；若要求 exactly-once 级保护，Operator 还必须提供执行前 admission fence，普通事后 suspend 不足以保证；
- 用户显式 opt-in，并配置 threshold、maxAttempts 和 cooldown。

### 本期不支持

- 已经 Running 或部分 Running 的任务；
- 需要 checkpoint 后跨集群续跑的任务；
- 同一任务的组件跨集群拆分；
- 未知 GVK 默认自动迁移；
- 失败 Job 的业务重试策略；
- StatefulSet/PVC 在线迁移。

### 仍需拿真实 YAML 确认

1. 千问实际 GVK 和 Operator；
2. 哪个 status 字段能证明任务尚未启动；
3. 哪个 condition/reason 能证明资源不足；
4. 是否存在部分 Pod 已运行、部分 Pod Pending；
5. Placement 是否严格单集群；
6. 删除未启动对象是否幂等；
7. 新目标开始的可信回执是什么；若短任务直接进入 `Completed`，如何作为成功接管；
8. cooldown 和最大尝试次数如何配置。
9. Operator 是否提供在执行开始前生效的 admission lock；如果没有，业务是否接受 best-effort 的中断或重复窗口。

这些问题影响 adapter 规则，不再改变核心调度抽象。

## 十、验证矩阵

### 单元测试

- `Assigned + NotStarted + SchedulerUnschedulable + threshold reached`：只创建一次 relocation action；
- `Running`、`PartiallyRunning`、`Terminal`、`Unknown`：绝不修改 Binding；
- action revision 与最新对象不一致：取消动作并重新观察；
- source 已在 `GracefulEvictionTasks`：幂等，不重复追加；
- maxAttempts/cooldown 命中：不迁移并给出稳定 reason；
- status generation 陈旧：返回 Unknown；
- 缺 `InterpretSchedulingState`：fail-closed；
- Job Complete/Failed：不重新入队；
- WorkloadRebalancer Fresh 不应被当作 source exclusion。

### 集成和 e2e

- `member-a` 资源不足，未启动 Job 被整体移到 `member-b`；
- `ClusterEviction` 确保本轮不选回 `member-a`；
- 没有任何新目标可行时，任务保持可恢复状态，不因默认 Healthy 误清源；
- 新目标 `Running` 或 `Completed` 后旧 Work 按完成合同清理；新目标 `Failed` 不算接管成功；
- 有 pre-start admission fence：任务不能在观察与动作之间启动；只有 revision、没有 fence：验证并记录 best-effort 的中断/重复窗口，不声称已阻止；
- 无新目标、Unknown 或 timeout 不沿用当前逻辑误清 task；
- controller 重启、API conflict 和重复事件不造成双重任务，attempt/cooldown 不因重启丢失；
- cooldown 到期前不发生 `A -> B -> A`；
- 未启用 opt-in 的 Job/CRD 行为完全不变。

## 十一、汇报时可直接使用的结论

> 第一，Karmada scheduler 本来就能调度 Job：Binding 会进入调度队列，Job 的资源需求和终态也已有解释器。当前缺的是“已经放错集群但尚未启动”时撤销放置并重新入队的闭环，不是让 scheduler 新认识一种 GVK。

> 第二，首版只支持 Deployment 是可以从代码确认的实现范围；通用 GracefulEviction、健康反馈和源集群排除确实在之后五到十四个月才补齐。提交和文档没有直接说明作者动机，所以不把这条时间线写成“为什么选择 Deployment”的唯一因果，只用它证明今天不必继承旧对象模型。

> 第三，千问场景应把整个任务当成 SchedulingUnit：Queued、Assigned、Running、Terminal。Descheduler 只处理 Assigned 但 NotStarted 且长期 Unschedulable 的任务。要真正保证 Running 不被误迁，还要在撤销前做 revision 二次确认，并由 Operator 提供执行前 admission fence；事后 suspend 仍有竞态，没有 fence 时只能承诺 best-effort。

> 第四，推荐先用 Job 内建规则验证，再把任务生命周期提升为 ResourceInterpreter 能力。member Pod observer 只作为缺少顶层状态时的证据来源；ApplicationFailover 只借鉴 threshold 模式和 eviction helper，不把进程内计时误当持久重试状态。

> 第五，标量、组件向量、checkpoint 和运行中迁移不再是本期 blocker。它们只有在产品要求部分副本重分配、组件跨集群拆分或运行中续跑时才重新进入范围。

## 十二、下一步

1. 用真实千问 YAML 填写 `SchedulingState` 映射和单目标 Placement 约束。
2. 为 Job 写一份状态转换测试表，明确 `NotStarted/Running/Terminal/Unknown` 的字段证据。
3. 设计 `InterpretSchedulingState` 的最小接口，不先修改上游 API。
4. 复用 `GracefulEvictCluster` helper 做一个本地 controller-level prototype，同时补 revision/fence 和 lifecycle-aware completion，验证 source exclusion、无目标、timeout 和清理顺序。
5. 将 Day39 HTML 试讲重点放在“任务重新入队”而不是 Deployment 适配。
