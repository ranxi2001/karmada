# Day 59：#7492 Phase IV 三 PR 重构收尾

日期：2026-08-27

状态核对时间：2026-08-27 21:56（Asia/Shanghai）

## 先说人话

#7492 的三个 PR 已经按“触发、计算、失败保护”重新发布，旧的 `ReviseComponents` / component delivery 大包没有保留。当前工作已从“继续改设计”转为“等待 official CI 和 human review”。

还不能把任务写成完全结束：#7841 旧 head `c8146e039` 的 official lint 发现 `calAvailableReplicas` cyclomatic complexity 为 17，超过阈值 15。修复已经以 signed-off follow-up `2b567c5a5` 发布；本地 core lint、完整 race tests 和 E2E compile 均通过，current-head official `lint` 与 `codegen` 也已通过，其余 jobs 仍在运行。

具体例子仍是：accepted `JM=1, TM=4`，source 改为 `JM=1, TM=6`。#7830 只触发 scheduler，#7835 只计算 `TM=+2`，#7841 只在 scheduler 接受后更新 Work；无法容纳时 accepted snapshot 与旧 Work 都保持 `TM=4`。

## 最终 PR 职责

| PR | Public head | 唯一职责 | Residual diff | Public stacked diff |
| --- | --- | --- | --- | --- |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `e3e9d4e9f` | component replicas changed → trigger rescheduling | 3 files，`+277/-8` | 同 residual |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `e19a318eb` | positive delta / scale-down skip calculation | 2 files，`+403/-6` | 5 files，`+680/-14` |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `2b567c5a5` | failure-safe accepted-result commit 与 Work guard | 14 files，`+816/-33` | 18 files，`+1496/-47` |

三个 remote head、title、changed-file surface 和 body bytes/SHA-256 已逐项验证。PR 仍为 Open / blocked on CI and review，没有 external human review，也没有 `/lgtm` 或 `/approve`。

## 分 PR 答辩口径

### #7830：触发重新调度

#7830 的核心目的是让 multi-template workload 在 component replicas 改变时重新进入现有 scheduler，因为这类 workload 的 scalar `spec.replicas` 为 0，旧的副本变化判断无法感知 `TM=4 -> 6`。它不新增 CRD 或 interpreter 接口，而是复用 #7837 定义、#7833 持久化的数据边界：desired `ResourceBindingSpec.Components` 与 accepted `ResourceBindingSpec.Clusters[0].Components`；实现上扩展现有 `IsBindingReplicasChanged`，并提供按 component name 比较的 `ComponentReplicasEqual`，只有 feature gate 开启、accepted snapshot 可比较且副本确实不同时才沿既有 `ScaleSchedule` 路径触发重调度，equal、普通单模板和不可比较状态保持旧行为。这个 PR 到“要不要重新调度”为止，不计算 delta，也不碰 Work。

### #7835：计算重新调度所需容量

#7835 的核心目的是在 component scale 已经被判定后给出不会 double count 的容量计算，而不是决定何时调度或如何提交结果。它没有增加对外 API，只在 scheduler core 内提供 `calculateMultiTemplateAvailableSetsForScale(ctx, multiTemplateEstimationContext)`：以 desired `spec.Components`、accepted `spec.Clusters[0].Components` 和唯一 accepted target 为输入，按 name 判断方向；纯扩容构造 positive delta 后通过现有 `ReplicaEstimator.MaxAvailableComponentSets` 估算，纯缩容直接返回 `minimumAvailableComponentSets` 这一内部容量证据并跳过 estimator，mixed、equal、snapshot 缺失/不完整以及 new candidate 都显式报错，绝不 fallback 到 full desired estimation。该 PR 有意不接 production caller，因为单独激活后，旧 scheduler 会在 `FitError` 时清空 accepted result；#7841 必须把 planner activation 与 failure retention 一起接入，最终完整 component assignment 仍由既有 scheduler result 流程生成。

### #7841：失败时保留已接受状态

