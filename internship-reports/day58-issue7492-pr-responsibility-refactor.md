# Day 58：#7492 三个 PR 的职责重构与反面案例

日期：2026-08-27

## 先说人话

今天最重要的结果不是增加了多少代码，而是把 #7492 的三个需求重新放回各自的负责人：`#7830` 只决定“要不要重新进入 scheduler”，`#7835` 只决定“进入后怎么算资源”，`#7841` 只决定“失败时能不能更新 Work”。

具体例子：member cluster 当前运行 `JM=1, TM=4`，用户把 source workload 改成 `JM=1, TM=6`。`TargetCluster.Components` 只是 scheduler 上次接受的 `JM=1, TM=4` 快照。它不是一份要求 binding controller 把 workload 改成 `TM=6` 的 delivery instruction，因为 source 自己已经是 `TM=6`。

Day 49 的材料保留为反面案例，不再修改。它记录了当时如何从已有代码出发，把 `#7830` 扩成 admission validation、`ReviseComponents` interpreter capability 和 component delivery。今天的工作改为从 Issue #7492 的原始需求出发，逐段判断代码归属。

## 三个需求的最终归属

| PR | 唯一职责 | 输入 | 输出 | 明确不负责 |
| --- | --- | --- | --- | --- |
| #7830 | component replica change trigger | desired `spec.components`、accepted `spec.clusters[].components` | 进入现有 `ScaleSchedule` | delta、estimator、Work、admission、interpreter |
| #7835 | rescheduling estimation | desired components、accepted snapshot | scale-up positive delta；scale-down skip | trigger、Binding/Work 更新、失败保护 |
| #7841 | failure-safe propagation | scheduler 是否接受最新 configuration | success 允许 Work 更新；failure 保留旧 Work | trigger、delta、`ReviseComponents` |

前置层保持不变：#7837 定义 `TargetCluster.Components`，#7833 把 scheduler 接受的 component result 持久化到 Binding。

## Day 49 反面案例

### 当时发生了什么

Day 49 的方向先看到 `TargetCluster.Components`，再假设该字段必须驱动 member workload 改写，因此逐步增加：

- `ReviseComponents` API 与 interpreter operation；
- declarative、Lua、webhook 和 built-in Flink 支持；
- binding controller 根据 persisted components 重写 Work；
- CRD、OpenAPI、deepcopy、applyconfiguration 和相关测试；
- admission / v1alpha1 compatibility 设计。

这些代码分别可能有独立价值，但无法回答 #7492 当前三条 scale/rescheduling 需求中的任何一条，所以不应留在这组三个 PR 中。

### 错误方法

1. 先接受现有实现，再用设计解释为什么代码应该保留。
2. 把 accepted scheduling snapshot 误读为 delivery instruction。
3. 为了让 E2E 跑通，同时扩展 scheduler、detector、binding controller、interpreter 和 API。
4. 把 future component splitting、compatibility policy 和当前单集群整体调度混在一起。
5. 只看整栈 diff，没有先区分当前 PR residual diff 与继承代码。

### 可重复的纠偏规则

判断每一段 production code 时先问：它对应 #7492 的哪一条明确需求？如果无法回答，先移出当前 PR。只有现有调用链证明职责不能拆开时，才记录架构冲突和最小替代方案；不能为了让既定方案成立而增加跨组件状态、direct GET、retry、watch 或新 API。

## #7830 已完成的纠偏

公开 PR #7830 已从 37-file `ReviseComponents` / Work delivery diff 重建为 3-file trigger-only diff：

```text
pkg/scheduler/scheduler_test.go
pkg/util/binding.go
pkg/util/binding_test.go
```

唯一 production change 位于 `pkg/util/binding.go`：扩展现有 `IsBindingReplicasChanged`，在 `MultiplePodTemplatesScheduling` 开启、accepted snapshot 可比较时，按 component name 比较 replicas。scale-up 和 scale-down 返回 changed；equal 与 reordered snapshot 不触发；feature gate 关闭和普通单模板 workload 保持旧行为。

