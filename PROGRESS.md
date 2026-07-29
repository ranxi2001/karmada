# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：战略主线继续等待 #7621/#7662 合同收敛；PR #7800 non-blocking review 已发布并等待作者回应，Issue #7802 下一步做确定性队列复现；同时维护 #7791、#7697、#7795 三条已发布交付线。

## Current Snapshot

状态核对时间：2026-07-29。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [PR #7662](https://github.com/karmada-io/karmada/pull/7662) | Open，head `586f6fc3508e`；作者的 `PreserveScheduled` 与 maintainer 的 `PreserveAvailableReplicas` 尚未形成合同 | maintainer 回复、作者更新 proposal，或社区要求补充 workload 状态语义 |
| [PR #7791](https://github.com/karmada-io/karmada/pull/7791) | Open，head `41ed652725fc`；Full affinity cursor reset 已收敛，等待 review | 新 CI、真人 review 或同范围 upstream 提交 |
| [PR #7697](https://github.com/karmada-io/karmada/pull/7697) | Open，head `bf24e47ce3bd`；证书轮换实现和定向验证已完成 | 新 review、CI 变化或 maintainer scope 决策 |
| [PR #7795](https://github.com/karmada-io/karmada/pull/7795) | Open，head `14b24b90db73`；`FIXTURE_LOCAL_E4 / TERMINAL_E2`，PR claim 已收紧 | maintainer review 或能够连接原 CI 404 的新证据 |

## Last Run

- 2026-07-29：完成 [PR #7800 waiting store 深度 review](internship-reports/day36-pr7800-waiting-store-deep-review.md)：未发现 correctness blocker；查询性能显著改善，但 24,564 对象下 retained heap 从约 3.15 MB 增至 40.56 MB，[non-blocking line review](https://github.com/karmada-io/karmada/pull/7800#discussion_r3671589022) 已发布。
- 2026-07-29：扫描过去一周 5 个 Open Issue 和 33 个 Open PR，形成 [Day 36 review 候选](internship-reports/day36-karmada-weekly-review-candidates-2026-07-29.md)：优先 PR #7800，Issue #7802 先补队列顺序证据，PR #7794 等作者修复已被 bot 指出的 timeout gap。
- 2026-07-29：将 `intern` 收敛为 record-only 分支，只保留 `.agents/`、`internship-reports/`、`AGENTS.md`、`PROGRESS.md`；upstream 代码工作改用独立 topic branch/worktree。
- 2026-07-29：删除本文件的历史长尾；119 条 `Last Run` 缩为最近 5 条，旧过程继续由日报、TODO 和 Git 历史承载，并建立滚动删除预算。
- 2026-07-28：完成 [Day 35 #7662 workload 状态调研](internship-reports/day35-pr7662-workload-unavailable-pending-research.md)，确认 `unavailable != Pending != Unschedulable != movable`，typed API 在权威信号、首版支持矩阵、单一 writer 和 completion contract 明确前暂停。

## Current Blockers

- #7662：`PreserveScheduled` 看不到“已经 assigned、但 member 内长期 Pending”的副本；`PreserveAvailableReplicas` 又会混入 image、readiness、rollout 和 application failure。没有权威 movable signal 前不开始 typed API。
- 三条个人 PR 当前都需要外部 review 或新证据；等待本身不产生代码动作，也不重复催促。
- `intern` 不含 Karmada 源码；任何源码验证必须在从最新 `upstream/master` 创建的独立 worktree 中进行。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- #7662 出现新回复时，用 Day 35 的 10 副本反例核对 `assigned`、`PodScheduled`、Ready、Available 和长期 Unschedulable 的数据源，再决定是否更新 proposal review。
- #7791、#7697 或 #7795 出现 review/CI 时，先回读 current head 和完整 thread，只处理与当前 diff 有因果关系的反馈。
- #7800 等待作者回应 [retained-memory line review](https://github.com/karmada-io/karmada/pull/7800#discussion_r3671589022)；若更新证据或索引实现则复测，不先把本地数据写成 OOM 结论。
- #7802 先用 fake clock 和受控 `Pop` 复现同时/错峰到期顺序，区分 capacity/quota 唤醒问题与 priority 排序问题，不先承诺 per-namespace 方案。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
