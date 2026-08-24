# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：按 #7492 最新任务拆分收敛 #7830、#7835、#7841 的依赖和验收边界；并行准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-24（本轮只复核 #7835 current-head CI；其余动态状态延续 2026-08-21 快照）。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | 最新 issue body 剩 4 项：component scale trigger、delta/scale-down estimation、失败不下发、超容量不迁移。#7835 current head 的 3 个红 job 已定性为端口冲突、artifact 上传超时和 control-plane collapse；`/retest` 被 Prow 的 trusted-user gate 拒绝；#7830/#7835 仍待 review；#7841 已更新到 `6a51dcd9c` | 等待 trusted user 在 #7835 留 `/ok-to-test`；继续等待 human review，不为环境红灯改 production code |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-24：完成 `#7835@3619c24f6` 三个红 job 的 exact-attempt RCA。CLI v1.35 是 Docker 绑定 `127.0.0.1:45215` 冲突；Operator v1.36 在 7/7 spec 通过后上传 artifact `ETIMEDOUT`；Base E2E v1.36 已成功调度普通 Job，随后 etcd linearized read / fdatasync 与 containerd 同时失速，control plane 连锁退出。三项均支持重跑，不支持修改 #7835；宿主最底层资源原因仍无直接证据。用户确认后已发送 [`/retest`](https://github.com/karmada-io/karmada/pull/7835#issuecomment-5389840800)，Prow 因缺少 trusted user 的 `/ok-to-test` 拒绝触发，新 run 未启动。[current-head CI RCA](internship-reports/issue7492-pr-stack-status.md#7835-current-head-ci-rca2026-08-24)
- 2026-08-21：在 `rewrite/pr7841-three-scenarios-20260821` 之后无冲突移植 `0ecf16531..3bb0a304a` 五个 test-only E2E commit，形成 `rewrite/pr7841-update-20260821@6a51dcd9c`，并按确认 force-with-lease 更新 #7841 fork head。62-file packet 的 focused production tests、E2E compile、E2E lint、签名与 diff checks 全通过；尚未在 exact tree 重跑 live E2E。[branch-update packet](internship-reports/issue7492-pr-stack-status.md#7841-branch-update-packet2026-08-21)
- 2026-08-21：按 #7492 最新 issue body 重排剩余任务。4 个未完成 checkbox 映射为 #7835 planner、#7830 Work delivery、#7841 trigger/failure retention/pinned target 三层；`GetTotalBindingReplicas` restart 现象来自外部 v1.17 fork，不能当作 upstream `master` 的直接复现，但“扩容超过容量不得迁移”已是 maintainer 明确的验收要求。[当前任务映射](internship-reports/issue7492-pr-stack-status.md#stack-overview)
- 2026-08-21：在当前 `upstream/master@a8ad84cb5288` 重建 `rewrite/pr7841-three-scenarios-20260821`，删除已合并 #7833 后保留 #7830/#7835/#7841 四个等价 patch，并推到 `origin` fork。scale-up delta、超容量 pinned no-fit、scale-down zero-estimator 及 binding Work fence focused tests 全通过；未发现额外 production fix，当前候选尚未重新跑 live E2E，也未创建 upstream PR。[三场景检查](internship-reports/issue7492-pr-stack-status.md#三场景检查与修复边界)
- 2026-08-20：核对 [PR #7833](https://github.com/karmada-io/karmada/pull/7833) 已于 `09:59:35Z` 合并到 `master`，merge commit `a8ad84cb5288709cc5f6f0e8a5aad0b87a000a31`。合并前 v1.35 control-plane failure 归档为环境 RCA，不再作为当前代码阻塞。

## Current Blockers

- #7492：#7830/#7835 尚无实质性 human review；#7835 重跑受 trusted-user `/ok-to-test` gate 阻塞；#7841 已更新到当前 master 后的 `6a51dcd9c`，仍缺 current-tree live E2E、arbitrary-client admission validation、mixed-version rollout，以及 CRB、自动 target-loss failover、split-write 的 live 证据。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 通过 direct GET、timer 或 ResourceInterpreter 猜 acceptance；source coherence 使用 detector-owned UID + exact RV 正向证据或 normalized source hash，scheduler acceptance 使用 component result + requirements hash。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- 等待 trusted user 在 #7835 留 `/ok-to-test` 后再观察 current-head CI；不为旧环境红灯修改 planner，也不把 #7841 的集成问题塞回两个基础 PR。
- 保留 `rewrite/pr7841-update-20260821@6a51dcd9c` 作为已推送的 exact branch-update packet；等待 #7830/#7835 review 和 #7841 upstream CI，不推到 upstream remote。
- #7841 验收至少覆盖 fit scale-up、no-fit scale-up、scale-down 和 restart/no-change；no-fit 同时检查 target、accepted result 和 Work 未变化。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