公开 head 仍为 `78dfc7a40092eaa08ee480af124d5b2069e0f120`，title 为 `feat: trigger rescheduling on component replica changes`，exact body SHA-256 为 `fe314b53e4594276d447353f9d5684e49e23c1bef471f32fa0e730512e51ba49`。后续核对形成 local candidate `e3e9d4e9f`：增加真实 branch test precondition，并把 comparator 提升为可复用的 `ComponentReplicasEqual(...)(equal, comparable)`。最终 #7830 diff 仍只有同 3 files，统计为 `+277/-8`。

验证通过：

```text
go test -race -count=1 ./pkg/util -run '^TestIsBindingReplicasChanged$'
go test -race -count=1 ./pkg/scheduler -run '^(TestDoScheduleBinding|TestDoScheduleClusterBinding)$'
go test -count=1 ./pkg/util ./pkg/scheduler
```

### 后续核对发现的测试前置条件缺口

#7835 接入 calculation mode 时，给 #7830 的 scheduler test 增加 `ScheduleAlgorithmOption.IsMultiComponentScale` 断言，测试意外失败。原因不是 production trigger 错，而是 #7830 新增的 RB/CRB component cases 没有设置 `PolicyPlacementAnnotation`。`placementChanged` 在 annotation 为空时先返回 true，因此测试实际走的是 placement-change branch，虽然 case 名称写着 `component replicas changed`。

修复方式是在两个 component cases 中写入与当前 `Placement` 等价的 applied placement：

```json
{"replicaScheduling":{"replicaSchedulingType":"Divided"}}
```

修复后 verbose test 日志分别命中：

```text
Reschedule ResourceBinding(default/test-binding-components) as replicas scaled down or scaled up
Reschedule ClusterResourceBinding(test-cluster-binding-components) as replicas scaled down or scaled up
```

branch test follow-up 为 `ae34007df`；复用 comparator 后 local final head 为 `e3e9d4e9f`。验证命令为：

```text
go test -race -count=1 ./pkg/scheduler -run '^(TestDoScheduleBinding|TestDoScheduleClusterBinding)$' -v
go test -race -count=1 ./pkg/util ./pkg/scheduler
```

> 分析：表驱动 case 的名称和最终对象变化只能说明测试“通过了”，不能证明命中了目标 branch。存在 placement、policy、replica、explicit reschedule 等多个前置判断时，测试必须控制更早 predicate，并直接断言传给下游的 mode 或检查可定位的调用证据。

## 发布过程中的教训

force-push 使用 explicit lease，把获准的旧 head `4583e06d2050058d4ff8a3980fe587ea12a48c79` 作为前置条件，避免覆盖并发更新。`gh pr edit` 因 token 缺少与写入无关的 `read:org` GraphQL scope 失败；push 已成功，但 title/body 当时尚未修改。随后使用 GitHub REST `PATCH /repos/karmada-io/karmada/pulls/7830` 发送同一获准内容，并用 remote body SHA-256 与 `cmp` 做逐字验证。

> 分析：命令返回 success 不能替代远端状态校验。force-push、title 和 body 是三个独立状态，必须分别验证 head、title、changed files 和 body bytes。

## #7835 当前核对状态

exact head `3619c24f6ebcd50e5d57e9ffeb90a231953b80bf`，当前 residual diff 只有 `pkg/scheduler/core/estimation.go` 和 `pkg/scheduler/core/estimation_test.go`。旧 patch 可以干净应用到新 #7830；这两个文件从旧 base 到 current `upstream/master` 没有漂移。

### 先说结论

当前 #7835 的算法边界大体正确，但没有任何 production caller。`calculateMultiTemplateAvailableSetsForScale` 只被单元测试调用；如果保持 2-file diff，PR 只是一段不会影响真实 rescheduling 的 dead planner。

实际调用链要求增加一个窄接线：#7830 已经通过 `IsBindingReplicasChanged` 选中 scale branch；#7835 在这个既有 branch 上只传递 `IsMultiComponentScale` calculation mode，让 scheduler core 选择 delta planner。它不增加 component change condition，也不改变 placement / explicit reschedule / failover 的入口。

```text
#7830 IsBindingReplicasChanged == true
        ↓ already decided scale branch
#7835 passes IsMultiComponentScale
        ↓
generic scheduler / calAvailableReplicas
        ↓
scale-up: positive delta estimator request
scale-down: return one available component set before estimator registry loop
```

### 计算边界

