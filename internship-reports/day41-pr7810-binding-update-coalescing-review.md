# Day 41：PR #7810 Binding 更新合并补丁的代码与系统 Review

日期：2026-08-04

Review 目标：[`karmada-io/karmada#7810`](https://github.com/karmada-io/karmada/pull/7810)

源码基线：`upstream/master@a5cf21eacf49373a6ebd57477ac49a52babdde49`

PR head：`31bef8d37e6505cb333026ec86b00d8ea3172339`

当前结论：问题和作者的本地复现都是真实的，但这个 patch 只能做 **best-effort coalescing（尽力合并）**，不能作为 #7805 的 correctness fix。当前版本还有一个独立的 P1：延迟 key 在 Binding 改为 suspended 或转交另一个 scheduler 后仍可能被旧 scheduler 消费。

## 先说人话

作者碰到的问题可以用两张配置解释：

- Deployment 从 4 副本改成 2 副本；
- PropagationPolicy 权重从 `A:B=1:1` 改成 `1:10000`。

这两张 YAML 是两次 API 请求。Karmada detector 可能先拼出“旧 4 副本 + 新权重”，也可能先拼出“新 2 副本 + 旧权重”，并把这个中间组合写进 `ResourceBinding`。scheduler 如果立刻处理，中间状态就会真的下发到成员集群。

PR #7810 的办法是：第一次看到 `ResourceBinding` spec 更新时，不立即调度，而是等 `D`；到期时再从 informer lister 读取最新版。作者实测 Argo CD 两次 apply 只差约 10ms，配置 2s 后确实能直接读到最终状态。这个实验足以证明“当前环境中能缓解”，但不能证明“系统从此不会调度中间态”。

关键原因有三层：

1. `AddAfter` 从第一次更新开始计时，后续更新不会重置截止时间，所以它不是通常所说的 trailing-edge debounce（最后一次更新后再等完整窗口）。
2. 同一个 key 还会被 cluster change、retry 等路径立即加入队列，这些路径可以绕过等待。
3. 队列只保存 `namespace/name`，不保存 workload generation、policy generation 或 batch ID；时间窗口无法证明两个输入属于同一次变更。

更严重的是，等待期间 Binding 可能已经改由另一个 scheduler 负责，或被设置为暂停调度。当前消费端重新取对象后不再检查这两个条件，旧 scheduler 仍可能修改它。

因此本次 review 的态度不是否定作者的事故和实验，而是：

> 可以讨论一个边界明确的概率优化，但不能用它关闭 #7805，也不能把一个全局 scheduler 参数合并成“看起来只影响 GitOps 两次 apply”的局部改动。

## Findings

### P1：延迟 key 会越过 scheduler ownership 和 suspension 边界

`ResourceBinding` informer 在入队前会检查：

- `spec.schedulerName` 是否属于当前 scheduler；
- `spec.suspension.scheduling` 是否为 false。

证据在 [`resourceBindingEventFilter`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/event_handler.go#L97-L123)。当对象从“通过过滤”变为“不通过过滤”时，client-go 的 `FilteringResourceEventHandler` 会调用 delete handler，而不是 update handler。

但是 [`onResourceBindingDelete`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/event_handler.go#L256-L281) 只清理 scheduler cache 和 assumptions，不会也不能取消 `AddAfter` 已登记的等待项。窗口到期后，[`doScheduleBinding`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/scheduler.go#L423-L496) 虽然重新从 lister 获取当前 Binding，却没有再次检查 `schedulerName` 或 `SchedulingSuspended()`。

一个可达时序是：

1. scheduler A 收到 replicas / placement 更新，登记 `key@t0+D`；
2. 到期前，Policy 把 `schedulerName` 改为 B，或 Binding 被设置为 `SchedulingSuspended=true`；
3. informer 对 scheduler A 触发 delete handler，但等待 key 仍在；
4. 到期后 scheduler A 读取当前 Binding；如果前面的 replicas / placement 仍需处理，它会继续调用 schedule algorithm 并 patch `spec.clusters` / status。

违反的不变量是：

```text
只有当前拥有 Binding 且 Scheduling 未暂停的 scheduler 才能提交调度结果。
```

最小修复不是只在 handler 上继续加条件，而是在 dequeue 后、调用调度算法前重新校验当前对象是否仍属于本 scheduler 且允许调度。对应回归应使用 fake clock 保留一个 delayed key，再改变 ownership / suspension，推进时钟后断言 algorithm 和 patch 都没有执行。

### P1：`AddAfter` 不是 debounce，也不是整个队列的 not-before barrier

PR 只在 [`onResourceBindingUpdate`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/event_handler.go#L203-L226) 的 legacy queue 分支调用 `AddAfter(key, D)`。

client-go 的真实规则是：同一个 key 已经有等待项时，只有新的 `readyAt` 更早才更新；更晚的截止时间直接忽略。证据在 [`insert`](https://github.com/kubernetes/client-go/blob/v0.36.2/util/workqueue/delaying_queue.go#L354-L368)，官方 [`TestDeduping`](https://github.com/kubernetes/client-go/blob/v0.36.2/util/workqueue/delaying_queue_test.go#L72-L124) 也明确验证了这一点。

假设 `D=2s`：

```text
t=0.00s  第一次 RB update -> readyAt=2.00s
t=1.99s  第二次 RB update -> 请求 readyAt=3.99s，但被忽略
t=2.00s  scheduler 出队，只在第二次更新后静默了 10ms
```

因此参数帮助文本中的“wait this long after a ResourceBinding spec update”并不准确。实际语义是“从 burst 中第一次 update 开始保留一个固定窗口”。

而且这个固定窗口只约束一个 producer：

- cluster change 调用 [`onResourceBindingRequeue -> queue.Add`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/event_handler.go#L284-L300)，可以让同 key 立即可运行；
- scheduling error 调用 [`queue.AddRateLimited`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/scheduler.go#L982-L988)，它也和 debounce 使用同一个 delaying queue；
- key 如果已经在 ready queue 或正在 processing，新的 `AddAfter` 不会撤销当前处理。

所以 `D` 不是“该 key 在此时间前绝不执行”的 barrier。要提供这种保证，需要在所有 producer 共享的 per-key state 上维护 not-before，并在 dequeue 时检查；单独改一个 event handler 做不到。

### P1：时间窗口没有建立跨对象一致性，`Fixes #7805` 过度承诺

detector 从 workload informer cache 读取对象，再独立匹配 Policy；随后把 workload 的 replicas / components 和 Policy 的 placement 组装到 Binding，并通过一次 `CreateOrUpdate` 写入。对应证据：

- [`GetUnstructuredObject`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/detector/detector.go#L668-L699)；
- [`ApplyPolicy`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/detector/detector.go#L440-L505)；
- [`BuildResourceBinding`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/detector/detector.go#L821-L863)。

`ResourceBinding` 单次写入是原子的，但输入组合没有共同 revision。PR 没有新增：

- workload generation + policy generation 配对；
- GitOps operation / batch ID；
- prepare / commit / acknowledge；
- “最后一次更新后已经静默 D”的持久证明。

窗口外第二次更新仍会调度中间态。更糟的是，如果第二次更新刚好在第一次截止时间之后到达：

1. `t0+D` 先把中间态调度到成员集群；
2. `t0+D+epsilon` 最终状态进入新的 `AddAfter(D)`；
3. 错误的成员集群分配会比原行为多维持约 `D`，到第二个窗口结束才纠正。

因此作者的 10ms / 2s 实验属于有效的 workload-specific mitigation evidence，不是 correctness proof。PR body 应改为 best-effort，不能用 `Fixes #7805` 自动关闭仍未解决的原子语义问题。

### P2：全局参数延迟的不只是 GitOps replicas / placement

代码只判断 `generation` 是否改变，并没有判断具体字段。因此非零 `D` 会延迟所有 `ResourceBinding.spec` 更新触发的 scheduler 动作。

| 事件来源 | 写入字段 / 入队方式 | 非零 `D` 的实际结果 |
| --- | --- | --- |
| detector workload / Policy reconcile | `replicas`、`components`、`placement` 等 | 被延迟；这是 PR 想覆盖的路径 |
| ApplicationFailover | `GracefulEvictCluster` 同时移除 `spec.clusters` 并新增 task | replacement scheduling 被延迟 |
| taint manager | 同样调用 `GracefulEvictCluster` | cluster failover 补副本被延迟 |
| Descheduler | 下调 `spec.clusters[].replicas` | source 先缩，scheduler 补目标副本等待 `D` |
| WorkloadRebalancer | 更新 `spec.rescheduleTriggeredAt` | 显式重调度被延迟 |
| scheduler 自己提交结果 | patch `spec.clusters` | 后续 generation acknowledgement / no-op reconcile 被延迟 |
| graceful-eviction controller | 清理 `spec.gracefulEvictionTasks` | 清理动作也触发延迟 reconcile |
| MCS / 外部 writer | 任意被当前 scheduler 接受的 RB spec 更新 | 同样进入全局延迟，没有来源隔离 |
| cluster change requeue | `queue.Add(key)` | 不延迟，并可绕过正在等待的窗口 |
| legacy error retry | `AddRateLimited(key)` | 与同 key 的等待项竞争最早截止时间 |
| `PriorityBasedScheduling=true` | `priorityQueue.Push` | 参数完全无效 |
| `ClusterResourceBinding` update | legacy `queue.Add` | 参数完全无效 |

ApplicationFailover 的证据链尤其直接：

1. [`GracefulEvictCluster`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/apis/work/v1alpha2/binding_types_helper.go#L153-L195) 从 `spec.clusters` 删除故障 cluster；
2. [`RBApplicationFailoverController.updateBinding`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/applicationfailover/rb_application_failover_controller.go#L121-L179) 更新 Binding；
3. scheduler 依靠 [`IsBindingReplicasChanged`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/scheduler/scheduler.go#L456-L461) 发现目标副本缺口并补齐。

PR 说“failover stays on the fast path”只对 scheduler 内部的 cluster requeue 成立，对真实 ApplicationFailover / taint eviction 的 Binding spec mutation 不成立。

Descheduler 的影响也很直接：[`updateScheduleResult`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/descheduler/descheduler.go#L208-L249) 先下调旧集群在 `spec.clusters[].replicas` 中的目标副本并更新 Binding；binding controller 会严格按当前 `spec.clusters` 下发，而 scheduler 要等 `D` 才补齐全局副本缺口。也就是说，这个参数会扩大“source 已缩、replacement 尚未选出”的交接窗口，正好影响 Descheduler 最需要守住的容量连续性。

WorkloadRebalancer 也有确定影响：[`triggerReschedule`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/pkg/controllers/workloadrebalancer/workloadrebalancer_controller.go#L189-L239) 写入 `rescheduleTriggeredAt` 后已经会立即标记成功；PR 又让 namespaced RB 的 scheduler 消费额外等待 `D`，而 CRB 路径不等待，进一步放大两条路径的完成语义差异。

scheduler 自己 patch `spec.clusters` 后也会制造新 generation。这个 generation 的后续确认被延迟时，[deploymentreplicassyncer](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/controllers/deploymentreplicassyncer/deployment_replicas_syncer_controller.go#L165-L186) 会继续等待 `generation == SchedulerObservedGeneration`，[graceful-eviction controller](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/controllers/gracefuleviction/rb_graceful_eviction_controller.go#L80-L104) 也把这个等式当作“已经完成调度”的条件。因此 `D` 不只是 scheduler 内部吞吐参数，还会延迟其他 controller 看到的完成回执。

如果社区仍接受一个 best-effort 参数，最小 blast-radius 收敛应只对 detector 负责的 `replicas/components/placement` 变化启用，并明确列出与 failover、explicit reschedule、scheduler result、suspension、scheduler ownership 的优先级规则。

### P2：queue mode、参数校验、生成文档和测试均未闭合

实现还存在六个可直接验证的完成度问题：

1. [`PriorityBasedScheduling`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/pkg/scheduler/event_handler.go#L208-L224) 分支在 debounce 逻辑前直接 `Push`；同一个公开 flag 在不同 feature gate 下语义相反。
2. [`Options.Validate`](https://github.com/karmada-io/karmada/blob/a5cf21eacf49373a6ebd57477ac49a52babdde49/cmd/scheduler/app/options/validation.go#L23-L39) 没有拒绝负数；负值实际静默退化为 disabled，而帮助文本只说 `0` disables。
3. 新 flag 没有写入自动生成的 [`docs/command-line-flags/karmada-scheduler.md`](https://github.com/karmada-io/karmada/blob/31bef8d37e6505cb333026ec86b00d8ea3172339/docs/command-line-flags/karmada-scheduler.md)，upstream `codegen` job 已在 `verify command line flags` 失败。
4. PR 没有新增任何测试；现有 scheduler tests 不会区分 fixed-window、fast-path bypass、stale delayed key 或不同 queue mode。
5. 延迟状态只存在 leader 进程内存。leader 退出后，新 leader 的 informer initial list 会走 add handler，现有 Binding 立即入队，所以同一配置在 leadership turnover 前后不保持等待合同。
6. scheduler 的 schedule latency 从 dequeue 后才开始计时，workqueue queue latency 又要等 delayed timer 真正调用 base `Add` 才开始；现有指标无法看到用户配置的等待时间、实际合并次数或 fast-path bypass。

这些不是核心设计问题的替代品。即使全部修完，时间窗口仍然不等于跨对象事务；但如果要保留这个 feature，它们至少是合并前的基本门槛。

## 运行时序图

这张图把三个容易混在一起的问题放进同一条时间线：后续 `AddAfter` 不延长窗口、立即 producer 可以绕过窗口、等待期间 ownership 改变不会取消旧 key。

- Canonical source：[Mermaid](day41-pr7810-delayed-key-race.mmd)
- 本地 review 以 `.mmd` 为交付，不额外生成 PNG，避免可选渲染挤占代码调研时间
- 图中所有标签为英文，便于后续复用于 upstream discussion

## 为什么作者的实验仍然有价值

作者验证了下面这个受限命题：

```text
legacy queue
+ scheduler 运行稳定
+ 同 key 没有 cluster/retry/add fast path
+ 两次 ResourceBinding update 间隔明显小于 D
=> worker 到期时通常能读到最终 Binding
```

这说明补丁不是“完全无效”，也说明问题不是理论臆测。不能从这个实验推出的是：

- 任意 GitOps / controller backlog 下两次 Binding update 都小于 D；
- D 内不会有第三种 producer 把 key 提前入队；
- 等待期间 scheduler ownership / suspension 不变；
- leader restart 后等待状态仍存在；
- 未命中窗口时系统不会把错误状态维持得更久。

工程上应把“当前 10ms workload 被缓解”与“系统获得一致性保证”明确分开。

## 可选方案对比

### 方案 A：收窄为 best-effort coalescing，作为最小改动继续讨论

建议动作：

- 改名和文档，不再使用暗示 trailing-edge 的 `debounce`；
- 删除 `Fixes #7805`，说明窗口只能降低中间态被物化的概率；
- 只延迟 detector 的 replicas / components / placement 变化；
- dequeue 后重新检查 scheduler ownership 和 suspension；
- 对 priority queue 明确实现或拒绝非零配置；
- 增加 duration validation、生成文档、指标和 fake-clock tests。

优点是改动仍可控制；缺点是不能给用户强一致性承诺。

### 方案 B：实现真正的 trailing-edge per-key debounce

每次相关更新都把 deadline 重置为“最后一次更新 + D”，并让所有 dequeue/requeue 路径尊重同一 not-before。这样至少能保证完整 quiet period，也能避免 client-go earliest-deadline 语义与参数名称不一致。

它仍然只是时间假设：只要下一次更新晚于 quiet period，或 leader restart 丢失内存状态，仍会调度中间组合。因此它比当前 patch 更准确，但仍不能关闭原子性 issue。

### 方案 C：显式 staged barrier 或 revision / batch contract

若目标是确定性地不下发中间态，需要让系统知道“这两次对象修改属于同一次操作”。可选机制包括：

- staged Suspension：先 suspend 并等待 Binding / Work acknowledgement，再修改 workload + Policy，确认最终组合后 resume；
- 单一 desired-operation 对象，携带 workload UID/generation、Policy UID/generation、request ID 和 commit/ack；
- GitOps 侧 prepare / commit protocol。

这类方案复杂，但它解决的是一致性合同，而不是猜测两次请求会相隔多久。

## 建议的测试门槛

### queue 语义

- fake clock：`t0` 第一次 update，`t0+D-epsilon` 第二次 update，明确断言采用 fixed-window 还是 trailing-edge contract；
- delayed key 存在时触发 `queue.Add`，证明 fast path 是否允许提前；
- delayed key 存在时触发 `AddRateLimited`，覆盖更早 / 更晚 deadline；
- key 正在 processing 时再 update，验证是否会在当前 pass 读取中间态。

### ownership 与控制面功能

- delayed 后把 `schedulerName` 从 A 改为 B，A 不得调用 algorithm 或 patch；
- delayed 后设置 `SchedulingSuspended=true`，不得调度；
- ApplicationFailover / taint eviction 更新 RB 后，replacement scheduling 的时延符合公开合同；
- Descheduler 下调 source allocation 时，replacement scheduling 与容量缺口满足明确的时延合同；
- WorkloadRebalancer namespaced RB 与 CRB 行为有明确支持矩阵；
- `PriorityBasedScheduling` 开关两侧不允许同一 flag 静默改变含义。

### 配置与交付

- `--binding-update-debounce < 0` 校验失败；
- 参数默认值和解析测试；
- `hack/update-command-line-flags.sh` 生成文档纳入 diff；
- leader turnover 时明确选择保留、重建或放弃 pending delay，并用测试锁定；
- 指标至少能区分 waiting、coalesced、fast-path bypass 和实际 schedule latency，否则用户无法评估概率收益与故障迁移代价。

## 验证记录

| 检查 | 结果 |
| --- | --- |
| `git diff --check upstream/master...HEAD` | PASS |
| `go test ./pkg/scheduler ./pkg/detector ./pkg/controllers/binding ./cmd/scheduler/app/options` | 首次编译长时间未完成后手动终止，exit 130；没有得到 PASS，也不是 test assertion failure |
| `go test ./util/workqueue -run '^TestDeduping$' -count=1`（client-go v0.36.2 module） | PASS，确认 earliest deadline 去重语义 |
| 本地重复启动的 `go test ./pkg/scheduler ./pkg/scheduler/internal/queue ./cmd/scheduler/app ./cmd/scheduler/app/options` | 与前一命令重复并争用首次编译资源，运行约 15 分钟后手动终止，exit 130；不是 test assertion failure |
| upstream head CI | Kubernetes matrix、lint、DCO 通过；`codegen` 在 `verify command line flags` 失败，compile/unit/e2e 依赖步骤被跳过 |
| PR 新增 regression tests | 0 |

## 社区证据边界

- Issue #7805 作者证明了真实 replica churn，并报告 Argo CD 两次 apply 约相差 10ms；这是事故和局部缓解证据。
- `@RainbowMango` 已指出固定窗口不能保证第二次更新落在窗口内，并建议使用 Suspension；这是 maintainer 对方案保证强度的质疑，不等于 Suspension 已形成完整自动协议。
- 同一 sync wave 的 Suspension + workload update 仍有竞态。可靠 Suspension 需要显式阶段和 acknowledgement barrier。
- 截至本次 review，PR #7810 没有人类 `lgtm` / `approved`，只有 bot review；不能把 bot 意见或作者实验写成社区共识。

## 准备发布的评论

英文 top-level review 已写入：[day41-pr7810-review-comment.md](day41-pr7810-review-comment.md)。

评论只保留三件事：

1. 一个新的 correctness finding：delayed key 越过 ownership / suspension；
2. 一个代码级语义判断：`AddAfter` 是 earliest-deadline fixed window，且会被其他 producer 绕过；
3. 一个具体请求：先降级为 best-effort、增加 dequeue guard、收窄字段范围并补 fake-clock / queue-mode / failover / Descheduler tests。

当前尚未发布。按照 upstream 写入规则，必须先让用户确认 `karmada-io/karmada#7810` 和评论全文。
