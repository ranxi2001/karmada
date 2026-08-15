# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 为 Week 33 核心，按 maintainer-provided Draft 对齐 PR1 scope 与版本合同，再进入调度行为；完成周一 Descheduler 专项汇报；其余任务仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-16。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR0-PR3 / Day 49-50](internship-reports/day50-issue7492-pr2-pr3-rebase-on-pr0.md) | #7830 head `6ff28fe4a` 的 16 个 GitHub Actions checks 与 DCO 全绿；#7833/#7835 已分别在 #7837 `76589a9d5` 上本地重建为 `98535c541`/`782232b7d`，residual 等价且 focused race、verify 通过 | 用户确认两个 exact force-with-lease target 与完整 PR body 后推送并触发 current-SHA CI；不评论、不改 Draft 状态 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，NodeResource spec 使用临时 Kind + 独立 estimator。compile/race-compile、vet、verify 通过；新 title/body 已发布并逐字校验 | 等 current-SHA upstream CI；真实多集群 E2E 仍是端到端验证边界，失败时按 job/source 对齐分析 |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |

## Last Run

- 2026-08-16：#7833/#7835 已按 residual-only 规则各自直接基于 #7837 `76589a9d5` 重建为 `98535c541`/`782232b7d`；两个 `range-diff` 均为 `=`、patch-id 不变，focused race、base E2E compile（仅 #7833）与 `make verify` 通过。远端未改，待 exact push/body 确认，详见 [Day 50](internship-reports/day50-issue7492-pr2-pr3-rebase-on-pr0.md)。
- 2026-08-16：复核 #7830 current head `6ff28fe4a`：16 个 GitHub Actions checks 与 DCO 全部成功，Tide 仅等待 `lgtm/approved`；因此不再添加修复 commit，也不发布 CI 评论。
- 2026-08-15：用户确认后，已用显式 lease `ac32f8671` 将 #7830 PR branch 更新到 `6ff28fe4a`；GitHub PR head 与 fork remote 均一致，DCO Success，首批 12 个 upstream checks queued/in-progress。title/body 未改、未评论，详见 [Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md)。
- 2026-08-15：不等 #7837 merge，已在其全绿 current head `76589a9d5` 上只重放 PR1 residual，得到本地 `6ff28fe4a`。`range-diff` 为 `=`、patch-id 相同、9 文件 `+1472/-11`；race、base E2E compile、`make verify` 通过。远端仍为 `ac32f8671`，待 exact force-with-lease 确认，详见 [Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md)。
- 2026-08-15：#7837 head 已改写为 `76589a9d5`，相对旧 `afecff517` 仅新增 `test/helper/scheduler.go` `+4/-1`，17/17 check runs（含 DCO）全绿；Tide 只缺 `lgtm/approved`。取消给 #7837 提交 `ce77a4cdf` 或发布 helper comment，PR1 等 merge 后丢弃临时 stack，详见 [Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md)。

## Current Blockers

- #7492 PR2/PR3：本地重排与验证完成；远端仍为 `1d2ee95c4`/`b1c41a584`，等待两个精确 `force-with-lease` target 和完整英文 PR body 的用户确认。#7837 current API 仍缺旧 PR 的 list/name/replica markers，不能静默带回。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不再给 #7837 提供 helper commit 或评论；新本地 stack 已丢弃 `afecff517 + ce77a4cdf`，采用 #7837 current head，最终仍以 #7837 merge 结果清理 ancestry。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 获得 exact-action/text 确认后，将 #7833/#7835 分别 force-with-lease 更新到 `98535c541`/`782232b7d`，同步修正 ancestry/validation body；不发评论、不改 Draft 状态，随后只看 upstream current-SHA CI。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7827 等 current-SHA upstream CI；不把本地 compile/race-compile 升级为真实多集群 E2E 证据，出现失败时再按具体 matrix job 分析。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
