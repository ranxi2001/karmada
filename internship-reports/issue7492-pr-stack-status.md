# #7492 多组件调度 PR 栈状态

> 状态核对：2026-08-24（Asia/Shanghai）。动态 PR / CI 状态以 GitHub 为准；本文只保存后续
> review 和发布仍需要的当前事实，不再维护 rebase、push 或旧 PR body 过程记录。

<a id="stack-overview"></a>

## 先说人话

#7492 当前有 4 个未完成项：让多模板应用进入重调度、按已调度组件估算增量、副本变更失败时阻止新配置下发，
以及扩容超过当前集群容量时不得迁移。它们不是 4 个独立实现：#7835 提供估算规则，#7830 提供 Work 改写能力，
#7841 负责触发、固定当前目标和失败保留。最后一个 bug 项应作为 #7841 的验收条件，不宜再补一个只修改
`IsBindingReplicasChanged` 的独立 quick fix。

#7837、#7833 已合并；#7830、#7835 仍等待实质性 review。#7841 公开 head 已更新为
`6a51dcd9cb93d44a08e7363475b6f5f26f656b05`，GitHub 当前判定 `MERGEABLE`，17 个检查成功、无失败，Tide
等待 `approved` / `lgtm`。该 head 已包含四个 production patch 和五个 E2E test patch，不再是此前包含旧
#7833 commit 的冲突版本；当前仍没有 human review 对整体设计作出认可。

```text
master / #7837 API + #7833 result producer merged
  |-- #7830  ReviseComponents + Work delivery
  |-- #7835  scale planner
  `-- #7841  integrates #7830/#7835 + safe activation + E2E
