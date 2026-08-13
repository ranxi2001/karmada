# Day 47：#7492 PR1 旧版本状态写入的数据保护设计

- 日期：2026-08-13
- 分析对象：`fix/issue-7492-pr1-api-compat@1382c90d99172c67dd1851b68db012ddd2afeb7b`
- 最新基线：`upstream/master@09c08f405b2f0b53106b1947e08a82d4cc94de28`
- 关联 Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- 官方机制说明：[Versions in CustomResourceDefinitions](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/)
- 时序源：[day47-issue7492-v1alpha1-status-data-loss.mmd](day47-issue7492-v1alpha1-status-data-loss.mmd)
- 本轮性质：修复设计和文件级范围确认；没有修改、提交或推送 upstream topic branch

## 先说人话

PR1 新增的 `Components` 会被旧版 `v1alpha1` 客户端的一次普通状态更新误删。

例如，当前存储的是：

```yaml
apiVersion: work.karmada.io/v1alpha2
spec:
  components:
  - name: worker
    replicas: 10
  clusters:
  - name: member1
    components:
    - name: worker
      replicas: 10
```

一个旧控制器只想把 `status.conditions` 改成 `Ready=True`。API Server 为处理
`v1alpha1 /status` 请求，会先把当前对象转换成旧结构；旧结构没有 `Components`，所以得到的是一份
已经缺字段的对象。CRD 的 status update strategy 随后保留这份旧 `spec`、替换 `status`，并把结果重新
写成存储版本 `v1alpha2`。最终状态更新成功了，但组件调度结果没了。

推荐 PR1 采用窄保护方案：

1. 让 `v1alpha1` 的 RB/CRB `/status` 请求真正进入 validating webhook。
2. Webhook 直接读取当前 `v1alpha2` 对象。
3. 当前对象只要含有 component scheduling data，就拒绝这次旧版本写入，并要求客户端改用
   `work.karmada.io/v1alpha2`。
4. `v1alpha2 /status` 和不含组件数据的 legacy Binding 保持原行为。

这会把“成功但静默丢数据”改成“明确返回错误”。Karmada 内建 scheduler、RB status controller 和 CRB
status controller 都使用 `v1alpha2`，不会被该限制影响；兼容影响只落在仍用 `v1alpha1` 写 Binding
status 的外部控制器。

> 边界：这只是 #7492 的 component-state guard。`v1alpha1` 还表达不了 `Placement`、
> `GracefulEvictionTasks`、`RequiredBy`、`SchedulerName` 等既有 `v1alpha2` 字段，因此它不是整个
> 多版本转换合同的根治方案。

## 已确认的故障链路

### 1. 实际部署使用 conversion webhook

只看生成的 CRD base 会漏掉转换配置。Karmada 通过：

- `charts/karmada/_crds/patches/webhook_in_resourcebindings.yaml`
- `charts/karmada/_crds/patches/webhook_in_clusterresourcebindings.yaml`
- `charts/karmada/_crds/kustomization.yaml`

为 RB/CRB 加上 `spec.conversion.strategy: Webhook`。本地执行 `kubectl kustomize
charts/karmada/_crds` 后可以看到 `/convert` 配置，所以真实路径会调用
`pkg/apis/work/v1alpha1/binding_types_conversion.go`，不是简单的 `None` conversion。

### 2. 转换本身是有损的

`ConvertBindingSpecFromHub` 只把 `TargetCluster.Name/Replicas` 投影到 `v1alpha1`：

- `pkg/apis/work/v1alpha1/binding_types_conversion.go:114-133`
- `pkg/apis/work/v1alpha1/binding_types_conversion_test.go:39-52`

测试已经明确证明 `v1alpha2 -> v1alpha1 -> v1alpha2` 后，
`TargetCluster.Components` 消失。`spec.Components`、eviction task 和 snapshot 中的 component data
也无法由 `v1alpha1` 类型承载。

### 3. `/status` 复制的是请求版本的旧对象

Kubernetes `apiextensions-apiserver` 为每个 served version 建立 Store：

- `decoderVersion` 是请求版本。
- `encoderVersion` 是 CRD storage version。
- status strategy 先深拷贝 `old`，再只替换 `status`。

因此 `v1alpha1 /status` 路径里的 `old` 已经是转换后的 legacy projection，不是 etcd 中原始的
`v1alpha2` 对象。复制 `old` 只能保留剩下的字段，不能恢复转换时丢掉的 `Components`。

### 4. 当前 validating rule 根本匹配不到 `/status`

四个安装入口的 validating rules 目前只列出：

```yaml
resources: ["resourcebindings"]
resources: ["clusterresourcebindings"]
```

它们不会匹配 `resourcebindings/status` 或 `clusterresourcebindings/status`。`matchPolicy: Equivalent`
只扩展等价 API version，不会把主资源规则扩展到 subresource。因此
`validating.go` 中“status 直接允许”的分支在真实配置下并不能保护该请求。

