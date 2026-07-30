# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：战略主线继续等待 #7621/#7662 合同收敛；PR #7800 retained-memory 回应与新实现已验证，Issue #7802 queue-contract 评论等待回应；同时维护 #7791、#7697、#7795 三条已发布交付线。

## Current Snapshot

状态核对时间：2026-07-30。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [PR #7662](https://github.com/karmada-io/karmada/pull/7662) | Open，head 仍为 `586f6fc3508e`；7 月 28 日会议收敛 offline scope，7 月 30 日 maintainer 提议 `GetComponents.selector -> estimator Unschedulable -> dynamicScaleUp` | `@zhy76` / `@RainbowMango` 回复或 proposal commit；再核对 API 集合、ownership、多组件和 completion contract |
| [PR #7791](https://github.com/karmada-io/karmada/pull/7791) | Open，head `41ed652725fc`；Full affinity cursor reset 已收敛，等待 review | 新 CI、真人 review 或同范围 upstream 提交 |
| [PR #7697](https://github.com/karmada-io/karmada/pull/7697) | Open，head `bf24e47ce3bd`；证书轮换实现和定向验证已完成 | 新 review、CI 变化或 maintainer scope 决策 |
| [PR #7795](https://github.com/karmada-io/karmada/pull/7795) | Open，head `14b24b90db73`；`FIXTURE_LOCAL_E4 / TERMINAL_E2`，PR claim 已收紧 | maintainer review 或能够连接原 CI 404 的新证据 |
| [Issue #7802](https://github.com/karmada-io/karmada/issues/7802) | Open；[queue-contract comment](https://github.com/karmada-io/karmada/issues/7802#issuecomment-5114587741) 已发布并逐字回读；无 assignee，等待首次回复 | 作者或 maintainer 明确 priority 候选范围，或提供生产 trace/方案方向 |

## Last Run

- 2026-07-30：复核 [PR #7800 作者回应与新 head](internship-reports/day36-pr7800-waiting-store-deep-review.md#2026-07-30-作者回应与新-head-复核)：本地 full-store retained delta 约 17.98 MiB、`byGVKName` 约 3.19 MiB，race/scaling 通过；[closure reply](https://github.com/karmada-io/karmada/pull/7800#discussion_r3681520974) 已发布，GitHub 因账号权限拒绝 resolve，等待作者/maintainer 关闭 thread。
- 2026-07-30：完成 [PR #7662 selector / unschedulable 更新 review](internship-reports/day37-pr7662-selector-unschedulable-review.md)：新方案解决 assigned-but-unschedulable 信号缺失，但 `Available != Unschedulable`、selector 不等于 ownership、多组件不能直接映射标量 `dynamicScaleUp`，且 scheduler/Descheduler ownership 与 completion 仍未收敛；未发布 upstream 评论。
- 2026-07-29：完成 [Issue #7802 priority queue 确定性实验](internship-reports/day36-issue7802-priority-queue-experiment.md)：确认不完整候选集合可产生一次 low-first，反证“持续 drain 整批”，并拆开 readmission ordering 与 capacity/quota wake-up；[179-word queue-contract comment](https://github.com/karmada-io/karmada/issues/7802#issuecomment-5114587741) 已发布并逐字回读。
- 2026-07-29：完成 [PR #7800 waiting store 深度 review](internship-reports/day36-pr7800-waiting-store-deep-review.md)：未发现 correctness blocker；查询性能显著改善，但 24,564 对象下 retained heap 从约 3.15 MB 增至 40.56 MB，[non-blocking line review](https://github.com/karmada-io/karmada/pull/7800#discussion_r3671589022) 已发布。
- 2026-07-29：扫描过去一周 5 个 Open Issue 和 33 个 Open PR，形成 [Day 36 review 候选](internship-reports/day36-karmada-weekly-review-candidates-2026-07-29.md)：优先 PR #7800，Issue #7802 先补队列顺序证据，PR #7794 等作者修复已被 bot 指出的 timeout gap。

## Current Blockers

- #7662：estimator 的长期 `PodScheduled=False/Unschedulable` 能识别目标副本，但 public API 仍写 `PreserveAvailableReplicas`；selector ownership/rollout、多组件 placement、alpha gate、scheduler/Descheduler ownership 和 request completion 尚未定义。
- 三条个人 PR 当前都需要外部 review 或新证据；等待本身不产生代码动作，也不重复催促。
- `intern` 不含 Karmada 源码；任何源码验证必须在从最新 `upstream/master` 创建的独立 worktree 中进行。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后先用 Day 37 的 10 副本反例和 Flink 多组件反例核对 signal、support matrix、owner 与 completion，再决定是否起草 upstream review。
- #7791、#7697 或 #7795 出现 review/CI 时，先回读 current head 和完整 thread，只处理与当前 diff 有因果关系的反馈。
- #7800 原 retained-memory finding 已由 current head `038e34d0d134` 实质处理并发布 closure reply；等待作者/maintainer resolve、current-head CI 和 maintainer review，不再追加评论或把剩余内存成本写成 OOM 结论。
- #7802 等待作者或 maintainer 回复 [queue-contract comment](https://github.com/karmada-io/karmada/issues/7802#issuecomment-5114587741)；maintainer 明确 strict priority 的候选范围前，不提交 queue/API 改动，也不重复催促。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