```

## 维护者最新任务映射

| Issue 未完成项 | 当前承载 | 代码现状 | 判断 |
| --- | --- | --- | --- |
| 多模板应用进入重调度 | #7841 | `schedulePendingComponentsFor*` 在旧的 `IsBindingReplicasChanged` 之前比较 desired / accepted component result | 已有实现，尚未合入 |
| scale-up 只估增量，scale-down 跳过估算 | #7835 + #7841 | #7835 提供 name-keyed planner；#7841 把 planner 接入 scheduler 入口 | planner 与接线必须一起验收 |
| 重调度失败时不下发新配置 | #7830 + #7841 | #7830 能按 result 改写 Work；#7841 在 pending / no-fit 时保留 accepted result 和现有 Work | #7830 单独不能闭合这个要求 |
| 扩容超过容量时不得迁移 | #7841 | scale 路径只保留当前 target；当前 target no-fit 时返回错误，不 patch 新 result | 应作为 #7841 的 blocking regression case |

## 最新讨论与实现影响（2026-08-24）

#7492 最后一条实质评论仍是 2026-08-20 的
[`@mszacillo` 说明](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5356519299)。在此之前，
[`@RainbowMango` 只要求确认代码来源](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5355736072)，
因为 upstream `master` 中不存在 `GetTotalBindingReplicas`。`@mszacillo` 随后确认该 helper 是其团队基于
Karmada v1.17 rebase 时加入的兼容代码，并认为这种修改方向不正确。

这段讨论确定了证据边界：fork 中的 helper 会把 component replicas 求和后继续进入 scalar replicas 比较，
但不能据此认定 upstream `master` 存在同一个 restart bug，也没有形成 quick fix 或 backport 共识。当前
upstream `IsBindingReplicasChanged` 在已有 target 时仍会继续执行 scalar 分支，但 `spec.Replicas` 与
`TargetCluster.Replicas` 都是 0，现有 non-empty-cluster 测试期望 `false`。

#7841 没有修改该 helper 来模拟 fork 行为。它在旧 scalar 检查之前用 `schedulePendingComponentsFor*` 比较
desired / accepted component result：equal snapshot 不进入 scale planner；真正的 scale-up/down 才进入
component scale 路径。对于 equal 的 duplicated steady reconcile，`scheduleResourceBindingForSteadyReconcile`
使用 `preserveResult + reuseAcceptedTarget`，在 target 仍满足 placement/filter 时复用 accepted result，不重新估算
相同 footprint；整体 scheduling 返回 no-fit 时也不覆盖 accepted result。target 真正失效后的 failover 是另一条
路径，不能与 scale-up capacity no-fit 混为一谈。这些结论由 current-head 源码与 focused tests 支持；
control-plane restart 后的 live 行为尚未单独执行。

另一个独立结论来自 issue body，而不是 fork helper：扩容超过当前集群容量时不得迁移 multi-template workload。
这仍是 #7841 的 blocking regression case，必须同时验证 target、accepted result 和 Work 不变。

## 三场景检查与修复边界

本轮只检查普通副本变更的三条路径。以 `taskmanager: 4` 为 accepted result：扩到 6 时 estimator 只能收到
`+2`；当前 target 放不下 `+2` 时不得改投其他集群，也不得改 Binding result 或 Work；降到 2 时不需要
额外容量，scheduler 直接提交包含 `taskmanager: 2` 的完整 result。

| 文件 / 区域 | 允许的改动 | 原因 | 验证 |
| --- | --- | --- | --- |
| `pkg/scheduler/core/` | 仅修复 delta、pinned target、scale-down 分支中的已证实缺陷，或补直接回归 | planner 和 cluster selection 归 scheduler 所有 | focused core tests |
| `pkg/scheduler/` | 仅修复 scale routing、result retention，或补 RB / CRB 对称回归 | scheduler 持久化 accepted result | focused scheduler tests |
| `pkg/controllers/binding/` | 仅修复 pending fence，或补 Work 不变断言 | binding controller 负责 Work delivery | focused binding tests |
| topic branch history | 保持 #7833 patch 已删除，后续只在 review 或 base 更新需要时 rebase | #7841 current head 已可合并，不再维护旧冲突栈 | range-diff、diff check |

不改 `TargetCluster.Components` API、detector source snapshot、custom scheduler、自动 target-loss failover、
admission 或 rollout 规则；不增加 direct GET、retry、watch 或跨组件同步。现有源码和 focused tests 若已经证明
某条路径，则不为凑改动而修改 production code。

### 检查结果（2026-08-21）

在当前 `upstream/master`（`a8ad84cb5288`）上重建了本地候选
`rewrite/pr7841-three-scenarios-20260821`：保留 #7830、#7835、#7841 四个 commit，删除已合入 master 的
#7833；`git range-diff` 显示保留的四个 patch 与原 #7841 等价。

三条路径的 focused tests 均通过，未发现需要追加 production fix 的行为缺口：

| 场景 | 代码检查 | 结果 |
| --- | --- | --- |
| scale-up 可容纳 | `calculateMultiTemplateAvailableSetsForScale` 对已有 target 只调用 `positiveComponentDelta`；scheduler 成功后写完整新 component result | 通过；estimator 只收到增量 |
| scale-up 超容量 | `retainScheduledClusters` 过滤掉其他候选；无 fit 时返回 `FitError`，`preserveResult` 阻止 patch；binding controller 的 pending fence 保留旧 Work | 通过；target、accepted result、Work 均不迁移或覆盖 |
| scale-down | `calAvailableReplicas` 在单 target pure scale-down 直接返回内部 capacity sentinel；不进入 estimator，`AssignReplicas` 再写完整 desired result | 通过；estimator 调用数为 0，持久化 `TargetCluster.Replicas` 仍为 0 |

验证命令：

```text
go test -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding ./pkg/util -run '^(Test_calculateMultiTemplateAvailableSetsForScale|Test_runMultiTemplateEstimatorUsesScalePlanner|TestComponentScaleDoesNotMigrateWhenCurrentTargetIsFilterIneligible|TestComponentScaleDownDoesNotLeakAvailabilitySentinelIntoScheduleResult|TestComponentScaleSchedulingPreservesAcceptedResult|TestComponentScaleRouting|TestResourceBindingControllerSyncBindingPreservesWorksWhileComponentResultPending|TestClusterResourceBindingControllerSyncBindingPreservesWorksWhileComponentRequirementsPending|TestShouldWaitForComponentScheduleResult|TestClassifyComponentReplicaTransition|TestIsBindingComponentResultPending|TestIsBindingComponentScaleSupported)$'
```

四个 package 均通过。这是 2026-08-21 branch update 前的 focused unit / controller evidence；current exact head
后来通过 upstream 三个 Kubernetes 版本的 base E2E，见下文当前 CI。

## #7841 branch-update packet（2026-08-21）

在四个功能 patch 之后移植原 test-only 栈 `0ecf16531 -> 0017dd94f -> ad3444697 -> 9dd7af61d ->
3bb0a304a`，形成本地分支 `rewrite/pr7841-update-20260821`，head 为 `6a51dcd9c`。该分支以
`upstream/master@a8ad84cb5288` 为祖先，保留 #7830、#7835、#7841 的四个分层 commit，并新增两个 Ray
fixture、`multi_component_rescheduling_test.go` 和对既有 suite 的测试改动；相对当前 master 为 62 个文件、
`+8037/-209`。

最终 packet 通过：

```text
go test -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding ./pkg/util -run '<focused component-scale and delivery fence tests>'
go test -count=1 ./test/e2e/suites/base -run '^$'
PATH=/root/go/bin:$PATH golangci-lint run ./test/e2e/suites/base/...
git diff --check upstream/master...HEAD
git show --check --oneline HEAD
```

已按确认执行唯一的 upstream-facing 动作：
`git push --force-with-lease origin HEAD:feature/multi-component-failure-safe-rescheduling`，远端 #7841 head
现为 `6a51dcd9c`。当时没有修改 PR body 或追加评论，也没有把本地 compile/lint 写成 live multi-cluster E2E
证据；current exact-head CI 和仍未闭合的 mixed-version / admission 边界按下文记录。

## 当前公开状态

| 层级 | Exact head | 当前职责 | 快照状态 |
| --- | --- | --- | --- |
| [#7837](https://github.com/karmada-io/karmada/pull/7837) | `76589a9d5145`，merge `1dd55a5d57b4` | `TargetCluster.Components` API / conversion / codegen | 已合并；18 checks success |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `4583e06d2050` | `ReviseComponents` capability + Work delivery | Open，非 Draft；2 commits，37 files，17 checks success，Tide pending |
| [#7833](https://github.com/karmada-io/karmada/pull/7833) | `29474a636cfb`，merge `a8ad84cb5288` | scheduler 写完整 component result | 已合并；helper rename 和 reply 已完成；v1.34/v1.36 E2E 通过，合并前 v1.35 因 control-plane failure 红灯 |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `3619c24f6ebc` | component scale planner，不接生产入口 | Open，非 Draft；1 commit，2 files；14 success、3 个已定位环境失败；`/retest` 受 `/ok-to-test` gate 阻塞；Tide pending |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `6a51dcd9cb93` | trigger、provenance、failure retention、delivery fence + E2E | Open，非 Draft；GitHub `MERGEABLE`；17 checks success、Tide pending；尚无实质性 human review |

#7833 合并前只有一条不改变行为的 helper 命名建议；其余开放 PR 尚无实质性 human review。当前没有 `/lgtm`、
`/approve` 或设计认可，bot、reviewer request 和 Tide 状态不能写成人类认可。

## #7841 当前九个 commits

| Commit | 对应公开分片 | 说明 |
| --- | --- | --- |
| `ec8139036` | #7830 commit A | `ReviseComponents` interpreter capability |
| `e127f36f1` | #7830 commit B | component result 到 Work 的 delivery |
| `f3902ffbb` | #7835 | component scale delta planner |
| `294d31eb2` | #7841 production residual | safe activation、failure retention、pinned target |
| `91e8ea27a` | #7841 tests | 扩展 multi-component rescheduling E2E |
| `e7f1aa623` | #7841 tests | quota-discriminating scale E2E |
| `8226fd26f` | #7841 tests | target taint 后的 result recovery |
| `b9460a233` | #7841 tests | label-filtered failover |
| `6a51dcd9c` | #7841 tests | 迁移后的 pinned scale rejection |

前三个是未合入 `master` 的 #7830/#7835 依赖；#7833 已由 base 提供。对应依赖 PR 合并后，rebase 应自然删除
等价 patch；在此之前保持分层 commit，便于分别 review。

## 当前技术合同

### accepted result

- `TargetCluster.Components` 保存 scheduler 接受的 component name / replicas；
- accepted requirements hash 绑定同一次接受的 CPU、memory 等 requirements；
- pure scale-up 只估 positive delta，pure scale-down 不调用 estimator；
- occupied target 的 unknown、equal、mixed、重复或不完整 transition 不回退 full desired；full desired 只用于
  新候选集群。

### source coherence

- detector 从用于 component interpretation 的同一 source 生成 normalized source hash 并写入 Binding；
- binding controller 使用已读取的 source，要求 UID 相同，并接受 exact ResourceVersion 或相同 source hash；
- source hash 保留用户 labels / annotations，去除 status 和明确列举的 API-managed identity fields；
- 这层只证明 source 与 Binding snapshot 一致，不替代 scheduler acceptance。

### Work delivery fence

- pending result 和 source mismatch 都在 orphan Work 删除、`ensureWork()` 和 Work 更新前返回；
- no-fit、requirements change、mixed/name/shape change、planner error 或 invalid result 都保留旧 accepted result
  和现有 Work；
- source desired state 不会回滚，只是未接受的新配置不会提前下发；
- default scheduler 在 suspension 下仍保持已有 component result 的 fence；custom scheduler 不属于该协议；
- feature gate 关闭后，default-scheduler delivery 忽略历史 `TargetCluster.Components`。

### commit 与修复

- scheduler 用 ResourceVersion CAS main patch 同时写 clusters 和 accepted metadata；
- status 是第二次 CAS patch；
- result-generation token 与 scheduling-spec hash 允许 main patch 成功、status patch 失败后的下一轮只修 status；
- `RequiredBy` 只拥有 dependency cluster reachability：inherited-only target 清除 foreign `Components`，同名
  target 以 dependency 自己的 result 为准。

完整设计和答辩解释见 [Day 52](day52-issue7492-multi-component-pr-design-defense.md)。

<a id="validation"></a>

## 验证与当前 CI

#7833 旧公开 head `014c555f898cf575422b65d8c4fbb95e56295cea` 的 compile、lint、codegen、unit、
v1.35/v1.36 E2E 和三组 Kubernetes 测试已通过；v1.34 E2E 在 2026-08-20 核对时仍 pending，Tide 等待
`approved` / `lgtm`。当前 head `29474a636cfbee097f43e6a78c6af3ca64fc67fa` 只把 helper 与调用点
改名为 `buildTargetComponents`，并 rebase 到 `upstream/master@1c4a0ff70`。range-diff 没有其他 patch
变化，以下命令通过：

```text
go test -race ./pkg/scheduler/core
go test ./pkg/scheduler/...
git diff --check upstream/master...HEAD
git range-diff 1819ee7bd..014c555f8 upstream/master..29474a636
```

公开 CI 已在 `29474a636` 上重新运行；旧 head 的结果不计入当前 candidate。

当前 head 的 v1.35 E2E job `96349704810` 在 `resource reschedule when join or unJoin cluster` 中失败。
测试于 `08:03:17` 创建临时 member，scheduler 于 `08:03:39` 把普通 Deployment 成功写为
`[{member-e2e-z9bx7 1 []} {member2 1 []} {member3 1 []} {member1 1 []}]`；该对象没有 components，
因此不会执行本 PR 新增的 `len(spec.Components) > 1` 分支。`08:03:42` 起 etcd 的 linearized read 在
`agreement among raft nodes` 阶段连续超时，Karmada API liveness 随后失败，scheduler 因无法续租退出，
etcd 容器最终以 137 结束；测试等 Ready 满 420 秒后只看到 `172.18.0.2:5443 connection refused`。
同一 SHA 的 v1.34、v1.36 E2E 均已通过。当前证据支持 CI 环境 / control-plane collapse，
不支持修改 #7833 代码；未定位宿主机层面的 CPU、I/O 或 memory 根因，因此不把 exit 137 直接写成 OOM。

### #7835 current-head CI RCA（2026-08-24）

公开 `#7835@3619c24f6ebcd50e5d57e9ffeb90a231953b80bf` 当前有 14 个 success、3 个 failure；
三个红 job 的失败机制彼此独立，但都不支持修改本 PR 的 component scale planner：

