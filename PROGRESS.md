# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：按 #7492 最新任务拆分收敛 #7830、#7835、#7841 的依赖和验收边界；并行准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-21。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | 最新 issue body 剩 4 项：component scale trigger、delta/scale-down estimation、失败不下发、超容量不迁移。#7830/#7835 仍待 review；#7841 `b2b27ad01` 因 #7833 已合并而冲突 | 先收敛 #7830/#7835；再重建 #7841 residual，并用 fit/no-fit/scale-down/restart 矩阵验收；暂不推 test-only 栈 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-21：按 #7492 最新 issue body 重排剩余任务。4 个未完成 checkbox 映射为 #7835 planner、#7830 Work delivery、#7841 trigger/failure retention/pinned target 三层；`GetTotalBindingReplicas` restart 现象来自外部 v1.17 fork，不能当作 upstream `master` 的直接复现，但“扩容超过容量不得迁移”已是 maintainer 明确的验收要求。[当前任务映射](internship-reports/issue7492-pr-stack-status.md#stack-overview)
- 2026-08-20：核对 [PR #7833](https://github.com/karmada-io/karmada/pull/7833) 已于 `09:59:35Z` 合并到 `master`，merge commit `a8ad84cb5288709cc5f6f0e8a5aad0b87a000a31`。合并前 v1.35 control-plane failure 归档为环境 RCA，不再作为当前代码阻塞。
- 2026-08-20：完成 #7833 新 head CI 红灯 RCA。v1.35 job `96349704810` 的普通 Deployment 不进入 `Components > 1` 新分支，scheduler 在 `08:03:39` 已成功重调度；`08:03:42` 起 etcd linearized read 无法完成 raft agreement，随后 API liveness、leader lease 和整个 host control plane 连锁失效。v1.34/v1.36 E2E 通过；当前不改代码、不把 exit 137 无证据写成 OOM。
- 2026-08-20：复核 [PR #7833](https://github.com/karmada-io/karmada/pull/7833) 当前 `014c555f8` 与完整 thread。`@RainbowMango` 最新建议仅把 `componentSchedulingResult` 改名为 `buildTargetComponents`；candidate `29474a636` 已按建议改名、rebase `upstream/master@1c4a0ff70`、force-push 到公开 PR，range-diff 无其他 patch 变化，`go test -race ./pkg/scheduler/core` 与 `go test ./pkg/scheduler/...` 通过；原 thread reply 已发布。
- 2026-08-19：在 #7841 production-equivalent tree 上完成 Kubernetes v1.36.1 三类 workload focused E2E：Flink、Volcano Job、RayCluster 共 4/4 通过（568.362s）。覆盖 2/3/4 组件、零副本、delta/no-fit、mixed/name/shape/requirements 拒绝、explicit recovery、label-filter eligibility 与迁移后 pinned no-fit；本地候选 `3bb0a304a` 只改 4 个 test/fixture 文件，compile、golangci-lint、diff/show checks 通过。[Day52 答辩稿](internship-reports/day52-issue7492-multi-component-pr-design-defense.md) 已更新证据边界。

## Current Blockers

- #7492：#7830/#7835 尚无实质性 human review；#7841 因包含已合并 #7833 commit 而冲突。当前栈仍缺 arbitrary-client admission validation、mixed-version rollout，以及 CRB、自动 target-loss failover、split-write 的 live 证据。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 通过 direct GET、timer 或 ResourceInterpreter 猜 acceptance；source coherence 使用 detector-owned UID + exact RV 正向证据或 normalized source hash，scheduler acceptance 使用 component result + requirements hash。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- 先复核 #7830、#7835 是否需要基于当前 `master` 调整，并等待各自 review；不把 #7841 的集成问题塞回两个基础 PR。
- #7841 重建时删除已合并 #7833 commit；功能 residual 收敛后再准备包含 test-only `3bb0a304a` 的 exact branch-update packet。
- #7841 验收至少覆盖 fit scale-up、no-fit scale-up、scale-down 和 restart/no-change；no-fit 同时检查 target、accepted result 和 Work 未变化。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
