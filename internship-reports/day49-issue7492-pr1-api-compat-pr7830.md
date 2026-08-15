# Day 49：#7492 PR1 API 与旧版本写入保护提交

- 日期：2026-08-13
- Issue：[`karmada-io/karmada#7492`](https://github.com/karmada-io/karmada/issues/7492)
- Pull Request：[`karmada-io/karmada#7830`](https://github.com/karmada-io/karmada/pull/7830)
- 当前 Head：`6ff28fe4a1d42b8a7980e60e0276306731c15656`
- 前一远端 Head：`ac32f86714425b7e2288ca75d7a15942655fec85`
- 初始 Head：`c0b68f728efe9336ff0ea226726228e4ea868fe8`
- Base：`09c08f405b2f0b53106b1947e08a82d4cc94de28`
- 状态：Open、非 Draft；已改基到 #7837 current head 并 force-with-lease 更新 PR；DCO 成功，upstream PR CI 已在新 SHA 上启动，未发布评论

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
但 #7837 增加 slice 字段后，`TargetCluster` 已不再是 Go 的 comparable type，现有
`test/helper/scheduler.go` 仍调用要求元素 comparable 的 `slices.Contains`，所以 API-only patch 不能独立
通过编译。此时不能只等 merge：应在 #7837 上补它直接引入的 helper 适配并验证；#7830 的正式 rebase
仍等稳定 merge SHA，不能把开放 head 当成最终历史基线。

#7837 current head 为 `afecff517`，base 为 `a957f64d5`，共 12 个文件、`+315/-4`。它只包含：

- `TargetCluster.Components` 和 `TargetComponent`；
- v1alpha1/v1alpha2 conversion；
- CRD、Swagger、OpenAPI、deepcopy 和 apply-configuration 生成物。

它不包含 #7830 的 webhook validation、RB/CRB legacy main/status guard、webhook manifests、compatibility
E2E、conversion test 或 result helper test。

### #7837 当前 CI blocker 与立即动作

2026-08-15 的 lint、unit、CLI、Operator 与 base E2E jobs 已给出同一编译错误：

```text
# github.com/karmada-io/karmada/test/helper
../../../helper/scheduler.go:31:27: "github.com/karmada-io/karmada/pkg/apis/work/v1alpha2".TargetCluster does not satisfy comparable
```

直接因果链是：`TargetCluster.Components []TargetComponent` -> `TargetCluster` 不再 comparable ->
`slices.Contains(tc2, c1)` 无法实例化。这个错误由 #7837 的 API change 直接触发，因此最小 helper 适配
应由 #7837 一起吸收，而不是等待 #7830 rebase 后才修。当前执行路径是在 #7837 exact head 上先复现，
再准备只涉及 `test/helper` 的本地 commit 和 targeted test 证据；任何 fork push 或 upstream comment 仍需
用户确认 exact target/text。

### 本地最小修复证据

在独立 worktree `karmada-pr7837-helper-fix` 中，从 #7837 exact head `afecff517` 创建本地分支
`pr7837-helper-compile-fix`。修复只改 `test/helper/scheduler.go`：用
`slices.ContainsFunc` + `reflect.DeepEqual` 替代要求 `TargetCluster` comparable 的 `slices.Contains`，形成
DCO commit `ce77a4cdf`（`test: compare non-comparable schedule results`）。

| 阶段 | 命令 | 结果 |
| --- | --- | --- |
| 修复前 | `go test ./test/helper` | 按 CI 同样的 `TargetCluster does not satisfy comparable` 编译失败 |
| 修复后 | `go test ./test/helper` | Pass；该包无独立 test files，结果证明 helper 自身可编译 |
| 调用方 | `go test ./pkg/scheduler/core ./pkg/util/helper ./pkg/util` | 3/3 packages Pass |
| 静态检查 | `gofmt`、`git diff --check` | Pass |

这里没有把 #7830 的完整 name-indexed comparator 移入 #7837。完整版本还会忽略 component 顺序、把
nil/empty 视为相等、拒绝 duplicate component name，并修复已有的 duplicate-cluster match reuse；这些
都在重新定义 helper 语义，且依赖 #7830 曾提出但 #7837 current API 尚未声明的 list-map 语义。API-only
PR 的 unblock patch 只恢复编译和原有整项相等模型。独立 scope 审计后决定不在 PR1 保留完整 comparator：
它还会引入 duplicate-cluster 修复、nil/empty 归一化和 component order-insensitive 语义，而 #7837
current schema 仍是 atomic list。若这些语义需要成为 API 合同，应在 #7837 或后续专门变化中明确决定。

### Fork branch 与策略变更

用户确认后，`pr7837-helper-compile-fix` 已以同名分支 push 到 `origin`，没有 force，也没有创建 PR。
准备给 #7837 的评论没有发布。fork push CI 停止等待时，codegen、lint、compile、unit、CLI 3/3、
Operator 3/3 和 Chart 3/3 已通过，base E2E 3 个仍在运行；这些结果只证明 `ce77a4cdf` 的 fork branch，
不作为 PR1 body 或 upstream merge 证据。

随后用户决定不再等待 #7837 merge 或 fork E2E，直接以这两个 exact commits 作为本地 stacked base 重建
PR1：

```text
afecff517  #7837 API and generated artifacts
  -> ce77a4cdf  minimal non-comparable helper adaptation
     -> <new PR1 commit> validation and compatibility only
```

这不是把 #7837 的开放 head 当作已合并的 upstream history；它是为尽快更新现有 PR #7830 而明确接受的
临时 stacked history。后续 #7837 若修改或 squash，PR1 仍需按最终 merge SHA 再做一次 ancestry cleanup。

### 基于两个 commit 的 PR1 重建设计

#### `/status` 语义复核

`statusStrategy.PrepareForUpdate` 确实会复制旧对象并只替换 status，但这里的旧对象不是 storage version。
`apiextensions-apiserver/pkg/apiserver/customresource_handler.go` 会为每个 served version 创建独立 Store，
其中 `decoderVersion` 是请求版本、`encoderVersion` 才是 CRD storage version；同文件还明确说明该 handler
使用 served version 作为内存表示。因此，`v1alpha1 /status` 从 etcd 读取对象时会先经 conversion 丢失
`Components`，`PrepareForUpdate` 复制的是已经有损的 `v1alpha1` 旧对象，再编码回 `v1alpha2` 时仍无法恢复。

结论是保留两条 `v1alpha1 */status` exact webhook rules，并继续在 status short-circuit 前执行 storage-state
guard。现有 E2E 已覆盖 status 拒绝，但没有证明主资源 `v1alpha1 Update` 经 `matchPolicy: Equivalent` 被实际
路由到 validator；重建时为 RB/CRB 补这个真实请求覆盖。

#### 文件范围

| 文件组 | 文件数 | PR1 保留行为 | 验证 |
| --- | ---: | --- | --- |
| webhook registration/configuration | 6 | 注册 RB/CRB 主资源 equivalent rules 与 `v1alpha1 /status` exact rules，并给 handler 注入 uncached `APIReader` | configuration unit test、`make verify` |
| v1alpha1 compatibility | 1 | 覆盖旧客户端 main/status 写入保护和 legacy Binding 正常写入 | base E2E compile |
| ResourceBinding validation | 2 | 保留 `TargetCluster`、`RequiredBy`、feature-gate rollback 和 v1alpha1 storage-state guard；删除全部 eviction component 逻辑 | focused unit/race tests |

精确 9 个 residual 文件：

```text
artifacts/deploy/webhook-configuration.yaml
charts/karmada/templates/_karmada_webhook_configuration.tpl
cmd/webhook/app/webhook.go
operator/pkg/karmadaresource/webhookconfiguration/manifests.go
pkg/karmadactl/cmdinit/karmada/webhook_configuration.go
pkg/karmadactl/cmdinit/karmada/webhook_configuration_test.go
pkg/webhook/resourcebinding/validating.go
pkg/webhook/resourcebinding/validating_test.go
test/e2e/suites/base/binding_version_compatibility_test.go
```

#### 明确不改

- 不修改 #7837 已拥有的 API types、conversion implementation、CRD、Swagger、OpenAPI、deepcopy 或
  apply-configuration 生成物。
- 不把 #7830 原有的 `listType=map`、`listMapKey=name`、`MinLength`、`MaxLength` 或 `Minimum` markers
  静默带回。
- 不添加 `GracefulEvictionTask.Components`，也不保留对应 legacy detection、validation helper 或 tests。
- 不保留 `binding_types_conversion_test.go`；它测试 #7837 拥有的 conversion implementation，应单独补给
  #7837，而不是让 runtime-validation PR 测试未修改的 base code。
- 不保留完整 `test/helper` comparator；`ce77a4cdf` 已提供编译适配，额外的 name-indexed/multiset 语义
  与当前 atomic-list API 合同不是同一项变化。
- 不加入 scheduler producer、component scale planner、delivery、failed-rescheduling protection 或新 controller。
- 不修改或 force-push #7837 helper branch；PR1 先在新的本地 rebuild branch 完成，更新开放 PR branch
  仍需 exact-action gate。

#### 实现与验证顺序

1. 从 `ce77a4cdf` 创建全新 worktree，机械移植 #7830 的 9 个 runtime validation/compatibility 文件。
2. 用源码级 patch 删除 `GracefulEvictionTask.Components` detection、validator 和专用测试。
3. 保留 status 专用 webhook rules 与 guard 顺序，为 RB/CRB 增加真实 v1alpha1 主资源 UPDATE 拒绝 E2E。
4. 确认相对 `ce77a4cdf` 只有上述 9 个文件，且相对旧 PR 的差异只来自 API/test ownership split、
   eviction scope 删除及 E2E 证据补强。
5. 运行 focused unit/race tests、E2E package compile、`make verify`；检查 DCO、range-diff、merge-base 和
   force-with-lease lease target。
6. 更新 PR title/body 草稿以删除 API ownership、Graceful 字段和过期 CI 描述；得到 exact user approval
   后才更新 `origin/feature/multi-component-scale-rescheduling` 与 PR metadata。

### Rebase 后预期 diff

| 归属 | 文件数 | 处理 |
| --- | ---: | --- |
| #7837 API 与生成物 | 12 | 合并后成为 base，必须从 #7830 diff 消失 |
| `GracefulEvictionTask` apply/API 产物 | 1 | #7837 从未增加该字段，#7830 不应重新引入 |
| #7830 validation 与 compatibility | 9 | 保留并基于 stacked API/helper base 重新验证 |

预期保留的 9 个文件是四份 webhook configuration、karmadactl configuration test、
`cmd/webhook/app/webhook.go`、`pkg/webhook/resourcebinding/{validating.go,validating_test.go}` 和
compatibility E2E。conversion test 与完整 result helper 已按 ownership 审计退出 PR1；最终合并历史仍需
以 #7837 merge SHA 再做 ancestry cleanup。

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

- PR #7830：Open、非 Draft；2026-08-15 已先按 exact lease 将远端 head 从 `c0b68f728` 更新到
  `ac32f8671`，随后采用 #7837 current head 再更新为 `6ff28fe4a`。title 保持
  `feat: validate component scheduling results in bindings`；没有发布评论。
- 本地重建：`pr7830-rebuilt-on-pr7837` 已在 `afecff517 -> ce77a4cdf` 上形成 DCO commit
  `ac32f8671`（`feat: validate component scheduling results`）。完整临时 stack 相对 `a957f64d5` 为
  22 文件 `+1791/-16`；PR1 residual 相对 `ce77a4cdf` 精确 9 文件 `+1472/-11`。
- 验证：focused unit tests、两包 race tests、base E2E package compile 和完整 repository verify 通过。
  第一次 bare `make verify` 只在清理临时 `_go/pkg/mod` 的只读 auto-toolchain cache 时失败；使用现有
  `GOMODCACHE` 重跑后 codegen、staticcheck、vendor、Swagger、CRD 和 license 全部通过，worktree clean。
- Review：Copilot nested validation finding 已在 current head 修复；`@RainbowMango` 创建 #7837 接管
  API 变化；本地重建已删除 `GracefulEvictionTask.Components` 与完整 helper comparator，并补 main-resource
  v1alpha1 E2E、status guard 文案断言和 TargetCluster rollback identity/multiset 反例。
- PR1 下一步：不为当前 v1.35 环境失败修改代码，也不再给 #7837 提供 helper commit 或评论。已先基于
  #7837 current head 重建本地 ancestry；待用户确认 exact lease 后 force-push 以触发新 head CI，评论等 CI
  结果。#7837 最终合并后仍需按实际 merge commit 做最终 ancestry cleanup。
- PR2 下一步：等待 PR1 API/validation 合同稳定后再 rebase 和提交，避免线性 stack 重复返工。

## `ac32f8671` Upstream CI 红灯复核

### 先说人话

这次红灯不是新 webhook 或 compatibility test 失败，而是现有
`Aggregated Kubernetes API Endpoint` 用例在真正执行断言前，创建第五个临时 kind 集群失败。
同一个 SHA 的 v1.34 和 v1.36 matrix 都通过；v1.35 中本 PR 新增的三个用例也全部通过。因此当前应重跑
失败 matrix，不应为这个红灯继续修改 PR1。

一个具体例子：v1.35 job 在 10:51:31 开始创建 `member-e2e-rlzt8`，但在 `BeforeEach` 卡了约 289 秒，
最后由 `kubeadm init` 返回 `exit status 1`。这个 spec 的测试主体位于
`aggregatedapi_test.go:210`，失败点却是准备集群的 `aggregatedapi_test.go:84`，说明业务断言尚未运行。

### 运行过程与证据

- 检查对象是 run `31879143221`、job `94999880311`、attempt 1；head 为 `ac32f8671`，没有 rerun
  artifact 归因歧义。除 v1.35 base E2E 外，其余 16 个 check runs 均为 Success。
- 本 PR 新增的 `ResourceBinding` 保护、`ClusterResourceBinding` 保护和 legacy status 更新用例分别在
  10:37:33、10:39:10、10:41:44 通过，耗时 `0.061s`、`0.267s`、`0.302s`。
- 首个硬失败是 10:56:20 的
  `failed to init node with kubeadm: ... member-e2e-rlzt8-control-plane ... exit status 1`。之后
  `172.18.0.5:5443` 和 `:6443` 的 `connection refused` 发生在 `AfterEach`、suite cleanup 和 CI 清理，
  都是控制面已经不可用后的级联错误。
- attempt-compatible component artifact `9245954402` 显示该窗口不是单个 webhook 进程失败：host
  Kubernetes etcd 从 10:51:54 开始出现读延迟，并在 10:52:02 报 `slow fdatasync`；apiserver 在
  10:51:59 至 10:52:03 进入 readiness/liveness failure；随后 containerd 操作连续
  `context deadline exceeded`，host kube-apiserver 和 Karmada etcd 分别在 10:54:03、10:54:08 以
  status 137 退出。
- v1.34 和 v1.36 的同名 `Aggregated Kubernetes API Endpoint` spec 分别在约 49 秒和 46 秒内通过，
  且临时集群创建通常只需约 12 至 16 秒。这与 v1.35 的 289 秒 setup failure 构成同 SHA 对照。

### 证据边界与动作

现有 artifact 足以把失败归类为 CI 环境整体失去响应，并排除 PR 新增断言的直接失败；但它没有 runner
host 的 kernel OOM、PSI 或完整磁盘指标，因此不能把物理根因进一步写成已证实的 OOM 或磁盘故障。
旧 issue #3667 记录过相同 `kubeadm init` 表象，但当时涉及不同 runner/kind 版本，不能直接套用其根因。

当前不改代码、不追加空 commit、不重写 PR。#7837 的新 head 已经全绿，当前临时 stack 很快会被正式
rebase 取代，因此默认不单独重跑该 v1.35 job；如果 #7837 合并延迟且必须先恢复当前 SHA 的绿灯，任何
`/retest` comment 或其他 upstream 动作仍需用户确认 exact target/text。

## #7837 已吸收 helper 修复

#7837 作者随后将 head 从 `afecff517` 改写为 `76589a9d5`，直接在其唯一 commit 中修复
`test/helper/scheduler.go`：用 `slices.ContainsFunc` 比较 cluster identity/replicas，并用
`slices.Equal` 比较有序 component 结果。两个 head 的实际 tree diff 只有该文件 `+4/-1`；current head 的
codegen、lint、compile、unit、三组 Kubernetes 三版本矩阵、base E2E 三版本和 DCO 共 17 个 checks
全部 Success。Tide 只等待 `lgtm/approved`，不是代码或 CI blocker。

因此本地 `ce77a4cdf` 只保留为 #7830 当前临时 stacked ancestry 的历史中间点，不再提交给 #7837，
也不再发布 helper comment。#7837 合并后，#7830 必须改基到实际 merge commit，完整丢弃
`afecff517 + ce77a4cdf`，采用 upstream 已验证的 helper 实现后重新运行 residual tests。

## 在 #7837 current head 上提前重建

### 先说人话

用户决定不等 #7837 合并：既然 `76589a9d5` 已经吸收 helper 修复并通过全部 checks，就直接把 #7830 的
临时前置历史换成这个 current head。这样不需要追加空 commit，也不需要为无关的 v1.35 环境失败改代码；
新的 PR head 会自然触发整套 CI。

旧、新历史分别是：

```text
旧：a957f64d5 -> afecff517 -> ce77a4cdf -> ac32f8671
新：a957f64d5 -> 76589a9d5 -> 6ff28fe4a
```

在独立 worktree `karmada-pr7830-current7837` 中，从 `76589a9d5` 只 cherry-pick PR1 residual
`ac32f8671`，得到 DCO commit `6ff28fe4a`。`range-diff` 标记两个 residual 为 `=`，stable patch-id 均为
`95394cbe4065b3a5f54abb456f14aabd3ac48681`；新 commit 的 parent 精确为 `76589a9d5`。相对新 base 仍是
原来的 9 文件 `+1472/-11`，旧、新最终 tree 只在 #7837 已修复的 `test/helper/scheduler.go` 有差异。

| 验证 | 结果 |
| --- | --- |
| `git diff --check a957f64d5..6ff28fe4a` | Pass |
| `go test -race -count=1 ./pkg/webhook/resourcebinding ./pkg/karmadactl/cmdinit/karmada` | 2/2 packages Pass |
| `go test -count=1 ./test/e2e/suites/base -run '^$'` | Pass，base E2E package 可完整编译 |
| `GOMODCACHE=/home/ranxi/go/pkg/mod make verify` | Pass；staticcheck、mock、gofmt、vendor、Swagger、CRD、codegen 和 license 均无漂移 |

用户确认 exact action 后，已以 `ac32f8671` 为显式 lease，将
`origin/feature/multi-component-scale-rescheduling` force-with-lease 更新到 `6ff28fe4a`。GitHub PR head
与 fork remote 均已核对为该 SHA；DCO Success，首批 12 个 checks 已进入 queued/in-progress，证明 upstream
PR CI 已重新触发。title、body 均未修改，也没有发布评论。现有 PR body 中 `minimal compile follow-up`
的描述会在新拓扑下过期；按用户要求先等 CI 结果，后续修改仍走 exact-text confirmation。
