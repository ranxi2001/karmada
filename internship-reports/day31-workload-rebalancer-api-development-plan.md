# Day 31：WorkloadRebalancer API 设计与分阶段开发方案

日期：2026-07-21

## 先说人话

今天不再等 PR #7662 的作者先重写 proposal。我们采用 maintainer 已经给出的收敛方向，但不把 API、controller、scheduler 和二十余个生成文件塞进第一个 PR。

先用一个 10 副本的例子说明最终目标：

```text
member1：当前分配 6，available 4
member2：当前分配 4，available 4

PreserveAvailableReplicas=true：
  固定 member1:4、member2:4 作为不可降低的基线；
  scheduler 只重新分配剩余 2 个 unavailable 副本；
  最后只 patch 一次完整结果。
```

不能先把 Binding 临时改成 `4/4` 再调度。那会真的把 10 副本中间缩成 8 个；如果第二步失败，系统会停在错误的半成品状态。正确做法是在 scheduler 内存中计算基线和缺口，成功后一次性写最终 `spec.clusters`。

开发按两个可独立审阅的行为 PR 推进：

1. 第一个 PR 只完成 #5070：显式完整重调度不仅重算副本，还从第一个顶层 `clusterAffinities` term 重新搜索。它没有 API 变更，改动小，而且历史 maintainer 已认可 scheduler-owned 的实现位置。
2. 第二个 PR 才端到端加入 typed `Reschedule` API 和 `PreserveAvailableReplicas`。API、controller、scheduler、CRD/OpenAPI、单元测试和 E2E 必须一起交付，不能拆成会被用户调用却没有效果的半成品。

这不是继续纠结原 issue 的边界，而是把 maintainer 的设计按可验证行为落地。#7621 的 SafeMigration、自动水位和无中断迁移继续保持开放，本系列不声称修复它们。

## 当前依据与决策强度

