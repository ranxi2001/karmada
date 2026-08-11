# Day 44：#7492 多组件调度结果 API 设计

- 日期：2026-08-11
- Maintainer API proposal：[`RainbowMango` 在 #7492 的 API 回复](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5248383498)
- 最新 API 讨论：[`TargetComponent.Replicas` 保持 `int32`](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5252661190)
- 详细 Draft：[`RainbowMango/pr_multi_component_next_move@c14af2f1119a66d4672a814cc80f7612943d35d3`](https://github.com/RainbowMango/karmada/blob/c14af2f1119a66d4672a814cc80f7612943d35d3/docs/proposals/scheduling/multi-podtemplate-support/scheduling-result-for-components.md)
- 源码基线：[`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`](https://github.com/karmada-io/karmada/commit/1c278577e7892b6ea44f86a4317c1eb1e013bb93)
- 状态复核：2026-08-11T20:59:10+08:00
- 上游状态：issue 正文三项仍未勾选，无关联 PR；详细文档仍标记为 `Draft (design discussion, not yet a formal proposal)`
- 本文范围：先固定 API 合同；文末追加个人特性分支的 API 实测，不包含调度行为实现

## 先说人话

`spec.components` 表示用户当前申请的每个组件副本数；
`spec.clusters[].components` 表示最近一次成功调度后，分配到该集群的每个组件副本数。

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

请求再次变化时，`spec.components` 可以先变化；只有新请求调度成功后，
`spec.clusters[].components` 才替换为新结果。调度失败时，已有结果保持不变。

## API 边界

本版面向 `MultiplePodTemplatesScheduling` 下的 multi-pod-template workload，定义：

1. `TargetCluster.Components`：集群维度的组件调度结果。
2. `TargetComponent`：结果侧最小组件分配单元。
3. `ReviseComponents`：把一个集群的组件结果写回资源模板的 Resource Interpreter 操作。
4. `v1alpha2` 的功能版本合同，以及 `v1alpha1` legacy projection 的保护规则。

其中，第 1、2 项来自 #7492 maintainer 回复；第 3 项来自详细 Draft；第 4 项和后文标记为
“Day44 补充合同”的内容用于固定本地实现边界，不表示已经获得 upstream acceptance。

本文以最新 #7492 回复和 `c14af2f11` 中的 API snippet 为准。详细 Draft 正文中仍保留的
单模板双写和 legacy 字段弃用路线不属于本版合同。

本版不定义：

- 把不同组件或同一组件的副本拆到多个集群。
- 单 Pod template workload 从 `Replicas` 迁移到 `Components`。
- `Replicas` / `ReplicaRequirements` 的弃用。
- 组件 add、remove 或 rename；本版只处理组件集合不变时的 replicas 变化。
- `GracefulEvictionTask.Components`、HPA、Descheduler、FRQ 或可观测性 API。

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

该回复还明确 `Components` 只在多 Pod template 工作负载且 feature gate 开启时填充，并保留
现有 `Replicas` 字段。本版不增加 deprecated 标记属于 Day44 的范围约束。

### `Replicas` 类型讨论

`zhzhuang-zju` 曾询问 `TargetComponent.Replicas` 是否应从 `int32` 改为 `*int32`，以便未来
区分零值和未指定；`RainbowMango` 要求给出必须使用指针的具体场景。提问者随后
[撤回该疑问](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5252661190)：
对于 `ConfigMap` 等非 workload 资源，整个 `TargetCluster.Components` 为 `nil` 已能表达
“不适用”，结果项内部不再需要用指针区分未指定和显式零值。

因此当前 API snippet 继续使用 `Replicas int32`。这只表示该局部类型疑问已经收敛，
不表示完整 API 或 Day44 补充合同已经获得 upstream approval。

## Day44 补充合同：结果字段

| 字段 | 合同 |
| --- | --- |
| `TargetCluster.Components` | 当前集群最近一次成功调度的完整组件副本快照 |
| `TargetComponent.Name` | 对应 `ResourceBindingSpec.Components[*].Name`；在一个 `TargetCluster` 内唯一 |
| `TargetComponent.Replicas` | 该组件在当前集群的已接受副本数；必须大于等于 0 |
| `TargetCluster.Replicas` | 保留既有单模板工作负载语义；多模板结果不使用该字段 |

`TargetCluster.Components` 采用 name-keyed、order-insensitive 语义。对本版完整集合调度模式，
每个非空列表必须满足：

- 组件 name 集合与 `spec.components` 完全一致。
- 每个 name 只出现一次。
- 零副本显式编码为 `{name: <component>, replicas: 0}`。
- 每次写入完整快照，不使用只包含变化项的 partial result。

`TargetCluster` 也被 `BindingSnapshot.Clusters` 复用。本版仅定义顶层
`ResourceBindingSpec.Clusters` 的组件结果；`spec.requiredBy[*].clusters[*].components` 必须缺失。

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

`spec.clusters[].components` 保存最近一次成功调度结果。在新结果成功提交前，该字段保持原值；
失败的重调度不覆盖或清空已有结果。

## Draft 提出的 Resource Interpreter API

详细 Draft 提出 `ReviseComponents`，用于把一个目标集群的组件副本结果写回资源模板：

```go
// ReviseComponents revises the per-component replicas of the object
// according to the scheduling result on a specific cluster.
ReviseComponents(
	object *unstructured.Unstructured,
	components []workv1alpha2.TargetComponent,
) (*unstructured.Unstructured, error)
```

## Day44 补充合同：Interpreter 协议

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

`components` 是一个 `TargetCluster.Components` 的完整快照。调用方必须先确认目标资源已声明
`ReviseComponents` hook。hook 未声明，或出现未知、缺失、重复 name 时，整个 operation 失败，
不返回或应用 partial patch，也不回退到 `ReviseReplica`。

## Day44 补充合同：校验

### 结构校验

- `TargetComponent.Name` 必填，并满足请求侧 component name 的同等约束。
- `TargetComponent.Replicas >= 0`。
- 同一 `TargetCluster.Components` 内的 name 唯一。
- `DesiredComponents` 复用相同的 name、replicas 和唯一性约束。

### 跨字段校验

对 `v1alpha2` 中带有 `spec.clusters[].components` 的多模板 binding：

- `spec.components` 必须非空。
- 每个目标集群的 component name 集合必须与 `spec.components` 相同。
- `spec.clusters[].replicas` 必须保持未设置的零值。

`ResourceBinding` 与 `ClusterResourceBinding` 使用相同规则。

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

### Feature Gate

- Gate 开启：多模板 producer 可以新增或更新 `TargetCluster.Components`，consumer 可以调用
  `ReviseComponents`。
- Gate 关闭：拒绝新增、修改或删除非空 `TargetCluster.Components`；允许语义不变的
  grandfathered value 随对象更新继续保留。相等性按 name -> replicas map 判断，单纯调整
  列表顺序不算修改。
- Gate 关闭时，consumer 不执行 `ReviseComponents`。
- absent、`null` 与 `[]` 的相互规范化不视为语义变更。

## 兼容性矩阵

| 工作负载 / 对象 | `TargetCluster.Replicas` | `TargetCluster.Components` |
| --- | --- | --- |
| Existing scalar workload | 既有值 | 缺失 |
| Existing object without component result | 既有值或 0 | 缺失 |
| Multi-pod-template workload under gate | 0 / omitted | 完整调度结果快照 |

本版不要求单模板工作负载双写 `Components`，也不标记 `Replicas` deprecated。

## API 验收用例

在 `v1alpha2` 且 Gate 开启时，以下对象必须被接受：

- 完整且 name 唯一的组件结果。
- 组件顺序与请求不同、但 name 集合相同的结果。
- 带显式 `replicas: 0` 的完整结果。
- 不含 `components` 的 legacy object。

Gate 关闭时，必须接受语义不变的 grandfathered component result。`v1alpha1` status
subresource update 在 storage spec 不变时也必须接受。

以下对象必须被拒绝：

- 空 name、重复 name 或负 replicas。
- 缺少请求组件的 partial result。
- 包含请求中不存在 name 的结果。
- 多模板结果同时写入非零 scalar `replicas`。
- `ReviseComponents` 请求缺少完整组件快照。
- `ReviseComponents` 与 `DesiredReplicas` 同时出现，或其他 operation 携带
  `DesiredComponents`。
- Gate 关闭时新增、修改或删除非空 component result。
- 通过 `v1alpha1` main resource 更新已有 component-aware storage object。
- `spec.requiredBy[*].clusters[*].components` 非空。

本文只固定上述 API 合同。Scheduler estimation、Work 下发时序、quota accounting 和
controller 实现另行设计。

## 特性分支实测：API 基础可编译，但合同尚未闭合

- 测试分支：[`ranxi2001/feature/multi-component-scale-rescheduling`](https://github.com/karmada-io/karmada/compare/master...ranxi2001:karmada:feature/multi-component-scale-rescheduling)
- 测试 HEAD：[`b0501d9b2ae036b956e1ea815cd0d75899f4bcb3`](https://github.com/ranxi2001/karmada/commit/b0501d9b2ae036b956e1ea815cd0d75899f4bcb3)
- merge base：[`upstream/master@1c278577e7892b6ea44f86a4317c1eb1e013bb93`](https://github.com/karmada-io/karmada/commit/1c278577e7892b6ea44f86a4317c1eb1e013bb93)
- 本地测试完成时间：2026-08-11T22:10:00+08:00

### 结论

这个分支已经把 `TargetCluster.Components`、`TargetComponent`、CRD、OpenAPI、deepcopy、
apply configuration 和 v1alpha1 legacy projection 放进代码，仓库标准单测、静态检查和生成检查
都能通过。
但它还不是 Day44 合同的完整实现：11 个可直接执行的 CRD 用例中，7 个符合合同，4 个应拒绝
对象被 schema 接受；测试 helper 还把 component 顺序变化误判成结果变化。

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

Day44 要求拒绝这个 partial result，但当前 CRD 校验返回 `errors=[]`。相同原因也会放过未知组件、
scalar/component 双写和 `requiredBy` 中的 component result。`make verify` 全绿只能证明代码和生成物
一致，不能证明这些跨字段 API 合同已经实现。

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

`合同结果` 表示上文“API 验收用例”固定的期望；`分支实际` 来自临时 schema 测试的直接观察。
临时夹具执行命令为
`go test -mod=mod ./_scratch -run '^TestDay44SchemaContract$' -count=1 -v`；测试按 Day44
合同断言，因此在下面 4 个错误接受项上退出失败。夹具已删除，命令仅作为本轮执行记录。

| 用例 | 合同结果 | 分支实际 | 判定 |
| --- | --- | --- | --- |
| 完整且 name 唯一 | 接受 | 接受 | 符合 |
| 组件顺序不同、name 集合相同 | 接受 | CRD 接受 | schema 符合 |
| 显式 `replicas: 0` | 接受 | 接受 | 符合 |
| legacy object 不含 `components` | 接受 | 接受 | 符合 |
| 空 name | 拒绝 | `minLength: 1` 拒绝 | 符合 |
| 重复 name | 拒绝 | list-map 唯一性校验拒绝 | 符合 |
| 负 replicas | 拒绝 | `minimum: 0` 拒绝 | 符合 |
| partial result | 拒绝 | 接受，`errors=[]` | **合同失败** |
| unknown component name | 拒绝 | 接受，`errors=[]` | **合同失败** |
| 非零 scalar `replicas` 与 `components` 共存 | 拒绝 | 接受，`errors=[]` | **合同失败** |
| `requiredBy[*].clusters[*].components` 非空 | 拒绝 | 接受，`errors=[]` | **合同失败** |

此外，针对 [`test/helper/scheduler.go`](https://github.com/ranxi2001/karmada/blob/b0501d9b2ae036b956e1ea815cd0d75899f4bcb3/test/helper/scheduler.go#L27-L39)
补的临时回归用例失败：两份结果只有 component 顺序不同，`IsScheduleResultEqual` 仍返回
`false`。原因是新实现对整个 `TargetCluster` 使用 `reflect.DeepEqual`，而 Day44 把
`Components` 定义为 name-keyed、order-insensitive 列表。这个问题影响测试判等，不是 CRD
接收行为。

### 尚未实现或尚未实测的合同

- `ReviseComponents`、`DesiredComponents` 和 `ComponentRevision` 在该分支中不存在，因此相关
  接受/拒绝用例无法执行。
- 现有 validating webhook 只在 Gate 开启时检查请求侧 `spec.components` 的空名和重复名，
  不检查 `spec.clusters[*].components`，也没有 Gate 关闭时的 grandfathered/mutation 保护。
- `ClusterResourceBinding` 没有对应 validating webhook；两份 CRD 都复用 `TargetCluster`，
  因而都把 `components` 暴露给 `requiredBy`。
- v1alpha1 conversion 单测已证明 component result 会被投影掉，但该分支没有阻止 v1alpha1
  main-resource update 的 admission 保护。真实 API server 上的数据丢失路径本轮未复现，当前结论
  是源码确认的兼容性风险，不是已观察事故。
- 仓库没有现成 envtest/kube-apiserver fixture，本轮没有实测 v1alpha1 status update、Gate 切换
  update 或完整 admission/conversion 链路。
- 分支没有 scheduler、estimator、binding controller 或 Work 下发逻辑；#7492 正文三项行为均
  不在这两个 commit 的测试范围内。

### 下一步

先把本轮临时矩阵变成 topic branch 上的正式 API/admission 单测，并决定校验归属：基础字段约束
继续留在 CRD，component 集合、scalar 互斥、`requiredBy`、feature gate 和 v1alpha1 update 保护
需要统一的 admission 边界。随后修正 name-keyed 语义判等，再进入 scheduler producer 和
`ReviseComponents` consumer；在这些边界闭合前，不把该分支描述为 #7492 功能实现完成。