## 方案比较

| 方案 | 做法 | 正确性 | 兼容性 | 范围 | 判断 |
| --- | --- | --- | --- | --- | --- |
| A2：component-aware 写入保护 | 仅拒绝 component-aware RB/CRB 的 `v1alpha1` main/status update | 闭合 #7492 component data-loss 路径 | legacy 对象仍可由旧客户端写 status | 小 | **PR1 推荐** |
| A1：旧版本写入全部关闭 | 拒绝所有 RB/CRB `v1alpha1` main/status update | 同时保护其他 `v1alpha2`-only spec | 旧写客户端全部失败，只剩读 | 中，且是公开兼容变更 | 需 maintainer 单独确认 |
| B：conversion-data envelope | down-convert 时把完整 hub-only data 序列化到 annotation，up-convert 时恢复 | 可实现真正的无损往返 | 旧 RMW 客户端可继续工作 | 大，需要版本化 envelope、完整字段和 fuzz/integration tests | 不适合塞进 PR1 |
| C：停止 serve `v1alpha1` | CRD 将 Binding `v1alpha1` 设为 `served:false` | 从入口消除所有旧读写 | 破坏所有旧客户端和 discovery | 发布/废弃议题，不是局部修复 | 长期推荐单独推进 |

### 为什么不推荐只往 `v1alpha1` 镜像几个字段

只补 `TargetCluster.Components` 仍不完整。component data 还出现在：

- `spec.Components`
- `spec.GracefulEvictionTasks[].Components`
- `spec.RequiredBy[].Clusters[].Components`

如果要让转换真正无损，还要承载其他所有 `v1alpha2`-only 字段。零散 mirror 会把实现细节变成新的公开
`v1alpha1` API，并在下一次加字段时再次遗漏。

### 为什么“新增真正的 hub”不能单独解决

`pkg/apis/work/v1alpha2/binding_types_conversion.go` 已经把 RB/CRB 的 `v1alpha2` 标记为
`conversion.Hub`。Hub 只是转换中转类型，不是隐藏存储。目标 `v1alpha1` JSON 没有字段时，经过 hub
仍然无法跨请求携带这些数据。

## 推荐的 PR1 实现

### Webhook 配置

保留当前 main-resource webhooks，再为 status 新增两个独立 entry：

```yaml
- name: resourcebindingstatus.karmada.io
  rules:
  - operations: ["UPDATE"]
    apiGroups: ["work.karmada.io"]
    apiVersions: ["v1alpha1"]
    resources: ["resourcebindings/status"]
    scope: "Namespaced"
  matchPolicy: Exact
  failurePolicy: Fail
  sideEffects: None

- name: clusterresourcebindingstatus.karmada.io
  rules:
  - operations: ["UPDATE"]
    apiGroups: ["work.karmada.io"]
    apiVersions: ["v1alpha1"]
    resources: ["clusterresourcebindings/status"]
    scope: "Cluster"
  matchPolicy: Exact
  failurePolicy: Fail
  sideEffects: None
```

它们复用现有 `/validate-resourcebinding` 和 `/validate-clusterresourcebinding` URL，不需要新增 server
handler。单独 entry 使用 `Exact`，避免让正常 `v1alpha2 /status` 也多走一次 admission。

`Exact` 也保护 Helm 的混合升级窗口。`pre-upgrade` job 会先应用新 webhook configuration，再滚动新
binary；此时旧 RB handler 收到带 GVK 的 `v1alpha1` raw object，decoder 会返回“无法解码到
`v1alpha2.ResourceBinding`”，旧 CRB binary 则还没有 validating route。两者在 `failurePolicy: Fail`
下都会拒绝请求，因此 rollout 期间可能出现短暂的 legacy status 写失败，但不会静默擦除数据。本轮用
真实 controller-runtime decoder 做了最小实验，分别验证了“带 GVK 时类型不匹配报错”和“不带 GVK
时可直接解码”；Kubernetes 在 AdmissionReview 中序列化的是带目标版本 GVK 的 versioned object。

> 未决验证：上述 mixed-version 结论目前是 API Server 源码 + decoder 最小实验的组合证据。提交前仍应
> 增加“旧 webhook binary + 新 configuration”的升级回归，或至少在支持的 Helm 升级路径实测一次；
> 不能只凭 handler unit test 把 rollout 兼容写成最终事实。

### Handler 顺序

RB 和 CRB 都应使用同一顺序：

```go
if response := v.validateLegacyVersionUpdate(ctx, req, clusterScoped); response != nil {
    return *response
}
if originalSubResource(req) == "status" {
    return admission.Allowed("")
}

// Only main-resource requests continue to decode and full validation.
```

