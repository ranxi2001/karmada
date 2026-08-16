# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：完成 #7492 最终 PR4 的确认、推送与 reviewer handoff；准备周一 Descheduler 专项汇报；其余任务只按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-16。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR4 / Day 52](internship-reports/day52-issue7492-final-pr4-redesign.md) | 最终 integration residual 已提交为 `40d82879f`，父提交 `ea8782509`；accepted provenance、失败交付栅栏、legacy/explicit recovery、Flink lifecycle 与 custom-scheduler 兼容已完成。race、base E2E compile、`make verify`、三路源码终审通过；source 未推送 | 用户确认 exact remote branch、old lease `f54f228d7`、new head `40d82879f`；随后再确认 upstream title/body |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 通过；live E2E 仍是边界 | 出现 current-SHA CI 或 review 新信号时处理 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-16：#7492 最终 PR4 在本地收敛为 `40d82879f`，父链固定为 PR0+PR1+PR2+PR3 integration；修复 accepted result provenance、split-write recovery、source/Work fence、legacy migration 与 custom scheduler 兼容。最终 race、base E2E compile、`make verify` 和独立终审通过，未推 source，详见 [Day 52](internship-reports/day52-issue7492-final-pr4-redesign.md)。
- 2026-08-16：PR4 prototype 曾原样重放为 `d005826b1`；源码审计证明 requirements-change 会绕过旧 fence，因此没有推送，并转入最终合同重做，详见 [Day 51](internship-reports/day51-issue7492-pr4-local-integration-design.md)。
- 2026-08-16：用户确认后，#7833/#7835 分别 force-push 到 `98535c541`/`782232b7d`；两个 residual 保持不变，详见 [Day 50](internship-reports/day50-issue7492-pr2-pr3-rebase-on-pr0.md)。
- 2026-08-16：#7833/#7835 已按 residual-only 规则分别基于 #7837 `76589a9d5` 重建，range-diff 与 patch-id 不变；当轮未擅自推送。
- 2026-08-16：#7830 current head `6ff28fe4a` 的当轮 checks 与 DCO 通过，因此未再添加 CI 修复提交或评论。

## Current Blockers

- #7492 PR4：本地实现无已知代码 blocker；source branch push、future PR title/body 和任何 upstream 动作仍待 exact confirmation。live multi-cluster Flink E2E 未在本机执行。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 为确定性测试扩大 scheduler 或 detector 的职责；只在交付边界比较 source UID、resourceVersion 与解释后的 component inputs。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- 用户确认后，以显式 `--force-with-lease` 将 `40d82879f` 推到 `origin/feature/multi-component-failure-safe-rescheduling`；推送后逐字核对 remote head，不自动创建或更新 upstream PR。
- PR 文案使用 [Day 52 draft](internship-reports/day52-issue7492-pr4-body-draft.md)；任何 upstream title/body 发布仍需再次确认 exact target/text。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。
- #7827、#7662 只在 CI/review/proposal 出现新信号时继续。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