1. [CLI v1.35](https://github.com/karmada-io/karmada/actions/runs/32130807490/job/95691311325)：
   Kind 创建 `member3-control-plane` 时，Docker 绑定 `127.0.0.1:45215` 失败，原始错误为
   `Bind for 127.0.0.1:45215 failed: port is already allocated`。测试尚未进入业务断言；同矩阵 v1.34、v1.36 通过。
2. [Operator v1.36](https://github.com/karmada-io/karmada/actions/runs/32130807245/job/95691310186)：
   operator suite 已报告 `SUCCESS! -- 7 Passed | 0 Failed`，随后 `actions/upload-artifact` 才因
   `Failed to CreateArtifact: Unable to make request: ETIMEDOUT` 把 job 标红。这是测试后的 artifact service 网络失败。
3. [Base E2E v1.36](https://github.com/karmada-io/karmada/actions/runs/32130807423/job/95693561431)：
   普通 `Job` 的 binding 在 `11:44:46.295` 已成功调度到 `member1/member2/member3`，随后同一 runner 上的多个
   control plane 失效。Karmada etcd 出现 7 至 37 秒的 linearized read、8.85 秒和 4.18 秒的 `slow fdatasync`；host kubelet
   无法续租，多个 control-plane container 同时退出，containerd 处理 task 时连续
   `context deadline exceeded`，最终 host、Karmada 与 member2 API 均 `connection refused`。失败列表中的
   Job status、其他并行 spec 和清理错误是同一次 control-plane collapse 的连锁结果。

第三项的测试对象是单模板 `batch/v1 Job`；新增 `calculateMultiTemplateAvailableSetsForScale` 在 #7835 中只被
单元测试调用，生产入口由 #7841 负责接入。因此三个失败均可先重跑，不为它们修改 #7835 production code。
现有 artifact 能证明 etcd / container runtime 同时失速，但不能区分 runner 最底层是 CPU、I/O、memory 还是
其他宿主资源故障，不把它进一步写成 OOM。Tide 仍独立等待 `approved` / `lgtm`。

公开 `#7841@6a51dcd9cb93d44a08e7363475b6f5f26f656b05` 的 lint、codegen、compile、unit、DCO、
CLI/Chart/Operator 三档矩阵，以及 Kubernetes v1.34、v1.35、v1.36 三个 base E2E 均通过，共 17 个 success、
0 个 failure。GitHub 当前判定 PR `MERGEABLE`；Tide 只等待 `approved` / `lgtm`，这仍不等同于 human review
已经接受设计。

此前在行为等价 tree 上执行的 Kubernetes v1.36.1 4-spec focused live E2E，以及 current head 的本地
focused/race/compile 证据仍保存在
[Day 52](day52-issue7492-multi-component-pr-design-defense.md#单版本-live-focus)。当前没有 mixed-version rollout；
也没有单独重启 control plane 后验证 no-change reconcile，因此最新 issue 评论中的 restart 场景仍以源码和
focused unit tests 为证据边界。

<a id="risks"></a>

## 未闭合边界

- 当前栈没有 arbitrary-client 的 admission-time component result validation；scheduler/runtime 会验证自身结果，
  但不能声称 webhook 已保护所有直接 API 写入；
- 仅支持 default scheduler、多个 components 和可证明为 exactly-one-cluster 的 placement；
- ordered `ClusterAffinities`、mixed-direction planning、name replacement 不在自动恢复合同；mixed/name
  transition 只能 fail closed 或走受控 explicit recovery，后者已有 Ray live focus；
- label-filter-ineligible target 的 explicit recovery 和迁移后的 pinned scale no-fit 已实测；CRB、自动
  missing/terminating target failover、spread-ineligible fallback 和 full-recovery no-fit 尚无 live 证据；
- 连续快速 scale-up 可能被旧 scheduling assumption 保守阻塞到 TTL / queue retry，但不会覆盖 accepted Work；
- controller-first rollout、feature gate enable 顺序和 admission owner 仍需 maintainer 确认；完整协议落地前保持
  `MultiplePodTemplatesScheduling=false`。

## 下一步

1. 先保持 #7830、#7835 的独立职责，分别拿到 Work delivery 和 delta planner 的 review 结论；
2. #7492 最新讨论只证明 `GetTotalBindingReplicas` 属于外部 v1.17 fork；不为 upstream 添加 quick fix 或
   backport。#7841 保持 component-aware trigger 与 accepted-target retention 方案；
3. 把“扩容可容纳、扩容 no-fit、缩容、重启后无变化”作为同一组验收矩阵；其中 no-fit 必须同时证明
   target 不变、accepted result 不变、Work 不变；
4. #7841 current head 已可合并且 17 个检查成功；当前不再 push 新 patch 或重复 CI，只等待 #7830/#7835 与
   #7841 的 human review。restart/no-change 仍缺 live restart 证据；
5. maintainer 仍需确认 accepted-result / source-coherence、`RequiredBy` ownership，以及 admission / rollout
   边界。

<a id="history-and-evidence"></a>

## 证据入口

- [Day 52：多组件调度 PR 设计与答辩](day52-issue7492-multi-component-pr-design-defense.md)
- [Day 49：#7830 ownership 与 stale-input 反例](day49-7830-review.md)
- [Day 44：component scheduling result API 设计](day44-issue7492-component-scheduling-result-api-design.md)
- [Day 46：跨集群重调度状态问题复现](day46-issue7492-mszacillo-state-reproduction.md)
- [Issue #7492](https://github.com/karmada-io/karmada/issues/7492)