- pure scale-up：按 component name 计算 `desired - accepted`，只把正 delta 传给 estimator；保留 desired component 的 `ReplicaRequirements`；
- pure scale-down：不进入 estimator registry；直接返回“one available component set”的 capacity evidence；
- mixed direction：unsupported，estimator 调用数必须为 0；
- existing target 缺少、部分缺少或 name 不可比较的 accepted snapshot：unsupported，不回退 full desired；
- equal snapshot：不是 scale calculation，返回 error，不调用 estimator；
- requirements 与 replicas 同时变化：`TargetCluster.Components` 不保存 accepted requirements，planner 无法证明只有 replicas 变化；本 PR 不新增 hash/API，必须作为未支持边界保留。

### 必须删除的旧 scope

当前 `componentScaleNewCandidate` 和 `fullDesiredClusters` 会对 accepted result 中不存在的 candidate 重新 estimate 完整 desired workload。这条路径应删除：Phase IV scale 针对当前单一 accepted target，scale-up 不应因为新 candidate 可以容纳完整 workload 而迁移；当前 #7841 的 `retainScheduledClusters` 也使这条路径在预期接线中不可达。保留它是在为未来 migration 提前扩 scope。

### `Replicas: 1` 的真实含义

这里的 `1` 表示“至少一个完整 component set 可继续使用当前 target”，不是 workload replica assignment。限定调用链为：

```text
calAvailableReplicas
  -> GroupClustersInfo.AvailableReplicas = 1
  -> component-scale SelectClusters checks AvailableReplicas >= 1
  -> AssignReplicas uses the multi-template branch
  -> TargetCluster{Replicas: 0, Components: desired}
```

因此 sentinel 不会写成真实 workload replicas。#7835 必须保留最终 result 不泄漏 sentinel 的 core regression test。

### 初始接线方案（已否决）

初始方案试图让 #7835 自己激活 planner，因此临时扩展到以下文件。该 experiment 只保留在本地 `d93b0f6f7` 供反例追溯，不会作为 #7835 candidate：

| 文件 | 当时计划的作用 | 复核结论 |
| --- | --- | --- | --- |
| `pkg/scheduler/scheduler.go` | 在 #7830 scale branch 传 mode | mode 激活后遇到 `FitError` 会沿旧逻辑清空 accepted result，不能独立合入 |
| `pkg/scheduler/core/generic_scheduler.go` | pin accepted target | 属于 failure-safe/no-migration orchestration，应与 result retention 同时出现 |
| `pkg/scheduler/core/common.go` / `util.go` | 路由 delta 和 scale-down skip | 单独接线会改变 production failure behavior；应由 #7841 原子调用 #7835 planner |
| 对应 scheduler/core tests | 证明 mode 和 sentinel | 可移到 #7841 integration tests；#7835 只保留 direct calculation tests |

### 实现后复核发现的架构冲突

1. 实际调用链：`IsBindingReplicasChanged -> ScheduleAlgorithmOption -> genericScheduler -> calAvailableReplicas -> planner -> scheduler patch`。planner 自己只返回 capacity 或 error，是否清空旧 result 由外层 scheduler 决定。
2. 冲突位置：#7835 单独激活 mode 后，accepted target 被 filter 或 delta capacity 不足时会返回 `FitError`；当前 scheduler 对 `FitError` 继续 patch `SuggestedClusters=nil`，直接清空旧 `Spec.Clusters`。这正是 #7841 必须阻止的 failure behavior。
3. 无法独立拆开的原因：scale-down skip 必须发生在 estimator registry loop 前，但只要 production routing 生效，就必须同时定义 failure result retention。把 routing 放进 #7835 会让 calculation PR 暂时拥有错误的失败提交语义；把 retention 放进 #7835 又会越过其职责。
4. 最小替代方案：#7835 保留 refined 2-file planner 和 direct tests；#7841 在 failure-safe scheduling wrapper 中设置 calculation mode、调用前置 planner，并在同一条路径上保证 error 不 patch accepted result。#7841 不重复 delta/direction 算法。

另一个未决边界是 component requirements：accepted `TargetCluster.Components` 只有 name/replicas，没有旧 requirements identity。`replicas + requirements` 同时变化时无法证明只估 delta 是安全的。当前 Phase IV 不新增 hash/API；报告必须把它标为不覆盖，不能声称 #7835 验证了 requirements unchanged。

### #7835 最终文件范围

