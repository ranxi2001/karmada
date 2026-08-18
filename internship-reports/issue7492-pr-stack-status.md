# #7492 多组件调度 PR 栈状态

> 状态核对：2026-08-18 17:22（Asia/Shanghai）。动态 PR / CI 状态以 GitHub 为准；本文只保存后续
> review 和发布仍需要的当前事实，不再维护 rebase、push 或旧 PR body 过程记录。

<a id="stack-overview"></a>

## 先说人话

#7492 已按职责拆成五层：API、result producer、interpreter / Work delivery、scale planner 和安全 activation。
#7837 已合并；#7830、#7833、#7835 仍独立 review；#7841 已按这些新分片重建。公开 head 已从 lint
失败的 `9a18960ea5f307df744784e00688e9c5987c7056` 更新为
`b2b27ad01c79ec8cb355461a674110c59d6fb3bf`。

当前 blocker 不是 integration history。4 个确定性 lint 问题已经修复，新 exact-head CI 正在运行。
完整功能启用前还要通过 live E2E、确认 rollout / admission validation 边界，并获得 maintainer review。

```text
master / #7837 API merged
  |-- #7833  scheduler result producer
  |-- #7830  ReviseComponents + Work delivery
  |-- #7835  scale planner
  `-- #7841  integrates the three heads + safe activation residual
```

## 当前公开状态

| 层级 | Exact head | 当前职责 | 快照状态 |
| --- | --- | --- | --- |
| [#7837](https://github.com/karmada-io/karmada/pull/7837) | `76589a9d5145`，merge `1dd55a5d57b4` | `TargetCluster.Components` API / conversion / codegen | 已合并；18 checks success |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `4583e06d2050` | `ReviseComponents` capability + Work delivery | Open，非 Draft；2 commits，37 files，17 checks success，Tide pending |
| [#7833](https://github.com/karmada-io/karmada/pull/7833) | `014c555f898c` | scheduler 写完整 component result | Open，非 Draft；1 commit，2 files；16 success、v1.34 E2E failure |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `9fb3992fd518` | component scale planner，不接生产入口 | Open，Draft；1 commit，2 files；15 success、v1.34/v1.36 E2E failure |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `b2b27ad01c79` | trigger、provenance、failure retention、delivery fence | Open，Draft；新 CI 已启动，DCO success，9 个 Kubernetes matrix jobs pending |

除 #7837 外，当前 heads 尚无实质性 human review。bot、reviewer request 和 Tide 状态不能写成人类认可。

## #7841 当前五个 commits

| Commit | 对应公开分片 | 说明 |
| --- | --- | --- |
| `014c555f8` | #7833 | scheduler result producer |
| `32d2e45d5` | #7830 commit A | 与公开 `997a594b1` patch-equivalent 的 interpreter capability |
| `db8073d38` | #7830 commit B | 与公开 `4583e06d2` residual patch-equivalent 的 Work delivery |
| `bdcc01b66` | #7835 | 与公开 `9fb3992fd` patch-equivalent 的 corrected planner |
| `b2b27ad01` | #7841 residual | safe activation protocol；lint 修复 amend 后仍是第五个 commit |

前四个是未合入 `master` 的依赖。对应 PR 合并后 rebase 会自然删除它们；提前 squash 不会减少 diff，只会
破坏 patch-equivalence 和分层 review。

## 当前技术合同

### accepted result

- `TargetCluster.Components` 保存 scheduler 接受的 component name / replicas；
- accepted requirements hash 绑定同一次接受的 CPU、memory 等 requirements；
- pure scale-up 只估 positive delta，pure scale-down 不调用 estimator；
- occupied target 的 unknown、equal、mixed、重复或不完整 transition 不回退 full desired；full desired 只用于
  新候选集群。

### source coherence

- detector 从用于 component interpretation 的同一 source 生成 normalized source hash 并写入 Binding；
- binding controller 使用已读取的 source，要求 UID 相同，并接受 exact ResourceVersion 或相同 source hash；
- source hash 保留用户 labels / annotations，去除 status 和明确列举的 API-managed identity fields；
- 这层只证明 source 与 Binding snapshot 一致，不替代 scheduler acceptance。

### Work delivery fence

- pending result 和 source mismatch 都在 orphan Work 删除、`ensureWork()` 和 Work 更新前返回；
- no-fit、requirements change、mixed/name/shape change、planner error 或 invalid result 都保留旧 accepted result
  和现有 Work；
- source desired state 不会回滚，只是未接受的新配置不会提前下发；
- default scheduler 在 suspension 下仍保持已有 component result 的 fence；custom scheduler 不属于该协议；
- feature gate 关闭后，default-scheduler delivery 忽略历史 `TargetCluster.Components`。

### commit 与修复

- scheduler 用 ResourceVersion CAS main patch 同时写 clusters 和 accepted metadata；
- status 是第二次 CAS patch；
- result-generation token 与 scheduling-spec hash 允许 main patch 成功、status patch 失败后的下一轮只修 status；
- `RequiredBy` 只拥有 dependency cluster reachability：inherited-only target 清除 foreign `Components`，同名
  target 以 dependency 自己的 result 为准。

完整设计和答辩解释见 [Day 52](day52-issue7492-multi-component-pr-design-defense.md)。

<a id="validation"></a>

## 验证与当前 CI

截至 17:15，公开 `#7841@9a18960ea` 的首次 upstream run 唯一已观察到的 failure 是 lint；DCO、codegen、
compile、unit、CLI / Chart / Operator 三档 Kubernetes checks 均通过，三个 base E2E jobs 仍在运行。
lint 的四个确定性问题是：

