# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：完成下周一 Karmada Descheduler 专项汇报；以 Day 40 跟进 #7621/#7662；等待并复查 Day 41 的 #7810 作者更新；维护 #7697 等已发布交付线。

## Current Snapshot

状态核对时间：2026-08-10。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |
| [PR #7810 / Day 41](internship-reports/day41-pr7810-binding-update-coalescing-review.md) | Open，reviewed head `31bef8d37`；fixed window 仅是 best-effort。P1 delayed key 可越过 ownership / suspension；delay 还覆盖 failover、Descheduler 和 WR，priority queue 忽略参数；[review 已发布](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994) | 作者回复或 push 新 head 后复查 dequeue guard、作用域、两类 queue、fake-clock tests 和 docs CI |
| [PR #7795](https://github.com/karmada-io/karmada/pull/7795) | `aaf1dc24c` 已 `lgtm/approved`；唯一红项为 v1.35 namespace 用例的无关 kind cgroup-ready 启动超时，同 job 的 top 用例和其他版本矩阵均通过；尚待重跑确认非确定性；[CI 分类证据](internship-reports/day33-karmadactl-top-flake-upstream-draft.md#upstream-ci-红项分类2026-08-10) | 用户确认后在 #7795 发布 `/retest`，随后核对重跑结果 |

## Last Run

- 2026-08-10：#7795 `aaf1dc24c` 已 `lgtm/approved`；[upstream CI 分类](internship-reports/day33-karmadactl-top-flake-upstream-draft.md#upstream-ci-红项分类2026-08-10)确认唯一红项为 v1.35 namespace 用例动态 kind 节点 cgroup-ready 超时；本 PR 的 top 用例在同 job 通过，v1.34/v1.36.1 矩阵也通过，不修改 PR 代码，待用户确认 `/retest`。
- 2026-08-10：#7795 发布 `8d2148606` 后重新审计 [`NewPod` 契约](internship-reports/day33-karmadactl-top-flake-upstream-draft.md)：无 command 的 BusyBox 在默认 `RestartPolicyAlways` 下不是一次性任务，而是持续重启；最终 `aaf1dc24c` 恢复两参数 API 并默认 `sleep 3600`，8 个 E2E 均有 cleanup；测试、force-push、194-word body 和第一条回复修订均完成并回读。
- 2026-08-04：完成 [Day 41 PR #7810 代码与系统 review](internship-reports/day41-pr7810-binding-update-coalescing-review.md) 和 [delayed-key 时序](internship-reports/day41-pr7810-delayed-key-race.mmd)：确认 `AddAfter` 保留最早 deadline 且可被 fast path 绕过，并发现 delayed key 可越过 ownership / suspension；全局延迟还覆盖 failover、Descheduler 与 WR，priority queue 不生效。[英文 review](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994)已发布并回读验证。
- 2026-08-04：新增 [Day 40 #7662 API/代码开发基准](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) 和 [流程图](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-flow.mmd)：确认当前 WR 写请求即成功、V1 estimator freshness 与 `FitError` retry 均有缺口；一期范围及 source generation、pinned capacity、commit recovery、ack/consume/abandon 等 stop gates 已定。
- 2026-08-04：纠偏 [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) 和 [整任务重入队图](internship-reports/day39-karmada-descheduler-code-contract-breaks.mmd)：改为 Binding 一级队列、member Pod 二级证据与 whole-task requeue；缺口收敛为生命周期、不可调度证据、pre-start fence、接管完成和持久 retry/cooldown，HTML 已同步验收。

## Current Blockers

- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。
- #7795 已 `lgtm/approved`；当前只被与 PR 无关的 v1.35 kind 启动失败阻塞 Tide，不需要代码修改，等待用户确认 `/retest`。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7810 等作者回复或新 head；更新后复查 dequeue guard、delay 作用域、legacy/priority queue、fake-clock 与 failover/Descheduler tests，不在无新信号时重复催促。
- #7795 经用户确认后发布 `/retest`；只核对重跑结果，不为无关 kind 启动超时修改 PR 代码。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
