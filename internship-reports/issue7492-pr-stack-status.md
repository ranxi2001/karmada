# #7492 多组件调度 PR 栈状态

> 状态核对：2026-08-21（Asia/Shanghai）。动态 PR / CI 状态以 GitHub 为准；本文只保存后续
> review 和发布仍需要的当前事实，不再维护 rebase、push 或旧 PR body 过程记录。

<a id="stack-overview"></a>

## 先说人话

#7492 当前有 4 个未完成项：让多模板应用进入重调度、按已调度组件估算增量、副本变更失败时阻止新配置下发，
以及扩容超过当前集群容量时不得迁移。它们不是 4 个独立实现：#7835 提供估算规则，#7830 提供 Work 改写能力，
#7841 负责触发、固定当前目标和失败保留。最后一个 bug 项应作为 #7841 的验收条件，不宜再补一个只修改
`IsBindingReplicasChanged` 的独立 quick fix。

#7837、#7833 已合并；#7830、#7835 仍等待实质性 review。#7841 公开 head
`b2b27ad01c79ec8cb355461a674110c59d6fb3bf` 因包含已合并的旧 #7833 commit，当前与 `master` 冲突；本地
test-only 候选仍在公开 head 之上，现阶段不应先推测试栈扩大冲突面。

#7833 在 2026-08-20 收到 `@RainbowMango` 的首条真人 review 建议：把 helper 从
`componentSchedulingResult` 改名为 `buildTargetComponents`。PR head `29474a636` 已按建议改名并 rebase 到
`upstream/master@1c4a0ff70`，聚焦 race test 和全部 scheduler package tests 通过；branch update 和原 thread
内的简短 reply 均已完成。#7833 随后于 `2026-08-20 09:59:35Z` 合并，merge commit 为
`a8ad84cb5288709cc5f6f0e8a5aad0b87a000a31`。合并前 v1.35 E2E 因 Karmada etcd / host control plane 失去响应而失败；
失败 Deployment 不进入本 PR 新增的 `Components > 1` 分支，scheduler 在控制面故障前已成功完成重调度。

本地 test-only 候选 `3bb0a304a` 新增 Flink、Volcano Job、RayCluster 三类 workload 的 4-spec focus 矩阵。
live E2E 实际运行在仅差一处注释的 `d8df11c3d` 上，并已在 Kubernetes v1.36.1 跑通。该测试栈尚未推到
开放 PR；完整功能启用前仍要确认 rollout / admission validation 边界并获得 maintainer review。

```text
master / #7837 API merged
  |-- #7833  scheduler result producer
  |-- #7830  ReviseComponents + Work delivery
  |-- #7835  scale planner
  `-- #7841  integrates the three heads + safe activation residual
