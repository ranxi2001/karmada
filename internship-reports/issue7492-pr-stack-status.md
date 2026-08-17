# #7492 多组件调度 PR 栈交接

> 状态核对：2026-08-17。PR 和 CI 状态会变化，技术合同与验证边界以本文记录的 exact SHA 为准。

这份文档合并原先分散的六份记录，只保留后续评审、发布和维护仍需要的信息。已发布的 PR 正文、rebase 命令、push 过程和被替代的设计可从 Git 历史或对应 GitHub PR 查询，不再单独维护副本。

<a id="stack-overview"></a>

## 先说人话

#7492 已拆成五个公开 PR，最后一片目前以 Draft 形式供 CI 和评审：

- PR0 提供 API 字段；
- PR1 保护这些字段不被非法或旧版本写入破坏；
- PR2 生成组件调度结果，并在 Work 交付时应用结果；
- PR3 计算扩缩容时需要估算的副本变化；
- PR4 把前述能力接入 scheduler，并在重新调度失败时保留旧结果和现有 Work。

公开的 PR1、PR2、PR3 都直接建立在 PR0 上，是三个 sibling PR。PR4 为了提前验证最终组合，在本地 integration history 中依次复制 PR1、PR2、PR3，再提交自己的 residual。两种历史用途不同：公开 sibling PR 便于分别 review，integration history 用于验证组合后的源码和 focused tests。

```text
公开 PR：
master -> 76589a9d5 (PR0)
                    |-> 6ff28fe4a (PR1)
                    |-> 98535c541 (PR2)
                    `-> 782232b7d (PR3)

