# Day 42：#7492 上下文基线与详细 API 等待状态

- 日期：2026-08-10
- 上下文复核时间：2026-08-10T19:38:30+08:00
- 源码基线：[`upstream/master@c884a95908c59a59788c6536fcec798624a09771`](https://github.com/karmada-io/karmada/commit/c884a95908c59a59788c6536fcec798624a09771)
- 当前状态：等待 `RainbowMango` 给出详细 API 和行为合同

## 先说人话

[#7492](https://github.com/karmada-io/karmada/issues/7492) 要补的是 multi-component workload
扩缩容后的重调度能力。当前请求侧能记录每个 component 的最新 replicas，但结果侧只有目标
cluster 和单一 scalar replicas，无法表达“上一次每个 component 调度成功了多少”。因此 Karmada
缺少比较新旧状态、估算增量和约束失败下发的共同基准。

维护者已经指出问题所在，并给出在 `clusters[].components` 中保存 component name/replicas 的
候选方向。这使 result-side per-component information 成为当前最明确的方向，但评论使用的是
“we might need to extend”，没有冻结准确 Go type、升级兼容和失败行为。

当前不继续替维护者补全这些细节。Day 42 只保留任务上下文；
[Day 43](day43-issue5115-evolution-and-7492-implementation-plan.md) 中的 result type、delta、
failure fence 和 legacy 处理都视为待对照假设。详细 API 出现前，不创建源码 worktree，
不修改 Karmada 源码，也不发布旧协调评论。

## 一个具体例子

FlinkDeployment 上一次成功运行的是：

```text
jobmanager=1
taskmanager=10
target=member1
```

用户把 `taskmanager` 改成 20 后，请求侧可以记录：

```yaml
spec:
  components:
  - name: jobmanager
    replicas: 1
  - name: taskmanager
    replicas: 20
  clusters:
  - name: member1
```

问题在于 `clusters` 只说明目标是 `member1`，没有保存“上一次 taskmanager 是 10”。Scheduler
无法从 Binding 中直接计算本次新增了 10 个 replicas，Binding controller 也没有 per-component
result 来判断最新模板是否已经被调度接受。

如果这次重调度失败，issue 明确要求新配置不能传播到 member cluster。详细 API 需要进一步说明：
旧的 10 存在哪里、谁在何时更新它、失败时哪些状态保持不变、下发端如何消费调度结果。

## 什么是 multi-component workload

普通 Deployment 通常只有一个 Pod template。FlinkDeployment、Volcano Job、RayJob、
SparkApplication 等资源可以在一个 CRD 中包含多个 Pod template；Karmada 把每个 template
解释为一个 component，例如 `jobmanager` 和 `taskmanager`。

当前 proposal 和实现把整个 CRD 当成一个完整 component set，选择一个 member cluster 承载
整组组件。#7492 不是把不同 component 拆到不同集群，也不是新增 component-level replica
division；它只处理这个完整 set 在后续 replicas 变化时如何重新调度。

## Issue 原始目标

[#7492 issue body](https://github.com/karmada-io/karmada/issues/7492) 给出三项要求：

1. multi-template application 的 component 变化必须有机会进入 rescheduling。
2. 重调度估算要考虑已调度的 components：scale-up 只考虑增量，scale-down 可以跳过
   replica set estimation。
3. rescheduling 失败时，更新后的配置不能传播到 member cluster。

当前 issue 为 Open，里程碑 v1.19，due 2026-08-31。`ranxi2001` 是唯一 assignee；截至复核时间，
没有发现关联 PR 或公开的同题实现。

## #5115 的四期演进

[#5115](https://github.com/karmada-io/karmada/issues/5115) 是 multi-component scheduling 总主线，
#7492 是 Phase IV，不是独立的新调度模型。

| 阶段 | 已交付 | 留下的边界 |
| --- | --- | --- |
| Phase I / [#6641](https://github.com/karmada-io/karmada/issues/6641)，v1.15 | feature gate、`GetComponents`、`spec.components`、Flink interpreter 和 quota 基础 | 精确 estimator 留到 Phase II |
| Phase II / [#6734](https://github.com/karmada-io/karmada/issues/6734)，v1.16 | full-set estimator、初次 Flink/Volcano placement 和 E2E | 没有 scale/result/failure contract |
| Phase III / [#6998](https://github.com/karmada-io/karmada/issues/6998)，v1.17 | [#7066](https://github.com/karmada-io/karmada/pull/7066) 让 clusters-empty failover 重新进入 Scheduler | 注释明确不能检测 component scale 或 swap |
| Phase IV / [#7492](https://github.com/karmada-io/karmada/issues/7492)，v1.19 | maintainer 给出 per-component target result 的候选方向 | 详细 API、scale estimation 和 failure delivery 待确认 |

前三期已经完成 request modeling、initial scheduling 和 failover 的基础能力。#7492 issue 本身聚焦
component replicas 变化后的 rescheduling、estimation 和 failure delivery。

## #6486 提供的先例

[#6486](https://github.com/karmada-io/karmada/issues/6486) 是 FederatedResourceQuota（FRQ）
Phase II umbrella，不是 #5115 的一个阶段。它包含三项与本任务有关的 scalar precedent：

- [#6474](https://github.com/karmada-io/karmada/pull/6474)：member 下发服从
  `bindingSpec.clusters[].replicas`，不能直接使用最新模板 replicas 绕过 quota。
- [#6477](https://github.com/karmada-io/karmada/pull/6477)：scalar FRQ usage 按实际调度结果计算。
- [#6481](https://github.com/karmada-io/karmada/pull/6481)：Scheduler 提交结果被 quota 拒绝时记录
  `Scheduled=False, reason=QuotaExceeded`。

这些修复说明 scalar workload 已经区分 request 与调度结果，并让下发服从结果。但 #6486 没有
定义 multi-component result API，也没有决定 FRQ 应如何消费未来的新字段。

新增 result 可能影响 quota consumer，因此收到详细 API 后必须重新核对 FRQ；这不等于把
[#6835](https://github.com/karmada-io/karmada/issues/6835)、
[#6836](https://github.com/karmada-io/karmada/issues/6836) 或
[#5130](https://github.com/karmada-io/karmada/issues/5130) 的其他 leftovers 并入 #7492。

## 维护者已经给出的方向

`RainbowMango` 在
[2026-08-07 的评论](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5212258262)
中指出，当前 `TargetCluster` 只有 cluster name 和一个 scalar `Replicas`，无法描述每个
component 的分配。他给出的候选 YAML 是：

```yaml
clusters:
- name: member1
  components:
  - name: jobmanager
    replicas: 1
  - name: taskmanager
    replicas: 20
```

该评论还说明，这份 result 可以为 scale detection 和 delivery-side replica enforcement 提供
依据。当前可以确认的是问题位置和候选数据形状；不能据此宣称具体 Go type、writer、提交时点、
conversion、legacy 和 failure contract 已经批准。

## 线程与 ownership 纠正

1. `mszacillo` 在
   [2026-05-28 的评论](https://github.com/karmada-io/karmada/issues/7492#issuecomment-4567706415)
   中表示愿意 “investigate these scale scenarios”。
2. `RainbowMango` 回复 “go ahead” 并把迭代移到 v1.19；`mszacillo` 后续表示会
   “take a look”。这些措辞支持调研意向，不证明 formal assignment 或正在编码。
3. `RainbowMango` 在 2026-08-07 给出上述候选方向，并邀请 `mszacillo`、`zhzhuang-zju`
   评估 API。
4. `ranxi2001` 在
   [2026-08-10 18:26 的评论](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5238938075)
   中发布 `/assign`，成为当前唯一 assignee。

因此当前没有发现公开重叠实现；等待点是详细 API，而不是已确认的 ownership 冲突。

## 当前源码只确认到哪里

- [`ResourceBindingSpec.Components`](https://github.com/karmada-io/karmada/blob/c884a95908c59a59788c6536fcec798624a09771/pkg/apis/work/v1alpha2/binding_types.go#L89)
  能保存完整 request；[`TargetCluster`](https://github.com/karmada-io/karmada/blob/c884a95908c59a59788c6536fcec798624a09771/pkg/apis/work/v1alpha2/binding_types.go#L286)
  只有 name 和 scalar replicas。
- [`detector.go`](https://github.com/karmada-io/karmada/blob/c884a95908c59a59788c6536fcec798624a09771/pkg/detector/detector.go#L470)
  更新最新 `Spec.Components`，同时保留 `Spec.Clusters`。
- [`IsBindingReplicasChanged`](https://github.com/karmada-io/karmada/blob/c884a95908c59a59788c6536fcec798624a09771/pkg/util/binding.go#L37)
  的注释明确当前临时逻辑不能检测 component scale 或 swap。
- [`ensureWork`](https://github.com/karmada-io/karmada/blob/c884a95908c59a59788c6536fcec798624a09771/pkg/controllers/binding/common.go#L80)
  已让 scalar workload 下发服从 accepted clusters，但 multi-component 还没有对应 result。

更完整的 Scheduler/Binding controller 并发链、estimator 和 served-version 影响保留在 Day 43，
本报告不再提前选择实现方案。

## 等待详细 API 明确

1. 字段的准确位置、Go type，以及 v1alpha1/v1alpha2 conversion。
2. result 表达什么状态、由谁写、在哪个成功点提交。
3. component identity、顺序、nil/empty/zero 和 legacy object 语义。
4. up/down/add/remove/mixed change 的比较和 estimation 规则。
5. 调度失败时 old result、condition 和 Work 的准确合同。
6. Binding controller、FRQ、ResourceBinding/ClusterResourceBinding 是否以及如何消费该 result。

这些是收到详细 API 后的对照清单，不是本报告自行给出的答案。

## 范围、停线与下一步

- 不扩展为 component-level multi-cluster division。
- 不把 resource requirement 或 NodeClaim change 宣称为 replica scale 已解决。
- 不吸收 #6486 的 Scope、ResourceLimit、cache/requeue 等 leftovers。
- 不把 Day 43 的 result-only type、positive delta、current-target continuity 或 Work fence 当成
  maintainer 已确认方案。
- 详细 API 出现前，不创建 #7492 源码 worktree，不修改源码，不发布旧协调评论或 upstream PR。

下一步只做三件事：固定详细 API 的 exact comment/commit/PR ref；逐项对照 Day 43 和 task matrix；
合同收敛后再从最新 canonical master 创建隔离 worktree。

本轮结论来自官方线程和静态源码，没有运行 unit、E2E 或真实 cluster 测试，也没有进行 upstream
写操作。
