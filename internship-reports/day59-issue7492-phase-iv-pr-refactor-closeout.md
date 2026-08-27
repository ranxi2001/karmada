# Day 59：#7492 Phase IV 三 PR 重构收尾

日期：2026-08-27

状态核对时间：2026-08-27 21:39（Asia/Shanghai）

## 先说人话

#7492 的三个 PR 已经按“触发、计算、失败保护”重新发布，旧的 `ReviseComponents` / component delivery 大包没有保留。当前工作已从“继续改设计”转为“等待 official CI 和 human review”。

还不能把任务写成完全结束：#7841 exact head `c8146e039` 的 official lint 发现 `calAvailableReplicas` cyclomatic complexity 为 17，超过阈值 15。本地已经提取 helper 并形成 signed-off follow-up `2b567c5a5`；core lint、完整 race tests 和 E2E compile 均通过，但该 commit 尚未获得 upstream push 确认。

具体例子仍是：accepted `JM=1, TM=4`，source 改为 `JM=1, TM=6`。#7830 只触发 scheduler，#7835 只计算 `TM=+2`，#7841 只在 scheduler 接受后更新 Work；无法容纳时 accepted snapshot 与旧 Work 都保持 `TM=4`。

## 最终 PR 职责

| PR | Public head | 唯一职责 | Residual diff | Public stacked diff |
| --- | --- | --- | --- | --- |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `e3e9d4e9f` | component replicas changed → trigger rescheduling | 3 files，`+277/-8` | 同 residual |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `e19a318eb` | positive delta / scale-down skip calculation | 2 files，`+403/-6` | 5 files，`+680/-14` |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `c8146e039` | failure-safe accepted-result commit 与 Work guard | 14 files，`+804/-26` | 18 files，`+1484/-40` |

三个 remote head、title、changed-file surface 和 body bytes/SHA-256 已逐项验证。PR 仍为 Open / blocked on CI and review，没有 external human review，也没有 `/lgtm` 或 `/approve`。

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
| #7830 | 13 success / 5 pending / 18 total | 0 | 无 external human review |
| #7835 | 6 success / 12 pending / 18 total | 0 | 无 external human review |
| #7841 | 2 success / 11 pending / 1 failure / 14 total | `lint` | 无 external human review |

动态 CI 状态以 GitHub 为准。本报告只记录核对时快照，不把 pending、DCO 或 Tide 当作设计认可。

## #7841 lint failure 与本地修复

Official job：[lint / 98535147326](https://github.com/karmada-io/karmada/actions/runs/33077412359/job/98535147326)

GitHub annotation：

```text
pkg/scheduler/core/util.go:57
cyclomatic complexity 17 of func `calAvailableReplicas` is high (> 15) (gocyclo)
```

漏检原因：发布前只对 `test/e2e/suites/base/...` 跑了 changed-path lint，没有覆盖同时修改的 `pkg/scheduler/core/...`。本地 follow-up `2b567c5a5` 把 component-scale pre-estimator resolution 提取到 `resolveComponentScaleWithoutEstimator`，并用 `targetClustersWithReplicas` 统一构造 capacity result；行为不变。

Follow-up 验证：

```text
golangci-lint run ./pkg/scheduler/core/...
golangci-lint run ./pkg/scheduler/core/... ./test/e2e/suites/base/...
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
```

全部通过。该 commit 尚未 push，必须单独获得 `c8146e039 -> 2b567c5a5` exact action 确认。

## 反面案例与方法沉淀

- [Day 49](day49-7830-review.md) 保留“从现有代码反推需求、扩成 API/interpreter/delivery”的反面案例；不再修改。
- [Day 58](day58-issue7492-pr-responsibility-refactor.md) 保存完整拆分、架构冲突、range/residual diff 和 upstream update packet。
- Day 59 只记录最终交付状态、CI gap 和下一 owner，不重复 Day 58 的完整实现过程。

可复用规则：

1. 先把 Issue requirement 映射到 owner，再看现有代码是否应保留。
2. stacked PR 必须同时报告 GitHub full diff 与当前 PR residual diff。
3. 测试 case 名称不能证明调用链；必须控制更早 predicate 并断言下游 mode/result。
4. changed-path lint 必须覆盖每个修改过的 production package，不只覆盖新增 E2E 文件。
5. remote update 必须分别验证 branch head、PR head、title、file surface 和 body bytes。

## 未决边界

- #7841 lint follow-up 尚待获准 push，public CI 仍红；
- official CI 其余 jobs 尚未完成；
- 三个 PR 尚无 external human review；
- live Flink quota/no-fit、ordered-affinity 和 CRB 行为尚未本地 E2E 验证；
- requirements provenance、legacy missing snapshot、failover/recovery 明确移出当前 Phase IV。

## 下一步

1. 请求并执行 #7841 lint follow-up exact push，验证 remote head 和 body不变。
2. 只监控 official PR CI；exact-head failure 出现后按 diff相关性分类。
3. 等待 maintainer review，不为 pending状态重复 push、retest或恢复旧大包范围。