`validateLegacyVersionUpdate` 的行为：

1. 使用 `RequestKind` 判断原始请求版本；只有它为空时才 fallback 到 `Kind`。
2. 只处理 `work.karmada.io/v1alpha1` 的 `UPDATE`。
3. 使用 uncached `APIReader` 以 `v1alpha2` 读取当前存储对象。
4. `isComponentAwareBindingSpec` 为真时拒绝 main 或 status update。
5. 当前对象不含 component data 时返回 `nil`；status 随后由入口直接允许，主资源继续普通校验。

这里的早退条件必须严格等于 `status`，不能写成 `subResource != ""`。后者会让未来新增的任意
Binding subresource 无条件跳过 validator，形成新的校验绕过。

`RequestKind` 不能换成 `Kind`：main-resource rule 使用 `Equivalent` 时，`Kind` 是 webhook 匹配后的
`v1alpha2`，而 `RequestKind` 才是用户真正调用的 `v1alpha1`。

检查当前状态也不能使用 AdmissionReview 的 `OldObject`。它已经是等价转换后的视图，可能恰好缺少要
保护的字段。`APIReader.Get` 读取 storage version，且 Kubernetes 的 resourceVersion 冲突会约束并发
更新窗口。

### 为什么 status 必须在完整校验前早退

如果仅删除当前“subresource 直接 Allow”，status 请求会继续进入：

- component result validation；
- annotation validation；
- `FederatedResourceQuota` 读取和 status 更新。

这些都不是 Binding `/status` 的职责，可能误拒请求或产生额外副作用。正确顺序只能是：

```text
legacy safety guard -> ordinary status early return -> main-resource validation
```

## 文件级范围

| 文件 / 区域 | 改动 | 原因 | 风险 | 验证 |
| --- | --- | --- | --- | --- |
| `pkg/webhook/resourcebinding/validating.go` | 调整 legacy guard，并只对 `status` early return | 切断危险写路径 | 放行任意 subresource 会绕过未来校验 | table-driven unit tests |
| `pkg/webhook/resourcebinding/validating_test.go` | 补 RB/CRB、main/status、版本矩阵 | 固定分支行为 | fake test 不能证明 rule 可达 | unit + live E2E |
| `artifacts/deploy/webhook-configuration.yaml` | 新增两个 exact status entries | raw install 生效 | 四份配置漂移 | manifest parse/render |
| `charts/karmada/templates/_karmada_webhook_configuration.tpl` | 同步 Helm entry | Helm install 生效 | 模板缩进/渲染 | `helm template` / chart CI |
| `operator/pkg/karmadaresource/webhookconfiguration/manifests.go` | 同步 operator entry | operator install 生效 | embedded YAML 漂移 | operator package test |
| `pkg/karmadactl/cmdinit/karmada/webhook_configuration.go` | 同步 init entry | `karmadactl init` 生效 | embedded YAML 漂移 | karmadactl package test |
| `pkg/karmadactl/.../webhook_configuration_test.go` 和 `operator/.../webhookconfiguration_test.go` | 校验 name、URL、version、resource、operation、scope、match policy | 防止入口只改一半 | operator 现有测试只验 URL/CA，会漏 rule 漂移 | focused package tests |
| `test/e2e/suites/base/binding_version_compatibility_test.go`（建议新增） | 真实 API Server + webhook 回归 | 证明 conversion、rule matching 和 status strategy 的组合 | 环境成本高于 unit | focused Ginkgo + upstream CI |

### 明确不改

| 区域 | 原因 |
| --- | --- |
| `pkg/apis/work/v1alpha1/binding_types.go` | 不把 component data 反向扩成新的 legacy API |
| `pkg/apis/work/v1alpha1/binding_types_conversion.go` | 保留显式 legacy projection；A2 在写入边界保护 |
| `pkg/apis/work/v1alpha2/*` 和生成物 | 本修复不改变公开类型或 schema |
| scheduler、binding/status controller | 当前内建 writer 都已使用 `v1alpha2`，没有责任变化 |
| feature gate | 关闭 gate 后仍需保护已存在的数据，不能用 gate 绕过 guard |
| FRQ validation | status 请求应该绕开它，而不是修改其合同 |

## 测试矩阵

### Handler unit tests

| 原始请求 | 当前 storage state | 期望 |
| --- | --- | --- |
| RB `v1alpha1` main update | component-aware | Denied |
| CRB `v1alpha1` main update | component-aware | Denied |
| RB/CRB `v1alpha1 /status` | component-aware | Denied，提示改用 `v1alpha2` |
| RB/CRB `v1alpha1 /status` | 仅 legacy-representable fields | Allowed，且不进入 decoder/FRQ |
| RB/CRB `v1alpha2 /status` | component-aware | Allowed，且不调用 legacy `APIReader` |
| `RequestSubResource=status` | 任意 | 使用原始 subresource |
| 仅 `SubResource=status` | 任意 | fallback 正常 |
| 未知 subresource | 任意 | 不得命中 status early return |
| legacy guard 的 `APIReader.Get` 失败 | 任意 | 500 / fail closed |