| 依据 | 已证明什么 | 没有证明什么 |
| --- | --- | --- |
| [RainbowMango 对 PR #7662 的 review](https://github.com/karmada-io/karmada/pull/7662#pullrequestreview-4742653446) | WorkloadRebalancer 应收敛为 typed reschedule；legacy timestamp 保留；较新请求生效；legacy/nil 表示完整重调度；SafeMigration 移出范围 | 这仍是 `COMMENTED` 设计建议，不是已合并 API；相同时间戳、行为可变性、availability 数据合同没有写全 |
| [Issue #5070](https://github.com/karmada-io/karmada/issues/5070) | on-prem A -> public-cloud B -> A 恢复后显式 failback 是真实公司业务；maintainer 认可 reset scheduling group 的方向 | 不代表自动 failback，也不保证迁移过程无中断 |
| [历史 PR #5425](https://github.com/karmada-io/karmada/pull/5425) | 在 scheduler 的 RB/CRB affinity 入口根据现有 trigger 把 index 设为 0，是历史 maintainer 建议过的最小实现 | 旧分支有污染、编译和测试问题，不能 cherry-pick 或直接 revive |
| 当前源码 `upstream/master@4926be09b` | Full 只让动态副本 assignment 进入 `Fresh`；外层仍从 `SchedulerObservedAffinityName` 开始 | 当前代码还没有 typed request，也没有 preserve-available 下界算法 |

本报告把 maintainer 没写全的部分收敛成实现默认值，后续以 draft PR 和精确测试暴露这些选择；如果 maintainer 反对某项公开 API 合同，在第二个 PR 合并前调整，不阻塞第一个 #5070 PR。

## 目标流程

![WorkloadRebalancer rescheduling development plan](day31-workload-rebalancer-api-development-plan.png)

- [可编辑 Mermaid 源](day31-workload-rebalancer-api-development-plan.mmd)

图只回答一个问题：当前 legacy 请求如何演进为完整重调度和保留 available 副本两条路径，以及两个 PR 各自负责哪一段。

颜色含义：灰色是 current，蓝色是保留的职责，深绿色是第一个 PR，青绿色是第二个 PR，黄色是必须通过的保护条件，红色表示不改 placement 的失败路径。

本机没有预装 `mmdc`，因此使用 repo-local renderer 的显式 `npx` fallback 和固定版本 `@mermaid-js/mermaid-cli@11.16.0` 渲染白底 PNG；实际预览尺寸为 `906x2612`，未发现文字裁切、节点重叠或空白画布。

## API 设计

### 类型归属

`Reschedule` 和唯一一份 `RescheduleBehavior` 放在 `pkg/apis/work/v1alpha2`。Binding 是 scheduler 的执行合同；WorkloadRebalancer 只是请求生产者，因此 `apps/v1alpha1 -> work/v1alpha2 -> policy/v1alpha1` 的依赖方向合理且没有 import cycle。

不复制 apps/work 两份 behavior，也不新增 common API package，否则相同字段以后容易发生 schema 漂移。

```go
// pkg/apis/work/v1alpha2/binding_types.go
type RescheduleBehavior struct {
    // PreserveAvailableReplicas keeps replicas currently reported available
    // in their assigned clusters and reschedules only the unavailable part.
    // Defaults to false.
    // +kubebuilder:default=false
    // +optional
    PreserveAvailableReplicas *bool `json:"preserveAvailableReplicas,omitempty"`
}

type Reschedule struct {
    // +required
    TriggeredAt metav1.Time `json:"triggeredAt"`

    // Nil means complete rescheduling.
    // +optional
    Behavior *RescheduleBehavior `json:"behavior,omitempty"`
}

type ResourceBindingSpec struct {
    // existing fields...

    // +optional
    Reschedule *Reschedule `json:"reschedule,omitempty"`

    // Deprecated: use Reschedule.TriggeredAt instead.
    // +optional
    RescheduleTriggeredAt *metav1.Time `json:"rescheduleTriggeredAt,omitempty"`
}
```

`ResourceBindingSpec` 已同时被 `ResourceBinding` 和 `ClusterResourceBinding` 使用，因此不再复制一套 CRB API。

```go
// pkg/apis/apps/v1alpha1/workloadrebalancer_types.go
type WorkloadRebalancerSpec struct {
    Workloads []ObjectReference `json:"workloads"`

    // Nil means complete rescheduling.
    // +optional
    Reschedule *workv1alpha2.RescheduleBehavior `json:"reschedule,omitempty"`

    TTLSecondsAfterFinished *int32 `json:"ttlSecondsAfterFinished,omitempty"`
}
```

用户 YAML：

```yaml
apiVersion: apps.karmada.io/v1alpha1
kind: WorkloadRebalancer
metadata:
  name: preserve-serving-replicas
spec:
  workloads:
    - apiVersion: apps/v1
      kind: Deployment
      namespace: default
      name: demo
  reschedule:
    preserveAvailableReplicas: true
```

不填写 `spec.reschedule`、填写 `{}` 或显式写 `false` 都表示 Full。这里的 nil 是行为默认值，不是“没有请求”；WorkloadRebalancer 对象本身就是请求。

### 请求仲裁

Binding 侧需要一个共享 helper，把新旧字段规范化为同一种有效请求，controller、scheduler reconcile、outer affinity 和 replica assignment 都使用同一结果，不能各写一套时间比较。

| Binding 状态 | 有效请求 |
| --- | --- |
| 只有 legacy timestamp | legacy Full |
| 只有 typed request | typed behavior |
| 两者都有且 typed 更新 | typed request |
| 两者都有且 legacy 更新 | legacy Full |
| 两者时间完全相同 | typed request 胜出，避免 deprecated Full 静默覆盖新 behavior |
| trigger 不晚于 `lastScheduledTime` | 已消费，不再执行 |
| `lastScheduledTime=nil` | 保留 current 行为：先完成首次调度；没有已确认 placement 时 preserve 不制造第二套初始调度 |

两个 typed 请求如果时间完全相同但 behavior 不同，没有足够字段建立全序。第一版采用“现有 typed 请求胜出”的幂等规则，不让并发 writer 来回覆盖；若社区要求严格多请求顺序，后续必须增加 request ID，而不是继续猜时间。

### WorkloadRebalancer behavior 不允许事后修改

当前 controller 使用 WorkloadRebalancer `creationTimestamp` 作为稳定 trigger，而且成功 workload 不会因为 behavior 被编辑而重新执行。若允许原地把 `false` 改成 `true`，API update 会成功，但 scheduler 看不到新时间戳，属于静默 no-op。

因此第二个 PR 的默认设计是：`spec.reschedule` 仅在创建时确定，之后 immutable；`workloads` 和 `ttlSecondsAfterFinished` 仍维持现有可更新行为。优先用 CRD transition validation 表达，不为一个字段新建 webhook。生成后必须用有效/无效 update 用例验证 CEL，而不是只相信 marker。

需要另一种 behavior 时，创建新的 WorkloadRebalancer。这样一个对象对应一个稳定请求，controller retry 仍然幂等。

## 行为设计

### Full：第一个 PR 即可落地

完整重调度要丢弃两层历史：

1. `spec.clusters` 表示的旧副本分配，由现有 `Fresh` assignment 处理；
2. `status.schedulerObservingAffinityName` 表示的顶层 affinity 搜索书签，由第一个 PR 在内存中把起始 index 设为 0。

controller 不清空 scheduler-owned status。scheduler 仍按 A、B、C 顺序尝试，成功后把实际选中的 affinity name 写回 status；如果 A 仍不可用，自然继续回到 B。

Full 保留现有的 ClusterAffinity、Duplicated、Static/Dynamic/Aggregated、Overflow 和非 workload 路径。第一个 PR 不引入任何新 API 或生成文件。

### PreserveAvailableReplicas：第二个 PR 端到端实现

第一版只支持 `apps/v1 Deployment` 的两种 Divided 动态算法：

- `ReplicaDivisionPreference=Aggregated`；
- `ReplicaDivisionPreference=Weighted` 且使用 `DynamicWeight`。

执行步骤：

1. scheduler 选出新旧字段中的有效 pending request。
2. preserve 请求保留当前 outer affinity group，不执行 Full 的 index 0 reset。
3. 从同一个 Binding 快照读取 `spec.clusters` 和 `status.aggregatedStatus`。
4. 对每个正副本 target，要求唯一 status、`Applied=true`、raw status 非空，并解析 Deployment `availableReplicas`。
5. 要求 `0 <= availableReplicas <= assignedReplicas`，且总 available 不超过 desired replicas。
6. deep-copy `ResourceBindingSpec`，只在内存中把 copy 的 `Clusters` 替换为 available 基线。
7. 运行现有 Steady dynamic scale-up，只分配 `desired - preserved` 的缺口。
8. 要求每个正数基线 cluster 仍然在 filter/select 的最终 candidates 中；否则 fail closed。
9. 成功后一次性 patch 最终 `spec.clusters`，绝不先写中间基线。

`availableReplicas` 指 member workload 经 ResourceInterpreter 反射到 `AggregatedStatusItem.Status` 的字段，不是 scheduler 中“集群剩余容量”的同名概念。当前 native Deployment reflector 已经保留该字段，因此第一版不修改 ResourceInterpreter。

这是 scheduler 执行时读取的最新缓存快照，不是 WorkloadRebalancer 创建时冻结的事务快照。它能保证“最终 assignment 不低于本次读取到的 available 基线”，不能承诺跨控制器的强一致状态或 target-first 无中断迁移。

### 第一版支持矩阵

| 场景 | Full | PreserveAvailableReplicas |
| --- | --- | --- |
| Deployment + Divided/Aggregated | 支持 | 支持 |
| Deployment + Divided/DynamicWeight | 支持 | 支持 |
| Divided/StaticWeight，包括默认静态等权 | 支持 | 明确拒绝；当前算法会重算全部比例，无法证明下界 |
| Duplicated | 支持 | 明确拒绝；没有“只移动部分全量副本”的清晰语义 |
| OverflowAffinities | 支持 | 明确拒绝；当前逐 tier allocator 没有 pinned lower bound |
| 多 Pod template | 保持现状 | 明确拒绝；没有单一 `availableReplicas` 合同 |
| 非 Deployment 或任意同名 CRD 字段 | 保持现状 | 明确拒绝，避免误读不同资源的字段语义 |
| 单 ClusterAffinity | 支持 | preserved clusters 仍 eligible 时支持 |
| 多 ClusterAffinities | 从 term 0 开始 | 保留当前 term；cursor 无效时拒绝 |
| SpreadConstraints | 支持 | selected set 包含全部 preserved clusters 时支持，否则拒绝 |
| ResourceBinding | 支持 | 支持上述 Deployment 场景 |
| ClusterResourceBinding | 支持 | API/调度入口对称；第一版没有 cluster-scoped Deployment 场景 |

失败时不修改 `spec.clusters`：

- status 缺失、未 Applied、空、重复或暂时不合法：记录 `Unschedulable`，等待 status 更新；
- preserved cluster 不再满足 filter/spread：记录明确原因，让用户选择 Full 或先修 policy；
- unsupported mode/resource：记录明确的 scheduler condition/event，不把它降级成 Full；
- API 或 patch 错误：沿用 scheduler backoff。

当前 event handler 会忽略不增加 generation 的 status-only 更新。第二个 PR 必须允许“存在 pending preserve 请求且 `AggregatedStatus` 实际变化”的 RB/CRB 重新入队，否则 status 后来就绪时 priority queue 不能及时自愈。

WorkloadRebalancer 的 `RebalanceSuccessful` 暂时仍表示“请求已成功写入 Binding”，不表示 scheduler 已完成，也不表示 workload 已 available。真正执行结果继续看 Binding `Scheduled` condition 和 `lastScheduledTime`；本 PR 不扩展 WR status machine。

## 分阶段 PR 方案

### PR 1：完成 #5070 的 Full 语义

建议标题：

```text
scheduler: reset cluster affinity group on explicit rescheduling
```

建议分支：`feature/reset-affinity-on-reschedule`

标签和关联：

```text
/kind feature
Fixes #5070
Related to #5172 and #7662
```

开 PR 前应在 #5070 留一条简短说明：这是从 current master 重建的 clean replacement，历史 #5425 只作为设计证据，不 cherry-pick 污染分支。#5172 仍有原 assignee，因此只 cross-link，不擅自改 ownership。任何这类 upstream 评论仍需用户确认 exact English text。

| 文件 | 修改 | 为什么属于 PR 1 |
| --- | --- | --- |
| `pkg/scheduler/scheduler.go` | RB/CRB 的 multi-affinity 入口在 pending explicit Full 时从 index 0 开始 | #5070 的直接 causal location；不清 status |
| `pkg/scheduler/scheduler_test.go` | RB/CRB 对称覆盖 pending、更新/更旧/相等 trigger、A 失败继续 B | 证明不是无条件 reset，也证明 fallback 仍工作 |
| `test/e2e/suites/base/clusteraffinities_test.go` | 在现有 top-level A/B 生命周期中补 A recover -> WR -> A | 复用真实 label failover 场景，证明生产生命周期而不只测 helper |

明确不改：`pkg/apis/**`、controller、`pkg/util/binding.go`、CRD/OpenAPI、generated files、PreserveAvailableReplicas、Overflow、SafeMigration 和 status schema。

### PR 2：typed API + preserve-available 闭环

建议标题：

```text
scheduler: preserve available replicas during explicit rescheduling
```

类型：

```text
/kind feature
/kind api-change
/kind deprecation
```

它只 `Part of` 或 `Related to` #7662/#7621，不写 `Fixes #7621`。SafeMigration、自动 waterline、CPU/内存比例和 anti-oscillation 都没有交付。

#### 手写源码范围

| 层 | 文件 | 计划改动 |
| --- | --- | --- |
| API | `pkg/apis/work/v1alpha2/binding_types.go` | 新增 `Reschedule`、`RescheduleBehavior`、typed request，deprecate legacy comment |
| API helper | `pkg/apis/work/v1alpha2/binding_types_helper.go` | 统一新旧请求仲裁和 behavior 默认语义 |
| Apps API | `pkg/apis/apps/v1alpha1/workloadrebalancer_types.go` | 引用唯一一份 behavior；增加 create-time immutable contract |
| Controller | `pkg/controllers/workloadrebalancer/workloadrebalancer_controller.go` | 只写 typed request；不删除/覆盖更新的 legacy 或 typed 请求 |
| Scheduler trigger | `pkg/scheduler/scheduler.go` | 所有显式请求统一读取 effective request；Full reset、Preserve retain cursor |
| Preserve preparation | 新建 `pkg/scheduler/reschedule.go` | 校验 Deployment/status/support matrix，构造内存基线 |
| Assignment | `pkg/scheduler/core/assignment.go` | Preserve 使用基线走 Steady dynamic scale-up；只返回最终结果 |
| Event | `pkg/scheduler/event_handler.go` | pending Preserve 的 AggregatedStatus 变化可重新入队 |
| E2E | `test/e2e/suites/base/workloadrebalancer_test.go` | 保留 available 下界并只分配 unavailable delta |

每个手写文件都要有相邻 `_test.go` 回归。若实现过程中需要修改 spreadconstraint、resource interpreter、descheduler 或 GracefulEviction，说明设计边界已经扩大，必须停下来更新本报告和支持矩阵，不能顺手扩散。

#### 生成文件范围

运行窄 codegen/crd/swagger 脚本后，预计至少更新：

- apps/work 两组 `zz_generated.deepcopy.go`；
- work `zz_generated.model_name.go`；
- `pkg/generated/openapi/zz_generated.openapi.go`；
- apps/work applyconfiguration spec、新增 reschedule/behavior applyconfiguration、internal schema 和 utils；
- WorkloadRebalancer、ResourceBinding、ClusterResourceBinding 三个 CRD；
- `api/openapi-spec/swagger.json`。

不手工挑掉由同一 API 字段生成的合法产物。`work/v1alpha1` 类型和 conversion 不增加字段：它当前本来就不包含 legacy reschedule，`v1alpha2` 仍是 storage hub。

## 函数级实现设计

| 函数/职责 | 输入 | 输出或副作用 | 关键不变量 |
| --- | --- | --- | --- |
| `LatestRescheduleRequest` | Binding spec 的 typed + legacy 字段 | 规范化 `*Reschedule` | 新字段在 legacy 同时间戳时胜出；legacy behavior 永远是 Full |
| `RescheduleRequired` | effective trigger + `lastScheduledTime` | pending bool | 继续使用严格 `After`，避免同一请求重复执行 |
| Full affinity start | affinity terms + status cursor + pending request | 起始 index | 只有 pending Full 为 0；普通 reconcile 和 Preserve 保留 cursor |
| controller request builder | WR creationTimestamp + behavior | typed Binding request | retry 生成完全相同的对象；不 dual-write legacy |
| preserve baseline builder | spec.clusters + aggregated status | deep-copied effective spec 或错误 | 不修改 informer 对象；每个正基线都可证明来源；失败不 patch |
| dynamic assignment | selected candidates + effective spec | final targets | 每个 target `final >= preserved`；总和等于 desired |
| status update event gate | old/new Binding | 是否 enqueue | 只为 pending Preserve 且 AggregatedStatus 真变化放行，不让所有 status update 触发 schedule storm |

## 测试矩阵

### PR 1

| 测试 | 必须证明 |
| --- | --- |
| RB observed=B，trigger > last | 首先调用 A |
| CRB observed=B，trigger > last | 与 RB 对称 |
| trigger nil、旧于或等于 last | 仍从 B 开始，不改变普通 reconcile |
| A 仍不匹配/容量不足 | 继续尝试 B，不因 reset 直接失败 |
| E2E A -> B -> A recover -> WR | 最终回到 A，且 WorkloadRebalancer lifecycle 正常 |

### PR 2

| 维度 | Cases |
| --- | --- |
| 请求仲裁 | old-only、new-only、两者 newer、legacy/new tie、nil/false/true behavior |
| Controller | RB/CRB 写 typed request；较旧 WR 不覆盖较新请求；retry 幂等；legacy 不被主动清除 |
| 正常 Preserve | `6 assigned / 4 available + 4/4 -> baseline 4/4 + allocate 2`，Aggregated 和 DynamicWeight |
| Status 防御 | missing、nil raw、invalid JSON、`Applied=false`、duplicate cluster、negative、available > assigned、sum > desired |
| Policy 冲突 | preserved cluster 被 affinity/filter/spread 排除时结果不 patch |
| Unsupported | StaticWeight、Duplicated、Overflow、多 template、非 Deployment 均明确报错，不能降级 Full |
| Cursor | Full 从 A 开始；Preserve 保留 B；无效 current cursor 时 Preserve 失败 |
| Event | 普通 status-only update 仍忽略；pending Preserve 的 AggregatedStatus 变化重新入队 |
| Completion | 只有最终 patch 成功才更新 Scheduled/lastScheduledTime；WR Successful 仍只是 accepted |
| E2E | available 下界不下降、只重新分配 unavailable delta、legacy WR manifest 仍执行 Full |

测试不能只断言 helper 返回值。至少一个单元测试必须在删除实际 scheduler reset 后失败，Preserve 测试必须断言每个 cluster 的下界和最终总副本数。

## 验证与 Review 路径

PR 1 聚焦验证：

```bash
go test ./pkg/scheduler/... -count=1
go test ./pkg/util/... -count=1
go test ./test/e2e/suites/base -run '^$' -count=0
make verify
```

有本地 Karmada 环境时运行聚焦 Ginkgo 用例；提交前把 clean topic branch 推到 fork，等待 push CI 的三版本 E2E，再做 upstream PR preflight。

PR 2 先运行聚焦包，再运行生成和全仓验证：

```bash
go test ./pkg/apis/work/v1alpha2 ./pkg/util ./pkg/controllers/workloadrebalancer ./pkg/scheduler/... -count=1
make update
make verify
git diff --check
```

`make update` 会包含较宽的生成步骤。实现时先运行窄脚本并检查 diff；最终仍以 `make update` 后无额外 diff 为门禁，避免提交过期 CRD/OpenAPI。

Reviewer ownership：

- API：`pkg/apis/OWNERS`，approvers `kevin-wangzefeng`、`RainbowMango`；
- Scheduler：`pkg/scheduler/OWNERS`，approvers `Garrybest`、`whitewindmills`、`XiShanYongYe-Chang`；
- E2E 和其余文件按最近 OWNERS 向上解析。

## 版本升级顺序

新 controller 按 maintainer 建议只写 typed request，旧 scheduler 完全不认识该字段。Preserve 请求不能 dual-write legacy timestamp，因为旧 scheduler 会把它当 Full，反而破坏 available 下界。

因此第二个 PR 的 release note 必须写明滚动升级顺序：

```text
CRD -> karmada-scheduler -> karmada-controller-manager
```

旧 controller + 新 scheduler 仍可通过 legacy timestamp 工作。新 controller 不应先于 scheduler 启用。若社区要求任意升级顺序，必须另设计 capability negotiation，不能用 dual-write 假装兼容。

## 明确不做

- 不实现 SafeMigration、target-first、stableWindow、rollback、cancel、progress 或 finalizer；
- 不让 WorkloadRebalancer controller 写 `spec.clusters` 或清 scheduler status；
- 不把 `RebalanceSuccessful` 改成 workload ready；
- 不自动检测水位、CPU/内存比例或周期 failback；
- 不把 arbitrary CRD 的同名 `availableReplicas` 当作相同语义；
- 不顺手重构通用 scheduler assignment framework；
- 不关闭 #7621，也不宣称本功能提供无中断迁移。

## 下一步

1. 在独立 topic worktree 从最新 `upstream/master` 创建 `feature/reset-affinity-on-reschedule`。
2. 先实现 PR 1 的 RB/CRB reset 和可失败的回归测试，不碰 API 文件。
3. 本地验证和 fork push CI 通过后，准备 #5070 clean-replacement 英文说明与 PR body，交用户确认后再发 upstream。
4. PR 1 进入 review 后，再从最新 master 开第二个端到端 API PR；实现中一旦超出本报告支持矩阵，先更新设计，不堆防御嵌套。

## Stop Conditions

- 第一个 PR 出现 API/generated diff，立即停止并拆回 #5070 causal scope。
- Preserve 不能证明 `final >= available baseline` 时，不允许以 best effort 名义合并。
- 缺失/unsupported status 不能静默降级成 Full。
- 未经用户确认，不发布 issue comment、PR、reviewer mention 或其他 upstream 动作。

## #5070 第一阶段实现与验证

### 通俗结论

这一阶段已经按计划收敛成一个很小的行为修复。工作负载原来从第一组亲和性 `A` 调度到第二组 `B` 后，即使 `A` 已恢复，WorkloadRebalancer 触发的“完整重调度”仍会沿用 Binding 状态里记录的 `B` 作为搜索起点，所以无法回到优先级更高的 `A`。

修复只在“存在尚未执行的显式重调度请求”时把 affinity 起点改为第 0 组。普通 reconcile 没有显式请求时仍从当前组继续，不改变故障切换、状态恢复和日常调度行为。

### 代码范围

独立 topic worktree：`/tmp/karmada-5070-affinity-reset`

- branch：`feature/reset-affinity-on-reschedule`
- base：`upstream/master@4926be09bc3546162a56faf92e7e3e96158d4bcd`
- commit：`06840d2203890c94b230c6028851f256e89f4324`
- fork branch：<https://github.com/ranxi2001/karmada/tree/feature/reset-affinity-on-reschedule>

提交仅修改 3 个文件，共 `299 insertions, 17 deletions`：

| 文件 | 改动 | 为什么需要 |
| --- | --- | --- |
| `pkg/scheduler/scheduler.go` | 6 行生产代码 | RB、CRB 两条 multi-affinity 调度路径在 pending reschedule 时从 index 0 开始 |
| `pkg/scheduler/scheduler_test.go` | 对称回归与负向控制 | 同时证明显式 reschedule 会回到第一组、普通调度仍从当前组继续 |
| `test/e2e/suites/base/clusteraffinities_test.go` | 真实 A -> B -> A 用例 | 用 WorkloadRebalancer 和真实 Binding/成员集群资源证明完整行为链 |

没有修改 API、CRD、controller、generated code，也没有为这个行为增加新的兼容层或防御嵌套。

### 测试如何对应同一个缺陷

单元测试先把 RB/CRB 的当前 cursor 都放在 `affinity2`：

- pending reschedule：第一次 scheduler 调用必须收到 `affinity1`；
- 没有 pending trigger：第一次调用仍必须是 `affinity2`。

E2E 使用真实对象完成同一条路径：

1. `affinity1/member1` 初始部署；
2. 修改 member1 标签使第一组不再匹配，普通调度落到 `affinity2/member2`；
3. 恢复 member1，并等待 cluster informer 与 Binding generation/status 都收敛；
4. 跨过 RFC3339 的下一秒再创建 WorkloadRebalancer，保证 `RescheduleTriggeredAt > LastScheduledTime`；
5. 断言最终回到 `affinity1/member1`，member2 上的副本被清理，Binding cursor 和 WorkloadRebalancer 状态均正确。

这里的秒级屏障不是延长业务超时，而是匹配 `metav1.Time` 持久化精度和 `RescheduleRequired` 的严格 `After` 合同，避免 trigger 与 last-scheduled 落在同一秒造成测试假失败。

### 反向证明

为避免“新增测试只是碰巧通过”，本地临时删除 6 行生产修复，只运行两个显式 reschedule case。RB 和 CRB 都稳定失败：实际首次调用仍为 `affinity2`，而测试期待 `affinity1`，随后 mock scheduler 报 `unexpected call to Schedule`。恢复生产修复后，相同命令通过。

因此测试和修复落在同一个 causal edge：

```text
pending explicit reschedule
  -> affinity start index must become 0
  -> first evaluated term changes from affinity2 to affinity1
  -> recovered preferred group can be selected again
```

### 本地验证

- focused RB/CRB tests：通过；
- `go test ./pkg/scheduler/... -count=1`：通过；
- `go test ./test/e2e/suites/base -run '^$' -count=1`：编译通过；
- `git diff --check`：通过；
- targeted golangci-lint：`0 issues`；
- mocks、gofmt、vendor、Swagger/OpenAPI、command-line flags、crdgen、codegen、license verify：逐项通过。

完整本地 golangci-lint 在冷缓存环境运行到仓库配置的 10 分钟上限后退出，但退出前报告 `0 issues`。fork 标准 lint 随后通过，因此没有以扩大 timeout 或修改代码来掩盖本机资源问题。本机没有现成 kind/Karmada 集群，真实 E2E 交给 fork push CI 三个 Kubernetes 版本执行。

### Fork CI 与 flake 分类

exact-SHA run：<https://github.com/ranxi2001/karmada/actions/runs/29823411230>

- codegen、lint、compile、unit：通过；
- Kubernetes v1.35.0：通过，新 A -> B -> A spec 用时 `20.804s`；
- Kubernetes v1.36.1：通过，新 A -> B -> A spec 用时 `23.157s`；
- Kubernetes v1.34.0 attempt 1：在新用例执行前，被既有 `federatedresourcequota` BeforeEach 的 `etcdserver: request timed out` 中断。

v1.34 attempt 1 的证据链是：多套 etcd 同时出现数秒 `slow fdatasync`，随后 raft/linearizable read stall，API `/readyz` 503 和拒绝连接，最终一个 namespace setup 失败并打断并行 specs/cleanup。它属于 Day 27 已记录的共享 runner 存储停顿簇；在本次 run 中，API 失败链达到 E3，物理触发原因仍只到 E2，不能口说无凭地归因于某一种宿主机硬件问题。该失败不经过本次修改的 scheduler 路径，因此没有为它增加 retry、timeout 或业务代码。

已对同一 SHA 单独发起 failed-job rerun。当前 v1.34 attempt 2 仍在运行；最终状态完成后再更新本节和短期进度记录。

### 当前边界

- 尚未创建 upstream PR，也未发布 #5070 技术评论或 maintainer mention；
- open PR [#5425](https://github.com/karmada-io/karmada/pull/5425) 与目标重叠但长期停滞、当前不可编译且混有无关改动；maintainer 当时也明确[建议用 `RescheduleRequired` 后把 affinity index 置 0](https://github.com/karmada-io/karmada/pull/5425#discussion_r1769531084)。准备上游 PR 时需要如实说明重叠关系，不擅自宣称 supersede；
- #5172 仍属于另一位 assignee，不把本次 #5070 修复写成接管 umbrella；
- typed reschedule request 和 PreserveAvailableReplicas 继续留在第二阶段，不混入这个 commit。

## 待确认的 Upstream PR 草稿

目标：`karmada-io/karmada:master <- ranxi2001:feature/reset-affinity-on-reschedule`

Title：

```text
scheduler: restart cluster affinity evaluation on reschedule
```

Body：

````markdown
**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

With multiple `clusterAffinities`, the scheduler resumes from `schedulerObservingAffinityName`. A WorkloadRebalancer request discards the previous cluster assignment but currently preserves that affinity cursor, so an earlier recovered group is never reconsidered.

For a pending explicit reschedule, this change restarts affinity evaluation from the first term for both ResourceBinding and ClusterResourceBinding. Ordinary scheduling still resumes from the observed affinity. This follows the scheduler-side approach suggested in #5425, applied to current master with regression and A -> B -> A E2E coverage.

**Which issue(s) this PR fixes**:

Fixes #5070

**Special notes for your reviewer**:

- Scope: scheduler affinity cursor only; no API, CRD, generated-code, or controller changes.
- Tests: `go test ./pkg/scheduler/... -count=1`; exact-SHA fork CI passed codegen, lint, compile, unit, and Kubernetes v1.35-v1.36 E2E; the v1.34 failed-job rerun is pending.
- AI assistance: Codex helped inspect the change and draft tests/text; I reviewed the code and validation results.

**Does this PR introduce a user-facing change?**:

```release-note
`karmada-scheduler`: WorkloadRebalancer-triggered rescheduling now evaluates multiple cluster affinity terms from the first term.
```
````

发布前必须先确认 v1.34 rerun 终态，再重新拉取 upstream master、#5070 assignee、#5425 head/activity 和 exact-SHA checks。上面的文本只是草稿，不构成发布授权。
