# #7492 多组件调度 PR 栈交接

> 状态核对：2026-08-18。PR 和 CI 状态会变化，技术合同与验证边界以本文记录的 exact SHA 为准。

这份文档合并原先分散的六份记录，只保留后续评审、发布和维护仍需要的信息。已发布的 PR 正文、rebase 命令、push 过程和被替代的设计可从 Git 历史或对应 GitHub PR 查询，不再单独维护副本。

<a id="stack-overview"></a>

## 先说人话

#7492 的公开 PR 在 PR0 合并后重新拆分：

- PR0 已合并，提供 API 字段；
- PR1 提供 `ReviseComponents` interpreter 能力，并在 Work 交付时应用组件结果；
- PR2 只生成并持久化 scheduler component result；
- PR3 计算扩缩容时需要估算的副本变化；
- PR4 的旧 candidate 把前述能力接入 scheduler，并在重新调度失败时保留旧结果和现有 Work。

当前 PR1/PR2 已从最新 `master` 重建；PR3 尚保持原 planner history。PR4 `49916cee1` 仍包含重构前
PR1/PR2 的 patch-equivalent copies，只能作为 provenance、delivery fence 与失败保留合同的历史实现证据，
不能当作当前分片已组合完成。

```text
master -> 1dd55a5d5 (PR0 merged)
                    |-> 4583e06d2 (PR1: interpreter + delivery)
                    |-> 014c555f8 (PR2: result producer)
                    `-> 9fb3992fd (PR3: planner, older ancestry)

