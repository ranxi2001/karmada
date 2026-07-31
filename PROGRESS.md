# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：完成下周一 Karmada Descheduler 专项汇报准备；战略主线继续等待 #7621/#7662 的 signal、workload support、single writer 与 completion contract 收敛；同时维护 #7697 等已发布交付线。

## Current Snapshot

状态核对时间：2026-07-31。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [Day 38 Descheduler 专项](internship-reports/day38-karmada-descheduler-special-study.md) | 完整证据报告、两张英文图和 [13 页 Style C HTML 汇报稿](internship-reports/day38-karmada-descheduler-presentation.html)已完成；固定 `1920×1080` 舞台并用章节轨、过桥句串联五章 | 周一前确认千问 workload 的 Kind、多组件/可替换语义和成功条件，并用 10 副本例子试讲 |
| [PR #7662](https://github.com/karmada-io/karmada/pull/7662) | Open，head 仍为 `586f6fc3508e`；7 月 28 日会议收敛 offline scope，7 月 30 日 maintainer 提议 `GetComponents.selector -> estimator Unschedulable -> dynamicScaleUp` | `@zhy76` / `@RainbowMango` 回复或 proposal commit；再核对 API 集合、ownership、多组件和 completion contract |
| [PR #7697](https://github.com/karmada-io/karmada/pull/7697) | Open，head `bf24e47ce3bd`；证书轮换实现和定向验证已完成 | 新 review、CI 变化或 maintainer scope 决策 |

## Last Run

- 2026-07-31：[PR #7791](https://github.com/karmada-io/karmada/pull/7791) 以 merge commit `35ee6092e499` 合并；PR checks 全绿，post-merge [Chart v1.36.1](https://github.com/karmada-io/karmada/actions/runs/30617396767/job/91113656882) 红灯是拉取 Docker Hub `common:2.41.0` 时的单 runner TCP timeout；[历史 run](https://github.com/karmada-io/karmada/actions/runs/30233127739) 有相同签名，归为 E2 external-registry flake / `NO_FIX`，与 test-only diff 无因果关系。
- 2026-07-31：完成 [Karmada Descheduler 专项调研](internship-reports/day38-karmada-descheduler-special-study.md)及固定 `1920×1080` 的 13 页 Style C HTML 稿：证明 Deployment-only 是窄 Story 1 MVP，对比 Kubernetes `v0.36.0`；逐页通过 1920×1080、1280×720、390×844 letterbox、键盘导航、溢出和 13 页打印检查。
- 2026-07-30：复核 [PR #7800 作者回应与新 head](internship-reports/day36-pr7800-waiting-store-deep-review.md#2026-07-30-作者回应与新-head-复核)：本地 full-store retained delta 约 17.98 MiB、`byGVKName` 约 3.19 MiB，race/scaling 通过；[closure reply](https://github.com/karmada-io/karmada/pull/7800#discussion_r3681520974) 已发布，GitHub 因账号权限拒绝 resolve，等待作者/maintainer 关闭 thread。
- 2026-07-30：完成 [PR #7662 selector / unschedulable 更新 review](internship-reports/day37-pr7662-selector-unschedulable-review.md)：新方案解决 assigned-but-unschedulable 信号缺失，但 `Available != Unschedulable`、selector 不等于 ownership、多组件不能直接映射标量 `dynamicScaleUp`，且 scheduler/Descheduler ownership 与 completion 仍未收敛；未发布 upstream 评论。
- 2026-07-29：完成 [Issue #7802 priority queue 确定性实验](internship-reports/day36-issue7802-priority-queue-experiment.md)：确认不完整候选集合可产生一次 low-first，反证“持续 drain 整批”，并拆开 readmission ordering 与 capacity/quota wake-up；[179-word queue-contract comment](https://github.com/karmada-io/karmada/issues/7802#issuecomment-5114587741) 已发布并逐字回读。

## Current Blockers

- #7662：estimator 的长期 `PodScheduled=False/Unschedulable` 能识别目标副本，但 public API 仍写 `PreserveAvailableReplicas`；selector ownership/rollout、多组件 placement、alpha gate、scheduler/Descheduler ownership 和 request completion 尚未定义。
- #7697、#7795 当前需要外部 review 或新证据；等待本身不产生代码动作，也不重复催促。
- `intern` 不含 Karmada 源码；任何源码验证必须在从最新 `upstream/master` 创建的独立 worktree 中进行。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- 周一前用 Day 38 HTML 稿试讲；先确认千问 workload 的真实 Kind、component/shard/checkpoint、GPU 属性和 replaceable replica 语义，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后先用 Day 37 的 10 副本反例和 Flink 多组件反例核对 signal、support matrix、owner 与 completion，再决定是否起草 upstream review。
- #7697 或 #7795 出现 review/CI 时，先回读 current head 和完整 thread，只处理与当前 diff 有因果关系的反馈。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
