# Day 46：#7492 跨集群重调度状态问题复现

- 日期：2026-08-12
- Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- 待核查评论：[`mszacillo` 的状态保留问题](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5254150877)
- 后续回复：[`RainbowMango` 对 Deployment / FlinkDeployment 行为的区分](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5261211769)
- 复现基线：`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`
- 本地验证分支：`verify/issue-7492-mszacillo-state-loss`
- 本地验证提交：`a649fe5c128b387b22fe4af583a810ea6d4193d6`
- 本轮范围：源码级和 controller-level 条件复现；没有发布 upstream comment，没有运行真实 Flink E2E

## 先说人话

结论是：**评论指出的风险机制成立，但评论描述的原始场景还没有被原样复现。**

假设一个 `FlinkDeployment` 当前在 `member1` 运行：

```text
扩容前：jobmanager=1, taskmanager=3 -> member1
扩容后：jobmanager=1, taskmanager=4
```

当前主干的实际行为分成两段：

1. 只修改 `Components` 时，scheduler 不会因为这次扩容重新选集群，而是继续保留 `member1`。
2. 如果随后有另一个触发器让它进入调度周期，例如显式设置 `rescheduleTriggeredAt`，并且容量估算结果是
   `member1=0`、`member2=1`，scheduler 会选择 `member2`。
3. 普通目标集群切换不会自动创建保存运行状态的 `GracefulEvictionTask`，旧 `Work` 上的状态标签也不会
   自动复制到新 `Work`。只有已经携带 `PreservedLabelState` 的 failover task 才会触发标签注入。

因此，不能把现象简化成“用户一扩容，当前主干就自动迁移并丢状态”。更准确的说法是：

> 当前主干的纯多组件扩容缺少重调度触发；一旦另一个触发器让目标集群发生变化，普通重调度路径又没有
> 接入 state preservation（状态保留）协议。这两段逻辑组合后，可能出现评论描述的迁移风险。

本轮没有真实 Flink Operator、共享 checkpoint 存储和恢复结果，所以尚不能把“没有携带状态交接信息”
升级为“已经证明 Flink checkpoint 或业务数据丢失”。

## 拟发布 Comment

以下文本面向 `mszacillo`，当前仅为草稿，尚未发布：

```markdown
Thanks for pointing this out, @mszacillo!

I checked the relevant paths on current `upstream/master` (`1c278577e`). @RainbowMango is right that scaling a multi-template workload alone cannot trigger this today: with `MultiplePodTemplatesScheduling` enabled, a `Components`-only update does not call the scheduling algorithm when the binding already has a target cluster. It only advances `SchedulerObservedGeneration`, so another rescheduling trigger would be needed.

However, if another trigger starts a scheduling cycle, I can reproduce the concern at the controller level. With `member1=0` and `member2=1` available component sets, the single-cluster `Divided/Aggregated` path selects `member2`. This target change does not create a `GracefulEvictionTask`, so no `PreservedLabelState` is passed to the new `Work`. State preservation is currently tied to the failover path rather than ordinary rescheduling.

This does not reproduce Flink state loss end to end: the capacity result was mocked, and no Flink operator or checkpoint recovery was involved.

@mszacillo, could you share the Karmada version or commit, the workload and propagation policy, what triggered the rescheduling, and what state was not conserved (for example, job ID, checkpoint/savepoint, or application data)? That would help us determine whether state preservation belongs in the scale contract or remains an explicit failover behavior.
```

## Comment 在说什么

第一段只做简短回应。#7492 现有讨论普遍先用 `Thanks...`、`Good point!` 或 `No problem!` 建立上下文，
再进入技术内容；这里采用一句 `Thanks for pointing this out`，不附加夸张评价。

第二段接住 `RainbowMango` 最新回复中的判断：对当前主干而言，`FlinkDeployment` 的纯多组件扩容不会
像 Deployment 一样直接进入重调度。这里同时给出我们已经验证的源码边界，不重复解释完整 issue 背景。

