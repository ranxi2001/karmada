# Day 12：新 Issue / PR 可介入机会扫描

日期：2026-07-13

## 一页结论

本次扫描覆盖 `karmada-io/karmada` 最近 30 天创建或更新的 open issue / PR，并核对了 assignee、`/assign`、关联 PR、真人 review、bot review 和 CI。

当前没有一个同时满足“维护者已确认有效、无人认领、没有 active PR”的干净新实现项。最近的新 issue 大多是作者建 issue 后立即开 PR，或者已经明确 `/assign`。因此当前最合理的介入方式不是抢实现，而是：

1. 自有 [PR #7732](https://github.com/karmada-io/karmada/pull/7732) 已由 `@RainbowMango` `/lgtm`、`/approve` 并合并为 `d0714678`；完整维护者 RCA 和 review 纠偏已归档到 Day 11。
2. 回复直接征求我们意见的 [issue #7757](https://github.com/karmada-io/karmada/issues/7757)：源码证据支持 issue 判断，但作者已认领，适合提供技术确认和后续 review。
3. 已完成 [PR #7692](https://github.com/karmada-io/karmada/pull/7692) 的 e2e flake review，没有阻塞性 finding，并已发布带失败时序证据的 [comment review](https://github.com/karmada-io/karmada/pull/7692#pullrequestreview-4681354181)；之后可 review [PR #7754](https://github.com/karmada-io/karmada/pull/7754)。
4. 再处理自己的 [PR #7697](https://github.com/karmada-io/karmada/pull/7697)：CI 全绿，但体量为 XXL，先清理已处理的 bot threads，再做一次简短 ready-for-review follow-up。

初次扫描只做只读分析和本地记录；后续 #7757 评论和 #7692 comment review 都已经用户确认并发布。

## 新 Issue 候选

| 优先级 | Issue | PR 认领 @ | 当前判断 | 建议介入方式 |
| --- | --- | --- | --- | --- |
| P0 | [#7757 Cluster Resource modeling underestimates capacity](https://github.com/karmada-io/karmada/issues/7757) | `@Priyanshu8023` 已 `/assign`，暂无 PR | 作者直接 `@ranxi2001` 征求意见。当前 `getAllocatableModelings()` 在饱和节点使 `getNodeAvailable()` 返回 `nil` 后执行 `break`，确实会遗漏后续健康节点 | 回复源码核对结论；建议最小修复为 `break -> continue`，并补“饱和节点在前、健康节点在后”的回归测试；后续 review，不重复实现 |
| P1 | [#7691 ClusterResourceBinding e2e cleanup race](https://github.com/karmada-io/karmada/issues/7691) | active PR [#7692](https://github.com/karmada-io/karmada/pull/7692) `@A69SHUBHAM` | 修复只有 `+4` 行，补 member cluster propagation barrier；全部 checks 通过，无真人 review | 核对 helper 放置位置、DeferCleanup 时序和历史 flake 证据，做小而完整的人工 review |
| P1 | [#7758 More distributed workload types](https://github.com/karmada-io/karmada/issues/7758) | active PR [#7759](https://github.com/karmada-io/karmada/pull/7759) `@Swaim-Sahay` | 新增 Argo Rollout multi-component interpreter，`+873/-2`；无真人 review，DCO 失败，两个 e2e job 失败，且混入 `CONTRIBUTING.md` 提交 | 仅 review/test；重点核对 dependency Kind 大小写、canary/blue-green 语义、nil 边界和 PR scope，不重复实现 |
| P2 | [#7751 Cluster deletion protection](https://github.com/karmada-io/karmada/issues/7751) | 无正式 assignee/PR；`@anjalichhikara-0907` 已请求认领 | 涉及 aggregated-apiserver/admission enforcement 边界，设计和复现成本较高 | 不抢实现；如介入，仅做最小复现和 enforcement point 分析，等待维护者确认方向 |
| P2 | [#7731 Operator CRD label validation](https://github.com/karmada-io/karmada/issues/7731) | 无正式 assignee/PR；`@swagatobauri` 已表示愿意测试和修复 | 已验证非法 label 被接受，同时用户 label 没传播到 PVC；需要先区分 schema validation 问题和字段未消费问题 | 补充行为矩阵或 review，先确认 metadata labels 的预期传播语义，不直接开 PR |
| P2 | [#7688 nil TolerationSeconds](https://github.com/karmada-io/karmada/issues/7688) | active PR [#7689](https://github.com/karmada-io/karmada/pull/7689) `@A69SHUBHAM` | `+10/-1` 的防御性 validation 修复，无真人 review；一个 v1.34 e2e 失败 | review nil 是否应跳过校验、非 nil 负值是否仍覆盖，并分类 e2e 失败 |

### 明确排除

- [#7717](https://github.com/karmada-io/karmada/issues/7717)：维护者已说明当前行为符合预期，应使用 `overflowAffinities`，不应再按 bug 实现。
- [#7740](https://github.com/karmada-io/karmada/issues/7740) 与 [#7746](https://github.com/karmada-io/karmada/issues/7746)：标题和目标重复，且已有 PR #7747。
- #7737 / #7738 / #7739 / #7749 等新 util 单测 issue：均已有同作者 active PR，不能重复实现。
- 当前 open `good first issue` 搜索为空；`help wanted` 只有较老的 umbrella/task，不是新且可直接认领的小任务。

## 新 PR 候选

| 优先级 | PR | 规模与状态 | 为什么适合我们 | 建议检查点 |
| --- | --- | --- | --- | --- |
| P0 | [#7692](https://github.com/karmada-io/karmada/pull/7692) e2e propagation barrier | XS，`+4`，CI 全绿，无真人 review | 与 #7719/#7732 的 cleanup barrier 分析完全同类 | setup/assert/cleanup 顺序、是否真的等待被删除对象曾到达 member cluster、helper 参数是否覆盖所有 target clusters |
| P0 | [#7754](https://github.com/karmada-io/karmada/pull/7754) preserve Flink memory quantity string | XS，`+3/-3`，CI 全绿，无真人 review | Day 5 已完整验证 `100m -> 0.1 -> resource.Quantity("100m")` 路径 | 当前行为语义上本来正确，因此应把它定位为去掉不必要转换/降低误解，而不是已证实的 correctness bug；核对删除 `kube` import 后脚本和现有测试 |
| P1 | [#7753](https://github.com/karmada-io/karmada/pull/7753) hostPath etcd taints | L，`+136/-3`，测试矩阵通过但 DCO 失败，无真人 review | 与 `karmadactl init` 主线直接相关 | `PreferNoSchedule` 不应作为硬拒绝；Toleration `Exists`/`Equal` 语义；生成 StatefulSet tolerations 与节点筛选必须一致 |
| P1 | [#7759](https://github.com/karmada-io/karmada/pull/7759) Argo Rollout interpreter | XL，`+873/-2`，DCO 和两个 e2e 失败，无真人 review | 与 Flink/resource interpreter 经验相邻，可做深 review | 先确认 `ConfigMap`/`Secret`/`PersistentVolumeClaim` Kind 大小写等 bot finding 是否真实，再检查 rollout strategy 和 dependency 语义；要求拆掉无关 CONTRIBUTING commit |
| P2 | [#7750](https://github.com/karmada-io/karmada/pull/7750) clusterrole tests | L，`+123/-1`，invalid commit message，无真人 review | 已有两个明显 scope/test hygiene 信号 | PR 混入未在 issue/title 中说明的 clusterinfo 测试；固定 `os.TempDir()` 文件名可能并发冲突，应拆 scope 或使用 `t.TempDir()` |
| P2 | [#7689](https://github.com/karmada-io/karmada/pull/7689) nil validation | S，`+10/-1`，无真人 review | 适合快速、低成本 review | 负值校验和 nil 语义；确认 v1.34 e2e 失败是否与 validation diff 无关 |

## 自有资产优先级

| 条目 | 最新状态 | 下一步 |
| --- | --- | --- |
| [PR #7732](https://github.com/karmada-io/karmada/pull/7732) | 已 `/lgtm`、`/approve`，并于 2026-07-13 合并为 `d0714678` | 已闭环；后续复用 Day 11 的 source-backed flake RCA 方法，不再跟踪 checks/review |
| [PR #7697](https://github.com/karmada-io/karmada/pull/7697) | CI 全绿，无真人 review；初始实质 bot 意见已在代码中处理，但 review threads 仍未清理 | 清理已处理/outdated threads，再向 assignee/reviewer 说明 ready for review；避免继续扩 scope |
| [PR #7666](https://github.com/karmada-io/karmada/pull/7666) | 2026-06-26 已 merged，merge commit `f2b7341` | 已完成，无需再观察 |
| [Issue #7690](https://github.com/karmada-io/karmada/issues/7690) | 维护者已把方向引导到 #7693 certificate rotation | 暂缓 split Secret layout，不继续实现；是否补 deferred/close 说明需用户确认 |

## #7757 简单 Review

### 技术结论

这是一个确定的 correctness bug，不只是可疑代码：

- `getNodeAvailable()` 只在单个节点剩余 Pod slot 小于等于 0 时返回 `nil`，日志也明确说只是不把“这个节点”加入 resource models。
- `getAllocatableModelings()` 遇到这个 `nil` 后却执行 `break`，会停止整个节点循环，后续健康节点都不会进入 modeling summary。
- `listNodes()` 来自 client-go informer cache；底层 `threadSafeMap.List()` 直接遍历 Go map，没有稳定顺序。因此同一组节点可能因为饱和节点出现位置不同而得到不同 modeling 结果。
- 最小修复 `break -> continue` 是安全的：调用使用 `node.Status.Allocatable.DeepCopy()`，`nil` 返回前没有修改共享 summary，也没有需要终止整个循环的全局错误。

影响需要准确限定：它不会影响所有普通资源传播或所有调度。主要风险在带 `ReplicaRequirements` 的动态副本估算路径；estimator 会把 resource models 得到的副本数作为上界之一，因此漏掉健康节点会低估可调度副本，极端情况下返回 0。

### 临时回归测试

在独立临时 worktree 基于 `upstream/master@3d4d14d74` 增加测试：第一个节点 Pod slot 已满，第二个节点仍有容量，期望 modeling count 为 1。

当前代码结果：

```text
expected: 1
actual:   0
--- FAIL: TestIssue7757SaturatedNodeDoesNotHideLaterNodes
```

仅把 `break` 改为 `continue` 后：

```text
--- PASS: TestIssue7757SaturatedNodeDoesNotHideLaterNodes
PASS
```

同时运行 `TestGetNodeAvailable`、`TestGetAllocatableModelings` 和临时回归测试，全部通过。临时 worktree 和测试文件已经删除，没有改动 upstream topic branch。

正式 PR 至少应覆盖：

1. 饱和节点在前、健康节点在后，健康节点仍被计数。
2. 交换两个节点顺序，结果保持一致。
3. 可选补充所有节点都饱和时 count 为 0。

现有 `TestGetAllocatableModelings` 还有一个测试质量问题：Pod 的 `NodeName` 是 `node1`，但测试里的两个 Node 都没有 Name，所以 Pod 实际没有匹配任何测试节点，没有覆盖已分配 Pod 或饱和逻辑。

### 作者公开背景判断

- GitHub 账号创建于 2024-01-24，当前公开信息为 3 followers、43 public repos，bio/company/location 为空；自建项目主要是 TypeScript，公开 Go 项目和 Karmada 经历较少。
- 他目前在 Karmada 发过 3 个 issue 和 2 个 PR，没有已合并的 Karmada PR/commit，属于新贡献者。
- #7638 曾把值类型 `Placement` 误判成 nil panic，维护者无法复现后作者关闭 issue/PR。
- #7643 曾声称 Flink memory `100m` 会错误变成 `1`；我们的函数级证据证明原功能 bug 不成立。后来的 PR #7754 已把理由降级为移除不必要转换，目前仍无真人 review。

所以合理判断是：作者之前的验证严谨度不足，后续 PR 必须看测试和 diff，不能只按 issue 描述背书；但粉丝数、知名背景和 issue 对错没有逻辑关系。本次 #7757 已有独立源码和运行证据，应认可问题本身，不等于认可作者的所有技术结论或实现能力。

## #7757 英文回复发布记录

目标：[karmada-io/karmada#7757](https://github.com/karmada-io/karmada/issues/7757)

状态：已于 2026-07-13 发布，评论链接：[#issuecomment-4953788174](https://github.com/karmada-io/karmada/issues/7757#issuecomment-4953788174)。GitHub 回读确认作者为 `ranxi2001`，正文包含 resource-model node count 澄清和 `cc @RainbowMango`。

````markdown
Thanks for raising this. I reviewed the current `upstream/master` implementation (`3d4d14d74`) and reproduced the control-flow issue with a focused temporary unit test.

Confirmed behavior:

- `getNodeAvailable()` returns `nil` when a node has no remaining Pod slots.
- `getAllocatableModelings()` currently handles that item-local result with `break`, which stops the entire node loop and omits all later healthy nodes.
- The NodeLister cache does not provide a stable iteration order, so the resulting modeling can depend on where the saturated node appears in the returned slice.

The focused test used a saturated node followed by a healthy node. For the test's only resource-model grade, the expected **node count** was `1` because one healthy node should remain in the model; the current code returned `0`. This value is not the number of remaining Pod slots:

```text
expected: 1
actual:   0
```

After changing only `break` to `continue`, the same regression test passed. The existing `TestGetNodeAvailable` and `TestGetAllocatableModelings` tests also passed with that change.

The impact appears limited to cluster resource modeling used by dynamic replica estimation when `ReplicaRequirements` are present; this does not affect every scheduling path.

The minimal fix looks like `break -> continue`, together with regression coverage for:

1. a saturated node before a healthy node;
2. the same nodes in the opposite order, with an identical result;
3. optionally, the all-saturated case.

Since you have already assigned the issue to yourself, I will not duplicate the implementation. I can help review the fix and test coverage when the PR is ready.

cc @RainbowMango, could you please help confirm whether this behavior and proposed fix match the intended cluster resource modeling semantics?
````

## #7692 Flake PR Review

目标：[karmada-io/karmada#7692](https://github.com/karmada-io/karmada/pull/7692)

状态：已于 2026-07-13 发布 [comment review #4681354181](https://github.com/karmada-io/karmada/pull/7692#pullrequestreview-4681354181)。GitHub API 回读确认作者为 `ranxi2001`、状态为 `COMMENTED`、正文包含三条失败时序和 `No blocking finding from my review.` 结论。

### 技术结论

- PR 只在 `test/e2e/suites/base/clusterresourcebinding_test.go` 的第一个 `It` 末尾增加 member `ClusterRole` present barrier，改动为 `+4/-0`。
- 旧流程只等 `Work` 创建就返回。`DeferCleanup` 随后删除 policy 和 source `ClusterRole`，再等 member `ClusterRole` 消失。但 disappear helper 会把首次观察到的 `NotFound` 当成清理成功，无法区分“还没传播到”和“已经创建后又删除”。
- 新增 present barrier 把顺序改为 `Work created -> member resources appeared -> cleanup -> member resources disappeared`，使后面的 disappear wait 成为有效的 cleanup barrier。
- `fit` 回调直接返回 `true` 符合用例边界：这个 `It` 检查的是 `Work` 上的 permanent-ID label；后一个 `It` 已单独检查传播后 `ClusterRole` 的 label。
- helper 使用 5 秒轮询和 420 秒超时，不会无限阻塞；如果传播未完成，现在会在正确的 setup/assert 边界显式失败。

### 独立失败证据

在已有 v1.34 e2e 失败产物 [run 28397071031 / job 84140026710](https://github.com/karmada-io/karmada/actions/runs/28397071031/job/84140026710) 中，时序为：

1. `19:57:47.708`：cleanup 开始删除 `ClusterPropagationPolicy`。
2. `19:57:47.873`：binding controller 开始删除 `Work`。
3. `19:57:48.083`：`member2` 才创建目标 `ClusterRole`。

这独立确认了 issue #7691 描述的竞态：member resource 可以在 cleanup 已经开始后才出现。

### 验证与剩余风险

- `git diff --check upstream/master...upstream/pr-7692` 通过。
- `go test ./test/e2e/suites/base -run '^$' -count=0` 通过，确认相关 e2e package 可编译。
- 当前 PR 的 lint、codegen、compile、unit 以及 e2e v1.34/v1.35/v1.36 checks 均通过。
- 剩余限制是每个 Kubernetes 版本只跑了一次，不是统计意义上的 flake 消失证明；但源码时序和已有失败产物都支持这个最小修复。

### 英文 Review 发布记录

````markdown
I reviewed the cleanup ordering in this PR and did not find a blocking issue.

The added barrier matches the race described in #7691. Before this change, the first `It` only waits for the expected `Work` objects. Its `DeferCleanup` can then remove the source objects and call `WaitClusterRoleDisappearOnClusters()`, which treats an initial `NotFound` as successful cleanup even if propagation is still in flight.

I also checked an existing [v1.34 e2e failure artifact](https://github.com/karmada-io/karmada/actions/runs/28397071031/job/84140026710) and found this ordering:

- `19:57:47.708`: cleanup started removing the `ClusterPropagationPolicy`.
- `19:57:47.873`: the binding controller started deleting the `Work` objects.
- `19:57:48.083`: `member2` created the target `ClusterRole`.

That independently confirms that the member resource can appear after cleanup has already started.

Waiting for the `ClusterRole` to appear on every target cluster before the `It` returns makes the later disappearance wait a valid cleanup barrier. A `fit` function that returns `true` is appropriate here because this `It` verifies the permanent-ID label on the `Work`; the following `It` separately verifies the propagated `ClusterRole` label.

Validation:

- `git diff --check` against the current master passed.
- `go test ./test/e2e/suites/base -run '^$' -count=0` passed.
- The current PR checks for lint, codegen, compile, unit tests, and e2e v1.34/v1.35/v1.36 all passed.

The remaining limitation is that CI ran each Kubernetes version once, so it is not statistical proof that the flake is gone. However, the source ordering and the existing failure artifact support this fix.

No blocking finding from my review.
````

## 推荐执行顺序

1. #7732 已合并并归档，不再执行 thread/reviewer follow-up。
2. #7757 技术回复已发布；等待 `@RainbowMango`、`@zhzhuang-zju` 或其他维护者确认语义，并在作者开 PR 后 review，不认领重复实现。
3. #7692 comment review 已发布；等待作者或 test OWNERS 回复，不重复催促。
4. 用 Day 5 证据 review #7754，明确“语义正确但转换多余”的边界。
5. 再清理 #7697 bot threads 并跟进真人 review。
