# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：以 #7492 为 Week 33 核心，按 maintainer-provided Draft 对齐 PR1 scope 与版本合同，再进入调度行为；完成周一 Descheduler 专项汇报；其余任务仅按新信号跟进。

## Current Snapshot

状态核对时间：2026-08-12。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [#7492 / Day 46](internship-reports/day46-issue7492-mszacillo-state-reproduction.md) | Draft PR1 仍为 `cf59527e2`；源码级条件复现完成：纯 `Components` scale 不触发调度，第二触发器进入调度后容量可换集群，普通 target switch 不构造或转移 `PreservedLabelState`；真实 Flink 状态丢失未复现 | 暂不发布重复性 comment；等待 `mszacillo` 的版本、YAML、触发器和 state 定义，再决定是否有新增事实值得回复；PR2 前决定跨集群状态合同 |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662 / Day 40](internship-reports/day40-pr7662-unschedulable-replica-rescheduling-api-plan.md) | Open，head `586f6fc3508e`；partial 一期为 Deployment：source generation/V2 freshness、pinned delta、strict capacity、原子 commit、ack/consume/abandon；Full 保持通用路径 | `@zhy76` / `@RainbowMango` 回复或 proposal commit；逐项确认 10 个 stop gates |
| [PR #7810 / Day 41](internship-reports/day41-pr7810-binding-update-coalescing-review.md) | Open，reviewed head `31bef8d37`；fixed window 仅是 best-effort。P1 delayed key 可越过 ownership / suspension；delay 还覆盖 failover、Descheduler 和 WR，priority queue 忽略参数；[review 已发布](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994) | 作者回复或 push 新 head 后复查 dequeue guard、作用域、两类 queue、fake-clock tests 和 docs CI |

## Last Run

- 2026-08-12：发布 `humanizer-cs v0.4.6`（`a0db303`）：新增按调用触发的 Release 检查、完整 release 元组确认、manifest/本地漂移校验和备份回滚；43 项测试、真实 Release 压缩包和 Latest API 验证通过，全局与 repo-local skill 已升级，旧全局副本保留在 `/root/.codex/skill-backups/humanizer-cs-pre-v0.4.6-20260812`。
- 2026-08-12：在独立 `upstream/master@1c278577e` worktree 以本地提交 `a649fe5c1` 完成 #7492 三段源码级复现，focused 与三个完整包测试通过；结论、边界和待确认英文 comment 见 [Day 46](internship-reports/day46-issue7492-mszacillo-state-reproduction.md)，未发布 upstream comment、未推送验证分支。
- 2026-08-12：将 Draft PR1 压成并推送单提交 `cf59527e2`：新增 `GracefulEvictionTask.Components`、RB result validation 与 downgrade grandfathering；相关 race tests 和 `make verify` 通过，`make test` 唯一红项为既有公网 `TestInternetIP`，其余范围补跑通过；[Day 45](internship-reports/day45-issue7492-progress-completeness-and-open-contracts.md)已记录。
- 2026-08-11：[#7795](https://github.com/karmada-io/karmada/pull/7795) 在维护者 `/retest` 触发同 SHA v1.35 attempt 2 转绿后由 Tide 合并为 `1c278577e789`；环境红项升级为非确定性 `E1`，runner I/O/运行时物理原因仍为 `E2` 假设。[最终 RCA 与合并证据](internship-reports/day33-karmadactl-top-flake-upstream-draft.md#最终合并结论)已归档，并纠正“workflow 事件列表可否定 bot rerun API”的误判。
- 2026-08-04：完成 [Day 41 PR #7810 代码与系统 review](internship-reports/day41-pr7810-binding-update-coalescing-review.md) 和 [delayed-key 时序](internship-reports/day41-pr7810-delayed-key-race.mmd)：确认 `AddAfter` 保留最早 deadline 且可被 fast path 绕过，并发现 delayed key 可越过 ownership / suspension；全局延迟还覆盖 failover、Descheduler 与 WR，priority queue 不生效。[英文 review](https://github.com/karmada-io/karmada/pull/7810#issuecomment-5178016994)已发布并回读验证。

## Current Blockers

- #7492：Draft PR1 已推送但尚未 review；`mszacillo` 未给版本、YAML、第二触发器和 state 定义，真实 Flink state loss 未复现；served v1alpha1、CRB validator、Gate downgrade、failed-rescheduling safety、scale trigger/delta 和跨集群状态合同仍未闭合。
- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：Deployment signal/owner-chain 可复用，但 V1 estimator 缺 source freshness；public mode、threshold、V2 观测合同、requestID/ack、pinned selection、Descheduler 仲裁和旧 WR controller 降级为 Full 的风险均待确认；详见 Day 40 stop gates。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7492 暂不发布当前重复性 comment；等 `mszacillo` 补版本、YAML、第二触发器和 state 定义后，只在出现新增事实时追加短回复。PR1 准备 exact title/body，PR2 前明确跨集群 scale 的状态合同，再实现 producer、snapshot merge、trigger/delta、`ReviseComponents` 和失败保护。
- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后逐项核对 Day 40 的 10 个 stop gates，只在准确 target/text 获用户确认后起草或发布 upstream review。
- #7810 等作者回复或新 head；更新后复查 dequeue guard、delay 作用域、legacy/priority queue、fake-clock 与 failover/Descheduler tests，不在无新信号时重复催促。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
