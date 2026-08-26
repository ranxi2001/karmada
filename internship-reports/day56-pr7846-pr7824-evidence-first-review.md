# Day 56：Karmada PR #7846 / #7824 证据优先评审（2026-08-25）

## 先说人话

这两条 PR 都抓到了真实问题，但当前实现各漏了一种正常场景，因此暂时不适合 `LGTM`。

- [PR #7846](https://github.com/karmada-io/karmada/pull/7846) 给失败 Job 补上了 Kubernetes 要求的 `FailureTarget=True`，但只要另一个 member 还在运行，聚合结果就会同时出现 `Active=1` 和 `Failed=True`。这仍是 Kubernetes 不允许保存的终态，控制面更新会继续失败。
- [PR #7824](https://github.com/karmada-io/karmada/pull/7824) 删除了普通 `spec.ports[*].nodePort`，但 `LoadBalancer + externalTrafficPolicy: Local` 还有一个同样由 API Server 分配的 `spec.healthCheckNodePort`。它仍会被原样传播，并可在 member 上发生完全相同的端口冲突。

具体例子：一个 Job 被分到两个集群，`member-a` 已失败，`member-b` 还有一个 Pod 在运行。#7846 会生成：

```text
member-a: Failed=True, Active=0
member-b: Active=1
aggregate: FailureTarget=True, Failed=True, Active=1
```

`FailureTarget` 的缺失虽然修了，但 `Failed=True + Active=1` 又触发另一条 Job status validation。#7824 的对应例子是：控制面给 LoadBalancer 分配 `healthCheckNodePort=30081`，member 已占用 30081；PR 只删普通 NodePort，member 仍会收到 30081 并拒绝创建。

2026-08-26 经用户确认，已向 #7846 发布一条关于 `failed + active` 的 inline review comment；其余三条 inline comment 和两条 `Request changes` review 均未发布。

## 结论

| PR | 当前 head | 结论 | 首要修改要求 |
| --- | --- | --- | --- |
| #7846 | `eb14ddd2eadc28866ab5d543b36e7d1c19d877bf` | `Request changes` | 明确 federated Job 何时进入全局 `Failed`，并用 Kubernetes Job status validation 覆盖 `failed + active` |
| #7824 | `b3e79305979efb63d14b2c556b62d09706d48aa8` | `Request changes` | 初次传播时同时删除 `spec.healthCheckNodePort`，并增加真实端口冲突的反事实测试 |

两个 finding 都满足生产相关性门槛：它们来自 Karmada 正常支持的多集群 Job、LoadBalancer Service 路径，不依赖 mock-only 输入或手工构造的不可能状态。

## 评审范围

审计时间为 `2026-08-25 16:32 CST`，当时 `upstream/master` 为 `b6c92395e6e9e0678452f22ce2d7242693fb881c`。

- #7846：review merge-base 为 `08f8a2016f20fc68544eb7cf66f360620db859b0`，3 files，`+81/-8`。
- #7824：GitHub API 显示 base ref SHA 为 `08f8a2016f20fc68544eb7cf66f360620db859b0`；current head 的真实 parent / review merge-base 为 `1c278577e7892b6ea44f86a4317c1eb1e013bb93`，3 files，`+148/-17`。
- 两条 PR 从各自 merge-base 到当前 master 的推进都没有直接修改本 PR 的 changed files。这只是 file-level 无冲突证据，不代表已经排除语义影响。
- 阅读了完整 PR diff、linked issue、conversation、formal reviews、line comments、OWNERS 和 current-head checks。Copilot、Codecov、`karmada-bot` 均未作为 human maintainer 结论。

本轮没有画流程图。两个反例都可由三行状态或一个端口分配序列完整表达，图不会增加判断信息。

## #7846：混合 member 状态仍无法写回控制面

### 运行过程

聚合链路为：

1. status controller 读取 `ResourceBinding.Status.AggregatedStatus`，调用 `AggregateStatus`，再对源 Job 执行 `UpdateStatus`（[`pkg/controllers/status/common.go:168-211`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/pkg/controllers/status/common.go#L168-L211)）。
2. `ParsingJobStatus` 先把所有 member 的 `Active`、`Succeeded`、`Failed` 相加（[`pkg/util/helper/job.go:42-63`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/pkg/util/helper/job.go#L42-L63)）。
3. 只要任一 member 已 `Failed=True`，当前 head 就立即追加 `FailureTarget=True` 和 `Failed=True`（[`pkg/util/helper/job.go:95-120`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/pkg/util/helper/job.go#L95-L120)）。
4. 控制面旧 Job 尚未终止时，`aggregateJobStatus` 的 terminal guard 不会阻止第一次写入；API Server 拒绝后，旧 Job 也永远到不了 guard 所检查的终态（[`aggregatestatus.go:252-275`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/pkg/resourceinterpreter/default/native/aggregatestatus.go#L252-L275)）。

> 分析：#7846 修复的是 `Failed=True` 缺少前置 `FailureTarget=True`，但 Kubernetes 对 Job 终态还有交叉字段约束。只检查 condition 是否齐全，不等于整个 `JobStatus` 可以被 API Server 接受。

### 技术证据

在 exact head 上增加临时测试，并用真实 Kubernetes v1.36.1 Job controller 生成 member 状态：一个 member 为 `Failed=True, Active=0`，另一个为 `Active=1`。把这两个状态依次交给 #7846 的 native reflection / aggregation 路径，得到：

```text
active=1 failed=1
conditions=[FailureTarget=True, Failed=True]
completionTime=<nil>
```

随后对真实 Kubernetes API Server 执行 `UpdateStatus`：

- issue 环境对应的 Kubernetes `v1.35.2` validation 拒绝它；
- 独立用真实 Kubernetes `v1.36.1` API Server 复核，得到同一错误；
- 单 member、`Active=0` 的失败聚合可以通过，说明失败原因不是 `FailureTarget` 本身。

```text
status.active: Invalid value: 1: active>0 is invalid for finished job
```

> 证据边界：这是“真实 Kubernetes member 状态 + #7846 exact-head native aggregation + 真实 API Server `UpdateStatus`”的受控集成复现，不是完整 Karmada 多集群 E2E，也不是 #7844 已记录的线上实例。因此本 finding 分类为 `reachable latent bug`，不写成 `observed production incident`。

源码上，Kubernetes 在终态发生变化时启用 `RejectFinishedJobWithActivePods`（[`strategy.go:373-418`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/registry/batch/job/strategy.go#L373-L418)），并明确拒绝 `status.Active > 0 && IsJobFinished(job)`（[`validation.go:530-534`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/apis/batch/validation/validation.go#L530-L534)）。

这不是极端构造。Karmada 的现有 E2E 会把一个 Job 的 completions 分到多个 member（[`scheduling_test.go:620-698`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/test/e2e/suites/base/scheduling_test.go#L620-L698)）；其中一个 member 先耗尽重试而另一个仍运行，是正常的跨集群中间状态。

### 测试证据缺口

PR 修改后的 failed fixture 仍带 `completionTime`，但没有 `Complete=True`（[`aggregatestatus_test.go:246-272`](https://github.com/karmada-io/karmada/blob/eb14ddd2eadc28866ab5d543b36e7d1c19d877bf/pkg/resourceinterpreter/default/native/aggregatestatus_test.go#L246-L272)）。Kubernetes `v1.35.2` 和 `v1.36.1` 都拒绝该对象：

```text
status.completionTime: Invalid value: "...": cannot set completionTime when there is no Complete=True condition
```

`job_test.go` 又在比较前把 `res.CompletionTime` 清空，因此 object equality 测试会掩盖这个非法输出。原生失败 Job 通常不会产生 `completionTime`，所以这里首先是 regression evidence 缺陷，不把它夸大为已证明的独立生产故障。修复方向是删除 failed fixture 的 `completionTime`，并对最终聚合状态执行版本匹配的 API validation。

### 已有讨论与边界

- `@whitewindmills` 已发现旧 member 不产生 `FailureTarget` 的 version-skew 缺口；作者随后改为只要有失败 member 就合成该 condition，并得到方向性确认。本轮不重复该 finding。
- issue reporter 已提出 terminal condition monotonicity，以及 `FailureTarget` 与 `Complete` / `SuccessCriteriaMet` 互斥的风险。本轮不把它们标成新发现。
- `failed member + active member` 的完整状态校验没有出现在 issue、PR conversation、line comments 或 reviews 中，是本轮新增 finding。
- PR body 已落后于 current head：仍描述已删除的 `failureTargetClusters` 实现和已解决的旧 member limitation；默认受影响版本应区分 Kubernetes `v1.32+` 与 `v1.31` 显式启用 feature gate。它是合并前文案修正，不替代代码 blocker。

## #7824：遗漏 healthCheckNodePort

### 运行过程

1. 控制面创建 NodePort 或 LoadBalancer Service，API Server 为它分配 cluster-local port。
2. Karmada 在创建 Work 前调用 `RemoveIrrelevantFields`（[`pkg/controllers/ctrlutil/work.go:38-56`](https://github.com/karmada-io/karmada/blob/b3e79305979efb63d14b2c556b62d09706d48aa8/pkg/controllers/ctrlutil/work.go#L38-L56)）。
3. #7824 删除每个 `spec.ports[*].nodePort`，但没有删除顶层 `spec.healthCheckNodePort`（[`prune.go:186-211`](https://github.com/karmada-io/karmada/blob/b3e79305979efb63d14b2c556b62d09706d48aa8/pkg/resourceinterpreter/default/native/prune/prune.go#L186-L211)）。
4. Kubernetes 对 `LoadBalancer + externalTrafficPolicy: Local` 判断 `NeedsHealthCheck=true`（[`service/util.go:87-93`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/api/service/util.go#L87-L93)）。请求里已有非零 `healthCheckNodePort` 时，member API Server 会精确申请该端口，而不是重新选择（[`alloc.go:570-588`](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/registry/core/service/storage/alloc.go#L570-L588)）。

### 技术证据

exact #7824 head 上的临时测试调用真实 `RemoveIrrelevantFields`：

```text
ports[0].nodePort: removed
spec.healthCheckNodePort: remains 30081
PASS
```

exact Kubernetes `v1.36.1` 上，用真实 Service allocator 预占 30081 后再创建携带该值的 LoadBalancer/Local Service：

```text
Internal error occurred: failed to allocate requested HealthCheck NodePort 30081:
provided port is already allocated
```

该回归也符合 Karmada 既有生命周期设计：`RetainServiceFields` 已明确把 member 的 `healthCheckNodePort` 视为 API Server 分配且不可变的值，在后续更新中保留（[`pkg/util/lifted/retain.go:39-65`](https://github.com/karmada-io/karmada/blob/b3e79305979efb63d14b2c556b62d09706d48aa8/pkg/util/lifted/retain.go#L39-L65)）。因此，初次 Work 中删掉控制面值、创建后保留 member 值，与已有 `create -> retain on update` 边界一致。

### E2E 没有反事实

新 E2E 只断言 member 的每个 `nodePort > 0` 和 Binding 最终 `FullyApplied=True`（[`resource_test.go:243-273`](https://github.com/karmada-io/karmada/blob/b3e79305979efb63d14b2c556b62d09706d48aa8/test/e2e/suites/base/resource_test.go#L243-L273)）。在无冲突环境中：

```text
旧行为：传播控制面的 nodePort 30080，30080 > 0
新行为：member 自动分配 nodePort 30093，30093 > 0
```

两条路径都通过当前断言。以上结果由 Kubernetes `v1.36.1` 的真实 allocator 复核，不是手工赋值。因此回退生产代码后 E2E 仍会绿，测试没有证明 #7823 的冲突机制已消失。

有效的反事实应先让控制面分配端口 `N`，在至少一个 member 用 blocker Service 占用 `N`，再传播目标 Service并验证：旧实现出现 issue 中的 `provided port is already allocated`，新实现达到 `FullyApplied=True`，且 member 获得不同端口。LoadBalancer/Local 变体还应覆盖 `healthCheckNodePort`。

### 实验阻塞与排除项

第一次运行 Kubernetes allocator 临时测试时，夹具没有模拟 API 默认化，`spec.allocateLoadBalancerNodePorts=nil` 在 `shouldAllocateNodePorts` 中触发 nil pointer panic。把它设为 API 默认值 `true` 后，同一真实路径稳定复现 30081 冲突。该首次失败只记录为测试夹具问题，不作为 PR 缺陷证据。

以下方向没有升级为新增 blocker：

- 显式用户固定 `nodePort` 会被无条件删除，以及控制面和 member 端口不一致后的可观测性，已经在现有 review thread 中讨论；合并前仍应在 release note 说明兼容性变化。
- `SetNestedSlice` error 被忽略已由 Copilot 提出；对合法 Service JSON 没有找到可达的生产失败链。
- Kubernetes update 路径会按 port name 保留 member 已分配端口，未发现普通更新导致端口反复变化的证据。

## CI 与 review 状态

| PR | Current-head checks | Human review | Merge gate |
| --- | --- | --- | --- |
| #7846 | 17/17 success，[run](https://github.com/karmada-io/karmada/actions/runs/32569797538) | approver 已确认 version-skew 方向，但最终 commit 后没有 human formal review | Tide 缺 `approved`、`lgtm` |
| #7824 | 16/17 success；[v1.35 E2E failed](https://github.com/karmada-io/karmada/actions/runs/32027850917/job/95385185452) | 唯一 human formal review 绑定旧 head | Tide 缺 `approved`、`lgtm` |

#7824 作者把 v1.35 E2E 失败判断为无关 flake，但没有 same-SHA rerun、maintainer 确认或独立 RCA，本报告不替作者补足这个结论。两条 PR 的 CI 均早于 current master，不能描述为 rebase 后验证。

## Upstream review 状态与草稿

以下文本经过术语与证据边界检查。#7846 comment 1 已于 2026-08-26 发布；其余文本仍是未发布草稿，发布前仍需用户确认 exact target 和 exact text。

### #7846 comment 1（已发布）

Target: `pkg/util/helper/job.go:112` on `eb14ddd2eadc28866ab5d543b36e7d1c19d877bf`

Published: [`discussion_r3858973277`](https://github.com/karmada-io/karmada/pull/7846#discussion_r3858973277)

```text
This still produces a status that the control-plane API server cannot store when member states are mixed. A normal `Duplicated` Job can reach this when one member exhausts `backoffLimit` while another is still running:

member-a: Active=0, Failed=1, Failed=True
member-b: Active=1
aggregate: FailureTarget=True, Failed=True, Active=1

In a controlled reproduction, the real Kubernetes v1.36.1 Job controller produced both valid member states. Passing their reflected statuses through the native aggregation path at `eb14ddd` produced the aggregate above, and a real API server rejected `UpdateStatus` with `status.active: Invalid value: 1: active>0 is invalid for finished job`. The control-plane Job therefore keeps its previous status and retries until the remaining member becomes inactive.

Could we keep `FailureTarget=True` as the interim aggregate condition while `Active > 0`, append `Failed=True` only after all reflected members are inactive, and cover `failed + active` by validating the complete aggregate against the version-matched Job status rules?
```

### #7846 comment 2

Target: `pkg/resourceinterpreter/default/native/aggregatestatus_test.go:272` on `eb14ddd2eadc28866ab5d543b36e7d1c19d877bf`

```text
This expected failed status is not valid under the same Job status rules: it has `completionTime` but no `Complete=True` condition. Kubernetes v1.35.2 rejects it with `cannot set completionTime when there is no Complete=True condition`. The helper test also clears `res.CompletionTime` before comparison, so the current object-equality coverage can pass while `UpdateStatus` would fail.

Could we remove `completionTime` from the failed fixtures and validate the final aggregate with the version-matched Job status validator? That would cover the cross-field rules this fix depends on, not only condition equality.
```

Review summary (`Request changes`):

```text
I found one normal mixed-member state that still fails control-plane Job status validation, and the failed fixture currently bypasses another cross-field rule. Details are inline. Requesting changes so the aggregate is validated as a complete `JobStatus`, not only by condition equality.
```

### #7824 comment 1

Target: `pkg/resourceinterpreter/default/native/prune/prune.go:208` on `b3e79305979efb63d14b2c556b62d09706d48aa8`

```text
`LoadBalancer` Services with `externalTrafficPolicy: Local` have a second API-server-allocated field, `spec.healthCheckNodePort`. This function removes `ports[*].nodePort` but leaves that field in the Work. On the current head I reproduced `healthCheckNodePort=30081` surviving `RemoveIrrelevantFields`; Kubernetes v1.36.1's Service allocator then rejects member creation if 30081 is already occupied: `failed to allocate requested HealthCheck NodePort 30081: provided port is already allocated`.

Karmada already retains the member-assigned `healthCheckNodePort` on update in `RetainServiceFields`, so pruning the control-plane value on initial propagation matches the existing lifecycle. Could this path remove `spec.healthCheckNodePort` as well and cover a LoadBalancer/Local collision?
```

### #7824 comment 2

Target: `test/e2e/suites/base/resource_test.go:254` on `b3e79305979efb63d14b2c556b62d09706d48aa8`

```text
This assertion does not distinguish the fix from the old behavior. In a collision-free member, both a propagated control-plane NodePort and a member-allocated NodePort are greater than zero; I verified both paths through Kubernetes v1.36.1's allocator (`30080` and `30093`). Reverting the production change would therefore leave this E2E green.

Could the test reserve the control-plane port on one member before propagation, then verify the target Service becomes `FullyApplied` with a different member port? A LoadBalancer/Local variant would also catch the `healthCheckNodePort` path above.
```

Review summary (`Request changes`):

```text
I found one additional API-server-allocated port that follows the same collision path, and the new E2E does not fail under the old behavior. Details are inline. Requesting changes to cover both the LoadBalancer/Local path and a real collision counterfactual.
```

## 未决边界

- #7846 的全局失败策略需要作者或 maintainer 明确：任一 member 失败是否立刻代表 federated Job 失败，还是要等其余 member 终止。review 只要求产出 API-valid status，不替项目决定策略。
- #7824 改变了显式固定 NodePort 的行为，并让各 member 的端口可以不同。现有 thread 已接受方向但未解决用户从控制面观察实际端口的问题，至少应有 release note，长期可观测性可单独跟进。
- #7824 的 v1.35 E2E 红灯尚无 E3 根因证据；在评论代码问题时不把它归类为 flake，也不让它干扰两个独立可执行反例。

## 下一步

1. 等待 #7846 作者回复或更新；只复查完整 Job status validation，不把 comment 1 重复成顶层评论。
2. #7846 comment 2、#7824 两条 comments 和两个 `Request changes` 仍需逐项确认；发布前重新核对 head SHA，head 变化则先重跑最小反例并更新 line anchors。
3. #7824 后续只复查 `healthCheckNodePort` prune 与真实冲突反事实，避免扩展到已有 thread 或 Copilot 已覆盖的旁支。
