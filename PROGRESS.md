# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 为 Week 33 核心，按 maintainer-provided Draft 对齐 PR1 scope 与版本合同，再进入调度行为；完成周一 Descheduler 专项汇报；其余任务仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-13。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [PR #7830 / Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md) | #7492 PR1 Open、非 Draft、mergeable，head `be8c7c3f7`；17/17 upstream checks 全绿。Tide 等 `lgtm/approved`；nested component validation 经复核确认为合并前 P1 | 在两个现有 webhook 文件补 ownership-aware gate-off/membership validation 和测试；本地验证后再申请开放 PR branch push/回复授权；PR1 稳定后再推进 PR2 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open、mergeable，head `ba531a9a1`；3 文件 test-only cleanup，official run 保持 E3；[#7826](https://github.com/karmada-io/karmada/issues/7826) 已替换为[时序图主导的正文](internship-reports/day48-issue7826-revised-body-draft.md) | PR 只在失败或 review 新信号时处理，不主动 retest/comment |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |

## Last Run

- 2026-08-13：按用户确认替换 [#7826](https://github.com/karmada-io/karmada/issues/7826) 正文；两个 run 现在分别用时序图明确 `producer spec -> 残留对象 -> consumer spec -> 失败断言`，线上正文与[本地定稿](internship-reports/day48-issue7826-revised-body-draft.md)逐字校验一致。
- 2026-08-13：创建 [#7492 PR1 #7830](https://github.com/karmada-io/karmada/pull/7830)，head `be8c7c3f7` 的 17/17 upstream checks 首次运行全绿；自动 review 指出的 nested component validation 经源码复核确认为合并前 P1，修复需区分 eviction 与 `RequiredBy` 所有权，详见 [Day 49](internship-reports/day49-issue7492-pr1-api-compat-pr7830.md)。
- 2026-08-13：创建 [#7826](https://github.com/karmada-io/karmada/issues/7826) 和 test-only [PR #7827](https://github.com/karmada-io/karmada/pull/7827)：官方与 fork CI 证明两个跨 spec workload producer，3 文件 cleanup 补丁等待 source/RB NotFound；证据保持 E3，详见 [Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md)。
- 2026-08-13：完成 [#7492 PR1 legacy status 数据丢失与修复设计](internship-reports/day47-issue7492-v1alpha1-status-data-loss-fix-design.md)：确认 RB/CRB `v1alpha1 /status` 的 request-version old object 会丢 component data，当前 main-resource rule 又不匹配 status；推荐 A2 exact status rule + storage-state guard，并验证混合升级期旧 handler 会 fail closed；未修改或推送 topic branch。
- 2026-08-12：发布 `humanizer-cs v0.4.6`（`a0db303`）：新增按调用触发的 Release 检查、完整 release 元组确认、manifest/本地漂移校验和备份回滚；43 项测试、真实 Release 压缩包和 Latest API 验证通过，全局与 repo-local skill 已升级，旧全局副本保留在 `/root/.codex/skill-backups/humanizer-cs-pre-v0.4.6-20260812`。

## Current Blockers

- #7492 PR1：CI 已完成；当前阻塞是 1 条未解决的自动 review，源码复核后定为 P1。两条 nested result 路径都缺 gate-off 新旧值保护；eviction 可按当前 Binding 校验 membership，`RequiredBy` 属于其他 Binding snapshot，只校验自身 duplicate；尚无 human review。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 在现有 webhook 两文件补 PR #7830 nested result 的 ownership-aware validation 与测试，跑 focused tests 和 `make verify`；完成本地 review 后，再经 exact-action gate 更新开放 PR branch/回复 thread。PR1 稳定后再 rebase PR2。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7826 正文已替换；#7827 current-SHA CI 已全绿，单次绿灯不升级为 E4，只在失败或 review 新信号时处理。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