旧 PR4 integration：... -> old PR1 copy -> old PR2 copy -> PR3 copy -> 49916cee1
当前要求：保留 PR4 自身合同，按新 PR1/PR2/PR3 heads 重新对齐
```

## 当前状态

| 层级 | 公开对象 / exact head | 作用 | 2026-08-18 状态 |
| --- | --- | --- | --- |
| PR0 | [#7837](https://github.com/karmada-io/karmada/pull/7837) `76589a9d514543edc8c8ca47174cff360d3b832e` | `TargetCluster.Components` 等 API 基线 | 已合并为 `1dd55a5d57b416ef8c7fb5876a961d24e342c007` |
| PR1 | [#7830](https://github.com/karmada-io/karmada/pull/7830) `4583e06d2050058d4ff8a3980fe587ea12a48c79` | `ReviseComponents` interpreter + Work delivery | Open，非 Draft；17 checks passed，Tide pending；无 human review decision |
| PR2 | [#7833](https://github.com/karmada-io/karmada/pull/7833) `014c555f898cf575422b65d8c4fbb95e56295cea` | scheduler component result producer | Open，非 Draft；16 passed、1 E2E failed，Tide pending；无 human review decision |
| PR3 | [#7835](https://github.com/karmada-io/karmada/pull/7835) `9fb3992fd518aa13992efddb2a8405a21d1b5414` | component comparison 与 scale estimation planner，本身不激活生产入口 | Open，Draft；15 passed、2 E2E failed，Tide pending；无 human review decision |
| PR4 | [#7841](https://github.com/karmada-io/karmada/pull/7841) `49916cee119fef3cbee1977c3675f38c9c2f6322` | scale detection、target pinning、失败保留、result provenance 与 delivery fence | Open，Draft；17 checks passed，Tide pending；旧 integration history 需要按当前 PR1/PR2 重新对齐 |

PR1-PR3 目前都没有 human review decision。PR1 的实质 checks 已通过，只有 Tide 等待；PR2/PR3 的
E2E 红灯需要另行分类。这些状态不影响本次职责边界的源码结论，也不能被写成当前栈已完成验证。

## 与 maintainer draft `c14af2f` 的对齐和 gap

[RainbowMango/karmada@c14af2f](https://github.com/RainbowMango/karmada/commit/c14af2f1119a66d4672a814cc80f7612943d35d3)
只新增了一份 286 行的 `scheduling-result-for-components.md`，文档自标记为
`Draft (design discussion, not yet a formal proposal)`。它是 maintainer 对数据流和分片的强方向证据，
但不等于当前 PR 实现已获得 maintainer acceptance。

总体结论是：**主路线高度一致，当前主要 gap 是缺少有效的 result validation 分片，以及
#7841 还是 stale integration history。** #7835/#7841 的 scale rescheduling 与失败保留是 #7492
在这条通用数据流之上追加的问题特定逻辑，不能因 maintainer draft 没有展开它们就判定为偏离。

| Maintainer 建议分片 | 当前公开栈 | 判断 |
| --- | --- | --- |
| 1. API + codegen + ResourceBinding webhook validation | #7837 只合入了 API/codegen；当前 #7830/#7833/#7835 都没有 result validation | **真实 gap**：旧 #7841 历史中的 `validateComponentFields` 不属于任何当前有效分片 |
| 2. Scheduler 双写 `Components` | #7833 在 scheduler 接受结果时写入 multi-component result | 对 #7492 当前范围对齐；未做 draft 更广的单组件 `Replicas + Components[0]` 双写 |
| 3. `ReviseComponents` 全链路 + `ensureWork` | #7830 提供 interpreter contract、各扩展路径和 Work delivery | 核心职责对齐；提前带了 Flink 这一个 concrete consumer，是可接受的 vertical slice |
| 4. thirdparty scripts + Flink E2E | #7830 只补 Flink script；旧 #7841 含 Flink E2E | 覆盖面比 draft 窄，且 E2E 依附的 integration history 已失效；本轮没有 live-run 证据 |
| 5. FRQ / eviction / HPA 等下游迁移 | 不在当前 #7492 PR1-PR4 内 | 明确 deferred；不应为了对齐一份较广的演进 draft 扩大当前 scale-rescheduling scope |

### 当前必须补的边界：result validation

API 已允许任意 v1alpha2 client 写 `clusters[*].components`，而当前有效 PR 栈没有负责以下
invariant 的 owner：

- `clusters[*].components[*].name` 必须属于本 binding 的 `spec.components[*].name`；
- 同一 target cluster 内 component name 不能重复；
- feature gate 关闭时，不能引入或修改新格式的 scheduling result，同时需明确已存对象的回滚语义。

这是 API/webhook 的职责，不应由 scheduler 假设“只有我会写”，也不应埋进最后的 activation
PR。既然 #7837 已经合并，当前最清晰的修复是补一个窄的 validation follow-up，在生产者激活之前合入；
如果必须减少 PR 数量，可将这一小段并入 #7833，但不应继续只存在于 stale #7841 中。

### 有意不同的 ownership 语义：`requiredBy`

Maintainer draft 建议 `mergeTargetClusters()` 对同名 component 取 `max`。当前 #7830 的规则是：
本 binding 自己的 target 优先；只由 `requiredBy` 引入的 target 保留 cluster name，但清空 foreign
`Components`。

这个差异不是漏实现。`requiredBy` snapshot 中的 component assignment 属于 referring
workload，其 component name 即使恰好与 dependency workload 同名，也不能自动变成后者的副本决策。
当前做法把 `requiredBy` 限定为 propagation reachability，权责更清晰。它是对 draft 的有意修正，
需要 maintainer 明确确认，不应对外描述为“已与 draft 完全等价”。

### 延后而非当前 blocker 的范围

- `GracefulEvictionTask.Components` 未随 #7837 合入，当前 #7492 也不做 partial component eviction；
  继续延后比为 API 对称而扩大协议面更稳妥。
- draft 的单组件双写、`ReviseReplica` fallback 和 Deployment/StatefulSet 原生 `GetComponents`
  是 legacy-field convergence 路线；当前 PR 只覆盖 multi-template scale rescheduling。
- FRQ result-based accounting、eviction、HPA、descheduler 和更多 thirdparty script 均应保持后续分片，
  不与 #7841 的失败保留一次合入。

### 我们超出 draft 的部分：provenance + delivery fence

Maintainer draft 解决的是“如何表示 component result，并把它写回 Work”，没有定义
“这份 result 对应 scheduler 接受过的哪一版 source input”。#7492 的失败语义使后一个问题
不能被略过：旧 result `taskmanager=4` 与新 source `500m CPU` 可以被 #7830 组合成 scheduler
从未接受过的 `4 x 500m CPU` Work。

因此，旧 #7841 实现的 accepted requirements hash、result generation/spec identity、source UID/component
校验、pending-result delivery fence 和失败保留，是 #7492 的必要安全扩展，不是与 draft 争夺职责。
正确分工仍是 scheduler 持久化 accepted identity，binding controller 在交付边界消费并冻结 Work，
ResourceInterpreter 不判断 freshness。这套扩展仍需 maintainer review，且必须在当前 PR heads 上重建后才是有效实现。

## 2026-08-18 拆分质量复核

当前分片的逻辑方向合理，但公开栈还没有形成可直接交给 reviewer 的一致历史。PR1-PR3 各自边界清楚；
PR4 仍引用重构前的 validation 版 PR1，正文中“包含 #7830、#7833、#7835 patch-equivalent copies”的描述
已经失效。整体可评价为“分片设计基本成立，integration PR 尚未重建”，不能按当前 #7841 直接请求 review。

| PR | 拆分判断 | 依据 | 当前处理 |
| --- | --- | --- | --- |
| #7830 | 可接受的 delivery vertical slice | 2 commits、37 files、`+1276/-40`；文件多主要来自 interpreter API、生成物和测试。hook 与唯一生产 consumer 放在一起，避免单独合入无 consumer 的 API | 不再拆 PR；按两个 commits 分段 review，并明确 accepted-input freshness 属于后续硬依赖 |
| #7833 | 当前最干净的分片 | 1 commit、2 files、`+102`；只在 scheduler 接受结果时写 `TargetCluster.Components` | 保持独立；feature gate 在 provenance + delivery fence 落地前必须保持关闭 |
| #7835 | 合理的无副作用 planner | 1 commit、2 files、`+478/-6`；没有 production caller | 保持独立；更新已失效的 base/review range，并单独分类当前 E2E 红灯 |
| #7841 | 目标合同原子，但当前 PR 不可 review | GitHub diff 为 76 files、`+8228/-171`；真正 residual 是 21 files、`+4554/-114`，其中大部分是 scheduler、binding 和 E2E tests。provenance、failure retention 与 delivery fence 共同构成安全激活合同，不宜按组件机械拆开 | 保留一个 activation PR，但先基于当前 PR1/PR2/PR3 重建，删除旧 validation/webhook copies，再验证 residual |

建议保留 #7830/#7833/#7835 的当前分片，但在 producer 激活前补上独立的 result-validation
follow-up，期间保持 Alpha gate `MultiplePodTemplatesScheduling=false`，最后从最新 `master`
重建 PR4。更严格的 owner-boundary 方案是让
PR2 同时持久化 accepted-input provenance、PR1 只在 delivery fence 通过后消费 result，再把 PR4 缩成纯
activation；该方案边界更完整，但会再次 force-push PR1/PR2 并增加 review churn，当前没有 maintainer 指示
要求这样重排。

推荐的 merge / rollout 约束是：API 已由 #7837 合入；binding delivery 先于 scheduler producer 部署；
PR4 安全合同合入并完成 runtime component 升级前，不启用 `MultiplePodTemplatesScheduling`。这是一项工程建议，
尚未获得 maintainer acceptance。

## 分片评审边界

- **PR1**：负责 `ReviseComponents` interpreter/delivery 链、Flink customization 和 `RequiredBy`
  ownership。它消费 `TargetCluster.Components`，但不生成 result，也不判断 result 是否对应当前 source input。
- **PR2**：只负责 scheduler result producer。它把 scheduler 接受的 per-component replica assignment 持久化到
  `TargetCluster.Components`，不理解 CRD 内部字段路径，也不负责 Work delivery。
- **PR3**：按组件名比较 desired 与 accepted 结果；纯 scale-up 只规划正 delta，纯 scale-down 不调用 estimator，缺快照或不支持的形状使用 full desired。predicate/planner 在该分片中没有生产调用者，因此 PR3 自身不改变生产行为。
- **PR4**：把 scale change 接入 scheduler，并负责 target pinning、失败保留、result provenance 和 delivery
  fence。其 `49916cee1` integration history 只能证明旧组合的局部合同，需按当前 PR1/PR2 重新对齐。

## 当前完整功能为什么仍需要 PR4 合同

旧 prototype 只保存组件名和副本数。假设已经接受：

```text
taskmanager = 4 x 100m CPU
```

用户一次更新为：

```text
taskmanager = 6 x 500m CPU
```

旧逻辑只估算新增的 `2 x 500m`，却可能在成功后交付完整的 `6 x 500m`；失败时也可能保留 4 个副本，却把每个副本的资源需求改成 `500m`。因此“副本数结果没变”不能证明旧 Work 应当接受最新 source。

旧 PR4 candidate 增加 accepted requirements identity 和 Work delivery fence：资源需求变化不能借旧结果通过；
scheduler 尚未接受新结果时，binding controller 也不能提前更新或删除 Work。当前拆分仍需要这套合同，但
必须重新对齐代码历史和 PR 依赖。

## 旧 PR4 candidate 已证明的目标合同

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

旧 PR4 candidate 的安全 rollout 前提是 `API/CRD (#7837) -> new binding controller leader -> new scheduler`。
这还不是 maintainer 已接受或 mixed-version live E2E 已证明的发布合同；重新对齐前也不是当前 PR 栈的有效
集成结论。无法保证两个 runtime component 都已更新时，应保持 Alpha feature gate
`MultiplePodTemplatesScheduling` 关闭。

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

1. 补一个窄的 result-validation follow-up，只管 API invariant 与 gate-off 写入边界，不恢复已删除的广泛 mixed-version 实验代码。
2. 分类 #7833/#7835 当前 E2E 红灯，不把单次 CI 现象直接写成产品代码根因。
3. 按当前 PR1/PR2/PR3 heads 重新对齐 #7841；保留 provenance + delivery fence 合同，删除旧 validation/producer copies。
4. 请 maintainer 分别确认 `requiredBy` 只承载 reachability 的语义，以及 provenance/fence 作为 #7492 安全扩展的必要性。

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
