# Day 52：#7492 最终 PR4 实现与验证

- 日期：2026-08-16
- Issue：[#7492](https://github.com/karmada-io/karmada/issues/7492)
- source worktree：`/home/ranxi/projects/karmada-pr4-integration`
- source branch：`pr4-local-integration-on-pr0-pr1-pr2-pr3`
- 最终本地提交：`40d82879fbbbc1535e8028108ce68cbf4f7b9736`
- 父提交：`ea87825092c2d225c574585626d1a3f844150bb0`（PR3 integration copy）
- 边界：源码已提交但未推送；未创建或更新 upstream PR

## 先说人话

这次 PR4 不再只是“让 scheduler 多跑一次”，而是把 #7492 的最后一个行为闭环补完整。

假设 FlinkDeployment 已在 `member1` 运行：

```text
accepted: jobmanager=1, taskmanager=1
desired:  jobmanager=1, taskmanager=2
```

scheduler 只向 `member1` 询问新增的一个 `taskmanager` 能否放下。能放下才把 accepted result 改为 `1/2`；
放不下时，binding 里的 desired 可以保持 `1/4`，但 accepted result 和现有 Work 仍保持旧值。这样同一次 source
更新中的 CPU、镜像或环境变量也不会趁调度失败传播到成员集群。

最终实现还处理了两个容易被 happy path 掩盖的问题：

1. scheduler 的 result patch 与 status patch 不是同一个 API 写操作。进程在两次写之间退出或遇到并发更新时，
   下一次 reconcile 必须知道哪个结果已经被接受，不能只猜 `generation`。
2. binding controller 读取的是最新 source。如果 detector 尚未把新组件需求写进 binding，controller 不能把
   更新后的 source 提前复制进 Work；但镜像等不影响调度的更新仍应正常传播。

## 结论

最终 PR4 已在本地完成以下行为：

- multi-component replica change 会重新进入 scheduling；
- 健康 accepted target 上的纯 scale-up 只估算正增量，纯 scale-down 跳过 estimator；
- 健康 target 不会因为 scale-up 容量不足迁移；target missing/terminating 时允许走原有 failover；
- `FitError`、不支持的 transition 或无效结果不会覆盖旧 `spec.clusters`；
- pending transition 会冻结整组 Work，包括 orphan cleanup、create 和 update；
- result/status 分步写入失败后可以依据持久 provenance 修复状态；
- legacy binding 有保守 backfill 与显式 reschedule 恢复路径；
- custom scheduler、suspended binding 和 feature-off 路径不被默认 scheduler 的新协议卡住。

## 运行过程

### 1. 判断是否存在 pending result

开启 `MultiplePodTemplatesScheduling` 且组件数大于 1 时，以下任一情况进入 pending：

- 尚无 accepted component result；
- desired name/replicas 与 `spec.clusters[*].components` 不一致；
- 当前 `ReplicaRequirements` 与 accepted requirements identity 不一致；
- 已有 component result，但 placement 已离开受支持的单集群形状。

### 2. 选择调度路径

| 当前状态 | 行为 | 失败后结果 |
| --- | --- | --- |
| 健康 target，纯 scale-up | 固定当前 target，只估算正增量 | 保留旧 result/Work |
| 健康 target，纯 scale-down | 固定当前 target，跳过 estimator | 保留旧 result/Work |
| target missing/terminating | 不固定 target，完整估算并走 failover | 保留旧 result/Work |
| name、mixed direction、requirements 或 placement 冲突 | 自动路径 fail closed，写 `Scheduled=False` | 保留旧 result/Work |
| pending 且有新的 explicit reschedule | 完整、不固定 target 的恢复调度 | 保留旧 result/Work |

ordered `ClusterAffinities` 没有被纳入这套自动恢复合同；它仍保持 fail closed。

### 3. 原子接受结果

scheduler 在同一个带 `metadata.resourceVersion` 前置条件的 main-resource merge patch 中写入：

- `spec.clusters`；
- applied placement；
- accepted requirements hash；
- accepted result generation token；
- accepted scheduling spec hash。

随后 status patch 也携带 `resourceVersion`。若 detector 在两次 patch 之间更新 binding，status patch 返回 conflict，
下一次 reconcile 再根据持久 token/hash 判断是修复 status、处理新 transition，还是继续 fail closed。

### 4. 控制 Work 交付

默认 scheduler 管理的 pending result 会在读取 source 和删除 orphan Work 之前直接返回，因此整个 Work 集保持不变。
result 已接受后，controller 再检查：

1. source UID 是否与 binding reference 一致；
2. source `resourceVersion` 是否与 reference 完全一致；
3. 若版本不同，重新解释 source 的 component replicas/requirements，并与 binding 比较。

第 3 步允许 image-only 等 config update 继续交付，同时阻止 detector lag 时的新副本或新资源需求提前泄漏。

这套门禁只属于 default scheduler 协议。custom scheduler、suspended binding 与 feature-off 路径继续接受旧式
`Clusters[].Replicas`，不会被缺少 `Clusters[].Components` 拒绝。

## 三个持久 identity

### Accepted requirements hash

```text
scheduler.karmada.io/accepted-component-requirements-hash=v1:sha256:<64 hex>
```

输入是按 name 排序的 `Name + ReplicaRequirements`，不含 replicas。replicas 已由
`TargetCluster.Components` 保存；将两者分开后，纯副本变化可以使用增量估算，requirements 变化则不会被误判为增量。

### Accepted result generation

```text
scheduler.karmada.io/accepted-component-result-generation=<generation>
```

它证明 main patch 产生的 result 属于哪个 binding generation。main patch 改 spec 时，scheduler 在 patch 前预测
generation 增量，并在 API 响应后校验实际 generation。

### Accepted scheduling spec hash

```text
scheduler.karmada.io/accepted-component-scheduling-spec-hash=v1:sha256:<64 hex>
```

它覆盖接受结果后的完整 `ResourceBindingSpec`，只清除 source `ResourceVersion`，并按 name 规范化 component 数组。
因此 config-only detector update 可以修复 status，而 placement、trigger、schedulerName、suspension、UID 等调度语义变化
不能借旧 token 被误认成成功。

## 升级与恢复

升级顺序必须是：

```text
API / CRD (#7837) -> new binding controller leader -> new scheduler
```

如果不能保证两个 runtime component 已更新，应保持 Alpha feature gate `MultiplePodTemplatesScheduling` 关闭。

旧对象按可证明程度处理：

| 旧状态 | 自动处理 |
| --- | --- |
| Duplicated、当前 success、无 component snapshot | 从 desired components 构造 snapshot，再补 identity |
| Duplicated、完整 snapshot、仅缺 requirements hash | 补 identity，不改 accepted result |
| Divided 或无法证明的 legacy result | 保持 pending；由新的 explicit reschedule 完整重算 |
| result patch 已成功、status patch 失败 | generation token 或 spec hash 匹配时只修复 status |
| 失败 transition 回滚到 accepted spec | spec hash 匹配时恢复 `Scheduled=True`，不重复估算 |

## 技术证据

主要实现位置：

- `pkg/util/binding.go`：pending/accepted 判定与 requirements hash；
- `pkg/scheduler/scheduler.go`：routing、result provenance、CAS patch、status repair 与 migration；
- `pkg/scheduler/core/estimation.go`、`generic_scheduler.go`：delta/downscale planner 与 target pinning；
- `pkg/controllers/binding/common.go`：Work freeze、source semantic fence 与 scheduler ownership；
- `test/e2e/suites/base/schedule_multi_template_test.go`：Flink lifecycle。

最终提交相对 `ea8782509` 修改 21 个文件，`4454 insertions(+), 114 deletions(-)`；新增规模主要来自 RB/CRB
对称场景和 scheduler 并发/迁移矩阵测试。

最终树通过：

```text
go test -race -count=1 ./pkg/util ./pkg/controllers/binding ./pkg/scheduler ./pkg/scheduler/core ./pkg/scheduler/metrics
go test -count=1 ./test/e2e/suites/base -run '^$'
GOMODCACHE=/home/ranxi/go/pkg/mod make verify
git diff --check
```

base E2E 命令只证明测试代码可编译，输出为 `[no tests to run]`；本机没有运行 live multi-cluster Flink E2E。

## 调试与终审记录

- 第一次 `make verify` 发现 5 个测试函数的 gocyclo 和 1 个 `map[string]interface{}` modernize 问题；
  拆出 fixture/runner/assert helper 后通过。
- 终审发现 custom scheduler 虽绕过 pending fence，底层仍会拒绝 legacy scalar result；修复为只对 feature-on +
  default-scheduler ownership 强制 accepted component result，并补 RB/CRB 完整 Reconcile 回归。
- 该修复一度让 `ensureWork` 圈复杂度从 15 变为 16；提取纯 helper 后，最终 `make verify` 通过。
- scheduler provenance、binding delivery 与 issue acceptance 三路独立源码复核均未留下可达 blocker。

## 未决边界

- live multi-cluster E2E 尚未执行；quota 场景的真实 estimator 行为仍需 upstream CI 或可用环境验证。
- ordered `ClusterAffinities` 不参与自动/显式 component recovery。
- custom scheduler 与 suspended binding 明确保留旧交付行为，不承诺 default scheduler 的 accepted-result 保护。
- source branch 尚未推送；远端目标和 force-with-lease 仍需用户确认。

## 下一步

reviewer-facing 文案见
[`day52-issue7492-pr4-body-draft.md`](day52-issue7492-pr4-body-draft.md)。确认后再把本地提交以显式 lease 推送到
`origin/feature/multi-component-failure-safe-rescheduling`；正文或 upstream PR 的任何更新仍需单独确认 exact target/text。