1. `ComponentScaleUnknown` 缺导出注释；
2. `ClassifyComponentReplicaTransition` gocyclo 16；
3. `runComponentScaleRoutingCase` gocyclo 16；
4. `TestAcceptedComponentTargetIsReusedOnlyWhileFilterEligible` gocyclo 25。

这不是 E2E flake。修复后的 `b2b27ad01c79ec8cb355461a674110c59d6fb3bf` 仅重构上述三处文件，
相对前一 head 为 3 files、`+159/-137`；它已通过：

```text
PATH=/root/go/bin:$PATH hack/verify-staticcheck.sh
go test -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
go test -race -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
PATH=/root/go/bin:$PATH make verify
git diff --check
git show --check
```

`9a18960ea` 功能 tree 的本地验证还通过完整 `make test` 和
`go test -count=1 ./test/e2e/suites/base -run '^$'`；后者输出 `[no tests to run]`，只证明 package 可编译。
lint-only amend 后没有重跑完整 `make test`，也没有本地 live multi-cluster Flink E2E 或 mixed-version rollout。
17:22 回读确认 PR head 已是 `b2b27ad01`；新 run 已启动，DCO 通过，9 个 Kubernetes matrix jobs pending。

<a id="risks"></a>

## 未闭合边界

- 当前栈没有 arbitrary-client 的 admission-time component result validation；scheduler/runtime 会验证自身结果，
  但不能声称 webhook 已保护所有直接 API 写入；
- 仅支持 default scheduler、多个 components 和可证明为 exactly-one-cluster 的 placement；
- ordered `ClusterAffinities`、自动 mixed scale、name replacement 不在自动恢复合同；
- 连续快速 scale-up 可能被旧 scheduling assumption 保守阻塞到 TTL / queue retry，但不会覆盖 accepted Work；
- controller-first rollout、feature gate enable 顺序和 admission owner 仍需 maintainer 确认；完整协议落地前保持
  `MultiplePodTemplatesScheduling=false`。

## 下一步

1. 监控 `b2b27ad01` 的新 exact-head CI，确定 lint 修复及三档 E2E 结果；
2. 继续分类 #7833/#7835 的 E2E failure，不把红灯直接等同于产品回归；
3. 运行或获得 exact-head live Flink E2E 证据；
4. 请 maintainer 评审 accepted-result / source-coherence 协议、`RequiredBy` ownership，以及 admission / rollout
   边界。

<a id="history-and-evidence"></a>

## 证据入口

- [Day 52：多组件调度 PR 设计与答辩](day52-issue7492-multi-component-pr-design-defense.md)
- [Day 49：#7830 ownership 与 stale-input 反例](day49-7830-review.md)
- [Day 44：component scheduling result API 设计](day44-issue7492-component-scheduling-result-api-design.md)
- [Day 46：跨集群重调度状态问题复现](day46-issue7492-mszacillo-state-reproduction.md)
- [Issue #7492](https://github.com/karmada-io/karmada/issues/7492)