```

## 维护者最新任务映射

| Issue 未完成项 | 当前承载 | 代码现状 | 判断 |
| --- | --- | --- | --- |
| 多模板应用进入重调度 | #7841 | `schedulePendingComponentsFor*` 在旧的 `IsBindingReplicasChanged` 之前比较 desired / accepted component result | 已有实现，尚未合入 |
| scale-up 只估增量，scale-down 跳过估算 | #7835 + #7841 | #7835 提供 name-keyed planner；#7841 把 planner 接入 scheduler 入口 | planner 与接线必须一起验收 |
| 重调度失败时不下发新配置 | #7830 + #7841 | #7830 能按 result 改写 Work；#7841 在 pending / no-fit 时保留 accepted result 和现有 Work | #7830 单独不能闭合这个要求 |
| 扩容超过容量时不得迁移 | #7841 | scale 路径只保留当前 target；当前 target no-fit 时返回错误，不 patch 新 result | 应作为 #7841 的 blocking regression case |

这里有两个证据边界：`@mszacillo` 给出的 `GetTotalBindingReplicas` 来自其 v1.17 fork，不能据此认定 upstream
`master` 已复现同一 restart bug；但 `@RainbowMango` 已把“扩容超过容量不得迁移”写进 #7492，目标行为已经明确。
当前 upstream `IsBindingReplicasChanged` 对 component workload 仍会落入标量逻辑，但 `spec.Replicas` 与
`TargetCluster.Replicas` 都是 0，现有 non-empty-cluster 测试期望 `false`。因此不应把 fork 中的 helper 修复
当成 upstream 方案；应验证 #7841 的 component-aware trigger 和 pinned-target 路径。

## 三场景检查与修复边界

本轮只检查普通副本变更的三条路径。以 `taskmanager: 4` 为 accepted result：扩到 6 时 estimator 只能收到
`+2`；当前 target 放不下 `+2` 时不得改投其他集群，也不得改 Binding result 或 Work；降到 2 时不需要
额外容量，scheduler 直接提交包含 `taskmanager: 2` 的完整 result。

| 文件 / 区域 | 允许的改动 | 原因 | 验证 |
| --- | --- | --- | --- |
| `pkg/scheduler/core/` | 仅修复 delta、pinned target、scale-down 分支中的已证实缺陷，或补直接回归 | planner 和 cluster selection 归 scheduler 所有 | focused core tests |
| `pkg/scheduler/` | 仅修复 scale routing、result retention，或补 RB / CRB 对称回归 | scheduler 持久化 accepted result | focused scheduler tests |
| `pkg/controllers/binding/` | 仅修复 pending fence，或补 Work 不变断言 | binding controller 负责 Work delivery | focused binding tests |
| topic branch history | 从当前 `upstream/master` 重建，删除已合并的 #7833 patch | #7841 当前冲突，旧栈不能作为新候选 | range-diff、diff check |

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

四个 package 均通过。这个结果是 focused unit / controller evidence，不等同于当前干净候选已经重新跑过 live
multi-cluster E2E；之前的 v1.36.1 live 结果仍属于旧行为等价 tree。

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
现为 `6a51dcd9c`。没有修改 PR body 或追加评论，也没有把本地 compile/lint 结果写成 live multi-cluster E2E
证据；live E2E、mixed-version rollout、arbitrary-client admission validation 和其他未闭合边界仍按下文记录。

## 当前公开状态

| 层级 | Exact head | 当前职责 | 快照状态 |
| --- | --- | --- | --- |
| [#7837](https://github.com/karmada-io/karmada/pull/7837) | `76589a9d5145`，merge `1dd55a5d57b4` | `TargetCluster.Components` API / conversion / codegen | 已合并；18 checks success |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `4583e06d2050` | `ReviseComponents` capability + Work delivery | Open，非 Draft；2 commits，37 files，17 checks success，Tide pending |
| [#7833](https://github.com/karmada-io/karmada/pull/7833) | `29474a636cfb`，merge `a8ad84cb5288` | scheduler 写完整 component result | 已合并；helper rename 和 reply 已完成；v1.34/v1.36 E2E 通过，合并前 v1.35 因 control-plane failure 红灯 |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `3619c24f6ebc` | component scale planner，不接生产入口 | Open，非 Draft；1 commit，2 files；14 success、3 failure、Tide pending |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `b2b27ad01c79` | trigger、provenance、failure retention、delivery fence | Open，非 Draft；与已合并 #7833 冲突，尚无实质性 human review |

#7833 合并前只有一条不改变行为的 helper 命名建议；其余开放 PR 尚无实质性 human review。当前没有 `/lgtm`、
`/approve` 或设计认可，bot、reviewer request 和 Tide 状态不能写成人类认可。

## #7841 当前五个 commits

| Commit | 对应公开分片 | 说明 |
| --- | --- | --- |
| `014c555f8` | #7833 | scheduler result producer |
| `32d2e45d5` | #7830 commit A | 与公开 `997a594b1` patch-equivalent 的 interpreter capability |
| `db8073d38` | #7830 commit B | 与公开 `4583e06d2` residual patch-equivalent 的 Work delivery |
| `bdcc01b66` | #7835 | 与当前公开 `3619c24f6` patch-equivalent 的 corrected planner |
| `b2b27ad01` | #7841 residual | safe activation protocol；lint 修复 amend 后仍是第五个 commit |

前四个是未合入 `master` 的依赖。对应 PR 合并后 rebase 会自然删除它们；提前 squash 不会减少 diff，只会
破坏 patch-equivalence 和分层 review。

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

公开 `#7841@b2b27ad01c79ec8cb355461a674110c59d6fb3bf` 的 lint、codegen、compile、unit、
CLI/Chart/Operator 三档矩阵、v1.35/v1.36 base E2E 和 DCO 均通过，共 16 个 success。唯一失败是
v1.34 base E2E：`rescheduling_test.go` 的 `BeforeEach` 创建临时 member 时
`kubeadm init` 失败；suite 因 fail-fast 在 232/274 后停止，新增 Flink spec 未执行。Tide 仍等待
`approved` / `lgtm`。