PR4 integration：
76589a9d5 -> PR1 copy -> PR2 copy -> ea8782509 (PR3 copy) -> 49916cee1 (PR4)
```

## 当前状态

| 层级 | 公开对象 / exact head | 作用 | 2026-08-17 状态 |
| --- | --- | --- | --- |
| PR0 | [#7837](https://github.com/karmada-io/karmada/pull/7837) `76589a9d514543edc8c8ca47174cff360d3b832e` | `TargetCluster.Components` 等 API 基线 | Open，非 Draft，17 项 checks/DCO 成功，已有 `lgtm` |
| PR1 | [#7830](https://github.com/karmada-io/karmada/pull/7830) `6ff28fe4a1d42b8a7980e60e0276306731c15656` | validation、feature-gate rollback 与 v1alpha1 防丢失保护 | Open，非 Draft，17 项 checks/DCO 成功 |
| PR2 | [#7833](https://github.com/karmada-io/karmada/pull/7833) `98535c5413cca7a697ee754934d4d3a147f90597` | result producer、`ReviseComponents`、Work delivery、Flink customization | Open，Draft，17 项 checks/DCO 成功 |
| PR3 | [#7835](https://github.com/karmada-io/karmada/pull/7835) `782232b7db4455b7339b669978a6e799753528df` | component comparison 与 scale estimation planner，本身不激活生产入口 | Open，Draft，16 项成功；`e2e v1.35` 的直接机制是 estimator 请求未使用已创建 quota，底层同步原因待确认 |
| PR4 | [#7841](https://github.com/karmada-io/karmada/pull/7841) `49916cee119fef3cbee1977c3675f38c9c2f6322`，review range `ea87825092c2d225c574585626d1a3f844150bb0...49916cee119fef3cbee1977c3675f38c9c2f6322` | scale detection、target pinning、失败保留、result provenance 与 delivery fence | Open，Draft；DCO 成功，CI 已启动 |

截至状态核对，PR0 已获 `lgtm` 但仍缺 `approved`；PR1-PR3 没有 human review decision。checks 成功不等于功能切分已获接受。PR2/PR3 调整 ancestry 后的 `range-diff` 均为 `=`；PR2 residual 为 40 个文件、`+1445/-45`，PR3 residual 为 4 个文件、`+448/-6`。

## 分片评审边界

- **PR2**：负责 scheduler result producer、`ReviseComponents` interpreter/delivery 链、Flink customization 和 `RequiredBy` ownership；单组件 `Divided` 调度保留 scalar result，变化后的多组件结果缺少 revision hook 时 fail closed。它不负责 scale detection、增量估算、重新调度或失败保留。这个范围比 maintainer Draft 中建议的 PR2 更宽，仍需 reviewer 确认拆分是否合适。
- **PR3**：按组件名比较 desired 与 accepted 结果；纯 scale-up 只规划正 delta，纯 scale-down 不调用 estimator，缺快照或不支持的形状使用 full desired。predicate/planner 在该分片中没有生产调用者，因此 PR3 自身不改变生产行为。
- **PR4**：才把 scale change 接入 scheduler，并负责 target pinning、失败保留、result provenance 和 delivery fence。PR4 的 integration history 只能证明组合可构建和局部合同成立，不能代替各 sibling PR 的独立 review。

## PR4 为什么需要重做

旧 prototype 只保存组件名和副本数。假设已经接受：

```text
taskmanager = 4 x 100m CPU
```

用户一次更新为：

```text
taskmanager = 6 x 500m CPU
```

旧逻辑只估算新增的 `2 x 500m`，却可能在成功后交付完整的 `6 x 500m`；失败时也可能保留 4 个副本，却把每个副本的资源需求改成 `500m`。因此“副本数结果没变”不能证明旧 Work 应当接受最新 source。

最终 PR4 增加 accepted requirements identity 和 Work delivery fence：资源需求变化不能借旧结果通过；scheduler 尚未接受新结果时，binding controller 也不能提前更新或删除 Work。

## PR4 最终合同

1. **判断 pending**：受支持的单集群 placement 尚无 component result、desired 与 accepted 的 name/replicas 不同、requirements hash 不同，或已有 accepted component result 后 placement 离开该形状时，进入 pending。
2. **安全估算**：健康 accepted target 上的纯 scale-up 固定该 target，只估算正 delta；纯 scale-down 跳过 estimator。容量不足时不迁移整个 workload。target missing/terminating 才允许走既有 failover。
3. **失败保留**：name change、mixed direction、requirements change、placement conflict、ordered `ClusterAffinities` 或无效结果均 fail closed，不覆盖 accepted `spec.clusters` 和现有 Work。新的 explicit reschedule 是受控恢复入口，但 ordered `ClusterAffinities` 仍明确排除。
4. **持久接受**：scheduler 用带 `metadata.resourceVersion` 前置条件的 main-resource patch 同时写 result、placement 与三个 accepted identity；status 使用独立 CAS patch。两次写之间失败时，下一次 reconcile 可以判断应修复 status 还是继续调度。
5. **冻结交付**：default scheduler 管理的 pending binding 在读取 source、删除 orphan Work、创建或更新 Work 前返回。result 接受后，再比较 source UID、`resourceVersion` 和重新解释的 component inputs；image-only 等非调度变化仍可传播。普通 multi-component placement 和仅由 `RequiredBy` 增加、没有自有 component result 的 target 保留旧交付语义。
6. **兼容边界**：custom scheduler、suspended binding 和 feature-off 路径保留旧交付语义。legacy 自动 backfill 只覆盖可证明成功的 `Duplicated` 状态；其他对象需要 explicit reschedule。

三个持久 identity：

| Annotation | 解决的问题 |
| --- | --- |
| `scheduler.karmada.io/accepted-component-requirements-hash` | 判断当前结果是否仍对应同一组 `ReplicaRequirements` |
| `scheduler.karmada.io/accepted-component-result-generation` | 标记 result 属于哪个 binding generation |
| `scheduler.karmada.io/accepted-component-scheduling-spec-hash` | 防止 placement、scheduler、suspension、UID 等语义变化复用旧成功状态 |

requirements hash 的输入是按 name 排序的 `Name + ReplicaRequirements`，不含 replicas；replicas 由 `TargetCluster.Components` 单独保存。result-generation token 对应 main patch 接受的 binding generation。scheduling-spec hash 覆盖接受后的完整 `ResourceBindingSpec`，只清除 source `ResourceVersion` 并规范化 component 顺序。

当前 PR4 设计的安全 rollout 前提是 `API/CRD (#7837) -> new binding controller leader -> new scheduler`。这还不是 maintainer 已接受或 mixed-version live E2E 已证明的发布合同；无法保证两个 runtime component 都已更新时，应保持 Alpha feature gate `MultiplePodTemplatesScheduling` 关闭。

<a id="history-and-evidence"></a>

## 验证与边界

PR2 已通过：

```text
go test -race -count=1 ./pkg/scheduler/core ./pkg/detector ./pkg/controllers/binding ./pkg/resourceinterpreter/... ./pkg/util/interpreter ./pkg/karmadactl/interpret ./pkg/webhook/configuration
go test -count=1 ./test/e2e/suites/base -run '^$'
make verify
```

PR3 已通过：

```text
go test -race -count=1 ./pkg/scheduler/core ./pkg/util
make verify
```

最终 PR4 candidate 是 1 个 DCO commit，修改 21 个文件，`+4554/-114`。已通过：

```text
go test -race -count=1 ./pkg/util ./pkg/controllers/binding ./pkg/scheduler ./pkg/scheduler/core ./pkg/scheduler/metrics
go test -count=1 ./test/e2e/suites/base -run '^$'
make verify
git diff --check
```

PR2 和 PR4 的 base E2E compile 命令输出 `[no tests to run]`，只证明测试 package 可编译。没有执行 live multi-cluster Flink E2E，也没有运行完整 `make test`；真实 quota/estimator 行为仍未在集群中验证。ordered `ClusterAffinities` 是有意排除项，custom scheduler 与 suspended binding 则明确保留旧交付语义；这些兼容边界有单元测试覆盖，但不属于 default-scheduler 自动恢复合同。

终审发现并修复了一个普通 placement 回归：旧 candidate 会要求所有 default-scheduler multi-component binding 都携带 component result，导致不产出该结果的普通 RB/CRB placement 和 `RequiredBy` target 无法创建 Work。新增的真实 `ensureWork` 回归在旧实现上三种场景均失败，在 `49916cee1` 上均通过；自有 accepted target 的 fail-closed 路径未放宽。

仍有一个非阻塞残余：成功 scale 后缓存的是完整 desired assumption；若 workload 一直保持 `Healthy`，紧接着的第二次 scale-up 可能把自身旧 reservation 与新 delta 同时扣减，保守地等待五分钟 TTL 和队列重试。它不会覆盖 accepted Work，但 generation-aware assumption release 需要后续处理。

[#7835 的 v1.35 红灯](https://github.com/karmada-io/karmada/actions/runs/31902564843/job/95056366571)闭合了直接失败机制：测试仅等待 ResourceQuota 对象可读便创建 Deployment，处理 member1 请求的 estimator 没有使用该 quota，返回无上限并把 4 个副本全部调度到 member1；断言继续等待固定的 2/2 结果。失败 spec 与 helper 在当前 master 上相同，同 head v1.34/v1.36 均通过。artifact 无法证明底层原因一定是 informer 未见对象，也没有 master 基线复现，因此不把它写成已确认的 master 回归；当前只确认测试同步边界不足，不据此修改 PR3/PR4 产品代码。完整归并见 [Day 51](day51-karmada-recent-pr-ci-e2e-failures-2026-08-17.md#7835等待-member-api-对象不等于-estimator-已看到它)。

## 下一步

1. 观察 #7841 upstream CI，重点核对 live Flink scale-up、scale-down、容量不足、requirements rejection 与恢复。
2. 等 PR0-PR3 review 信号后再调整依赖和 merge 顺序；当前 Open/Draft 状态不等于 maintainer acceptance。

<a id="pr4-upstream-draft"></a>

## PR4 upstream publication

Exact target：`karmada-io/karmada:master`

Posted Draft PR：[karmada-io/karmada#7841](https://github.com/karmada-io/karmada/pull/7841)

Exact head：`ranxi2001:feature/multi-component-failure-safe-rescheduling@49916cee119fef3cbee1977c3675f38c9c2f6322`

已发布标题：

```text
feat: reschedule scaled multi-component workloads
```

已发布正文：

````markdown
**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

Multi-template workloads managed by the default `karmada-scheduler` did not re-enter scheduling when component replicas changed, and a failed reschedule could allow the updated source configuration to reach member clusters.

This change routes component replica changes through scheduling using the last accepted per-component result. While the accepted target is available, pure scale-up estimates only the positive replica delta on that target and pure scale-down skips estimation. If no cluster fits or the transition is unsupported, the accepted result and existing Work remain unchanged. It also adds a FlinkDeployment E2E scenario for scale-up, scale-down, failed-update retention, requirements rejection, and recovery; the scenario compiles locally but has not run against a live cluster.

**Which issue(s) this PR fixes**:

Fixes #7492

**Special notes for your reviewer**:

- This integration branch contains patch-equivalent copies of #7830, #7833, and #7835 on #7837. Review the PR4-specific changes as `ea8782509...49916cee1`.
- Rollout order: update the API/CRD first, then the binding-controller leader, then the scheduler; keep `MultiplePodTemplatesScheduling` disabled until all three are updated. A healthy accepted target stays pinned, while a missing or terminating target may use failover. A rapid consecutive scale-up may be delayed until the preceding scheduling assumption is released or expires; generation-aware release is follow-up work.
- Validation: `go test -race -count=1 ./pkg/util ./pkg/controllers/binding ./pkg/scheduler ./pkg/scheduler/core ./pkg/scheduler/metrics`; `go test -count=1 ./test/e2e/suites/base -run '^$'` (compile only); `make verify`. Full `make test` and live multi-cluster E2E were not run.

Codex assisted with implementation, tests, review, and PR drafting.

**Does this PR introduce a user-facing change?**:

```release-note
`karmada-scheduler`: With `MultiplePodTemplatesScheduling` enabled and the accepted target available, component replica changes now trigger rescheduling on that target; scale-up estimates only added replicas, scale-down skips estimation, and a no-fit or unsupported transition keeps the previously accepted member-cluster configuration.
```
````

后续修改 upstream PR、评论、reviewer request 和 Ready transition 仍需单独确认 exact action/text。
