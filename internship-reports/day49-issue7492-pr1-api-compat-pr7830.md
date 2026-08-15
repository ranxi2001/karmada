# Day 49：#7492 PR1 API 与旧版本写入保护提交

- 日期：2026-08-13
- Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- Pull Request：[`karmada-io/karmada#7830`](https://github.com/karmada-io/karmada/pull/7830)
- Head：`c0b68f728efe9336ff0ea226726228e4ea868fe8`
- Base：`09c08f405b2f0b53106b1947e08a82d4cc94de28`
- 状态：Open、非 Draft；current-SHA upstream checks 全绿；maintainer 已用 #7837 接管 API 变化，#7830 等其合并后 rebase 并收窄为 validation 与 compatibility

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

截至 2026-08-15，current head `c0b68f728` 的 17 个执行型 checks 和 DCO 全部通过。当前仍不能写成
“可以合并”：Tide 等待 `lgtm` 和 `approved`，`@RainbowMango` 已开始 human review，并要求解释
`GracefulEvictionTask.Components` 的必要性。源码复核后已确认该字段没有当前 consumer，公开回复已承诺
移除。随后 maintainer 创建 API-only PR #7837，并明确要求 #7830 等它合并后再 rebase；因此当前不再
继续生成、测试或提交旧 head 上的字段删除。

## PR1 的实际范围

PR 为一个 DCO commit，current head 共 25 个文件，`+2403/-17`。手写行为和生成面包括：

1. 在 `work.karmada.io/v1alpha2` 增加 `TargetComponent` 和 `TargetCluster.Components`；
   `GracefulEvictionTask.Components` 将按 human review 从当前 PR 删除。
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

精确 SHA `c0b68f728` 的检查如下：

| 检查面 | 结果 |
| --- | --- |
| DCO | Success |
| codegen、lint、compile、unit test | 全部 Success |
| base E2E：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| CLI：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| Operator：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |
| Chart：Kubernetes v1.34、v1.35、v1.36 | 3/3 Success |

所有执行型 checks 为 `17/17 SUCCESS`，DCO 也为 Success；没有 failed、cancelled 或 pending job。
这只证明 current head，后续 rebase 后必须按新 SHA 重新验证。

Codecov comment 报告 patch coverage 为 `88.25503%`，35 行未覆盖。它不是 required check，也没有让
CI rollup 失败；未覆盖行中包含生成的
apply-configuration 和 webhook registration。该结果应作为覆盖信息保留，不能写成 CI blocker。

## Review 新信号

Copilot 的唯一 inline comment 指出：`validateComponentFields()` 只处理
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

`RequiredBy` 有正常生产 writer，这个缺口不是只能手工构造的状态。该缺口已在 `c0b68f728` 修复：
`RequiredBy` 按 snapshot identity 做 duplicate 与 gate-off old/new validation；当时也为
`GracefulEvictionTask.Components` 增加了相应 validation。Copilot thread 已回复，但没有 bot resolve 信号。

2026-08-15，`@RainbowMango` 进一步问：为什么需要给 `GracefulEvictionTask` 增加 component，是否必要。
这条 human review 改变了当前 scope。#7492 的 maintainer-provided API 草案只提出
`TargetCluster.Components`；公开回复已经说明 `GracefulEvictionTask` 只跟踪从旧 cluster 的 eviction，
没有当前 component consumer，并承诺从本 PR 删除该字段。

## 2026-08-15 收窄设计

### 先说人话

调度结果需要回答“`member1` 上的 `jobmanager` 和 `taskmanager` 各分了多少副本”，所以这个信息属于
`TargetCluster.Components`。驱逐任务当前只回答“哪个 cluster 正在退出、何时超时、是否可以完成”，
没有任何 controller 会读取 component 明细。继续把同一字段放进 `GracefulEvictionTask`，不仅没有当前
行为收益，还需要 CRD/OpenAPI、legacy guard、rollback validation 和大量测试长期维护。因此本轮把它
从 API 中删除，而不是为尚未定义的 future consumer 保留扩展面。

具体例子：`FlinkDeployment` 在 `member1` 上记录
`jobmanager=1, taskmanager=20` 时，scheduler 和 binding controller 后续都需要从
`spec.clusters[0].components` 读取这份持久化结果；当 `member1` 被驱逐时，现有 graceful-eviction
controller 只按 `fromCluster=member1`、健康状态、超时和标量 `replicas` 处理任务，不读取每个 component。

### 文件范围

| 文件 / 区域 | 改动 | 原因 | 验证 |
| --- | --- | --- | --- |
| `pkg/apis/work/v1alpha2/binding_types.go` | 删除 `GracefulEvictionTask.Components` | 收回没有 producer/consumer 的 API 字段 | codegen、CRD、OpenAPI verify |
| `pkg/webhook/resourcebinding/validating.go` | 删除 eviction component 的 legacy 检测、validation 调用和 helper | 字段删除后不再存在对应写入路径 | webhook unit tests |
| `pkg/webhook/resourcebinding/validating_test.go` | 删除只证明 eviction component 合同的 cases | 避免测试继续固化已撤回的 API；保留 `TargetCluster` 与 `RequiredBy` 覆盖 | focused `go test` |
| 生成物 | 由 `update-codegen.sh`、`update-crdgen.sh`、`update-swagger-docs.sh` 重生成 | 只移除 `GracefulEvictionTask.components` schema/apply/deepcopy 内容 | 对应 verify scripts 与 diff 审计 |

### 明确不改

| 文件 / 区域 | 原因 |
| --- | --- |
| `TargetCluster.Components`、`TargetComponent` | 这是 #7492 maintainer 草案要求的持久化调度结果 |
| `RequiredBy[*].Clusters[*].Components` validation | snapshot 会复制另一个 Binding 的 `TargetCluster`，仍需 duplicate 与 gate-off 保护 |
| v1alpha1 main/status storage-state guard | legacy 写回仍会丢失 `spec.components`、target result 和 snapshot result |
| scheduler、binding、graceful-eviction controller | 本 PR 只收窄 API 基线，不新增或改变 runtime consumer |
| webhook manifests 与 compatibility E2E | 与 legacy status data-loss 保护有关，不由本次字段删除改变 |

### 验证计划

1. 依次运行 `hack/update-codegen.sh`、`hack/update-crdgen.sh`、`hack/update-swagger-docs.sh`，不并发执行生成器。
2. 确认 diff 只删除 eviction-specific API、validation、tests 和对应生成内容；`TargetCluster` 与
   `RequiredBy` component paths 必须保留。
3. 运行 `go test ./pkg/webhook/resourcebinding ./pkg/apis/work/v1alpha1 ./pkg/apis/work/v1alpha2 ./test/helper`。
4. 依次运行 `hack/verify-codegen.sh`、`hack/verify-crdgen.sh`、`hack/verify-swagger-docs.sh`；再按结果决定
   是否需要完整 `make verify`，不重复启动同类生成或验证。
5. 对最终 diff 做一次未提供既有结论的独立反证审查，重点检查 legacy guard 与 snapshot validation
   是否被误删。

上面这份计划在手写删除和第一次 `update-codegen.sh` 后被新的 maintainer 指令暂停，没有形成 commit，
也没有 push。它仍保留为“为什么不应扩展 `GracefulEvictionTask`”的设计证据，但不再是当前执行路径。

## #7837 拆分后的所有权边界

2026-08-15 16:43 CST，`@RainbowMango` 在 #7830 留言：

> I sent #7837, which focuses on API changes. @ranxi2001, please rebase this PR after that.

### 先说人话

#7837 先把“API 长什么样”单独落地；#7830 等它合并后，只保留“怎样阻止错误数据和旧客户端擦数据”。
现在立即 rebase 没有稳定目标，因为 #7837 仍是 Open，且刚收到 4 条 bot review，head 可能继续修改。
因此正确动作是等待 merge，而不是把 #7837 的开放分支临时当成新的 upstream base。

#7837 current head 为 `afecff517`，base 为 `a957f64d5`，共 12 个文件、`+315/-4`。它只包含：

- `TargetCluster.Components` 和 `TargetComponent`；
- v1alpha1/v1alpha2 conversion；
- CRD、Swagger、OpenAPI、deepcopy 和 apply-configuration 生成物。

它不包含 #7830 的 webhook validation、RB/CRB legacy main/status guard、webhook manifests、compatibility
E2E、conversion test 或 result helper test。

### Rebase 后预期 diff

| 归属 | 文件数 | 处理 |
| --- | ---: | --- |
| #7837 API 与生成物 | 12 | 合并后成为 base，必须从 #7830 diff 消失 |
| `GracefulEvictionTask` apply/API 产物 | 1 | #7837 从未增加该字段，#7830 不应重新引入 |
| #7830 validation 与 compatibility | 12 | 保留并基于 #7837 最终 API 重新验证 |

预期保留的 12 个文件是四份 webhook configuration、karmadactl configuration test、
`cmd/webhook/app/webhook.go`、v1alpha1 conversion test、
`pkg/webhook/resourcebinding/{validating.go,validating_test.go}`、compatibility E2E，以及
`test/helper/{scheduler.go,scheduler_test.go}`。最终文件数仍需以 #7837 merge SHA 上的真实 rebase 为准，
不能把这份静态比较写成已完成结果。

### 未决 API 边界

#7837 current API 注释使用 `spec.Components`，Copilot 已指出应为 JSON path `spec.components`。此外，
#7830 current head 曾为 target component list/name/replicas 增加 `listType=map`、`listMapKey=name`、
`MinLength`、`MaxLength` 和 `Minimum` markers，而 #7837 current head 没有这些 markers。API 变化已由
#7837 负责，所以 #7830 rebase 时不能静默重新带回；若它们属于必要 API 约束，应先完整审查 #7837，
再通过单独且经用户确认的 review comment 讨论。

### 本地中断证据

本地 comparison worktree `karmada-pr7830-remove-eviction-components` 从 `c0b68f728` 创建，曾完成 3 个
手写文件的 eviction-only 删除。第一次 `hack/update-codegen.sh` 已生成 4 个预期 Go 产物，但最终以
exit 1 结束：`GOTOOLCHAIN=auto` 在临时 `_go/pkg/mod` 下载只读 toolchain，脚本的 EXIT cleanup 报
`Permission denied`。已确认生成 diff 仅删除 eviction 字段，并删除本轮新建的 `_go/`；准备以
`GOFLAGS=-modcacherw` 重跑时收到 #7837 指令，因此停止，没有继续 CRD/Swagger generator、tests、commit
或 push。该 dirty worktree 只作对照，不是待推分支。

## 当前状态与下一步

- PR #7830：Open、非 Draft；Tide pending 的直接原因是缺少 `lgtm` 和 `approved`。
- CI：current SHA `c0b68f728` 全绿；任何本地后续提交都不能继承这份 current-SHA 结论。
- Review：Copilot nested validation finding 已在 current head 修复；`@RainbowMango` 创建 #7837 接管
  API 变化，并明确要求 #7830 在其后 rebase。
- PR1 下一步：等待 #7837 merge；以实际 merge SHA rebase，确认上述 13 个 API/eviction 文件从 diff
  消失，再验证 12 个 residual validation/compatibility 文件。完成本地 review 后，才申请开放 PR branch
  force-with-lease push 和 title/body 更新授权。
- PR2 下一步：等待 PR1 API/validation 合同稳定后再 rebase 和提交，避免线性 stack 重复返工。
