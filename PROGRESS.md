# PROGRESS.md

这个文件只保存未来几轮仍有用的短期状态。完整过程、日志和技术证据放在 `internship-reports/`，任务库存放在 `internship-reports/todo.md`，过期状态通过 Git 历史追溯。

## Goal

阶段目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

当前优先级：完成下周一 Karmada Descheduler 专项汇报准备；战略主线继续等待 #7621/#7662 的 signal、workload support、single writer 与 completion contract 收敛；同时维护 #7697 等已发布交付线。

## Current Snapshot

状态核对时间：2026-08-04。

| 主线 | 当前状态 | 下一触发条件 |
| --- | --- | --- |
| [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) | 已纠偏为整任务调度模型：`ResourceBinding` 是一级队列的 `SchedulingUnit`，Descheduler 只撤回 `Assigned + NotStarted + SchedulerUnschedulable`；五个代码合同为状态、证据、执行前 fence、接管完成、持久重试。A 为逐 GVK 试点，B 为 ResourceInterpreter 主线，C 为 member Pod 观察 fallback，D 仅借 ApplicationFailover 模式；[16 页 Style A 汇报稿](internship-reports/day39-karmada-descheduler-code-research-presentation.html)同步更新 | 周一前拿千问真实 YAML 核对生命周期、不可调度诊断、单目标 Placement、执行前 lock、接管回执和 cooldown，并用 HTML 试讲 |
| [PR #7662](https://github.com/karmada-io/karmada/pull/7662) | Open，head 仍为 `586f6fc3508e`；7 月 28 日会议收敛 offline scope，7 月 30 日 maintainer 提议 `GetComponents.selector -> estimator Unschedulable -> dynamicScaleUp` | `@zhy76` / `@RainbowMango` 回复或 proposal commit；再核对 API 集合、ownership、多组件和 completion contract |
| [PR #7697](https://github.com/karmada-io/karmada/pull/7697) | Open，head `bf24e47ce3bd`；证书轮换实现和定向验证已完成 | 新 review、CI 变化或 maintainer scope 决策 |

## Last Run

- 2026-08-04：纠偏 [Day 39 Descheduler 代码专项](internship-reports/day39-karmada-descheduler-code-contracts-and-options.md) 和 [整任务重入队图](internship-reports/day39-karmada-descheduler-code-contract-breaks.mmd)：不再从 Deployment 副本算法倒推通用设计，改为 Karmada Binding 一级队列、member Pod 二级队列和 whole-task requeue；源码确认默认 legacy queue、可选 priority queue、Job 资源/终态解释及 `GracefulEvictCluster/ClusterEviction` 机械原语。真实缺口收敛为生命周期、不可调度证据、pre-start fence、lifecycle-aware completion、持久 attempts/cooldown；普通 Job 事后 suspend 会删 active Pods，只能在无协作时声明 best-effort。HTML 同步纠偏并重新验收。
- 2026-08-03：新增 [build-technical-research-slides skill](.agents/skills/build-technical-research-slides/SKILL.md)，固化“证据冻结 → 连续叙事 → 术语首次解释 → Style A 实现 → 真实浏览器验收 → 版本替换与交付”流程，并补充插件逐项释义、等距实测与固定高度覆盖检查；`quick_validate.py` 与独立的 controller retry 调研前向测试均通过。
- 2026-08-03：最终保留 [15 页 Style A 无表格汇报稿](internship-reports/day38-karmada-descheduler-presentation-style-a.html)，删除已被替代的 Style C：以时间线、双轨、闭环和风险带替代表格，白底主强调色统一为绿色，第 7 页以活力橙区分 estimator 核验；补全 `GVK`、`Binding`、`Fresh`、`affinity`、`opt-in` 等术语的中文作用，第 13 页为 10 个 Kubernetes 插件增加逐项说明，第 15 页路线方块改为等间距。保留 API、模式、插件名和 #7662 未决边界；复用 Chromium build `1234`，通过 1280×720 逐页截图、1920×1080、390×844、键盘导航、无溢出和 15 页打印检查。
- 2026-07-31：[PR #7791](https://github.com/karmada-io/karmada/pull/7791) 以 merge commit `35ee6092e499` 合并；PR checks 全绿，post-merge [Chart v1.36.1](https://github.com/karmada-io/karmada/actions/runs/30617396767/job/91113656882) 红灯是拉取 Docker Hub `common:2.41.0` 时的单 runner TCP timeout；[历史 run](https://github.com/karmada-io/karmada/actions/runs/30233127739) 有相同签名，归为 E2 external-registry flake / `NO_FIX`，与 test-only diff 无因果关系。

## Current Blockers

- Day 39：尚缺千问真实 YAML 来证明 `NotStarted`、长期 `SchedulerUnschedulable`、单目标 Placement、执行前 admission lock 和新目标 Running/Completed 回执；无 fence 时只能承诺 best-effort。
- #7662：estimator 的长期 `PodScheduled=False/Unschedulable` 能识别目标副本，但 public API 仍写 `PreserveAvailableReplicas`；该 PR 的副本重调度 scope 与 Day 39 整任务重入队分开分析。
- #7697、#7795 当前需要外部 review 或新证据；等待本身不产生代码动作，也不重复催促。
- `intern` 不含 Karmada 源码；任何源码验证必须在从最新 `upstream/master` 创建的独立 worktree 中进行。

## Ruled Out

- 不把 #7662 的作者反提案或 maintainer `COMMENTED` review 写成最终 API 共识。
- 不把旧 Descheduler 的 Deployment whitelist、`readyReplicas` 和副本减法当成新任务模式必须适配的抽象。
- 不把 #7795 的 fixture-local 机制复现升级成原 CI terminal 根因证明。
- 不把 #7802 的受控 interleaving 写成线上频率证明，不用 per-namespace API 同时解决 wake-up 与 priority 两项合同。
- 不把学习记录、skills 或任务状态混入 upstream-facing topic branch，也不把 upstream 源码重新加入 `intern`。

## Next

- 周一前用 Day 39 HTML 稿试讲；拿千问真实 YAML 确认 `Queued/Assigned/Running/Terminal` 映射、`NotStarted + SchedulerUnschedulable` 证据、单目标 Placement、pre-start lock、handoff completion 和 cooldown，不把公开的 offline / long-running Pending story 自动写成具体产品合同。
- #7662 等 `@zhy76` / `@RainbowMango` 回复或 proposal commit；更新后先用 Day 37 的 10 副本反例和 Flink 多组件反例核对 signal、support matrix、owner 与 completion，再决定是否起草 upstream review。
- #7697 或 #7795 出现 review/CI 时，先回读 current head 和完整 thread，只处理与当前 diff 有因果关系的反馈。

## Stop Conditions

- 任何 upstream PR、issue、comment、reviewer request 或 maintainer mention 都必须先让用户确认 exact target/text。
- 某任务已有活跃 owner 修改同一问题时，不开重复 PR。
- 只能靠猜测才能继续时，停止并补源码、官方文档、日志或可复现实验。
- `PROGRESS.md` 超过 `AGENTS.md` 规定的滚动预算时，先删除/下沉旧状态，再添加新条目。
