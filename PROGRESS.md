# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：按 #7492 最新任务拆分收敛 #7830、#7835、#7841 的依赖和验收边界；并行准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-25。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | [`@RainbowMango` 已确认](https://github.com/karmada-io/karmada/issues/7492#issuecomment-5404808509)：故障来自 fork，upstream 的 scalar fields 均为 0，不会因 restart 或 scale 触发重调度；下一步按 `.spec.clusters[].components` 检测组件副本变化。#7841 current `6a51dcd9c` 行为目标一致，17 checks success、GitHub `MERGEABLE` | 等待 #7841 human review 确认独立 component-aware precheck 是否符合预期入口；#7835 等待 trusted user `/ok-to-test` |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-25：完成 [PR #7860 Release Notes Skill 完整性 Review](internship-reports/pr7860-generating-release-notes-skill-review.md)，并已发布 [`/assign` + review acknowledgment](https://github.com/karmada-io/karmada/pull/7860#issuecomment-5413148977)。current `2e7ae71` 的 17 checks success，但真实 release data 证明 4 条 completeness blocker：v1.18 minor 285 commits 超过默认 250 后直接失败、#7298 多行 fence 丢四条 deprecation、null commit author 漏 `@SujoyDutta`、GraphQL failure 被折叠成 exit 0。英文 inline drafts 已准备，技术评论尚未发布，等待用户确认 exact text。
- 2026-08-25：完成 [#7846 / #7824 evidence-first review](internship-reports/pr7846-pr7824-evidence-first-review-2026-08-25.md)。#7846 用真实 Kubernetes v1.36.1 Job controller 生成 `failed + active` member 状态，经 exact-head native aggregation 后由真实 API Server 拒绝 `Active>0 + Failed=True`；已准备锚定 `job.go:112@eb14ddd2` 的精简 inline comment。#7824 exact head 漏删 LoadBalancer/Local 的 `healthCheckNodePort`，真实 allocator 复现已占用端口拒绝，且新 E2E 对旧行为也会通过。所有 upstream 评论与 review 仍待用户确认，尚未发布。
- 2026-08-25：work-api Kubernetes/Go 升级 [PR #74](https://github.com/kubernetes-sigs/work-api/pull/74) 已合并为 `b13d322`。final head `f608bdc` 为单一 signed-off commit：L11-L16 逐项 `>=` Karmada，Gomega 对齐 `v1.42.0`；upstream `lint`、`verify`、`unit test`、`e2e` 全部 success，`RainbowMango` `/lgtm`、`/approve`，没有 inline comment 或额外适配要求。[完整记录](internship-reports/k8s-go-update.md)
- 2026-08-25：完成 [community PR #216 Agent Skills 范式复核](internship-reports/community-pr216-agent-skills-paradigm-review.md)。7 个 skill package 均通过 OpenAI validator，merged SHA 的 deterministic suite 通过；同时以最小函数级输入确认 grader error 会被排除出统计分母、`target_triggered=false` 不会使 output gate 失败。结论是格式与任务边界达到高质量 beta 水平，但 eval gate 暂不足以作为 gold-standard reference；是否发送 upstream comment 后续单独决定，本轮没有准备或发布社区文本。
- 2026-08-25：#7492 最新 maintainer 回复确认故障来自 fork；upstream multi-template workload 的 scalar fields 均为 0，restart 与 scale 不会从旧逻辑触发重调度或迁移。维护者明确下一步应基于已持久化的 `.spec.clusters[].components` 做组件级变化检测。#7841 current `6a51dcd9c` 通过 `schedulePendingComponentsFor*` 在旧检查前完成该行为，而不是直接扩展 `IsBindingReplicasChanged`；这是待 human review 的实现入口问题，不把 issue 方向性评论当作 PR 批准。该案例已沉淀为 issue comment 的 `scope boundary -> decisive mechanism -> next upstream action` 收敛方法。[最新讨论与实现影响](internship-reports/issue7492-pr-stack-status.md#最新讨论与实现影响2026-08-25)

## Current Blockers

- #7492：#7830/#7835/#7841 尚无实质性 human review；#7835 重跑受 trusted-user `/ok-to-test` gate 阻塞；#7841 的独立 component-aware precheck 是否应收回 `IsBindingReplicasChanged` 仍待 review，且仍缺 arbitrary-client admission validation、mixed-version rollout、live restart/no-change，以及 CRB、自动 target-loss failover、split-write 的 live 证据。
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
- 保持 #7841 current head `6a51dcd9c` 不变；17 个 checks 已成功，不重复 push 或重跑。等待 #7830/#7835/#7841 human review，重点确认组件变化检测应直接进入 `IsBindingReplicasChanged`，还是保留当前独立 precheck。
- #7841 验收至少覆盖 fit scale-up、no-fit scale-up、scale-down 和 restart/no-change；no-fit 同时检查 target、accepted result 和 Work 未变化。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
