# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 多组件扩缩容重调度为 Week 33 核心；完成周一 Descheduler 专项汇报；#7621/#7662、#7810 和 #7697 仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-10。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 / Day 42](internship-reports/day42-issue7492-multi-component-scale-rescheduling-intake.md) | v1.19 umbrella 仍 open，`ranxi2001` 已正式 assigned；`mszacillo` 更早获 maintainer 同意承接，8 月 7 日又收到 per-component `TargetCluster` API 前置方向。`upstream/master@c884a959` 确认 request/result 缺口；无关联 PR | 用户批准精确英文协调评论后，与早期 owner 划分 API/compatibility/test 独立切片；确认 ownership 前不建 worktree |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |
| [PR #7810 / Day 41](internship-reports/day41-pr7810-binding-update-coalescing-review.md) | Open，reviewed head `31bef8d37`；fixed window 仅是 best-effort。P1 delayed key 可越过 ownership / suspension；delay 还覆盖 failover、Descheduler 和 WR，priority queue 忽略参数；[review 已发布](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994) | 作者回复或 push 新 head 后复查 dequeue guard、作用域、两类 queue、fake-clock tests 和 docs CI |

## Last Run

- 2026-08-10：将 [#7492 / Day 42](internship-reports/day42-issue7492-multi-component-scale-rescheduling-intake.md) 定为 Week 33 核心；完成线程、关联 PR、`upstream/master@c884a959` API/scheduler/detector/binding 和 conversion 基线；18:26 `ranxi2001` 已 `/assign`，但 `mszacillo` 的更早承接仍需协调。无关联 PR；精确评论待用户批准，ownership 划分前不建 worktree。
- 2026-08-10：#7795 已发布 `/retest`，但 bot 因缺 `/ok-to-test` 拒绝，且该命令不能重跑 GitHub Actions。[深入 RCA](internship-reports/day33-karmadactl-top-flake-upstream-draft.md#upstream-ci-红项分类2026-08-10)确认 top 用例通过；红项终止于无关 kind cgroup-ready 失败，现场三套 etcd 同时慢盘，runner I/O/运行时根因为 E2；等待维护者重跑 failed jobs。
- 2026-08-10：#7795 发布 `8d2148606` 后重新审计 [`NewPod` 契约](internship-reports/day33-karmadactl-top-flake-upstream-draft.md)：无 command 的 BusyBox 在默认 `RestartPolicyAlways` 下不是一次性任务，而是持续重启；最终 `aaf1dc24c` 恢复两参数 API 并默认 `sleep 3600`，8 个 E2E 均有 cleanup；测试、force-push、194-word body 和第一条回复修订均完成并回读。
- 2026-08-04：完成 [Day 41 PR #7810 代码与系统 review](internship-reports/day41-pr7810-binding-update-coalescing-review.md) 和 [delayed-key 时序](internship-reports/day41-pr7810-delayed-key-race.mmd)：确认 `AddAfter` 保留最早 deadline 且可被 fast path 绕过，并发现 delayed key 可越过 ownership / suspension；全局延迟还覆盖 failover、Descheduler 与 WR，priority queue 不生效。[英文 review](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994)已发布并回读验证。
- 2026-08-04：新增 [Day 40 #7662 API/代码开发基准](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) 和 [流程图](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-flow.mmd)：确认当前 WR 写请求即成功、V1 estimator freshness 与 `FitError` retry 均有缺口；一期范围及 source generation、pinned capacity、commit recovery、ack/consume/abandon 等 stop gates 已定。

## Current Blockers

- #7492 已有活跃 owner；per-component target API、served-version conversion、mixed scale semantics 和 failed-rescheduling fence 均待协作/maintainer 确认。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 经用户确认 exact target/text 后发布协作评论；owner 确认独立切片才从最新 `upstream/master` 建 worktree，并先冻结 API/test contract。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7810 等作者回复或新 head；更新后复查 dequeue guard、delay 作用域、legacy/priority queue、fake-clock 与 failover/Descheduler tests，不在无新信号时重复催促。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