#7841 的核心目的是把“新配置是否被 scheduler 接受”变成 Work 更新的门槛：成功时提交新 accepted snapshot 并允许最新 source 下发，失败时保留旧 snapshot 和旧 Work。接口设计只增加内部调度选项 `ScheduleAlgorithmOption.IsMultiComponentScale`，用它固定当前 accepted target、调用 #7835 planner，并让任何 component-scale error 在现有 `Spec.Clusters` result patch 前返回；交付侧在 source fetch 与既有 `ensureWork` 之间调用 `shouldWaitForComponentScheduleResult`，通过现有只读接口 `ResourceInterpreter.GetComponents` 提取 source replicas，再用 #7830 的 `ComponentReplicasEqual` 对照 accepted `TargetCluster.Components`，相等才继续更新 Work，不相等或不可比较就等待。source 本身已经包含新 replicas，所以这里不需要 `ReviseComponents`、workload rewrite 或新的 interpreter API。

## 实际代码数据流

```text
source workload replicas change
        ↓
detector updates Binding.Spec.Components
        ↓
#7830: IsBindingReplicasChanged
        ↓ component ScaleSchedule
#7841 routing calls #7835 planner on accepted target
        ↓
#7835: positive delta / scale-down skip / unsupported fail closed
        ↓
success                       failure
  ↓                              ↓
patch complete accepted result   return before Spec.Clusters patch
  ↓                              ↓
source replicas == accepted      source replicas != accepted
  ↓                              ↓
ensureWork updates Work          binding controller keeps old Work
```

> 注释：#7835 保持 calculation-only，没有 production caller。production activation 必须与 #7841 的 failure result retention 同时出现，否则 intermediate PR 遇到 `FitError` 会清空 accepted result。#7841 只调用 #7835，不复制 delta 算法。

## #7830 收尾

Production 只修改 `pkg/util/binding.go`：

- `IsBindingReplicasChanged` 使用 desired `spec.components` 与 accepted `clusters[0].components`；
- `ComponentReplicasEqual` 返回 `equal/comparable`，供 #7841 Work guard 复用；
- scale-up / scale-down changed，equal/reordered no-change，missing/incomparable 保持旧 trigger 行为。

测试前置条件也已纠正：component cases 设置与当前 Placement 相等的 `PolicyPlacementAnnotation`，verbose 日志证明实际命中 replica-change branch，而不是更早的 `placementChanged` branch。

## #7835 收尾

Residual 只包含：

```text
pkg/scheduler/core/estimation.go
pkg/scheduler/core/estimation_test.go
```

- scale-up 按 name 计算 positive delta；
- scale-down 返回内部 one-component-set capacity evidence，不调用 estimator；
- mixed、equal、missing/partial/incomparable snapshot 与 new candidate 全部 error；
- 不再对新 candidate fallback full desired estimation；
- requirements provenance 没有存入 `TargetCluster.Components`，因此 replicas 与 requirements 同时变化仍是未覆盖边界，本轮没有增加 hash/API。

## #7841 收尾

Scheduler owner：

- component scale pin 当前 accepted target；
- ordered `ClusterAffinities` 只按当前 observed path 调一次，不进入 fallback migration loop；
- mixed/unknown/estimator failure capacity 为 0，不回退 scalar `spec.Replicas`；
- success 继续使用现有 result patch；任何 component-scale error 在 main-resource patch 前返回。

Binding controller owner：

- source fetch 后调用现有 `GetComponents`；
- 使用 #7830 comparator 与 accepted snapshot 比较；
- mismatch / incomparable 在 `ensureWork` 前返回；
- equal replicas 的 image/label/annotation/requirements-only update 保持旧 propagation 行为；
- feature off、single-template、custom scheduler 和 missing snapshot 保持旧行为。

因此不需要 `ReviseComponents`：success 时 source 已包含新 replicas；failure 时旧 Work 不被覆盖。

## 本地验证