`b2b27ad01` 已通过：

```text
PATH=/root/go/bin:$PATH hack/verify-staticcheck.sh
go test -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
go test -race -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
PATH=/root/go/bin:$PATH make verify
git diff --check b2b27ad01^..b2b27ad01
git show --check --oneline b2b27ad01
```

`9a18960ea` 功能 tree 的本地验证还通过完整 `make test` 和
`go test -count=1 ./test/e2e/suites/base -run '^$'`；后者输出 `[no tests to run]`，只证明 package 可编译。

2026-08-19 的本地 test-only 候选 `3bb0a304a` 位于 `b2b27ad01` 之上，只改 4 个 E2E/fixture 文件
（`+1224/-3`），没有 production-code diff。最终候选通过：

```text
go test -count=1 ./test/e2e/suites/base -run '^$'
/root/go/bin/golangci-lint run ./test/e2e/suites/base/...
git diff --check b2b27ad01..3bb0a304a
git show --check --oneline 3bb0a304a
```

live E2E 在注释修正前的行为等价 tree `d8df11c3d` 上执行。Kubernetes v1.36.1 的 3-member 环境运行
`--focus='\[MultiComponentRescheduling\]'`：FlinkDeployment 134.880s、Volcano Job 72.867s、
RayCluster lifecycle 212.689s、Ray label-eligibility recovery 142.202s，最终
`Ran 4 of 277 Specs in 568.362 seconds`，`4 Passed / 0 Failed`。
完整矩阵、观察窗和未覆盖边界见 [Day 52](day52-issue7492-multi-component-pr-design-defense.md#单版本-live-focus)。
本地没有运行多 Kubernetes 版本或 mixed-version rollout。

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
2. 保留本地干净候选 `rewrite/pr7841-three-scenarios-20260821`，等待 #7830、#7835 的 review 后再决定是否
   更新 #7841；当前不追加 production fix；
3. 把“扩容可容纳、扩容 no-fit、缩容、重启后无变化”作为同一组验收矩阵；其中 no-fit 必须同时证明
   target 不变、accepted result 不变、Work 不变；
4. #7841 公开 head 仍冲突，依赖未收敛前不推 test-only `3bb0a304a`。功能 residual 稳定后，再决定是否把本地 4-spec
   E2E 补到公开 PR；
5. maintainer 仍需确认 accepted-result / source-coherence、`RequiredBy` ownership，以及 admission / rollout
   边界。

<a id="history-and-evidence"></a>

## 证据入口

- [Day 52：多组件调度 PR 设计与答辩](day52-issue7492-multi-component-pr-design-defense.md)
- [Day 49：#7830 ownership 与 stale-input 反例](day49-7830-review.md)
- [Day 44：component scheduling result API 设计](day44-issue7492-component-scheduling-result-api-design.md)
- [Day 46：跨集群重调度状态问题复现](day46-issue7492-mszacillo-state-reproduction.md)
- [Issue #7492](https://github.com/karmada-io/karmada/issues/7492)