| 文件 | 类型 | 责任 |
| --- | --- | --- |
| `pkg/scheduler/core/estimation.go` | production calculation | single accepted target；positive delta；scale-down skip result；mixed/equal/unknown error；删除 new candidate full estimation |
| `pkg/scheduler/core/estimation_test.go` | direct tests | name-keyed classifier、delta request、scale-down zero estimator call、mixed/missing/equal/new-candidate rejection、estimator error |

明确不改：scheduler trigger/routing、generic scheduler、Binding result patch、detector、binding controller、Work、ResourceInterpreter、API/CRD/OpenAPI/generated files、Flink customization、admission、v1alpha1 compatibility。

### #7835 验证计划

1. focused planner tests：delta、all-components-up、scale-down zero call、mixed/missing/equal/new-candidate zero call、estimator error；
2. `go test -race -count=1 ./pkg/scheduler/core`；
3. `git diff --check` 与 2-file residual diff ownership audit；
4. sentinel 的最终不泄漏由 #7841 integration test 证明，不为此扩大 #7835。

### #7835 本地最终结果

最终 candidate：

```text
base: e3e9d4e9f  (#7830 local final head)
head: e19a318eb  (rewrite/pr7835-estimation-only-20260827)
```

Residual diff：

```text
pkg/scheduler/core/estimation.go
pkg/scheduler/core/estimation_test.go
2 files changed, 403 insertions(+), 6 deletions(-)
```

行为结论：

- scale-up：`JM=1, TM=4 -> JM=1, TM=6` 只向 estimator 发送 `TM=2`；accepted slice 反序测试证明 subtraction 按 name；
- all-components-up：每个 component 只发送各自 positive delta；
- scale-down：返回 `minimumAvailableComponentSets=1`，direct planner test 证明 estimator 调用数为 0；
- mixed、equal、missing/partial snapshot、duplicate/empty/different names、candidate 不等于 accepted target：全部返回 error，estimator 调用数为 0；
- estimator error：原样返回，不回退 full desired。

验证通过：

```text
go test -count=1 ./pkg/scheduler/core -run '^(Test_componentReplicaScaleDirection|Test_calculateMultiTemplateAvailableSetsForScale|Test_calculateMultiTemplateAvailableSetsForScaleRejectsBeforeCallingEstimator)$'
go test -race -count=1 ./pkg/scheduler/core
git diff --check
```

fresh-context final review 未发现 blocker，确认 residual 为 calculation-only 且没有 production caller。公开 #7835 仍为旧 head `3619c24f6`，本轮尚未 force-push 或修改 title/body。

## #7841 当前核对状态

exact head `6a51dcd9cb93d44a08e7363475b6f5f26f656b05`，当前仍是 9-commit、62-file 整栈，累计 `+8037/-209`。它不能直接跟随新 #7830/#7835，必须从新 stack 重建。

### 旧提交归属

| Commit | 当前内容 | 新归属 |
| --- | --- | --- |
| `ec8139036` | 旧 #7830 `ReviseComponents` API，35 files | remove |
| `e127f36f1` | binding controller component rewrite，2 files | remove |
| `f3902ffbb` | 旧 #7835 planner | 用新 #7835 替代，不重复 cherry-pick |
| `294d31eb2` | 25-file production residual，混合 trigger、routing、hash、failure guard、migration/failover | 只提取 failure-safe edges |
| 后 5 commits | 4-file、`+1224/-3` E2E matrix | 只保留精简 Flink scale/no-fit 场景 |

### 实际调用链

```text
detector reads source
  -> Binding.Spec.Components becomes desired replicas
  -> Binding.Spec.Clusters keeps scheduler-accepted snapshot
  -> #7830 enters scale scheduling
  -> #7841 activates #7835 planner
  -> scheduler success or error

binding controller reconcile
  -> FetchResourceTemplate reads current source
  -> ensureWork clones source
  -> CreateOrUpdateWork overwrites Work.Spec.Workload
```

当前 scheduler 对普通 `FitError` 会继续 patch `SuggestedClusters=nil`，清空旧 `Spec.Clusters`。当前 binding controller 会把 fetched source 原样交给 `ensureWork`，因此 source 已是 `TM=6`、accepted snapshot 仍是 `TM=4` 时，Work 可能在 scheduler 接受前被更新。

