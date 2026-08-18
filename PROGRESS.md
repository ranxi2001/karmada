# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：确认 #7830 职责定位和 CI、分类 #7833/#7835 E2E 红灯，并按新分片重新对齐 #7841；准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-18。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | PR0 #7837 已合并；PR1 #7830 已重构为 interpreter + Work delivery，PR2 #7833 只生产 result，PR3 #7835 保留 planner；旧 PR4 #7841 仍含重构前副本 | 等 #7830 checks/review，分类 #7833/#7835 红灯，并按当前 PR1/PR2/PR3 heads 重新对齐 #7841 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-18：复审 [PR #7830 当前 head](internship-reports/day49-7830-review.md#当前-review-finding)：组件职责放置合理，但当前 delivery 可组合“旧 accepted replicas + 新 source requirements”；完整功能必须依赖 scheduler-owned provenance + binding delivery fence。新增 [职责图](internship-reports/day49-7830-review-component-ownership.mmd)，未发布 upstream review。
- 2026-08-17：完成 [近期 PR CI E2E 归并](internship-reports/day51-karmada-recent-pr-ci-e2e-failures-2026-08-17.md)：51 次 `pull_request` workflow 中 12 次失败，19 个红 E2E job 归并为 12 个确定性契约问题、1 个已确认直接机制但底层原因待定的 estimator 同步问题、6 个环境/control-plane 故障；与 Day 50 的 schedule 样本分开处理。
- 2026-08-17：完成 [近期 schedule E2E 归并](internship-reports/day50-karmada-recent-e2e-failure-scan-2026-08-17.md)：16 个 Job 红 job 是同一聚合边界的两个相反 version-skew 合同；PR 需先确认版本化终态合同。
- 2026-08-17：发布 PR4 Draft [#7841](https://github.com/karmada-io/karmada/pull/7841) at `49916cee1`；DCO 成功、CI 已启动。PR3 红灯的直接机制是 estimator 请求未使用已创建 quota，底层原因待定，不据此修改 PR3/PR4 产品代码。
- 2026-08-17：把 #7492 的六份过程记录合并为一份 [PR stack 交接](internship-reports/issue7492-pr-stack-status.md#history-and-evidence)，保留当前 refs、最终合同、关键反例与验证边界。

## Current Blockers

- #7492：#7841 的 provenance + delivery fence 仍是完整功能所需合同，但当前 integration history 未按重构后的 #7830/#7833 对齐；live multi-cluster Flink E2E 未在本机执行。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 为确定性测试扩大 scheduler 或 detector 的职责；只在交付边界比较 source UID、resourceVersion 与解释后的 component inputs。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- PR CI：优先修正 #7832 的 reason 断言、#7824 的 NodePort 断言，并为 #7835 设计 estimator 行为边界同步；环境类红灯只在同阶段重复后深挖 artifact。
- 等 #7830 checks/review，分类 #7833/#7835 E2E 红灯；再按当前分片重建 #7841 integration history。任何 upstream 更新仍需确认 exact action/text。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
