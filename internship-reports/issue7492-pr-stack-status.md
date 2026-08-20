# #7492 多组件调度 PR 栈状态

> 状态核对：2026-08-20（Asia/Shanghai）。动态 PR / CI 状态以 GitHub 为准；本文只保存后续
> review 和发布仍需要的当前事实，不再维护 rebase、push 或旧 PR body 过程记录。

<a id="stack-overview"></a>

## 先说人话

#7492 已按职责拆成五层：API、result producer、interpreter / Work delivery、scale planner 和安全 activation。
#7837、#7833 已合并；#7830、#7835 仍独立 review；#7841 已按这些新分片重建，公开 head 为
`b2b27ad01c79ec8cb355461a674110c59d6fb3bf`。#7841 已转为 Ready，当前 16 个 checks success；
唯一红灯是 v1.34 base E2E 在不相关 rescheduling spec 的 `BeforeEach` 创建临时 member 失败。

#7833 在 2026-08-20 收到 `@RainbowMango` 的首条真人 review 建议：把 helper 从
`componentSchedulingResult` 改名为 `buildTargetComponents`。PR head `29474a636` 已按建议改名并 rebase 到
`upstream/master@1c4a0ff70`，聚焦 race test 和全部 scheduler package tests 通过；branch update 和原 thread
内的简短 reply 均已完成。#7833 随后于 `2026-08-20 09:59:35Z` 合并，merge commit 为
`a8ad84cb5288709cc5f6f0e8a5aad0b87a000a31`。合并前 v1.35 E2E 因 Karmada etcd / host control plane 失去响应而失败；
失败 Deployment 不进入本 PR 新增的 `Components > 1` 分支，scheduler 在控制面故障前已成功完成重调度。