### #7841 最小 success / failure 合同

Success：

```text
#7835 calculation succeeds
  -> existing AssignReplicas writes complete desired TargetCluster.Components
  -> existing scheduler patch commits accepted snapshot
  -> fetched source replicas equal accepted snapshot
  -> existing ensureWork updates Work from source
```

Failure：

```text
#7835 calculation or target selection fails
  -> component-scale scheduler wrapper returns before main-resource patch
  -> old TargetCluster.Components remains accepted
  -> fetched source replicas differ from accepted snapshot
  -> binding controller returns before ensureWork
  -> old Work remains unchanged
```

### 为什么 planner activation 放在 #7841

#7835 只定义 calculation。production activation 必须与 `FitError` result retention 同时出现，否则 intermediate PR 会清空 accepted result。#7841 可以设置 `ScheduleAlgorithmOption.IsMultiComponentScale`、pin accepted target 并调用 #7835；它不能复制 `positiveComponentDelta` 或 direction classifier。

core routing 还必须 fail closed：mixed/unknown/planner error 或 estimator registry 为空时，component-scale capacity 保持 0，不能回退 multi-template 的 scalar `spec.Replicas`；scale-down 在 registry loop 前直接返回 one available component set。

### Work guard

新增 helper 使用现有 `ResourceInterpreter.GetComponents(fetchedSource)`，再调用 #7830 的 `ComponentReplicasEqual` 与 accepted `clusters[0].components` 比较。只比较 name/replicas，顺序无关；image、labels、annotations 和 requirements-only change 不被冻结。

启用条件：

- `MultiplePodTemplatesScheduling` 开启；
- default scheduler（`schedulerName` 为空或 `default-scheduler`）；
- desired 至少两个 components；
- 恰好一个 target，且 accepted component snapshot 非空。

source interpretation error 返回 error，不继续 Work mutation；changed 或 incomparable replica vector 直接 return，不调用 `ensureWork`。feature gate off、single-template、custom scheduler、missing accepted snapshot 保持旧行为，不在本 PR 引入 compatibility/migration policy。

guard 放在现有 source fetch 后、`ensureWork` 前。orphan cleanup 保持旧顺序：scheduler failure 已保留 accepted target，因此当前 Work 不会成为 orphan；不为 guard 改变 source NotFound 时的既有 cleanup 行为。

### 明确删除的旧协议

- detector full-source hash：证明 detector 看过哪个完整 source，不等于 scheduler 接受了哪个 replica vector；
- requirements hash：把 requirements-only change 纳入新 acceptance protocol，超出 replica-scale scope；
- accepted generation/spec hash、CAS repair、legacy backfill：属于 crash/migration/split-write protocol；
- accepted-target reuse、target taint/label failover、explicit recovery、Ray/Volcano/name/shape matrix：属于 selection/failover 或 future scope；
- `ReviseComponents`：success 时 source 已含新 replicas，failure 时 guard 保留旧 Work。

### 并发边界

若 `TM=6` 已被 scheduler 接受，但 Work 写入前 source 又变成 `TM=8`，guard 能阻止未接受的 `TM=8` 下发，却不能从当前 source 重建已接受的中间版本 `TM=6`。本 PR 的最小保证是“不下发未接受的 component replica vector”，不保证每个中间版本必达，也不因此重新引入 `ReviseComponents` 或 persisted manifest。

### #7841 预定文件范围

| 区域 | 责任 |
| --- | --- |
| `pkg/scheduler/scheduler.go` + tests | component-scale success 沿旧 patch；任何 error 在 main-resource patch 前返回 |
| `pkg/scheduler/core/{generic_scheduler,common,util}.go` + tests | pin accepted target、调用 #7835、scale-down registry skip、planner error capacity=0、sentinel 不泄漏 |
| `pkg/controllers/binding/common.go` + tests | fetched source 与 accepted snapshot comparator/guard |
| RB/CRB binding controller + tests | guard 通过后才 `ensureWork`；pending 时当前 Work 不变 |
| 一个精简 Flink E2E | initial、fit scale-up、scale-down、quota no-fit；no-fit 同时断言 accepted snapshot、Work、member replicas |

明确不改 detector、eventfilter、ResourceInterpreter API、CRD/OpenAPI/generated files、Flink customization、admission 或 v1alpha1 compatibility。新增文件超出该表时先停止更新设计。