三条结果分别回答三个不同问题：

| 问题 | 结果 | 含义 |
| --- | --- | --- |
| 扩容是否直接触发重新选集群？ | 当前主干不会 | `Components` 变化与已有调度结果还无法比较，纯扩容只推进 observed generation |
| 已进入调度周期后，容量不足会不会换集群？ | 在受控容量结果下会 | 单集群 `Divided/Aggregated` 策略会放弃容量为 0 的 `member1`，选择容量为 1 的 `member2` |
| 换集群时是否自动交接状态？ | 普通重调度不会 | `PreservedLabelState` 只在已有 failover task 时注入，普通目标切换没有这个 task |

最后的问题不是让对方重新解释整个 feature，而是补齐原评论缺少的复现条件。最关键的是确认“第二触发器”究竟是
`rescheduleTriggeredAt`、`WorkloadRebalancer`、application failover、旧版本逻辑还是其私有分支；否则我们
无法判断需要修改 scale API、failover API，还是只需明确已有行为边界。

## 运行过程

### 1. 纯 `Components` 扩容

测试显式开启 `MultiplePodTemplatesScheduling`，构造以下条件：

- `ResourceBinding.spec.components` 已更新；
- `spec.clusters=[member1]`；
- Placement 没有变化；
- 没有显式重调度时间；
- 没有 terminating cluster；
- `generation=2`，`schedulerObservedGeneration=1`。

结果：`Algorithm.Schedule` 没有被调用，`spec.clusters` 仍是 `member1`，scheduler 只把
`SchedulerObservedGeneration` 更新到 2。

### 2. 进入调度周期后的容量选择

测试向真实的多组件容量计算和 cluster selection 代码传入：

```text
desired components: jobmanager=1, taskmanager=4
member1 available component sets: 0
member2 available component sets: 1
spread: exactly one cluster
replica scheduling: Divided / Aggregated
```

即使给 `member1` 更高的静态 score，最终仍选择 `member2`。这证明容量结果可以导致目标切换，但不证明
真实 estimator 必然返回这组数值，也不证明扩容会自动进入调度周期。

### 3. 调度结果写回

另一个用例使用同一个 `FlinkDeployment` 多组件 Binding，并通过 `rescheduleTriggeredAt` 显式触发调度。
mock algorithm 返回 `member2` 后：

- Binding 的目标从 `member1` 更新为 `member2`；
- `AggregatedStatus` 中的 `jobId` 仍存在；
- `spec.gracefulEvictionTasks` 仍为空。

这说明“旧状态仍保存在 Binding status”不等于“新目标会使用这份状态”。普通 scheduler path 不会顺便
构造状态交接任务。

### 4. `Work` 切换与状态标签

binding controller 正反两个用例得到：

- 普通目标切换：发出旧 `Work` 的 Delete 请求，再发出新 `Work` 的 Create 请求；新 manifest 没有旧
  `Work` 上的 checkpoint 标签；
- 预填 `PreservedLabelState` 的 `Directly` failover task：新 manifest 得到该标签。

这里验证的是 API 调用顺序和 manifest 变换。fake client 中的旧 `Work` 没有生产 finalizer，因此不能写成
“成员集群工作负载已经彻底删除后才创建新工作负载”，也不能据此推断实际停机窗口。

## 技术证据

### 当前源码边界