本地 test-only 候选 `3bb0a304a` 新增 Flink、Volcano Job、RayCluster 三类 workload 的 4-spec focus 矩阵。
live E2E 实际运行在仅差一处注释的 `d8df11c3d` 上，并已在 Kubernetes v1.36.1 跑通。该测试栈尚未推到
开放 PR；完整功能启用前仍要确认 rollout / admission validation 边界并获得 maintainer review。

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
| [#7833](https://github.com/karmada-io/karmada/pull/7833) | `29474a636cfb`，merge `a8ad84cb5288` | scheduler 写完整 component result | 已合并；helper rename 和 reply 已完成；v1.34/v1.36 E2E 通过，合并前 v1.35 因 control-plane failure 红灯 |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `3619c24f6ebc` | component scale planner，不接生产入口 | Open，非 Draft；1 commit，2 files；14 success、3 failure、Tide pending |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `b2b27ad01c79` | trigger、provenance、failure retention、delivery fence | Open，非 Draft；16 success、v1.34 base E2E failure、Tide pending |

#7833 合并前只有一条不改变行为的 helper 命名建议；其余开放 PR 尚无实质性 human review。当前没有 `/lgtm`、
`/approve` 或设计认可，bot、reviewer request 和 Tide 状态不能写成人类认可。

## #7841 当前五个 commits

| Commit | 对应公开分片 | 说明 |
| --- | --- | --- |
| `014c555f8` | #7833 | scheduler result producer |
| `32d2e45d5` | #7830 commit A | 与公开 `997a594b1` patch-equivalent 的 interpreter capability |
| `db8073d38` | #7830 commit B | 与公开 `4583e06d2` residual patch-equivalent 的 Work delivery |
| `bdcc01b66` | #7835 | 与当前公开 `3619c24f6` patch-equivalent 的 corrected planner |
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

#7833 旧公开 head `014c555f898cf575422b65d8c4fbb95e56295cea` 的 compile、lint、codegen、unit、
v1.35/v1.36 E2E 和三组 Kubernetes 测试已通过；v1.34 E2E 在 2026-08-20 核对时仍 pending，Tide 等待
`approved` / `lgtm`。当前 head `29474a636cfbee097f43e6a78c6af3ca64fc67fa` 只把 helper 与调用点
改名为 `buildTargetComponents`，并 rebase 到 `upstream/master@1c4a0ff70`。range-diff 没有其他 patch
变化，以下命令通过：

```text
go test -race ./pkg/scheduler/core
go test ./pkg/scheduler/...
git diff --check upstream/master...HEAD
git range-diff 1819ee7bd..014c555f8 upstream/master..29474a636
```

公开 CI 已在 `29474a636` 上重新运行；旧 head 的结果不计入当前 candidate。

当前 head 的 v1.35 E2E job `96349704810` 在 `resource reschedule when join or unJoin cluster` 中失败。
测试于 `08:03:17` 创建临时 member，scheduler 于 `08:03:39` 把普通 Deployment 成功写为
`[{member-e2e-z9bx7 1 []} {member2 1 []} {member3 1 []} {member1 1 []}]`；该对象没有 components，
因此不会执行本 PR 新增的 `len(spec.Components) > 1` 分支。`08:03:42` 起 etcd 的 linearized read 在
`agreement among raft nodes` 阶段连续超时，Karmada API liveness 随后失败，scheduler 因无法续租退出，
etcd 容器最终以 137 结束；测试等 Ready 满 420 秒后只看到 `172.18.0.2:5443 connection refused`。
同一 SHA 的 v1.34、v1.36 E2E 均已通过。当前证据支持 CI 环境 / control-plane collapse，
不支持修改 #7833 代码；未定位宿主机层面的 CPU、I/O 或 memory 根因，因此不把 exit 137 直接写成 OOM。

公开 `#7841@b2b27ad01c79ec8cb355461a674110c59d6fb3bf` 的 lint、codegen、compile、unit、
CLI/Chart/Operator 三档矩阵、v1.35/v1.36 base E2E 和 DCO 均通过，共 16 个 success。唯一失败是
v1.34 base E2E：`rescheduling_test.go` 的 `BeforeEach` 创建临时 member 时
`kubeadm init` 失败；suite 因 fail-fast 在 232/274 后停止，新增 Flink spec 未执行。Tide 仍等待
`approved` / `lgtm`。

`b2b27ad01` 已通过：

```text
PATH=/root/go/bin:$PATH hack/verify-staticcheck.sh
go test -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
go test -race -p 2 -count=1 ./pkg/util ./pkg/scheduler/core ./pkg/scheduler
PATH=/root/go/bin:$PATH make verify
git diff --check b2b27ad01^..b2b27ad01
git show --check --oneline b2b27ad01
```

`9a18960ea` 功能 tree 的本地验证还通过完整 `make test` 和
`go test -count=1 ./test/e2e/suites/base -run '^$'`；后者输出 `[no tests to run]`，只证明 package 可编译。

2026-08-19 的本地 test-only 候选 `3bb0a304a` 位于 `b2b27ad01` 之上，只改 4 个 E2E/fixture 文件
（`+1224/-3`），没有 production-code diff。最终候选通过：

```text
go test -count=1 ./test/e2e/suites/base -run '^$'
/root/go/bin/golangci-lint run ./test/e2e/suites/base/...
git diff --check b2b27ad01..3bb0a304a
git show --check --oneline 3bb0a304a
```

live E2E 在注释修正前的行为等价 tree `d8df11c3d` 上执行。Kubernetes v1.36.1 的 3-member 环境运行
`--focus='\[MultiComponentRescheduling\]'`：FlinkDeployment 134.880s、Volcano Job 72.867s、
RayCluster lifecycle 212.689s、Ray label-eligibility recovery 142.202s，最终
`Ran 4 of 277 Specs in 568.362 seconds`，`4 Passed / 0 Failed`。
完整矩阵、观察窗和未覆盖边界见 [Day 52](day52-issue7492-multi-component-pr-design-defense.md#单版本-live-focus)。
本地没有运行多 Kubernetes 版本或 mixed-version rollout。

<a id="risks"></a>

## 未闭合边界

- 当前栈没有 arbitrary-client 的 admission-time component result validation；scheduler/runtime 会验证自身结果，
  但不能声称 webhook 已保护所有直接 API 写入；
- 仅支持 default scheduler、多个 components 和可证明为 exactly-one-cluster 的 placement；
- ordered `ClusterAffinities`、mixed-direction planning、name replacement 不在自动恢复合同；mixed/name
  transition 只能 fail closed 或走受控 explicit recovery，后者已有 Ray live focus；
- label-filter-ineligible target 的 explicit recovery 和迁移后的 pinned scale no-fit 已实测；CRB、自动
  missing/terminating target failover、spread-ineligible fallback 和 full-recovery no-fit 尚无 live 证据；
- 连续快速 scale-up 可能被旧 scheduling assumption 保守阻塞到 TTL / queue retry，但不会覆盖 accepted Work；
- controller-first rollout、feature gate enable 顺序和 admission owner 仍需 maintainer 确认；完整协议落地前保持
  `MultiplePodTemplatesScheduling=false`。

## 下一步

1. 保留 #7833 合并前 v1.35 control-plane failure 的 RCA，不再为已合并 PR 触发重跑或改代码；
2. 决定是否整理并把 test-only `3bb0a304a` 更新到 #7841；
3. 更新后只把新 SHA 的 upstream checks 归属于对应新 candidate；保留旧 head 的验证边界；
4. 请 maintainer 评审 accepted-result / source-coherence 协议、`RequiredBy` ownership，以及 admission / rollout
   边界。

<a id="history-and-evidence"></a>

## 证据入口

- [Day 52：多组件调度 PR 设计与答辩](day52-issue7492-multi-component-pr-design-defense.md)
- [Day 49：#7830 ownership 与 stale-input 反例](day49-7830-review.md)
- [Day 44：component scheduling result API 设计](day44-issue7492-component-scheduling-result-api-design.md)
- [Day 46：跨集群重调度状态问题复现](day46-issue7492-mszacillo-state-reproduction.md)
- [Issue #7492](https://github.com/karmada-io/karmada/issues/7492)
