# Day 45：#7492 进度、完整性与待确认合同

- 日期：2026-08-12
- Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- Feature branch：[`ranxi2001/feature/multi-component-scale-rescheduling`](https://github.com/karmada-io/karmada/compare/master...ranxi2001:karmada:feature/multi-component-scale-rescheduling)
- Feature HEAD：[`a3547a3a84ef93e6cf1bf08422ae6465e381d6bd`](https://github.com/ranxi2001/karmada/commit/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd)
- Merge base：[`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`](https://github.com/karmada-io/karmada/commit/1c278577e7892b6ea44f86a4317c1eb1e013bb93)
- Maintainer-provided Draft：[`RainbowMango/pr_multi_component_next_move@c14af2f1119a66d4672a814cc80f7612943d35d3`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md)
- 前置设计与实测：[Day 44：#7492 多组件调度结果 API 设计](day44-issue7492-component-scheduling-result-api-design.md)
- 本轮范围：只读复核 issue、分支、生产调用链和 PR readiness；没有修改 feature branch，也没有发布 upstream PR 或评论

## 先说人话

当前分支已经造好了“记录每个组件上次调度结果”的位置，但生产代码还没有向这个位置写数据，也没有
读取它来判断扩缩容。

例如，FlinkDeployment 原来是：

```text
request: jobmanager=1, taskmanager=10
result:  member1
```

用户把 `taskmanager` 改成 20 后，当前 Binding 仍只有 `member1`，没有
`member1/jobmanager=1/taskmanager=10` 这份旧结果。调度器因此缺少可比较的基线。feature branch 新增了
`spec.clusters[].components`，但当前 scheduler 仍只产生 `TargetCluster{Name: "member1"}`，所以字段实际
不会被填充。

需要把三种“完成”分开：

| 目标 | 当前判断 | 还差什么 |
| --- | --- | --- |
| **可以开 API groundwork PR** | 机械 preflight 已完成；可以开更窄的 design/review surface | exact body 必须披露当前 branch 只覆盖 Draft PR1 的 API/codegen，缺 webhook validation 与 `GracefulEvictionTask.Components` |
| **API PR 可以合并** | 尚未按维护者 Draft 对齐 merge-ready scope | 补齐或明确拆出 PR1 scope gap；处理 v1alpha1 数据保护，不能再把已回答的 single/`BindingSnapshot` 作为 blocker |
| **完整实现 #7492** | 约 **25% ±5%** | producer、scale trigger、失败保护、component dispatch/interpreter、正式 validation 和行为测试 |

> 分析：百分比是按功能链路和未决合同给出的工程估计，不是测试覆盖率，也不是 maintainer 承诺。
> 当前最准确的结论是：**代码已足够形成 API review surface，但严格按维护者 Draft 的 PR1 还缺实现；
> 离“关闭 #7492”仍很远。**

## 本轮进度

### 分支与社区状态

截至 2026-08-12 的回读结果：

- feature HEAD、本地 branch 和 `origin/feature/multi-component-scale-rescheduling` 都是 `a3547a3a8`。
- `upstream/master` 仍是该提交的直接父提交；branch 为 `0 behind / 1 ahead`，工作树干净。
- 只有 1 个 DCO commit：`feat(api): add component scheduling results`。
- diff 为 15 files、`+604/-5`：5 个手写文件和 10 个对应生成物，没有实习记录或无关源码。
- #7492 仍为 Open，milestone 为 v1.19，assignee 为 `ranxi2001`；正文三项任务均未勾选。
- issue 最新一条评论仍是 2026-08-11 `mszacillo` 提出的跨集群重调度状态保留问题；8 月 12 日没有新
  maintainer 回复。
- 当前没有关联 #7492 或该 feature head 的 upstream PR。

### 已经完成的代码

1. **结果 API 载体**：`TargetCluster` 已增加 name-keyed、order-insensitive 的
   `Components []TargetComponent`；`TargetComponent` 保存 `Name` 和 `Replicas`。
2. **发布产物**：deepcopy、apply configuration、OpenAPI、swagger 和 RB/CRB CRD 已同步。
3. **legacy projection 显式化**：v1alpha1 conversion 只投影 `Name/Replicas`，测试明确记录
   `Components` round-trip 后丢失，而不是依赖不再可编译的类型强转。
4. **测试 helper 语义**：`IsScheduleResultEqual` 按 component name 比较，忽略 component 顺序及
   nil/empty 差异，并拒绝重复 name；11 个 table-driven case 已覆盖关键边界。
5. **API 注释纠偏**：删除未经解释的 “only workloads with multiple pod templates”，改成中性的
   component-based scheduling result 描述；它与维护者 Draft 明确的 single-component 双写路线兼容。

### 已有验证证据

以下命令在 Day44 对当前 exact tree 执行并通过；Day45 没有重跑全量测试，因为 HEAD、tree、base 和远端
均未变化：

| 命令 | 结果 | 能证明什么 |
| --- | --- | --- |
| `go test ./test/helper -run '^TestIsScheduleResultEqual$' -count=1 -v` | 11 个子用例通过 | helper 符合 map-list 判等语义 |
| `go test ./pkg/apis/work/v1alpha1 ./pkg/apis/work/v1alpha2 ./test/helper -count=1` | PASS | API、conversion 和 helper 基础回归通过 |
| `make verify` | PASS | 生成物、格式、静态检查、vendor、license 一致 |
| `make test GO_TEST_FLAGS='--race -covermode=atomic'` | 最终完整重跑 PASS | 当前 tree 的仓库 Go tests 通过 |
| `git diff --check` | PASS | 无 whitespace error |

这些结果证明当前 API patch 自洽、可编译、生成物完整；它们不证明 production path 已经使用新字段，也
不证明未确认的跨字段和版本合同正确。

## Maintainer-provided Draft 已给出的答案

`c14af2f1` 是用户确认的维护者设计资料。它仍标记为 `Draft (design discussion, not yet a formal
proposal)`，所以这里只把它作为当前实现方向，不写成 upstream 已合入共识。Day44/Day45 原先三组
blocker 中，下面内容已有答案：

| 事项 | 已给出的方向 |
| --- | --- |
| API 方案 | 选择方案 B，在 `TargetCluster` 内保存 name-keyed component result |
| single component | 迁移期双写 scalar `Replicas` 和一个 `Components` entry |
| multi component | scheduler 写 `fullComponentSetOf(spec.Components)`，不是 delta |
| request/result 迁移 | 两侧结构同构，`Components` 是迁移方向，legacy scalar 暂时双写 |
| result validation | RB webhook 校验 request membership、cluster 内 duplicate；Gate 关闭时拒绝携带结果字段 |
| `BindingSnapshot` | 复用 `TargetCluster` 是有意的；同名 component merge 取最大 replicas |
| dispatch | PR3 增加 `ReviseComponents` 并贯通 interpreter；single component 可 fallback `ReviseReplica` |
| eviction | `GracefulEvictionTask` 增加 `Components` 并保存被驱逐集群结果 |
| PR 切分 | PR1 API+codegen+webhook，PR2 scheduler 双写，PR3 interpreter+ensureWork，PR4 third-party+Flink E2E，PR5 downstream |

因此 single/scalar 三选一、是否允许 `requiredBy` 暴露 Components、Gate-off 基本策略、
`ReviseComponents` 是否属于闭环，都不再列为“需要 maintainer 从零回答”。仍未回答的是失败状态机、
v1alpha1 保护、partial/mismatch/CRB 校验边界和 scale delta/trigger 细节。

## 完整性分析

### #7492 的实际验收目标

Issue 正文明确列出三项 phase IV 行为：

1. multi-template application 能进入 rescheduling。
2. rescheduling 的 estimator 考虑已调度组件：scale-up 只估算增量，scale-down 可以跳过估算。
3. rescheduling 失败时，不把更新后的配置传播到 member clusters。

当前三项仍全部未完成。新增 API 是这三项的前置数据结构，不等于行为已经接通。

### 当前生产链路

1. 资源解析器（`ResourceInterpreter.GetComponents`）可以把请求模板解析到
   `ResourceBindingSpec.Components`。
2. 调度器的 component estimator 可以用整份 `spec.Components` 估算某集群能容纳多少完整 component
   sets。
3. 选择阶段把 component workload 当作不可拆分的一个整体，只选择一个集群。
4. 结果生成阶段仍返回 `TargetCluster{Name: clusterName}`，没有生成
   `TargetCluster.Components`。
5. `IsBindingReplicasChanged` 对 component workload 只在 `Clusters` 为空时触发 failover；它明确不检测
   component scale 或等总副本的 component swap。
6. Binding controller 下发 Work 时只支持 scalar `ReviseReplica(targetCluster.Replicas)`；
   `ResourceInterpreter` 没有 `ReviseComponents`，因此也没有把 component result 原子写回模板的协议。

因此当前数据流在“结果记录”处断开：

```text
GetComponents -> spec.Components -> component capacity estimation
                                    |
                                    v
                            TargetCluster{Name}
                                    X
                  TargetCluster.Components -> scale comparison -> component dispatch
```

### 分层状态矩阵

| 层次 | 状态 | 已有基础 | 主要缺口 |
| --- | --- | --- | --- |
| 请求解析 | **已有上游基础** | `GetComponents` 生成 `spec.Components` | Draft 已给同构/双写迁移方向；mismatch 权威与迁移终点未定义 |
| API 结果载体 | **本分支部分完成** | `TargetCluster.Components`、`TargetComponent`、生成物 | 按 Draft PR1 仍缺 `GracefulEvictionTask.Components` 和 result webhook validation |
| Scheduler producer | **未接通** | 已有选择结果和 desired components | `AssignReplicas` 仍只写 cluster name；没有成功结果快照 |
| Reschedule trigger | **未接通** | scheduler 已调用 `IsBindingReplicasChanged` | helper 不比较 request components 与旧 result，scale/swap 不入队 |
| Estimator | **可部分复用** | `MaxAvailableComponentSets` 已支持完整 component set 和 assumptions | 需要验证 scale-up delta、scale-down skip 与旧成功结果如何组合 |
| Dispatch / interpreter | **未实现** | scalar `ReviseReplica` 路径成熟；Draft 已给 PR3 方向 | 缺 `ReviseComponents` interface、webhook/declarative/Lua routing 和错误原子性 |
| 失败保护 | **合同和实现均未闭合** | 普通 `FitError` 有既有处理 | 当前 FitError 会 patch 空 `Clusters`；component scale 应保留旧结果、冻结下发还是采用别的状态，需先确认 |
| Validation / version | **部分完成** | 基础字段 schema 和 list-map 结构存在 | 缺 Draft 要求的 RB membership/duplicate/Gate 校验；partial/mismatch、CRB 与 v1alpha1 main/status 未闭合 |
| 行为测试 | **未覆盖主链路** | equality、conversion 和既有 component scheduling tests | 缺 producer、trigger、scale up/down、dispatch、failure preservation 和 version-skew tests |

### 关键源码证据

| 结论 | exact-SHA 证据 |
| --- | --- |
| 新结果字段及 validation markers 已存在 | [`binding_types.go:286-315`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/apis/work/v1alpha2/binding_types.go#L286-L315) |
| `BindingSnapshot.Clusters` 复用 `TargetCluster` | [`binding_types.go:389-403`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/apis/work/v1alpha2/binding_types.go#L389-L403) |
| component workload 的结果 producer 仍只写 cluster name | [`common.go:50-77`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/scheduler/core/common.go#L50-L77) |
| component estimator 仍以完整 desired components 估算整组容量 | [`estimation.go:75-112`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/scheduler/core/estimation.go#L75-L112) |
| scale trigger 明确不检测 component scale/swap | [`binding.go:37-68`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/util/binding.go#L37-L68) |
| Binding controller 只执行 scalar `ReviseReplica` | [`common.go:74-96`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/controllers/binding/common.go#L74-L96) |
| Resource Interpreter interface 没有 `ReviseComponents` | [`interpreter.go:42-64`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/resourceinterpreter/interpreter.go#L42-L64) |
| `FitError` 路径继续把空结果 patch 到 Binding | [`scheduler.go:590-615`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/scheduler/scheduler.go#L590-L615)、[`scheduler.go:686-702`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/scheduler/scheduler.go#L686-L702) |
| v1alpha1 projection 不保存 component result | [`binding_types_conversion.go:75-133`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/apis/work/v1alpha1/binding_types_conversion.go#L75-L133)、[`binding_types_conversion_test.go:39-52`](https://github.com/ranxi2001/karmada/blob/a3547a3a84ef93e6cf1bf08422ae6465e381d6bd/pkg/apis/work/v1alpha1/binding_types_conversion_test.go#L39-L52) |

### 失败路径需要特别区分

当前通用 scheduler 在没有可行集群时返回 `FitError`；`scheduleResourceBindingWithClusterAffinity` 会继续
执行 `patchScheduleResultForResourceBinding(..., nil)`，后者把 `Spec.Clusters` 设为空。这个行为对普通
“当前集群不再可用”的重调度有清理意义，但不能自动等价为 #7492 想要的安全 scale 语义。

多组件扩容失败时至少有三种可能合同：

1. 保留旧 `Clusters/Components`，并阻止新模板下发。
2. 清空调度结果并删除旧 Work。
3. 另存 pending request/condition，让旧结果继续服务，新结果成功后再原子切换。

#7492 只明确“更新配置不得传播”，没有明确在失败期间旧 workload 是否必须继续运行。Day44 的本地倾向是
保留最近一次成功结果，但这仍是 **INFERENCE**，不能在没有 maintainer 决策时改写通用 FitError 语义。

## API Groundwork PR 完整性

### 可以现在开 PR 的理由

- branch hygiene、DCO、base、远端同步和生成物已经闭合。
- API、conversion、helper regression、`make test` 和 `make verify` 都有 exact-tree 证据。
- diff 聚焦，没有 scheduler/controller 的半成品混入 API patch。
- #7492 maintainer 已明确提出需要 component scheduling result，并给出候选类型结构。

因此，当前 branch 可以作为更窄的 API review surface，但不能再说“没有额外普通代码是 merge-ready
门槛”。维护者 Draft 推荐的 PR1 还包含 `GracefulEvictionTask.Components`、RB result validation 及测试；
若不先补齐，PR body 必须明确这是比 Draft PR1 更窄的拆分，并让 reviewer 判断是否接受该切分。

### PR 不能怎样描述

- 不能写 `Fixes #7492`，因为 umbrella issue 三项行为都未完成。
- 不能宣称 component scale rescheduling 已经工作。
- 不能把 RainbowMango 的 “Proposing the API” 写成已接受或最终合同。
- 不能把 v1alpha1 round-trip 丢字段只描述成无影响的测试细节。

正确的 metadata 应是：

- primary kind：`/kind feature`
- additional kind：`/kind api-change`
- issue relation：`Part of #7492`
- release note：说明新增 `TargetCluster.Components` / `TargetComponent` API，不能写 `NONE`
- reviewer notes：明确 Draft 已回答的设计点、当前 PR1 scope gap、v1alpha1 风险，并说明 trigger、
  estimator、failed-rescheduling safety 和 dispatch 是后续

## 仍需确认的问题

### P0：合并 public API 前必须闭合

#### 1. 当前 branch 如何对齐 Draft PR1？

维护者 Draft 把 PR1 定义为 API、codegen 和 webhook validation，并同时提出
`GracefulEvictionTask.Components`。当前 branch 只有 `TargetCluster` API/codegen/helper，缺：

- `GracefulEvictionTask.Components` 及生成物；
- RB result-name membership、duplicate 与 Gate-off validation；
- 对应 webhook unit tests。

可选路径只有两个：补齐上述 Draft PR1 后再提交 merge-ready PR，或在 exact PR body 中明确做更窄的
API-only split。后者可以用于 review，但不能把 scope 差异隐藏成“已经完成 PR1”。

#### 2. served v1alpha1 如何保护 v1alpha2-only 数据？

当前 v1alpha1 无法表达 `spec.components` 和 `clusters[].components`；conversion test 已证明 typed
round-trip 会丢结果。需要分别决定：

| 操作 | 必须选定的合同 |
| --- | --- |
| v1alpha1 GET | 是否接受只读 lossy projection |
| RB/CRB main update | 接受丢失、拒绝 legacy write，还是 preservation strategy |
| RB/CRB `/status` update | 是否能证明保留 storage spec；若不能，是拒绝还是额外保存 |

**当前倾向**：可以接受只读 projection，但不能接受一次无关的 legacy write 静默删除调度基线。先用真实
API server 建立 main/status baseline，再按 maintainer 选择实现拒绝或保留策略。

#### 3. admission 的未覆盖边界是什么？

Draft 已回答 RB 的 unknown/duplicate/Gate-off 校验和 `BindingSnapshot` max merge，不应再问是否禁用
`requiredBy`。仍需在 PR 中收敛：missing component 是否由 admission 拒绝，scalar/components 不一致时
如何处理，CRB 是否需要对等 validator，以及 Gate strict-reject 对已存在对象/滚动降级的操作影响。

### P1：后续实现要确认，但不阻止创建 groundwork PR

1. **scale trigger / backfill**：Draft 已指定 scheduler 写 full set/dual-write，但没有说明旧对象如何
   backfill，`IsBindingReplicasChanged` 是唯一 trigger 还是还要修改 detector/controller event path。
2. **失败状态机**：无可行集群时，谁保留旧成功结果、谁阻止 binding controller 使用新模板，以及什么
   condition 表示 pending/failed reschedule。
3. **estimator 输入**：scale-up 的 delta 是由 scheduler 先计算后传入 estimator，还是 estimator 同时接收
   desired 与 scheduled snapshot；scale-down 如何绕过 estimate 而不绕过 placement/eligibility 检查。
4. **`ReviseComponents` 错误合同**：Draft 已把它放入 PR3，并允许 single-component fallback；仍需明确
   多组件修改是否 all-or-nothing、partial mutation 如何回滚，以及 third-party interpreter error 行为。
5. **snapshot/eviction consumers**：按 Draft 实现 `BindingSnapshot` component max merge、
   `GracefulEvictionTask.Components` 快照和 FRQ accounting，并确定对应 unit/integration tests。

### P2：移出当前 API PR，另做设计或复现

1. **跨集群重调度的应用状态保留**：`mszacillo` 观察到 workload 被迁往新集群时“不保留状态”，但尚未
   给出 workload kind、状态类型、复现步骤或期望 continuity contract。这可能涉及存储、checkpoint、
   workload-specific migration，不是增加 replica result 字段即可解决。除非 maintainer 明确纳入 phase IV，
   否则应单独复现和设计。
2. **收紧既有 request schema**：给 `Component.Name` 增加 `MinLength`、把 `spec.components` 改成
   name-keyed map-list、统一 RB/CRB admission 都会改变既有对象或 SSA/merge 语义，不应顺带塞进当前
   result API PR。
3. **长期 API 迁移**：`Replicas` / `ReplicaRequirements` 是否 deprecated、是否改 pointer、何时删除
   scalar path，不属于本次最小结果载体。
4. **扩展场景**：component 跨多个集群拆分、add/remove/rename、HPA、Descheduler 和通用状态迁移均
   另行设计；FRQ 与 `GracefulEvictionTask.Components` 已在 Draft 内，不再归为无方向的扩展项。

## 证据边界

| 标签 | 本文中的含义 | 本轮结论 |
| --- | --- | --- |
| `MAINTAINER` | #7492 正文、真人讨论，以及用户确认的 RainbowMango `c14af2f1` Draft | 方案 B、双写、producer、snapshot merge、interpreter 和 PR 切分已有 maintainer direction；仍非 merged project consensus |
| `CODE` | `a3547a3a8` 及其基线源码 | 新字段无 production producer/consumer；trigger、dispatch 和 FitError 行为可由源码证明 |
| `OBS` | exact-tree 测试结果、git/remote/issue 回读 | branch clean、0 behind/1 ahead、测试和 verify 通过、无关联 PR |
| `INFERENCE` | 对完成度、失败状态机和兼容方案的工程判断 | 完整 feature 约 25%、last-success 保留和 v1alpha1 保护建议仍等待 PR/maintainer 收敛 |

`TargetComponent.Replicas int32` 的 pointer 疑问已经由提问者主动撤回；这只关闭该局部问题，不表示完整
API 已获 approval。维护者 Draft 与 #7492 snippet 在 “only multiple pod templates” 上仍有文字冲突；
本文采用 Draft 更具体的 single-component 双写步骤，并把注释最终措辞留给 PR review。

## 下一步

1. 先决定按维护者 Draft 补齐 PR1 的 `GracefulEvictionTask.Components`、RB result validation/tests，
   还是提交更窄的 API-only review PR；后一种必须在 exact body 披露 scope 差异。
2. 基于官方 PR template 准备 150–400 词的 exact English title/body，使用 `/kind feature`、
   `/kind api-change` 和 `Part of #7492`；用户确认 exact target/text 后再创建 upstream PR。
3. 用真实 API server 覆盖 v1alpha1 main/status read-modify-write，再按 maintainer 选择实现拒绝或保留策略。
4. 按 Draft PR2/PR3 实现 scheduler full-set/dual-write producer、snapshot merge、scale trigger/delta、
   `ReviseComponents`/dispatch 和 failed-rescheduling safety，再推进 third-party/Flink E2E 与 downstream。
5. 生产链路闭合前，不勾选 issue 正文三项，也不宣称完整 feature 可用。