- [`IsBindingReplicasChanged`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/util/binding.go#L37-L68)：多组件分支只处理 `clusters` 为空的 failover 场景，明确不检测 component replica changes。
- [`doScheduleBinding`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/scheduler/scheduler.go#L419-L465)：scale、显式重调度和 terminating cluster 是相互独立的触发条件；无触发时只推进 observed generation。
- [`calculateMultiTemplateAvailableSets`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/scheduler/core/estimation.go#L75-L112)：容量请求使用当前完整 `spec.Components`，返回各候选集群可容纳的 component set 数量。
- [`buildTaskOptions`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/controllers/applicationfailover/common.go#L138-L159)：只有 application failover、feature gate 和 `statePreservation` 规则同时成立时，才从 aggregated status 构造 `PreservedLabelState`。
- [`syncBinding`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/controllers/binding/binding_controller.go#L109-L151)：先清理 orphan `Work`，再为当前目标执行 `ensureWork`。
- [`injectReservedLabelState`](https://github.com/karmada-io/karmada/blob/1c278577e7892b6ea44f86a4317c1eb1e013bb93/pkg/controllers/binding/common.go#L203-L235)：只有单目标、存在 task、`PurgeMode=Directly` 等条件满足时才注入保存的标签。

### 本地复现测试

本地提交 `a649fe5c1` 只新增三份测试，没有修改生产代码：

- `pkg/scheduler/issue7492_reproduction_test.go`
- `pkg/scheduler/core/issue7492_reproduction_test.go`
- `pkg/controllers/binding/issue7492_reproduction_test.go`

执行结果：

```text
go test ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding -run 'Issue7492' -count=1 -v
PASS

go test ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding -count=1
PASS

git diff --check
PASS
```

## 未决边界

1. `mszacillo` 没有给出 Karmada version/commit、workload YAML、PropagationPolicy、容量设置、日志和触发器。
2. 评论中的 “state” 没有定义。结合 Flink 场景，它可能指 job ID、checkpoint/savepoint 或业务运行状态，
   但当前只能视为推断。
3. 本机没有可用 kubeconfig/context，未启动 Karmada control plane、两个容量不对称的 member clusters、
   Flink Operator 和共享 checkpoint storage。
4. 容量测试使用 mock estimator；它验证给定响应后的选择逻辑，不验证真实 estimator 响应。
5. scheduler 入口测试假定 Binding generation 由 `Components` 更新产生，没有覆盖 detector 的真实更新链路。
6. failover 正对照直接预填 `PreservedLabelState`；它不证明 application-failover controller 能从该用户的
   Flink status 成功提取状态，也不证明 Flink 能消费标签并恢复。
7. 当前证据不能称为数据丢失 RCA。准确等级是：关键代码边界上的条件性复现。

## 对 #7492 的影响

这个问题需要先确定产品合同，不能由 `TargetCluster.Components` 字段顺带决定：

| 方向 | 行为 | 主要代价 |
| --- | --- | --- |
| 保留原集群 | 扩容后原集群放不下时，不跨集群迁移，也不传播无法承载的新配置 | 扩容会等待或失败，需要明确旧配置是否继续运行 |
| 显式状态迁移 | 允许换集群，但只有配置了 state preservation 并完成交接时才迁移 | API、controller 和 workload interpreter 需要新增合同与失败处理 |
| 普通无状态迁移 | 继续允许目标切换，不保证运行时状态 | 对无状态 workload 简单，但必须让用户明确知道 stateful workload 的风险 |

当前 feature branch 中“优先保留已调度集群”的实验方向接近第一种方案。它能避免普通扩容直接跨集群迁移，
但这是 API/行为选择，不是 `Components` 结果字段自然推导出的唯一答案。

## 下一步

1. 用户确认上面的 exact English comment 后，再回复 #7492；发布前不修改技术强度。
2. 拿到 `mszacillo` 的版本、YAML、触发器和 state 定义后，决定复现路径。
3. 若其场景确为 Flink checkpoint 恢复，搭建 Flink Operator + shared checkpoint storage + 两个容量不对称
   member clusters，分别验证纯 scale、显式 reschedule 和 application failover。
4. 在 #7492 的 scale API 设计中明确选择“保留原集群”“显式状态迁移”或“普通无状态迁移”，不要让行为
   由现有 controller 的偶然组合决定。
