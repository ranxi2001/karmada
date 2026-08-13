# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 为 Week 33 核心，按 maintainer-provided Draft 对齐 PR1 scope 与版本合同，再进入调度行为；完成周一 Descheduler 专项汇报；其余任务仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-13。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 / Day 47](internship-reports/day47-issue7492-v1alpha1-status-data-loss-fix-design.md) | PR1 head `1382c90d9` exact-SHA CI 全绿，但确认 `v1alpha1 /status` 可经有损转换擦除 component data；推荐新增 exact status rules，并仅拒绝 component-aware legacy writes | 先实现 A2 guard、真实 API Server 回归并 rebase；PR text 明确它不是完整多版本根治，长期另议停止 serve `v1alpha1` |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open、mergeable，head `ba531a9a1`；3 文件 test-only cleanup。证据为 E3；DCO/codegen/compile/lint/unit 和普通 Kubernetes tests 已通过，三组 upstream E2E pending | 等 current-SHA E2E 与 maintainer review；只在失败或 review 新信号时处理，不主动 retest/comment |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |

## Last Run

- 2026-08-13：创建 [#7826](https://github.com/karmada-io/karmada/issues/7826) 和 test-only [PR #7827](https://github.com/karmada-io/karmada/pull/7827)：官方与 fork CI 证明两个跨 spec workload producer，3 文件 cleanup 补丁等待 source/RB NotFound；证据保持 E3，详见 [Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md)。
- 2026-08-13：完成 [#7492 PR1 legacy status 数据丢失与修复设计](internship-reports/day47-issue7492-v1alpha1-status-data-loss-fix-design.md)：确认 RB/CRB `v1alpha1 /status` 的 request-version old object 会丢 component data，当前 main-resource rule 又不匹配 status；推荐 A2 exact status rule + storage-state guard，并验证混合升级期旧 handler 会 fail closed；未修改或推送 topic branch。
- 2026-08-12：发布 `humanizer-cs v0.4.6`（`a0db303`）：新增按调用触发的 Release 检查、完整 release 元组确认、manifest/本地漂移校验和备份回滚；43 项测试、真实 Release 压缩包和 Latest API 验证通过，全局与 repo-local skill 已升级，旧全局副本保留在 `/root/.codex/skill-backups/humanizer-cs-pre-v0.4.6-20260812`。
- 2026-08-12：在独立 `upstream/master@1c278577e` worktree 以本地提交 `a649fe5c1` 完成 #7492 三段源码级复现，focused 与三个完整包测试通过；结论、边界和待确认英文 comment 见 [Day 46](internship-reports/day46-issue7492-mszacillo-state-reproduction.md)，未发布 upstream comment、未推送验证分支。
- 2026-08-12：将 Draft PR1 压成并推送单提交 `cf59527e2`：新增 `GracefulEvictionTask.Components`、RB result validation 与 downgrade grandfathering；相关 race tests 和 `make verify` 通过，`make test` 唯一红项为既有公网 `TestInternetIP`，其余范围补跑通过；[Day 45](internship-reports/day45-issue7492-progress-completeness-and-open-contracts.md)已记录。

## Current Blockers

- #7492：PR1 尚不能正式提交；必须先阻断 component-aware RB/CRB 的 `v1alpha1 /status` 有损写入，并用真实 API Server 证明完整 spec 保留。A2 只修 component state；完整 legacy conversion 或停止 serving 需另行决策。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 按 [Day 47](internship-reports/day47-issue7492-v1alpha1-status-data-loss-fix-design.md) 先补 A2：exact `v1alpha1 */status` rules、storage-state guard、status early return 和 RB/CRB live regression；rebase/新 SHA 验证后再准备 exact PR text。PR2 前另定跨集群状态合同。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7827 等 current-SHA E2E 和 maintainer review；单次绿灯不升级为 E4，只在失败或 review 新信号时处理。主动作继续 #7492 PR1 legacy-write safety guard 与 live regression。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
