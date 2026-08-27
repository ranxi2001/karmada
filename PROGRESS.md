# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：按 #7492 最新任务拆分收敛 #7830、#7835、#7841 的依赖和验收边界；并行准备 Descheduler 专项汇报。

## Current Snapshot

状态核对时间：2026-08-27。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 PR stack](internship-reports/issue7492-pr-stack-status.md#stack-overview) | 三需求重新拆为 #7830 trigger、#7835 estimation、#7841 failure-safe propagation；#7830 已更新为 trigger-only head `78dfc7a40`，3-file diff 与 title/body 已远端精确验证 | 等 #7830 official PR CI / human review；之后基于新 head 重整 #7835 |
| [PR #7827 / Day 48](internship-reports/day48-estimator-assumption-e2e-isolation-pr7827.md) | Open，head `6ebc4b459`；最终 diff 仅 `estimator_test.go`，focused validation 与 current-SHA 3 个 upstream E2E jobs 通过；本地未运行 live E2E | 等待 maintainer review 新信号 |
| [Day 39 Descheduler](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 汇报稿按整任务调度模型整理；仍缺真实 YAML 对生命周期、诊断、lock、回执与 cooldown 的证据 | 周一前拿真实 YAML 核对并试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期限定 Deployment，10 个 stop gates 尚待确认 | `@zhy76` / `@RainbowMango` 回复或 proposal commit |

## Last Run

- 2026-08-27：完成并发布 #7830 scope reset：旧 37-file `ReviseComponents` / Work delivery diff 全部移出，公开 head `78dfc7a40` 仅修改 `IsBindingReplicasChanged` 及 RB / CRB tests；focused race 与完整受影响 package tests 通过。explicit-lease force-push 与 REST title/body update 完成，remote head、title、3-file diff 和 body SHA-256 `fe314b53e4594276d447353f9d5684e49e23c1bef471f32fa0e730512e51ba49` 已精确验证。[职责、diff 与发布证据](internship-reports/issue7492-pr-stack-status.md#7830-本地实现结果)
- 2026-08-27：补全 [PR #7830 component delivery 数据流与 reviewer comment 草稿](internship-reports/day49-pr7830-component-delivery-comment-draft.md)：区分已有 `Component` scheduler input、`TargetComponent` per-cluster output、commit 1 `ReviseComponents` capability 与 commit 2 `ensureWork` consumer；exact Markdown Mermaid 通过 `@mermaid-js/mermaid-cli@11.16.0` 临时渲染为纵向 `609×2204`，草稿 243 visible words、SHA-256 `44b0118081b5f3adfd23a525ceee9dda7337b2eb6f8673554f2ee8cde82f32ed`。未发布上游评论。
- 2026-08-26：完成 [Day 57：PR #7860 Release Notes Skill 完整性 Review](internship-reports/day57-pr7860-release-notes-skill-review.md)，并已发布 [`/assign` acknowledgment](https://github.com/karmada-io/karmada/pull/7860#issuecomment-5413148977) 与包含 [4 条 completeness blocker](https://github.com/karmada-io/karmada/pull/7860#pullrequestreview-5021435325) 的 `COMMENTED` review；remote body 与获准草稿逐条哈希一致，未给 `/lgtm` 或 `/approve`。同轮将全局 `humanizer-cs` 从 `v0.5.0` 升级到稳定版 `v0.5.1@865e6feabc5c803d4b6e08a8581d23f4ddfb4a9c`，备份位于 `/home/ranxi/.codex/skills/.humanizer-cs-backup-0.5.0-20260825163316`，新 session 生效。
- 2026-08-26：完成 [Day 56：#7846 / #7824 evidence-first review](internship-reports/day56-pr7846-pr7824-evidence-first-review.md) 的首条上游反馈。#7846 用真实 Kubernetes v1.36.1 Job controller 生成 `failed + active` member 状态，经 exact-head native aggregation 后由真实 API Server 拒绝 `Active>0 + Failed=True`；用户确认后已发布 [`job.go:112` inline comment](https://github.com/karmada-io/karmada/pull/7846#discussion_r3858973277)。未提交 `Request changes`；#7846 第二条与 #7824 两条草稿仍待逐项确认。
- 2026-08-25：#7492 最新 maintainer 回复确认故障来自 fork；upstream multi-template workload 的 scalar fields 均为 0，restart 与 scale 不会从旧逻辑触发重调度或迁移。维护者明确下一步应基于已持久化的 `.spec.clusters[].components` 做组件级变化检测。#7841 current `6a51dcd9c` 通过 `schedulePendingComponentsFor*` 在旧检查前完成该行为，而不是直接扩展 `IsBindingReplicasChanged`；这是待 human review 的实现入口问题，不把 issue 方向性评论当作 PR 批准。该案例已沉淀为 issue comment 的 `scope boundary -> decisive mechanism -> next upstream action` 收敛方法。[最新讨论与实现影响](internship-reports/issue7492-pr-stack-status.md#最新讨论与实现影响2026-08-25)

## Current Blockers

- #7492：#7830 已更新，等待 official PR CI / human review；#7835/#7841 仍需按新依赖栈重整，本轮未修改。
- Day 39：尚缺真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标回执。
- #7662：V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection 与 Descheduler 仲裁仍待确认。

## Ruled Out

- 不把 delta estimator 结果当成完整 replacement capacity 证明；requirements 或 accepted baseline 变化必须 full schedule 或 fail closed。
- 不用 `generation > observedGeneration` 单独证明 result 已接受；split result/status write 必须有持久 token、spec hash 与 resourceVersion CAS。
- 不让 binding controller 通过 direct GET、timer 或 ResourceInterpreter 猜 acceptance；source coherence 使用 detector-owned UID + exact RV 正向证据或 normalized source hash，scheduler acceptance 使用 component result + requirements hash。
- 不把 local E2E compile 写成 live multi-cluster 行为证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch。

## Next

- 等 #7830 official PR CI / human review；不把 fork push CI 作为验证证据。
- 基于公开 #7830 head `78dfc7a40` 重整 #7835；不把 Work propagation 回填到 #7830/#7835。
- 保持 #7841 current public head `6a51dcd9c` 不变，等 #7830/#7835 新栈确定后再处理 residual diff。
- #7841 验收至少覆盖 fit scale-up、no-fit scale-up、scale-down 和 restart/no-change；no-fit 同时检查 target、accepted result 和 Work 未变化。
- 周一前用 Day 39 HTML 稿试讲，并用真实 YAML 核对生命周期、诊断、lock、handoff 和 cooldown。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 80 行或 8 KiB 时，先下沉旧状态再添加。
