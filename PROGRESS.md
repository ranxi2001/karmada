# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：完成 #7492 PR3 红灯归因与 PR4 Draft 发布确认；准备 Descheduler 专项汇报；其余任务只按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-17。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | PR0 #7837、PR1 #7830、PR2 #7833 的 current checks 成功；PR3 #7835 有 1 个 `e2e v1.35` 红灯；PR4 fork head `40d82879f` 已验证并推送，尚无 upstream PR | 先完成 PR3 红灯 RCA，再确认 PR4 Draft 的 exact target/title/body；live Flink 行为仍待真实集群验证 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 通过；live E2E 仍是边界 | 出现 current-SHA CI 或 review 新信号时处理 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-17：把 #7492 的六份过程记录合并为一份 [PR stack 交接](internship-reports/issue7492-pr-stack-status.md#history-and-evidence)，保留当前 refs、最终合同、关键反例、验证边界和 PR4 草稿；删除重复 PR body、rebase/push 过程及已淘汰设计副本。
- 2026-08-16：PR2/PR3 residual 重放后 patch 等价，PR4 最终收敛为 `40d82879f`；focused race、base E2E compile 和 `make verify` 通过，fork source branch 已回读确认。

## Current Blockers

- #7492：#7835 的 `e2e v1.35` 尚待 RCA；PR4 实现/source push 无已知 blocker，但 Draft 创建和任何 reviewer-facing 动作仍待 exact confirmation。live multi-cluster Flink E2E 未在本机执行。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 为确定性测试扩大 scheduler 或 detector 的职责；只在交付边界比较 source UID、resourceVersion 与解释后的 component inputs。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- PR4 文案使用 [合并记录中的 exact draft](internship-reports/issue7492-pr-stack-status.md#pr4-upstream-draft)；任何 upstream PR 创建、title/body 发布或 reviewer-facing 动作仍需再次确认 exact target/text。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。
- #7827、#7662 只在 CI/review/proposal 出现新信号时继续。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