`isComponentAwareBindingSpec` 继续分别覆盖：top-level request、target result、eviction result 和
snapshot result。

### 真实 API Server 回归

RB 和 CRB 都要走完整链路：

1. 用 `v1alpha2` 创建 component-aware Binding。
2. 用 `v1alpha1` typed client `Get` 后执行 `UpdateStatus`，断言 Forbidden。
3. 再用 `v1alpha2` `Get`，断言完整 `Spec` 未变化。
4. 用 `v1alpha2 UpdateStatus`，断言成功且 `Spec` 未变化。
5. 创建只含 legacy-representable fields 的对象，验证 A2 下 `v1alpha1 UpdateStatus` 仍成功，并再次
   对比完整 `Spec`。
6. RB/CRB 至少各覆盖一种 PUT 或 PATCH status 入口，因为两者最终都必须命中 UPDATE admission rule。
7. Helm 升级路径用旧 webhook binary + 新 configuration 重放 legacy status，断言请求失败且完整 `Spec`
   不变；新 binary ready 后再断言 A2 的 allow/deny 矩阵恢复。

纯 handler unit test 不能替代该回归：它无法证明 `resource/status` rule、`matchPolicy`、conversion
webhook、`RequestKind` 和 CRD status strategy 在真实 API Server 中按预期组合。

### 提交前验证

```bash
go test --race ./pkg/webhook/resourcebinding \
  ./pkg/karmadactl/cmdinit/karmada \
  ./operator/pkg/karmadaresource/webhookconfiguration
make verify
git diff --check
```

随后在实际 Karmada control plane 上运行新增的 focused E2E，并以 rebase 后的新 SHA 为最终证据。

本轮曾审查一份未提交的七文件初稿；它通过了上述三个 focused package tests 和 `git diff --check`，但
随后被并发 rebase 清除，**不在当前 topic HEAD `492ba86de` 中**，也没有推送到 fork。该短暂结果只能
证明实现方向能通过现有单测，不能作为当前分支的完成证据。重做时仍需闭合：

- status early return 目前是“任意非空 subresource”，需要收紧为 `== "status"` 并补 unknown-subresource test；
- operator 配置测试仍只校验 URL/CA，尚未固定新增 rules；
- 尚无真实 API Server + conversion webhook 回归，也没有 mixed-version Helm upgrade 回归；
- 四份静态配置在短暂初稿中曾同步，但 Helm render 尚未完成。本轮运行 `helm template karmada charts/karmada
  --namespace karmada-system` 在渲染前失败：`Chart.yaml` 声明的 `common` dependency 不在本地
  `charts/`；应先按仓库流程补齐 dependency，再重跑 render 和 manifest 一致性检查，不能把该错误归因
  于本次模板内容。

## 不应采用的短路修法

- 只改 handler，不给 webhook rule 增加 `*/status`：真实请求仍到不了代码。
- 只给现有 `Equivalent` rule 追加 status，却不做 status early return：可能让 `v1alpha2 /status`
  进入完整 RB/FRQ validation。
- 从 `req.OldObject` 判断是否有 Components：该对象可能已经是有损转换后的视图。
- 仅靠 retry、resourceVersion 或 status strategy：它们防并发覆盖，无法重建转换已经删除的字段。
- 只镜像一个 `Components` 字段到 `v1alpha1`：不能覆盖完整 component state，更不能保证全部
  `v1alpha2` 字段往返无损。
- 再增加一个 hub 类型：当前 `v1alpha2` 已经是 hub，缺的是跨请求的数据承载能力。

## 最终建议与待确认边界

本次 PR1 采用 A2 最合理：它直接保护 #7492 引入和依赖的 component scheduling data，diff 小，且不
改变 Karmada 内建组件。PR body 必须准确写成“拒绝 component-aware Binding 的 legacy writes”，不能
声称“修复了全部 v1alpha1/v1alpha2 conversion”。

长期应另开 API deprecation 议题评估 C。Karmada 的 `CHANGELOG-0.9` 曾写明 Binding `v1alpha1` 只再
保留一个 release，但它至今仍在 serving。继续保留时，应选择完整 conversion-data envelope；不继续
保留时，应走显式 deprecation、discovery、升级和回滚流程，不能在 #7492 PR1 中顺带关闭。

如果 maintainer 要求旧 `v1alpha1` controller 在 component-aware 对象上仍能成功写 status，A2 就不
满足该合同；此时应暂停 PR1，改为设计完整 B，而不是继续堆局部例外。
