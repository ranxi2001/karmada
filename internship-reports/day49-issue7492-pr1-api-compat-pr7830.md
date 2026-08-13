# Day 49：#7492 PR1 API 与旧版本写入保护提交

- 日期：2026-08-13
- Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- Pull Request：[`karmada-io/karmada#7830`](https://github.com/karmada-io/karmada/pull/7830)
- Head：`be8c7c3f778e41490d37dff0a2374a6aa5d5ffab`
- Base：`09c08f405b2f0b53106b1947e08a82d4cc94de28`
- 状态：Open、非 Draft、mergeable；upstream CI 全绿，存在一项合并前 P1，尚无 human review

## 先说人话

#7492 的第一阶段已经从本地设计进入 upstream review。PR #7830 先给 Binding 增加一份可以持久化的
component 调度结果，并阻止旧 `v1alpha1` 客户端在更新主资源或 `/status` 时静默擦除
`v1alpha2` 才能表达的 component data。

例如，`v1alpha2` 的 `ResourceBinding` 已经记录
`taskmanager=20`，旧客户端只能看到 `v1alpha1` 的标量字段。旧客户端若直接写回，API Server 的版本转换
无法恢复 `Components`。当前实现使用 uncached `APIReader` 读取 storage 中的 `v1alpha2` 对象；只要对象
已经包含 component data，就拒绝这次旧版本写入并提示改用 `v1alpha2`。没有 component data 的 legacy
Binding 仍可继续使用 `v1alpha1`。

这次 PR 只建立 API、兼容保护和 validation 基线。scheduler 还不会产出 component result，也没有启用
扩缩容触发、delta estimation、`ReviseComponents` 下发或失败保留策略。因此 PR body 使用
`Part of #7492`，没有宣称完成 umbrella issue。

截至 2026-08-13 14:27 CST，PR exact head 的 17 个 checks 全部通过，且四个 Actions workflow 都是
attempt 1，没有依赖 rerun。当前不能写成“可以合并”：Tide 仍等待 `lgtm` 和 `approved`，并且 Copilot
指出的 nested component validation 缺口经源码复核后确认为合并前 P1。

## PR1 的实际范围

PR 为一个 DCO commit，共 25 个文件，`+1938/-17`。手写行为和生成面包括：

1. 在 `work.karmada.io/v1alpha2` 增加 `TargetComponent`、`TargetCluster.Components` 和
   `GracefulEvictionTask.Components`。
2. 同步 CRD、OpenAPI、Swagger、deepcopy 和 apply-configuration 生成物。
3. 为 ResourceBinding 和 ClusterResourceBinding 增加 component result validation；主调度结果按
   component name 校验 membership 和 duplicate。
4. feature gate 关闭时，允许既有主调度结果保持不变、顺序调整或清除，但拒绝新增或修改。
5. 对 component-aware RB/CRB 的 `v1alpha1` main-resource 和 `/status` UPDATE 做 storage-state guard；
   `v1alpha2` 写入和不含 component data 的 legacy 对象保持原行为。
6. 调度结果测试 helper 改为 cluster/component 顺序无关比较。

明确未包含：scheduler producer、component scale planner、Binding controller 下发、失败重调度保护、
eviction producer/consumer 和 #7492 功能 E2E。这些仍属于后续线性 PR。

## Upstream CI 终态

精确 SHA `be8c7c3f7` 的检查如下：

| 检查面 | 结果 |
| --- | --- |
| DCO | Success |
| codegen、lint、compile、unit test | 全部 Success |
| base E2E：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| CLI：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| Operator：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| Chart：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |

最后一个 check 于 2026-08-13 13:45:17 CST 完成。所有执行型 checks 为 `17/17 SUCCESS`；没有
failed、cancelled 或 pending job，也没有 rerun attempt。

Codecov comment 报告 patch coverage 为 `83.56808%`，35 行未覆盖，project coverage 从 `42.08%`
升至 `42.28%`。它不是 required check，也没有让 CI rollup 失败；未覆盖行中包含生成的
apply-configuration 和 webhook registration。该结果应作为覆盖信息保留，不能写成 CI blocker。

## Review 新信号

当前没有 human review。Copilot 的唯一 inline comment 指出：`validateComponentFields()` 只处理
`spec.components` 和 `spec.clusters[*].components`，没有处理
`spec.gracefulEvictionTasks[*].components` 与 `spec.requiredBy[*].clusters[*].components`。

源码核对后的结论需要按字段所有权拆开：

- **gate-off 保护存在确定缺口。** 这两个嵌套路径确实没有进入新旧值比较，所以 `v1alpha2` UPDATE
  仍可能在 feature gate 关闭时新增或修改 component data。`isComponentAwareBindingSpec()` 只负责
  legacy write guard，虽然覆盖这两个路径，但不能替代 `v1alpha2` 的 feature-gate validation。
- **`GracefulEvictionTask` 属于当前 Binding。** 新增或变更的驱逐 component result 应按当前
  `spec.components` 校验 membership 和 duplicate；已有历史快照仍需 grandfather，避免普通更新被
  component-set 演进锁死。
- **`RequiredBy` 属于另一个 Binding。** dependencies-distributor 会把被依赖 Binding 的
  `Spec.Clusters` 复制进 attached Binding 的 snapshot；attached Binding 自身可能是没有
  `spec.components` 的 ConfigMap 或 Secret。因此不能按当前对象的 desired components 判 unknown，
  只应校验每个 nested result 自身 duplicate，并补 gate-off 新旧值保护。

`RequiredBy` 有正常生产 writer，这个缺口不是只能手工构造的状态。最小修复仍可限制在
`pkg/webhook/resourcebinding/validating.go` 和 `validating_test.go`：按各嵌套对象的稳定身份比较新旧
component result，允许 unchanged/reordered 和 removal，拒绝 introduction/change；同时按上述所有权
分别处理 membership。任何开放 PR 分支 push 或 upstream reply 都要重新经过 exact-action gate。

## 当前状态与下一步

- PR #7830：Open、非 Draft、mergeable；Tide pending 的直接原因是缺少 `lgtm` 和 `approved`。
- CI：current SHA 全绿，验证阶段已完成。
- Review：一条未解决的 Copilot inline comment，经源码复核确认为合并前 P1；没有 human review。
- PR1 下一步：在两个现有 webhook 文件内补 nested result 的 ownership-aware validation 和测试，运行
  focused tests 与 `make verify`；完成本地 review 后，再申请开放 PR branch push 与回复授权。
- PR2 下一步：等待 PR1 API/validation 合同稳定后再 rebase 和提交，避免线性 stack 重复返工。