### #7841 本地最终结果

```text
base: e19a318eb  (#7835 local final head)
core: 561921ff6
head: c8146e039  (rewrite/pr7841-failure-safe-20260827)
```

Residual diff 为 14 files、`+804/-26`：13 个 scheduler/binding production+unit files，加现有 `schedule_multi_template_test.go` 的精简 Flink workflow。旧 #7841 的 interpreter/API/generated/detector/hash/Ray fixture 均未进入 candidate。

Success path 已由 scheduler RB/CRB tests证明：algorithm 返回完整 desired result 后，现有 patch 更新 `TargetCluster.Components`；controller tests随后把 fetched source 原样写入同一个 Work，不调用 `ReviseComponents`。

Failure path 已由 scheduler + controller tests证明：component-scale `FitError` 不修改旧 `Spec.Clusters`；source `TM=6` 与 accepted `TM=4` 不一致时，同一个 Work 的 `Spec` 保持不变；accepted 更新为 `TM=6` 后，下一轮 reconcile 更新该 Work。普通 non-component `FitError` 仍走旧 cleanup 行为。

额外边界覆盖：

- ordered `ClusterAffinities` 不进入 fallback loop，只对当前 accepted target 调一次 component-scale algorithm；
- custom scheduler 不激活新 scheduler routing，和 Work guard 的旧行为保持一致；
- mixed/unknown/planner error 和 estimator registry 为空时，component-scale capacity 为 0，不回退 scalar `spec.Replicas`；
- scale-down sentinel 只进入 `AvailableReplicas`，final `TargetCluster.Replicas` 保持 0 并写完整 desired Components。

验证结果：

```text
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
PATH=/root/go/bin:$PATH golangci-lint run ./test/e2e/suites/base/...
git diff --check
```

三个 race packages、E2E package compile 和 changed-path lint 均通过。没有运行 live multi-cluster E2E；新增 Flink workflow 只完成 compile/lint，不能写成 live quota/no-fit 已验证。fresh-context final review 对 exact head `c8146e039` 未发现 blocker；remaining risks 为 requirements provenance、live ordered-affinity/CRB coverage 和明确移出的 failover/recovery。

### Upstream update packets

| PR | public head | local head | proposed title | body | visible size | SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| #7830 | `78dfc7a40` | `e3e9d4e9f` | unchanged: `feat: trigger rescheduling on component replica changes` | [current snapshot](day58-pr7830-current-body.md) | 210 words / 16 lines | `fe314b53e4594276d447353f9d5684e49e23c1bef471f32fa0e730512e51ba49` |
| #7835 | `3619c24f6` | `e19a318eb` | `feat: plan component replica scale estimation` | [draft](day58-pr7835-body-draft.md) | 202 words / 16 lines | `2c965c47e9ed17b4f637dc37dbb46db64a96cbd10870fb03087ae6145d265551` |
| #7841 | `6a51dcd9c` | `c8146e039` | `feat: preserve accepted component state on rescheduling failure` | [draft](day58-pr7841-body-draft.md) | 240 words / 16 lines | `71b09b39992fdfb446689aaccea96116cd15ad86e18a39e56b3ba591da5797ac` |

三个 packet 分别请求确认、分别 explicit-lease force-push、分别验证 remote head/title/body bytes；不批量执行。

## 数据流

canonical Mermaid source：[issue7492-pr-responsibility-flow.mmd](issue7492-pr-responsibility-flow.mmd)。

```text
source workload changes
        ↓
#7830 detects component replica change
        ↓
existing scheduler path
        ↓
#7835 estimates positive delta or skips scale-down
        ↓
scheduling success / failure
        ↓
#7841 allows new Work or preserves old Work
```

## 下一步

1. 先请求 #7830 exact packet 确认，只更新 public head `78dfc7a40 -> e3e9d4e9f`，title/body 不变并做 remote byte verification。
2. #7830 验证完成后，再单独请求 #7835 `3619c24f6 -> e19a318eb` 与新 body 确认。
3. #7835 验证完成后，最后请求 #7841 `6a51dcd9c -> c8146e039` 与新 title/body 确认。
4. 只监控 official PR CI；live Flink workflow 由 upstream PR CI 验证，本地 compile/lint 不写成 live 结果。
