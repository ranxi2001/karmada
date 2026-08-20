# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：用本地多 workload E2E 结果完成 #7492 答辩，并在 exact action gate 后决定是否把测试补强推到 #7841；并行准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-20。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | #7833 收到 `@RainbowMango` helper 命名建议；本地 `29474a636` 已改为 `buildTargetComponents`、rebase 最新 master 并通过 scheduler tests，尚未 push。#7841 公开 head `b2b27ad01` 已 Ready；本地 E2E 候选 `3bb0a304a` 尚未 push | 先审批 #7833 exact branch update 与 thread reply，再决定 #7841 test-only 更新；rollout、admission、CRB 和自动 target-loss failover 仍是边界 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-20：复核 [PR #7833](https://github.com/karmada-io/karmada/pull/7833) 当前 `014c555f8` 与完整 thread。`@RainbowMango` 最新建议仅把 `componentSchedulingResult` 改名为 `buildTargetComponents`；本地 candidate `29474a636` 已按建议改名、rebase `upstream/master@1c4a0ff70`，range-diff 无其他 patch 变化，`go test -race ./pkg/scheduler/core` 与 `go test ./pkg/scheduler/...` 通过。尚未 push 或回复 upstream。
- 2026-08-19：在 #7841 production-equivalent tree 上完成 Kubernetes v1.36.1 三类 workload focused E2E：Flink、Volcano Job、RayCluster 共 4/4 通过（568.362s）。覆盖 2/3/4 组件、零副本、delta/no-fit、mixed/name/shape/requirements 拒绝、explicit recovery、label-filter eligibility 与迁移后 pinned no-fit；本地候选 `3bb0a304a` 只改 4 个 test/fixture 文件，compile、golangci-lint、diff/show checks 通过。[Day52 答辩稿](internship-reports/day52-issue7492-multi-component-pr-design-defense.md) 已更新证据边界。
- 2026-08-18：完成 [PR #7830 文件规模与职责拆解](internship-reports/day49-7830-review.md#为什么会改-37-个文件)：37 files 中 11 个是测试/fixture、9 个是生成/schema、17 个是手写代码；主链仍是 `ReviseComponents` capability + binding Work delivery。未发布 upstream review/comment。
- 2026-08-18：#7841 已用 exact lease 从 `9a18960ea` 更新到 `b2b27ad01`；4 个 lint 问题完成本地 staticcheck、focused/race、`make verify` 和 diff checks，新 CI 已启动。完成 [Day52 多组件设计答辩](internship-reports/day52-issue7492-multi-component-pr-design-defense.md)。
- 2026-08-18：复审 [PR #7830 当前 head](internship-reports/day49-7830-review.md#当前-review-finding)：组件职责放置合理，但当前 delivery 可组合“旧 accepted replicas + 新 source requirements”；完整功能必须依赖 scheduler-owned provenance + binding delivery fence。新增 [职责图](internship-reports/day49-7830-review-component-ownership.mmd)，未发布 upstream review。

## Current Blockers

- #7833：本地 `29474a636` 已完成维护者 rename 建议，但开放 PR 分支更新与 thread reply 尚未获 exact action approval。
- #7492：本地 test-only 候选 `3bb0a304a` 尚未获开放 PR 分支更新授权；当前栈仍缺 arbitrary-client admission validation、mixed-version rollout，以及 CRB、自动 target-loss failover、split-write 的 live 证据。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 通过 direct GET、timer 或 ResourceInterpreter 猜 acceptance；source coherence 使用 detector-owned UID + exact RV 正向证据或 normalized source hash，scheduler acceptance 使用 component result + requirements hash。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- 准备 #7833 exact branch-update packet：目标分支、旧/新 SHA、单一 rename range-diff、两组 scheduler tests 和 thread reply；获确认后才 force-push 与回复。
- 准备 #7841 的 exact branch-update packet：目标、旧/新 SHA、4-file test-only diff、v1.36.1 4/4 live E2E、未跑项和 PR body 增量；获确认后才 push。
- 若更新 #7841，跟进新 SHA 的 upstream lint/compile/unit/E2E；不把单版本本地 focus 写成多版本或全量 base suite。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
