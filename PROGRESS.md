# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 为 Week 33 核心，按 maintainer-provided Draft 对齐 PR1 scope 与版本合同，再进入调度行为；完成周一 Descheduler 专项汇报；其余任务仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-15。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [PR #7830 / Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md) | 远端仍为 `c0b68f728`；本地已在 `afecff517 -> ce77a4cdf` 上重建 PR1 commit `ac32f8671`，residual 9 文件。unit/race、E2E compile、verify 通过 | exact-action 后 force-with-lease 更新 PR head 与 title/body，不发评论；随后看 upstream PR CI |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，NodeResource spec 使用临时 Kind + 独立 estimator。compile/race-compile、vet、verify 通过；新 title/body 已发布并逐字校验 | 等 current-SHA upstream CI；真实多集群 E2E 仍是端到端验证边界，失败时按 job/source 对齐分析 |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |

## Last Run

- 2026-08-15：#7830 已在 #7837 API commit `afecff517` 与 helper fix `ce77a4cdf` 上重建为 `ac32f8671`：PR1 residual 9 文件 `+1472/-11`，删除 eviction/API/helper ownership 重叠，补真实 v1alpha1 main UPDATE E2E 和 rollback 反例；unit/race、E2E compile、verify 通过。待 exact push/title/body approval，未更新远端或评论，详见 [Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md)。
- 2026-08-14：#7827 专用集群方案已实现并推送 commit `6ebc4b459`：最终 PR diff 仅 `estimator_test.go` `+190/-8`；compile/race-compile、vet、`make verify`、diff check 通过。新 title/body 已发布，远端 body SHA-256 `2200fe0e...4183e` 与确认稿一致。
- 2026-08-14：研究 #7827 专用集群方案：base E2E 已有 `member-e2e-*` 的 `create/join/wait Ready/unjoin/delete` 先例；NodeResource 主修复可只改 `estimator_test.go`，复用 suite helper 并在 spec 内部署/清理 estimator。PDB cleanup 若保留则不再是单文件；PR head 尚未修改。
- 2026-08-14：#7826 两条 comments 已原位替换并逐字校验：真正 hard-coded target 是 `estimator_test` 的 member1，scheduler 日志只让 member1 进入 estimator；新文案删除三集群 90m 主叙事，聚焦 member1 外来 30m 与 TTL refresh。
- 2026-08-13：完成 #7826 后的 3 项 skill 更新：RCA causal tuple/五泳道 + attempt 审计、最终 Markdown Mermaid fence 自动渲染、issue body target/hash approval 状态机；10 项脚本测试、3 项 skill 校验和 #7826 两图/两个真实 run 正向验证通过，未再次编辑上游 issue，详见 [Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md)。

## Current Blockers

- #7492 PR1：本地 stack 已验证，唯一当前 blocker 是开放 PR branch 的 exact force-with-lease 与 title/body approval；#7837 仍缺旧 PR 的 list/name/replica markers，后续不能在 rebase 时静默带回。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把 #7837 开放 head 当成 #7830 的正式 rebase base；允许只为验证和修复 #7837 自身 CI blocker 创建临时本地 worktree。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 经用户确认 exact target/text 后，把 `feature/multi-component-scale-rescheduling` 从 `c0b68f728` force-with-lease 更新到 `ac32f8671` 并同步 PR #7830 title/body；不发评论，先看 upstream PR CI。#7837 merge 后再清理 stack，PR1 稳定后 rebase PR2。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7827 等 current-SHA upstream CI；不把本地 compile/race-compile 升级为真实多集群 E2E 证据，出现失败时再按具体 matrix job 分析。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
