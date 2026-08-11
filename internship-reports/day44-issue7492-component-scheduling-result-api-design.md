# Day 44：#7492 多组件调度结果 API 设计

- 日期：2026-08-11
- Maintainer API proposal：[`RainbowMango` 在 #7492 的 API 回复](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5248383498)
- 最新 API 讨论：[`TargetComponent.Replicas` 保持 `int32`](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5252661190)
- 最新场景补充：[`mszacillo` 提醒跨集群重调度可能丢失应用状态](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5254150877)，尚无复现细节或已接受合同
- Maintainer-provided Draft：[`RainbowMango/pr_multi_component_next_move@c14af2f1119a66d4672a814cc80f7612943d35d3`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md)
- 源码基线：[`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`](https://github.com/karmada-io/karmada/commit/1c278577e7892b6ea44f86a4317c1eb1e013bb93)
- 状态复核：2026-08-12（补充维护者 Draft 答案）
- 上游状态：issue 正文三项仍未勾选，无关联 PR；文档仍标记为 `Draft (design discussion, not yet a formal proposal)`
- 本文范围：先固定 API 合同；文末追加个人特性分支的 API 实测，不包含调度行为实现

> 证据定位：用户确认上述文档是维护者为本特性提供的设计资料。本文因此把文档中已经明确选择的
> 方案固定为当前实现依据，不再重复列为“待询问 maintainer”。但该文档位于维护者 fork，且自身仍
> 标记为 Draft；“已有答案”表示 maintainer-provided direction，不等于已经合入 upstream 的正式合同。

## 先说人话

`spec.components` 表示用户当前申请的每个组件副本数；
`spec.clusters[].components` 表示分配到该集群的组件调度结果。Day44 建议把它作为“最近一次成功结果”，
但维护者 Draft 尚未定义失败重调度时是否保留旧值。

例如，FlinkDeployment 请求 `jobmanager=1`、`taskmanager=20`，成功调度到
`member1` 后，结果写成：

```yaml
spec:
  components:
  - name: jobmanager
    replicas: 1
  - name: taskmanager
    replicas: 20
  clusters:
  - name: member1
    components:
    - name: jobmanager
      replicas: 1
    - name: taskmanager
      replicas: 20
```

维护者 Draft 已经回答“结果长什么样、由谁写、怎样下发”：多组件结果写完整 component set；
单组件迁移期同时写 scalar `Replicas` 和一个 `Components` entry；Binding controller 通过
`ReviseComponents` 下发。它没有回答“新请求调度失败时，旧成功结果是否保留、谁阻止新模板下发”，
所以失败状态机仍是本文保留的核心未决项。

## API 边界

本版的行为目标仍是 `MultiplePodTemplatesScheduling` 下的 component scale。已合入的 #7287
证明只要 `spec.components` 非空，即使只有一个 component，也会进入 component-based scheduling
path；维护者 Draft 则补上了结果编码：迁移期单组件双写 scalar 与 component，多组件写完整
component set。本文讨论：

1. `TargetCluster.Components`：集群维度的组件调度结果。
2. `TargetComponent`：结果侧最小组件分配单元。
3. `ReviseComponents`：把一个集群的组件结果写回资源模板的 Resource Interpreter 操作。
4. `GracefulEvictionTask.Components` 与 `BindingSnapshot` 的组件结果传播。
5. `v1alpha2` 的功能版本合同，以及 Draft 未覆盖的 `v1alpha1` legacy projection 保护规则。

其中，第 1、2 项也出现在 #7492 maintainer 回复；第 3、4 项以及 producer、validation、PR 切分来自
维护者 Draft。后文明确标记为“Day44 补充”的失败保护、版本兼容和原子性内容仍只是本地候选合同。

[#7287](https://github.com/karmada-io/karmada/pull/7287/files) 已把 component-based scheduling
入口从 `len(spec.Components) >= 2` 改为 `len(spec.Components) > 0`。#7492 issue snippet 中的
“only for workloads with multiple pod templates” 与 Draft 正文明确的 single-component 双写存在文字
冲突；本文按更具体的 producer 路线记录双写，并把公开 API 注释对齐留给 PR review，而不是重新把
编码选择列为无答案。

本版不定义：

- 把不同组件或同一组件的副本拆到多个集群。
- 迁移完成后何时弃用 `Replicas` / `ReplicaRequirements`。
- 组件 add、remove 或 rename；本版只处理组件集合不变时的 replicas 变化。
- 扩缩容失败时旧 Work/旧成功结果的生命周期和 condition。
- `v1alpha1` main/status read-modify-write 的字段保护。
- HPA、Descheduler、可观测性 API，以及跨集群迁移时应用状态连续性。

## Maintainer 提出的 Work API

以下类型逐字对应 [#7492 maintainer 回复](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5248383498)：

```go
// TargetCluster represents the identifier of a member cluster.
type TargetCluster struct {
	// Name of target cluster.
	Name string `json:"name"`

	// Replicas in target cluster.
	// +optional
	Replicas int32 `json:"replicas,omitempty"`

	// Components represents the per-component replica assignment in this cluster.
	// It is populated only for workloads with multiple pod templates, and only
	// when the MultiplePodTemplatesScheduling feature gate is enabled.
	// Each entry corresponds to an entry in spec.Components by Name.
	// +optional
	Components []TargetComponent `json:"components,omitempty"`
}

// TargetComponent represents the replica assignment of a component in a cluster.
type TargetComponent struct {
	// Name of the component, matching spec.components[*].name.
	// +required
	Name string `json:"name"`

	// Replicas of this component assigned to the cluster.
	// +required
	Replicas int32 `json:"replicas"`
}
```

该 issue 回复把结果限定为多 Pod template 工作负载且 feature gate 开启时填充，并保留现有
`Replicas` 字段。维护者 Draft 的 producer 章节进一步明确：single-component + `Divided` 在迁移期
双写 `Replicas` 与单元素 `Components`。两处文字存在冲突，feature 分支把注释改成中性的
component-based result 是合理的；实现方向按 Draft 的具体双写步骤记录，公开注释最终措辞由 PR
review 收敛。`Replicas` 暂不增加 deprecated 标记。

### `Replicas` 类型讨论

`zhzhuang-zju` 曾询问 `TargetComponent.Replicas` 是否应从 `int32` 改为 `*int32`，以便未来
区分零值和未指定；`RainbowMango` 要求给出必须使用指针的具体场景。提问者随后
[撤回该疑问](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5252661190)：
对于 `ConfigMap` 等非 workload 资源，整个 `TargetCluster.Components` 为 `nil` 已能表达
“不适用”，结果项内部不再需要用指针区分未指定和显式零值。

因此当前 API snippet 继续使用 `Replicas int32`。这只表示该局部类型疑问已经收敛，
不表示完整 API 或 Day44 补充合同已经获得 upstream approval。

## Maintainer-provided Draft 已固定的答案

以下内容已有维护者资料，不再列入待确认清单：

证据可直接定位到固定 commit：[`方案 B、API 与 single-component 双写`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md#L66-L113)、
[`producer 与 webhook validation`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md#L131-L159)、
[`ReviseComponents、BindingSnapshot 与 eviction`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md#L161-L222)、
[`PR 切分`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md#L235-L243)。

| 设计点 | Draft 给出的方向 | 当前代码状态 |
| --- | --- | --- |
| 结果结构 | 选择方案 B，在每个 `TargetCluster` 内增加 name-keyed `Components` | feature branch 已完成类型和生成物 |
| request/result 关系 | 两侧结构同构；`Components` 是迁移方向，legacy scalar 过渡期双写 | 分支仅有结果载体 |
| single component | `Divided` 路径同时写 `TargetCluster.Replicas=r` 和 `Components=[{name, replicas:r}]` | producer 未实现 |
| multi component | `Duplicated` 路径写 `fullComponentSetOf(spec.Components)` | producer 未实现 |
| 结果校验 | RB webhook 校验 result name 属于 request、同 cluster 不重复；Gate 关闭时拒绝携带结果字段 | 分支未实现 result webhook validation |
| `BindingSnapshot` | 继续复用 `TargetCluster`；merge 时同名 component 的 replicas 取最大值，与 scalar 规则对齐 | merge helper 未实现 component 语义 |
| 下发 | 新增 `ReviseComponents` 并贯通 built-in、declarative、webhook、third-party 与 karmadactl；单 component 可 fallback 到 `ReviseReplica` | 未实现 |
| 驱逐/故障迁移 | `GracefulEvictionTask` 增加 `Components`，保存被驱逐集群的 component result | 当前 API branch 未包含 |
| PR 切分 | PR1 API+codegen+webhook；PR2 scheduler 双写；PR3 `ReviseComponents`+ensureWork；PR4 third-party+Flink E2E；PR5 downstream | 当前 branch 只覆盖 PR1 的 API/codegen 部分 |

> 注释：Draft 要求正常 producer 写完整集合，但没有规定调度失败是否保留“最近一次成功结果”；
> webhook 列表也没有明确要求拒绝 missing component。完整 producer 输出与失败提交语义不能混为一谈。

## Day44 结果合同：已回答部分与本地补充

> 分析：single-component 双写、multi-component full-set producer 和 `BindingSnapshot` merge 已由
> 维护者 Draft 给出方向；“最近一次成功结果”、失败保留、partial admission 和 scalar/component
> 不一致处理仍是 Day44 补充候选，不能据此宣称上游 API 已定稿。

| 字段 | 合同 |
| --- | --- |
| `TargetCluster.Components` | 当前集群的组件调度结果；正常 producer 写完整 component set |
| `TargetComponent.Name` | 对应 `ResourceBindingSpec.Components[*].Name`；非空，且在一个 `TargetCluster` 内唯一 |
| `TargetComponent.Replicas` | 该组件在当前集群的已接受副本数；必须大于等于 0 |
| `TargetCluster.Replicas` | 保留 legacy scalar 语义；single-component 迁移期与一个 component entry 双写 |

`TargetCluster.Components` 采用 name-keyed、order-insensitive 语义。维护者 Draft 已明确：

- scheduler producer 从 `spec.components` 写完整集合，不写 delta；
- result name 必须属于 request components；
- 同一 `TargetCluster` 内每个 name 只出现一次。

零副本应显式编码为 `{name: <component>, replicas: 0}`。是否还要在 admission 层拒绝缺少请求组件的
partial result，Draft 没有明确写出，不能把 producer 的 full-set 责任自动升级为 API rejection。

`TargetCluster` 也被 `BindingSnapshot.Clusters` 复用。维护者 Draft 明确选择继续复用：
`spec.requiredBy[*].clusters[*].components` 是有意暴露的 surface，合并 snapshot 时按 component name
匹配并取最大 replicas，行为与现有 scalar merge 对齐。

`work.karmada.io/v1alpha2` 的 `ResourceBinding` 与 `ClusterResourceBinding` schema 必须将该
列表声明为 `x-kubernetes-list-type: map`，并将 `name` 声明为
`x-kubernetes-list-map-keys`。这是本地补充约束，不属于 maintainer 回复中的原始类型。

### 缺失、空列表与零值

API 将 absent、`null` 与 `[]` 视为语义等价的“无组件结果”。Go `omitempty` 通常把 `nil`
或空 slice 编码为 absent。三种输入统一表示：

- 当前对象还没有组件级调度结果；或
- 当前对象只包含 legacy scalar result。

`replicas: 0` 与“没有该组件结果”不同。前者保留 `TargetComponent` entry，后者表现为整个
`components` 字段缺失。

### 请求侧与结果侧

请求侧 `Component` 包含 name、replicas 和 `ReplicaRequirements`；结果侧
`TargetComponent` 只包含 name 和 replicas。两者按 `Name` 关联。

结果侧不复制 `ReplicaRequirements`、`NodeClaim`、`ResourceRequest` 或
`PriorityClassName`。

### 结果不变量

Day44 的本地候选是：`spec.clusters[].components` 保存最近一次成功调度结果，在新结果成功提交前
保持原值，失败的重调度不覆盖或清空已有结果。维护者 Draft 没有定义这一失败状态机，因此后续不能
仅凭这段文字改写通用 `FitError` 行为。

## Maintainer Draft 固定的 Resource Interpreter 方向

详细 Draft 提出 `ReviseComponents`，用于把一个目标集群的组件副本结果写回资源模板：

```go
// ReviseComponents revises the per-component replicas of the object
// according to the scheduling result on a specific cluster.
ReviseComponents(
	object *unstructured.Unstructured,
	components []workv1alpha2.TargetComponent,
) (*unstructured.Unstructured, error)
```

## Day44 补充合同：Interpreter 细节

### Operation

API、Go interface、Lua function 与 webhook operation 统一使用复数形式：

```go
const (
	InterpreterOperationReviseComponents InterpreterOperation = "ReviseComponents"
)
```

不定义 `ReviseComponent` operation。

### Webhook request

`ResourceInterpreterRequest` 增加：

```go
// DesiredComponents contains the component replica assignment that the webhook
// should apply to Object.
// It is set only for InterpreterOperationReviseComponents.
// +optional
DesiredComponents []workv1alpha2.TargetComponent `json:"components,omitempty"`
```

响应继续使用现有 JSON Patch 合同，不增加 response 字段。

请求字段构成判别联合：

- `operation=ReviseComponents` 当且仅当 `DesiredComponents` 非空。
- `DesiredComponents` 与 `DesiredReplicas` 互斥。
- 其他 operation 携带 `DesiredComponents` 时，请求无效。
- `DesiredComponents` 按 name 消费，不依赖列表顺序。

```yaml
request:
  operation: ReviseComponents
  object:
    apiVersion: flink.apache.org/v1beta1
    kind: FlinkDeployment
    metadata:
      name: analytics
  components:
  - name: jobmanager
    replicas: 1
  - name: taskmanager
    replicas: 20
```

### Declarative customization

详细 Draft 提出 `CustomizationRules.ComponentRevision`；Day44 将字段形状固定为：

```go
// ComponentRevision describes how to revise component replicas.
// +optional
ComponentRevision *ComponentRevision `json:"componentRevision,omitempty"`

// ComponentRevision holds the script for revising component replicas.
type ComponentRevision struct {
	// +required
	LuaScript string `json:"luaScript"`
}
```

Lua contract：

```lua
function ReviseComponents(desiredObj, components)
    -- components is a list of { name = string, replicas = integer }
    -- revise every named component in desiredObj
    return desiredObj
end
```

`components` 是一个 `TargetCluster.Components` 的完整 producer 结果。Draft 允许只有一个 component
时 fallback 到现有 `ReviseReplica`；多组件必须调用 `ReviseComponents`。hook 未声明、解释器发生错误
或返回 partial mutation 时如何回滚，Draft 没有明确原子性合同，仍需在 PR3 设计与测试中收敛。

## Day44 补充合同：校验

### 结构校验

- `TargetComponent.Name` 必填且非空。当前请求侧 `Component.Name` 的 CRD 只有
  `MaxLength=32`，并没有同等的 `MinLength=1`；二者如何统一见后文 review 复核。
- `TargetComponent.Replicas >= 0`。
- 同一 `TargetCluster.Components` 内的 name 唯一。
- `DesiredComponents` 复用相同的 name、replicas 和唯一性约束。

### 跨字段校验

维护者 Draft 已指定 RB validating webhook 检查：

- result component name 必须存在于 request `spec.components`；
- 同一 `TargetCluster` 内不允许重复 name；
- Gate 关闭时拒绝携带 `TargetCluster.Components`。

Draft 没有要求 scalar 与 components 互斥；相反，single-component 迁移期需要双写。它也没有明确
partial result 的 admission 规则、ClusterResourceBinding 的 validator 或 RB/CRB 共享校验方式，
这些仍是实现边界问题。

## Day44 补充合同：版本与 Feature Gate

### Served versions

- `v1alpha2` 继续作为 storage version。
- `TargetCluster.Components` 只加入 `v1alpha2`；`v1alpha1` 保持现有 legacy schema。
- 从 `v1alpha2` 转为 `v1alpha1` 时，`spec.components` 和
  `spec.clusters[].components` 都不出现在 legacy projection 中。
- `v1alpha1` payload 中的 component-only 字段不是该版本的 API；API server 可以按其 field
  validation 模式 prune 或拒绝未知字段，它们不会创建 component-aware state。
- 若 storage object 已包含 `spec.components` 或 `spec.clusters[].components`，通过
  `v1alpha1` 发起的 main-resource update 必须由 admission 拒绝，包括只修改 metadata 的
  main-resource update。调用方必须改用 `v1alpha2`。
- `v1alpha1` 的 status subresource update 可以接受，但不得修改、清空或重建 storage spec。
- conversion 不根据 legacy scalar 字段合成组件请求或组件结果。

> 分析：status 条目是 Day44 的目标合同，不是当前 branch 已有保证。Kubernetes 为每个 served
> version 构造的 storage codec 会按请求版本解码旧对象；v1alpha1 视图可能在 status strategy
> 复制 old object 之前就已丢掉 v1alpha2-only spec。必须用真实 API server 用例证明保留行为。

### Feature Gate

- Gate 开启：component-based producer 可以新增或更新 `TargetCluster.Components`，consumer 可以调用
  `ReviseComponents`。
- Gate 关闭：按维护者 Draft 的明确方向，validating webhook 拒绝携带
  `TargetCluster.Components` 的 ResourceBinding。
- Gate 关闭时，consumer 不执行 `ReviseComponents`。

Draft 没有展开滚动降级时已有对象如何清理或完成无关字段更新；当前不能用 Day44 原先提出的
grandfathering 规则覆盖维护者给出的 strict-reject 方向。

## 兼容性矩阵

| 工作负载 / 对象 | `TargetCluster.Replicas` | `TargetCluster.Components` |
| --- | --- | --- |
| Existing scalar workload，`spec.components` 为空 | 既有值 | 缺失 |
| Existing object without component result | 既有值或 0 | 缺失 |
| Single-component binding under gate | 组件副本数 | 同名的一个 entry；迁移期双写 |
| Multi-component binding under gate | 0 / omitted | 完整调度结果快照 |

Draft 的迁移路线是 request/result 两侧逐步改用 `Components`，传统 single-template workload 在
过渡期双写 scalar 与单元素 component。何时完成迁移并标记 scalar deprecated 尚未定义。

## API 验收用例

在 `v1alpha2` 且 Gate 开启时，以下对象必须被接受：

- 完整且 name 唯一的组件结果。
- `spec.components` 只有一个 entry 时，同时接受 scalar 与对应的一个结果 entry。
- 组件顺序与请求不同、但 name 集合相同的结果。
- 带显式 `replicas: 0` 的完整结果。
- 不含 `components` 的 legacy object。

Gate 关闭时，按 Draft 方向拒绝携带 component result 的 RB。`v1alpha1` status subresource update
是否能保留 storage spec 仍需真实 API server 证明。

以下对象必须被拒绝：

- 空 name、重复 name 或负 replicas。
- 包含请求中不存在 name 的结果。
- `ReviseComponents` 与 `DesiredReplicas` 同时出现，或其他 operation 携带
  `DesiredComponents`。
- Gate 关闭时携带非空 component result。
- 通过 `v1alpha1` main resource 更新已有 component-aware storage object。

partial-result rejection、scalar/component mismatch、v1alpha1 preservation 与 interpreter 原子性不在
Draft 的已回答集合中。Scheduler producer、snapshot merge、Work 下发和 FRQ accounting 的方向已有
设计，但当前 feature branch 尚未实现。

## 特性分支实测：API 基础可编译，但合同尚未闭合

- 测试分支：[`ranxi2001/feature/multi-component-scale-rescheduling`](https://github.com/karmada-io/karmada/compare/master...ranxi2001:karmada:feature/multi-component-scale-rescheduling)
- 测试 HEAD：[`b0501d9b2ae036b956e1ea815cd0d75899f4bcb3`](https://github.com/ranxi2001/karmada/commit/b0501d9b2ae036b956e1ea815cd0d75899f4bcb3)
- merge base：[`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`](https://github.com/karmada-io/karmada/commit/1c278577e7892b6ea44f86a4317c1eb1e013bb93)
- 本地测试完成时间：2026-08-11T22:10:00+08:00

### 结论

这个分支已经把 `TargetCluster.Components`、`TargetComponent`、CRD、OpenAPI、deepcopy、
apply configuration 和 v1alpha1 legacy projection 放进代码，仓库标准单测、静态检查和生成检查
都能通过。
但它还没有覆盖维护者 Draft 建议的 PR1 范围：缺 result-side webhook validation 及其测试，也没有
`GracefulEvictionTask.Components`。最初按 Day44 本地候选合同执行的 11 个 CRD 用例中有 4 个被
schema 接受；对照维护者 Draft 后，只有 unknown-name rejection 是明确缺口，partial、scalar 共存和
`requiredBy` 三项不能再标成 schema 合同失败。测试 helper 当时还把 component 顺序变化误判成结果变化。

更直观地说，若请求声明 `worker` 和 `master` 两个组件，下面这个结果缺少 `master`：

```yaml
spec:
  components:
  - name: worker
    replicas: 2
  - name: master
    replicas: 1
  clusters:
  - name: member1
    components:
    - name: worker
      replicas: 2
```

当前 CRD 校验对这个 partial result 返回 `errors=[]`。维护者 Draft 要求 producer 输出 full set，
但没有明确要求 admission 拒绝 partial input，因此该观察只能说明校验边界待定。unknown component
则已明确应由 RB webhook 拒绝；scalar/component 双写和 `requiredBy` component result 都是 Draft
允许或要求的路径。`make verify` 全绿只能证明代码和生成物一致，不能证明 webhook 与运行时合同已实现。

### 实际运行过程

测试在独立 worktree `/home/ranxi/projects/karmada-feature-multi-component-scale-rescheduling`
进行，本轮没有新增特性分支提交或推送。先跑已有单测和生成检查，再用临时 Go 测试夹具加载生成后的
ResourceBinding CRD，调用 Kubernetes `ValidateCustomResource` 和
`ValidateListSetsAndMaps` 执行对象矩阵。夹具完成后已删除，工作树恢复干净。

第一次执行 `hack/verify-codegen.sh` 时，`GOTOOLCHAIN=auto` 把 Go 1.26.5 下载到脚本临时
`_go/`，只读 module cache 导致退出清理报 `Permission denied`。清理该临时目录后，直接使用
已下载的 Go 1.26.5 binary 并设置 `GOTOOLCHAIN=local`，codegen 和完整 `make verify` 均通过。
这也确认当前 `go.mod` 与 `.go-version` 已要求 1.26.5，原本记录的 1.26.4 已过期。

### 已通过的检查

| 检查 | 结果 | 证明范围 |
| --- | --- | --- |
| `go test ./pkg/apis/work/v1alpha1 -run '^TestConvertBindingSpec' -count=1 -v` | PASS | legacy cluster 保留；v1alpha2 component result 转为 v1alpha1 后被投影掉 |
| `go test ./pkg/apis/work/... ./test/helper` | PASS | work API 包通过；`test/helper` 仅完成编译，本身没有测试文件 |
| `go test ./pkg/webhook/resourcebinding -count=1` | PASS | 既有 ResourceBinding webhook 回归通过，不覆盖结果侧 `clusters[*].components` |
| `go test ./pkg/generated/...` | PASS | apply configuration、client、informer、lister、OpenAPI 生成包可编译 |
| `make test` | PASS | race-enabled 的 `pkg/...`、`cmd/...`、`examples/...`、`operator/...` 全部通过 |
| `hack/verify-crdgen.sh`、`hack/verify-codegen.sh`、`hack/verify-swagger-docs.sh` | PASS | 提交的 CRD、codegen 与 Swagger 没有生成漂移 |
| `make verify` | PASS | lifted、imports、staticcheck、mocks、gofmt、vendor、生成物和 license 全部通过 |
| `git diff --check upstream/master...HEAD` | PASS | patch 无 whitespace error |

### Day44 可执行验收矩阵

`Draft/候选结果` 区分维护者 Draft 的明确方向与 Day44 当时的本地候选；`分支实际` 来自临时 schema
测试的直接观察。
临时夹具执行命令为
`go test -mod=mod ./_scratch -run '^TestDay44SchemaContract$' -count=1 -v`；测试按 Day44 当时的本地
候选合同断言，因此在 4 个接受项上退出失败。维护者 Draft 提供后，下面已按新的证据层级重分类；
原始失败不能继续整体当作 maintainer contract failure。夹具已删除，命令仅作为本轮执行记录。

| 用例 | Draft/候选结果 | 分支实际 | 判定 |
| --- | --- | --- | --- |
| 完整且 name 唯一 | 接受 | 接受 | 符合 |
| 组件顺序不同、name 集合相同 | 接受 | CRD 接受 | schema 符合 |
| 显式 `replicas: 0` | 接受 | 接受 | 符合 |
| legacy object 不含 `components` | 接受 | 接受 | 符合 |
| 空 name | 拒绝 | `minLength: 1` 拒绝 | 符合 |
| 重复 name | 拒绝 | list-map 唯一性校验拒绝 | 符合 |
| 负 replicas | 拒绝 | `minimum: 0` 拒绝 | 符合 |
| partial result | producer 不应产生；admission 未定义 | 接受，`errors=[]` | **仍需明确 validation 边界** |
| unknown component name | Draft 要求 RB webhook 拒绝 | 接受，`errors=[]` | **PR1 实现缺口** |
| 非零 scalar `replicas` 与 `components` 共存 | single component 迁移期必须接受 | 接受，`errors=[]` | **不能作为通用拒绝用例** |
| `requiredBy[*].clusters[*].components` 非空 | Draft 有意复用并定义 max merge | 接受，`errors=[]` | **schema 符合；merge 尚未实现** |

此外，针对 [`test/helper/scheduler.go`](https://github.com/ranxi2001/karmada/blob/b0501d9b2ae036b956e1ea815cd0d75899f4bcb3/test/helper/scheduler.go#L27-L39)
补的临时回归用例失败：两份结果只有 component 顺序不同，`IsScheduleResultEqual` 仍返回
`false`。原因是新实现对整个 `TargetCluster` 使用 `reflect.DeepEqual`，而 Day44 把
`Components` 定义为 name-keyed、order-insensitive 列表。这个问题影响测试判等，不是 CRD
接收行为。

### 尚未实现或尚未实测的合同

- `ReviseComponents`、`DesiredComponents` 和 `ComponentRevision` 在该分支中不存在，因此相关
  接受/拒绝用例无法执行。
- 现有 validating webhook 只在 Gate 开启时检查请求侧 `spec.components` 的空名和重复名，
  不检查 `spec.clusters[*].components`，也没有实现 Draft 要求的 Gate-off rejection。
- `ClusterResourceBinding` 没有对应 validating webhook；两份 CRD 都复用 `TargetCluster`，
  因而都把 `components` 暴露给 `requiredBy`，但 snapshot component max-merge 尚未实现或测试。
- v1alpha1 conversion 单测已证明 component result 会被投影掉，但该分支没有用于阻止 v1alpha1
  main-resource update 的 admission 保护。真实 API server 上的数据丢失路径本轮未复现，当前结论
  是源码确认的兼容性风险，不是已观察事故。
- 仓库没有现成 envtest/kube-apiserver fixture，本轮没有实测 v1alpha1 status update、Gate 切换
  update 或完整 admission/conversion 链路。
- 分支没有 Draft PR2 的 scheduler producer、PR3 的 interpreter/binding controller、snapshot merge
  或 FRQ/eviction consumer；#7492 正文三项行为均不在这两个 commit 的测试范围内。

## 第三方 review 复核

### 复核结论

如果把当前 2 个 commit 作为 API groundwork PR 提交，给出 `Request changes` 是合理的。
但四项意见的证据强度和影响范围并不相同：

| 意见 | 复核结论 | 影响边界 |
| --- | --- | --- |
| `IsScheduleResultEqual` 不应直接 `reflect.DeepEqual` | **成立** | P2 测试语义错误；7 个调用方都在 `_test.go`，不是生产调度回归 |
| 新注释排除了 single-component | **指出了真实冲突；维护者 Draft 已给出双写方向** | scheduling path 已覆盖单 component；producer 章节要求迁移期双写，公开注释需在 PR review 对齐 |
| `Component.Name` 与 `TargetComponent.Name` 的 `MinLength` 不一致 | **事实成立，影响需补充上下文** | ResourceBinding webhook 已拒绝空 name；ClusterResourceBinding 没有 validating webhook，结构层不一致仍然存在 |
| v1alpha1 round-trip 丢结果 | **风险成立，且不只需检查 main PUT** | typed conversion 已有单测；main/status 的真实 API server 用例未跑，maintainer 兼容策略尚未确认 |

这份 review 开头还有一句需要收窄：`TargetCluster.Components` 并没有“解决”
`IsBindingReplicasChanged`。当前分支对 `pkg/util/binding.go` 没有任何修改；该函数的现有注释仍明确
只处理 `clusters` 被清空的 failover，不检测 component scale 或 component swap。新字段只是未来比较
“当前请求”和“上次调度结果”所需的数据载体，当前还没有生产代码写入或读取它。

### 判等意见成立，但只影响测试

`TargetCluster.Components` 使用 `+listType=map` 和 `+listMapKey=name`。Kubernetes 的
[CRD validation 语义](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#validation-rules)
明确说明 map-list 的相等性忽略元素顺序；`reflect.DeepEqual` 却按 slice 下标比较，并区分
`nil` 与非 nil 空 slice。因此下列两组结果都应相等，当前 helper 都会返回 `false`：

```text
[worker=2, master=1] == [master=1, worker=2]
Components: nil      == Components: []
```

第三方给出的按 `name -> replicas` 比较方向正确。更稳妥的实现应在每个 `TargetCluster` 内把
component 规范化为 `map[name]TargetComponent`，检测重复 name，并比较其余 cluster 字段；这样未来
`TargetComponent` 新增字段时不会被 `map[string]int32` 静默忽略。至少补以下回归：

- component 反序仍相等；
- `nil` 与空 components 相等；
- component replicas 不同不相等；
- missing、unknown 或 duplicate component 不相等。

### Single-component 意见找到冲突，Draft 已给出实现方向

[#7287](https://github.com/karmada-io/karmada/pull/7287/files) 已在 2026-03-18 合入：
`isMultiTemplateSchedulingApplicable` 从 `len(spec.Components) < 2` 改为
`len(spec.Components) == 0`，`IsBindingReplicasChanged` 也从 `> 1` 改为 `> 0`，并添加单 component
用例。该 PR 是当前 master 的已接受实现；#7492 中“only for workloads with multiple pod
templates”的新 snippet 则是结果 API proposal。单看 #7287 确实无法推出结果编码；但用户随后提供的
维护者 Draft 明确要求 single-component + `Divided` 双写 scalar 与单元素 component。第三方 review
找到的冲突成立，答案不再是三选一，而是按 Draft 双写，并在 PR review 修正或解释公开注释。

建议将新字段注释改为：

```go
// Components represents the per-component replica assignment in this cluster.
// It is used to record component-based scheduling results when the
// MultiplePodTemplatesScheduling feature gate is enabled.
// Each entry corresponds to an entry in spec.Components by Name.
```

该候选文案删除未经解释的 “only multiple” 限定，并与 Draft 的双写路线兼容。feature branch 保持
中性注释没有问题；scheduler producer 的具体行为已有维护者资料，不再放入待确认问题。

`MinLength` 观察也属实，但不应简单删除结果侧约束。请求侧 `Component.Name` 的 CRD 只有
`MaxLength=32`；ResourceBinding 在 Gate 开启时由 webhook 拒绝空 name 和重复 name，
ClusterResourceBinding 却没有 validating webhook。结果侧 `TargetComponent.Name` 的
`MinLength=1` 因此暴露了既有 RB/CRB schema 差异。优先方向是评估把请求侧结构约束向上对齐，
或定义 grandfathering/admission 路线，而不是让新的 map key 接受空字符串。

### v1alpha1 风险成立，但不是新字段独有

最终安装产物通过 `charts/karmada/_crds/kustomization.yaml` 给 ResourceBinding 和
ClusterResourceBinding 加入 `strategy: Webhook` 的 conversion，并由 `/convert` 调用 Go
conversion；本轮 `kubectl kustomize charts/karmada/_crds` 已确认两种资源都包含该 patch。
两份 CRD 同时保持 `v1alpha1 served=true, storage=false` 和
`v1alpha2 served=true, storage=true`。Kubernetes
[CRD versioning 文档](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#writing-reading-and-updating-versioned-customresourcedefinition-objects)
说明：客户端可以读取任一 served version；更新对象时会按当前 storage version 重写，非 storage
version 的 PUT 会触发 conversion。

分支单测已经直接证明 `v1alpha2 -> v1alpha1 -> v1alpha2` 后
`TargetCluster.Components` 为空。真实 API server 的完整 GET/PUT 链路本轮未复现，所以这里记录为
源码和平台合同支持的兼容性风险，不写成已观察事故。

ClusterResourceBinding 没有 UPDATE validating webhook，因此从源码看，其 v1alpha1
main-resource GET-modify-PUT 会丢失 component request/result。ResourceBinding 有 validating webhook，但 handler 对
v1alpha1 请求的实际解码/拒绝结果尚未做 API-server 实测；不能把可能的 decode failure 当成有意的
字段保护。

更深一层的 Kubernetes 源码复核表明，不能直接把 `/status` 当成安全例外：每个 served version
storage 的 `decoderVersion` 是请求版本，existing object 可能先经 conversion webhook 降为
v1alpha1；status strategy 随后复制的是这份已经 lossy 的 old object，再把 status 替换回去。
当前 validating webhook 的 resource rule 也只匹配 `resourcebindings`，不匹配
`resourcebindings/status`。因此“v1alpha1 status update 保留 storage spec”仍是待实现、待实测的
合同，而不是框架自动提供的保证。

这也不是本 patch 首次引入的整个问题：既有 `ResourceBindingSpec.Components` 同样不在
v1alpha1 projection 中。按预期 component-based 合同，新字段没有扩大受影响对象集合，但会让
同一次 legacy read-modify-write 再丢失一份 scheduler result，而后续 scale-rescheduling 正准备
依赖这份结果。
第三方把 main-resource 风险写成 maintainer question 是克制的；按 Day44 本地合同，它仍是进入
实现前必须闭合的版本 blocker，而且 `/status` 也要纳入同一测试。可验证的最小策略是：在真实
API server 上创建带 component request/result 的 v1alpha2 对象，先观察 v1alpha1 main 与
`/status` update 的 baseline，再证明最终实现会拒绝 main update 或保留字段，并保证 `/status`
保留 storage spec。当前 branch 两项都没有覆盖。

## 本轮修复设计（动代码前）

### 问题与目标

本轮不是继续实现 #7492 的 scheduler 主流程，而是先修掉当前 API groundwork 中已经有充分证据的
两处 review 问题：测试 helper 必须按 map-list 语义比较 component result；公开 API 注释不应继续用
“only multiple” 掩盖 single-component 已进入 scheduling path 的事实。当时 feature 修复保持中性注释；
本次回读维护者 Draft 后，producer 结果已固定为迁移期双写。

具体例子是：`worker=2, master=1` 与 `master=1, worker=2` 应视为同一结果；当
`spec.components` 只有一个 `worker` 时，scheduler 已走 component path；维护者 Draft 要求结果同时写
scalar `Replicas` 与一个 `worker` component entry。

### 文件范围

| 文件 | 计划修改 | 原因 |
| --- | --- | --- |
| `test/helper/scheduler.go` | 对每个 cluster 的 component 按 `name` 做无序、完整字段比较；外层 cluster 继续无序比较，但每个元素只能匹配一次 | 对齐 map-list 语义，并避免重复 cluster 复用同一个匹配项 |
| `test/helper/scheduler_test.go` | 新增反序、nil/empty、replicas 差异、集合差异、重复 name 和 cluster 基础字段用例 | 把 review 指出的语义变成稳定回归测试 |
| `pkg/apis/work/v1alpha2/binding_types.go` | 删除 “only multiple” 的过强限定，改为中性的 component-based result 描述 | 与维护者 Draft 的 single-component 双写路线兼容 |
| OpenAPI、CRD 等生成文件 | 只接受由仓库生成脚本带出的注释同步 | 保证发布 schema 与 Go API 文档一致 |

### 本轮明确不改

- 不实现 scheduler producer、`IsBindingReplicasChanged` consumer、Resource Interpreter 或 Work 下发；
  当前分支仍只是 API groundwork。
- 不修改 v1alpha1 conversion，也不增加拒绝 legacy update 的 admission。可选策略会影响已 served 的
  API 行为，必须先由 maintainer 选定。
- 不给既有 `Component.Name` 直接增加 `MinLength=1`，也不新增 ClusterResourceBinding validating
  webhook；两项都会改变既有对象的可接受集合。
- 不把临时 CRD harness 的 4 个本地候选一次性写成 CEL 或 webhook。维护者 Draft 后来明确了 unknown
  name 的 RB webhook 校验，同时要求 single-component 双写并允许 `requiredBy` 复用；partial admission
  仍未定义，因此四项不能作为同一组 rejection 实现。
- 不改外层 `TargetCluster` 的 API list 类型。helper 保留原有“不关心 cluster 顺序”的测试语义，
  只把匹配改为一对一。

### 验证方案

1. 运行 `go test ./test/helper -run TestIsScheduleResultEqual -count=1`，覆盖本轮新增矩阵。
2. 使用仓库规范生成脚本更新 CRD/OpenAPI，检查 diff 只包含预期注释变化。
3. 运行相关 API/conversion 测试，并执行 `make test`、`make verify`；若环境或既有基线失败，记录
   完整命令、错误和与本次变更的关系。
4. 再次运行 `git diff --check`，确认 topic branch 不包含实习记录，`intern` branch 不包含上游源码。

## 本轮修复结果

本轮在现有 `feature/multi-component-scale-rescheduling` worktree 中完成 3 个手写文件和 5 个生成
文件的窄范围修改：

- `IsScheduleResultEqual` 现在把外层 clusters 当作无序多重集，一对一匹配；每个 cluster 内的
  components 按 `name` 建索引，并比较完整 `TargetComponent`，因此顺序和 nil/empty 差异不再造成
  false negative，重复 component name 会被视为无效结果。
- 新增 11 个 table-driven case，覆盖 cluster 反序和重复匹配、component 反序、nil/empty、replicas、
  missing/unknown/duplicate component，以及 cluster name/scalar replicas 差异。
- `TargetCluster.Components` 注释已改为中性的 component-based scheduling result 描述；apply
  configuration、Go OpenAPI、两份 CRD 和 swagger 均由仓库脚本同步。精确旧文案在源码和生成产物中
  已无残留；该注释与维护者 Draft 后续固定的 single-component 双写方向兼容。

最终将该 feature 相对 `upstream/master@1c278577e` 的 4 个提交压缩为 1 个 DCO commit：
`a3547a3a8 feat(api): add component scheduling results`。squash 前后的 tree hash 均为
`df4abb15440d89e465286b7e3c2e6362bcc204c6`，因此只改写历史，没有改变 15 个文件的最终内容。
远端原 head `b0501d9b2` 经精确 `--force-with-lease` 更新为 `a3547a3a8`，回读后本地与
`origin/feature/multi-component-scale-rescheduling` 一致。仓库仍无关联 upstream PR，也没有发布
issue comment；squash 前历史保存在本地
`backup/feature-multi-component-scale-rescheduling-pre-squash-20260811`。

最终验证结果：

| 命令 | 结果 |
| --- | --- |
| `go test ./test/helper -run '^TestIsScheduleResultEqual$' -count=1 -v` | 11 个子用例全部通过 |
| `go test ./pkg/apis/work/v1alpha1 ./pkg/apis/work/v1alpha2 ./test/helper -count=1` | 3 个 package 通过 |
| `hack/update-codegen.sh`、`hack/update-crdgen.sh`、`hack/update-swagger-docs.sh` | 成功；只产生预期的 5 个注释同步文件 |
| `make verify` | 通过；staticcheck、gofmt、vendor、swagger、CRD、codegen、license 全部通过 |
| `make test GO_TEST_FLAGS='--race -covermode=atomic'` | 最终完整重跑通过，`EXIT_CODE=0` |
| `git diff --check` | 通过 |

过程中的环境问题也保留如下：

- 第一次以 `GOTOOLCHAIN=local go test ...` 运行时，`/usr/local/bin/go` 的本地基础工具链仍是
  Go 1.26.4，报错 `go.mod requires go >= 1.26.5`；改用本机已下载的 Go 1.26.5 绝对路径后通过。
- 第一次 `make verify` 已把 `golangci-lint v2.12.2` 安装到 `/home/ranxi/go/bin`，但固定工具链的
  PATH 漏掉该目录，报 `golangci-lint: command not found`；补齐 PATH 后完整通过。
- 一次中间的安静版 `make test` 在网络依赖的 `pkg/karmadactl/cmdinit/utils.TestInternetIP` 上返回
  nil/error；该文件与本次 diff 无交集。随后单独重跑该用例 1.57 秒通过，再次完整重跑也通过。
- `openapi-gen` 输出仓库已有的 `list_type_missing`/`names_match` API rule warnings；生成脚本退出成功，
  `verify-codegen` 确认产物 up to date，本次没有新增对应 schema finding。

这些修复闭合了可以独立判断的判等问题，并把公开注释改成与维护者 Draft 双写路线兼容的中性文案。
分支仍未生产或消费 component scheduling result，也没有完成 Draft 的 PR1 validation，不能宣称已经
解决 #7492 的 scale rescheduling。

## 仍需确认或在 PR 中收敛的问题

以下只保留维护者 Draft 没有回答完整的边界；single-component 双写、full-set producer、
`BindingSnapshot` max merge、Gate-off reject、`ReviseComponents` 所属阶段和五段 PR 切分不再重复询问。

1. **失败重调度的状态合同是什么？** Draft 没有说明 component scale 后无可行集群时，scheduler 是否
   保留旧 `Clusters/Components`、旧 Work 是否继续运行、谁阻止带新 replicas 的 source template 被
   binding controller 下发，以及用什么 condition 表达 pending/failed reschedule。当前通用 `FitError`
   会清空 `Clusters`，不能直接假定符合 #7492 的“失败时不传播新配置”。
2. **full-set producer 之外，API 是否拒绝 partial/mismatch？** Draft 要求 producer 写完整集合，并让
   RB webhook 拒绝 unknown/duplicate；它没有要求 admission 拒绝 missing component，也没有定义
   scalar 与 component 不一致时谁是权威。还需确认 CRB 是否需要同等 validator，以及 schema/CEL、
   webhook 与 producer defensive check 的分层。
3. **v1alpha1 的读写合同分别是什么？** conversion 无法表达 `spec.components` 和
   `clusters[*].components`，不能把 lossy GET、main update 和 status update 混成一个“兼容性限制”。
   维护者 Draft 没有讨论版本转换；需分别确认下表策略，并用真实 API server 建立 baseline：

| 操作 | 需要确认的合同 | 当前倾向 |
| --- | --- | --- |
| v1alpha1 GET | 是否接受只读的 lossy projection，还是必须保留 hub-only state | 可接受 projection，但不能允许它随后静默破坏 storage object |
| RB main update | 明确拒绝 component-aware object 的 legacy write，还是转换时保留 hub-only fields | 在有 preservation 方案前显式拒绝 |
| CRB main update | 明确拒绝还是保留；当前无 validating webhook，源码链路支持静默丢失 | 在有 preservation 方案前显式拒绝 |
| RB/CRB `/status` update | 必须保留 storage spec，还是也拒绝 legacy status write | 优先证明 spec 可保留；证明不了就拒绝，不能静默丢字段 |

4. **scale trigger 与 estimator 的 delta 合同是什么？** Draft 说明 producer 和 dispatch，没有说明
   `IsBindingReplicasChanged` 如何比较 desired/result、scale-up delta 由谁计算并交给 estimator、scale-down
   跳过 estimate 时还要执行哪些 placement/eligibility 检查。
5. **`ReviseComponents` 的失败原子性是什么？** Draft 已把 operation 放在 PR3，并允许单 component
   fallback `ReviseReplica`；仍需在实现中明确多组件 hook 发生 partial mutation/error 时是否 all-or-nothing、
   如何回滚，以及第三方 interpreter 的错误合同。

以下不是当前 API PR blocker，但应单独跟踪：request-side `Component.Name`/map-list 的兼容收紧、
Gate strict-reject 下的滚动降级操作体验、scalar 字段最终弃用，以及跨集群迁移时应用状态连续性。

## 修正后的下一步

1. 先按维护者 Draft 对齐 PR1：在现有 API/codegen 基础上补
   `GracefulEvictionTask.Components`、RB result membership/duplicate/Gate validation 和测试；若要提交更窄
   的 API-only PR，必须在 PR 文案中明确与 Draft 切分的差异。
2. 根据版本策略建立真实 API server baseline，覆盖 v1alpha1 main/status read-modify-write。
3. 按 Draft PR2 实现 scheduler full-set/dual-write producer，并补 `BindingSnapshot` component max-merge；
   同时单独收敛 scale trigger、delta 与失败状态机。
4. 按 Draft PR3 实现 `ReviseComponents` 和 ensureWork，再推进 third-party/Flink E2E 与 downstream。
5. PR1-3 的生产链路闭合前，只写 `Part of #7492`，不宣称 issue 三项行为已经完成。