```text
go test -race -count=1 ./pkg/util ./pkg/scheduler
go test -race -count=1 ./pkg/scheduler/core
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
golangci-lint run ./pkg/scheduler/core/... ./test/e2e/suites/base/...
git diff --check
```

以上 unit/race、E2E package compile 和本地 lint 已通过。没有运行 live multi-cluster E2E；新增 Flink workflow 只完成 compile/lint，不能写成 live quota/no-fit 已验证。

## Official CI 快照

| PR | Checks | Failure | Human review |
| --- | --- | --- | --- |
| #7830 | 14 success / 3 jobs running + Tide pending / 18 total | 0 | 无 external human review |
| #7835 | 14 success / 3 jobs running + Tide pending / 18 total | 0 | 无 external human review |
| #7841 | 3 success / 10 jobs running + Tide pending / 14 total | 0 | 无 external human review |

动态 CI 状态以 GitHub 为准。本报告只记录核对时快照，不把 pending、DCO 或 Tide 当作设计认可。

## #7841 lint failure 与本地修复

Official job：[lint / 98535147326](https://github.com/karmada-io/karmada/actions/runs/33077412359/job/98535147326)

GitHub annotation：

```text
pkg/scheduler/core/util.go:57
cyclomatic complexity 17 of func `calAvailableReplicas` is high (> 15) (gocyclo)
```

漏检原因：发布前只对 `test/e2e/suites/base/...` 跑了 changed-path lint，没有覆盖同时修改的 `pkg/scheduler/core/...`。Follow-up `2b567c5a5` 把 component-scale pre-estimator resolution 提取到 `resolveComponentScaleWithoutEstimator`，并用 `targetClustersWithReplicas` 统一构造 capacity result；行为不变。

Follow-up 验证：

```text
golangci-lint run ./pkg/scheduler/core/...
golangci-lint run ./pkg/scheduler/core/... ./test/e2e/suites/base/...
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
```

全部通过。用户确认后已按旧 head `c8146e039` 执行精确 `--force-with-lease`；origin branch 与 GitHub PR head 均为 `2b567c5a553b6c34b49e0a7d5b0a6d1630b3a7cf`。Title 未变，remote body 与获准草稿逐字节一致，SHA-256 仍为 `71b09b39992fdfb446689aaccea96116cd15ad86e18a39e56b3ba591da5797ac`。Current-head official [lint job 98540268305](https://github.com/karmada-io/karmada/actions/runs/33078785199/job/98540268305) 已在 5m46s 后通过，旧 head 的唯一红灯已经消除。

## 反面案例与方法沉淀

- [Day 49](day49-7830-review.md) 保留“从现有代码反推需求、扩成 API/interpreter/delivery”的反面案例；不再修改。
- [Day 58](day58-issue7492-pr-responsibility-refactor.md) 保存完整拆分、架构冲突、range/residual diff 和 upstream update packet。
- Day 59 记录最终交付状态、分 PR 答辩口径、CI gap 和下一 owner，不重复 Day 58 的完整实现过程。

可复用规则：

1. 先把 Issue requirement 映射到 owner，再看现有代码是否应保留。
2. stacked PR 必须同时报告 GitHub full diff 与当前 PR residual diff。
3. 测试 case 名称不能证明调用链；必须控制更早 predicate 并断言下游 mode/result。
4. changed-path lint 必须覆盖每个修改过的 production package，不只覆盖新增 E2E 文件。
5. remote update 必须分别验证 branch head、PR head、title、file surface 和 body bytes。

## 未决边界

- #7830、#7835 的 live E2E jobs 与 #7841 新一轮 official jobs 尚未完成；
- 三个 PR 尚无 external human review；
- live Flink quota/no-fit、ordered-affinity 和 CRB 行为尚未本地 E2E 验证；
- requirements provenance、legacy missing snapshot、failover/recovery 明确移出当前 Phase IV。

## 下一步

1. 只监控 official PR CI；exact-head failure 出现后按 diff 相关性分类。
2. 等待 maintainer review，不为 pending 状态重复 push、retest 或恢复旧大包范围。
