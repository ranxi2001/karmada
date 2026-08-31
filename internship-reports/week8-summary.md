# Week 8 总结：Waiting Store Review、Queue 实验与 Descheduler 专项调研

日期：2026-07-27 至 2026-07-31

证据截止：2026-07-31 23:59 CST

## 主管摘要

### 本月目标

| 目标 | 状态 |
| --- | --- |
| 完成 Karmada scheduler / detector 状态所有权 Review | 进行中 |
| 明确 WorkloadRebalancer 与 Descheduler 的职责划分 | 进行中 |
| 让 Karmada scheduler regression 具备可审核的行为与测试证据 | 已完成当周提交；等待维护者审核 |

### 本周进展

| 工作项 | 结果、价值或剩余风险 | 状态 |
| --- | --- | --- |
| ResourceDetector waiting store PR Review（Karmada PR #7800） | 证明同名对象删除后 stale waiting entry 可错误匹配新对象，发布 identity、delete path 和最小修正建议 | 已完成；等待作者处理 |
| Priority queue re-entry（Karmada Issue #7802） | 用确定性实验说明 retry object 保留旧 sequence 后可能持续排在新对象前，发布 bounded observation 和建议 | 已完成；等待社区讨论 |
| Scheduler affinity reset（Karmada PR #7791） | 处理 scope 反馈和无关 CI failure，PR 于 7 月 31 日 merge | 已完成并 merge |
| Karmada Descheduler 专项 | 完成与 Kubernetes Descheduler 的分层对照和 Style A 汇报稿，明确它重新调度 Karmada Work 而不是直接驱逐 member Pod | 已完成第一版 |

### 收获与分享

1. waiting store 保存的是对象 identity，不只是 name。删除后不清理 stale entry，会让后续同名对象继承旧等待关系。
2. queue retry 是否公平不能只看 priority；Karmada workqueue 的 sequence 和 re-entry 时机会共同决定排序。
3. Karmada Descheduler 的输出仍是 Binding / Work 调度变化，member Pod eviction 只是后续执行结果。以后对比 Kubernetes 组件时先比较 control object 和 writer。

### 疑惑与问题

1. ResourceDetector 删除事件后应立即移除 waiting entry，还是保留一段时间等待对象重建？需要在恢复速度与 stale identity 风险之间明确选择。
2. WorkloadRebalancer、Descheduler 和 scheduler 都可能触发重新分配，项目应如何定义 request precedence、执行锁和完成回执？

### 下周计划

| 任务 | 可检查结果 |
| --- | --- |
| Descheduler source contract | 从源码恢复 selector、NotStarted、eviction 和 requeue 路径，修正汇报稿中不准确的 Pod 级表述 |
| Binding update coalescing Review | 对 Karmada PR #7810 的 timer / queue 行为输出 current-path counterexample 和最小测试要求 |
| WorkloadRebalancer API | 给出长期 Unschedulable 副本的 first-phase API 边界和 stop gates |

## 先说人话

本周主要回答“状态到底由谁保存、什么时候失效”。ResourceDetector 的 waiting entry 不能只按名称延续，queue 的旧 sequence 会影响重试顺序，Descheduler 也不是绕开 scheduler 直接搬 Pod。三个结论共同指向同一规则：先找 state owner，再决定 retry、cleanup 和 reschedule。

## 主要输出与证据

| 类型 | 数量 | 对象 |
| --- | ---: | --- |
| 本周 merge 的本人 PR | 1 | Karmada scheduler affinity reset #7791 |
| 已发布实质 PR Review | 1 | Karmada ResourceDetector waiting store #7800 |
| 已发布 Issue 评论 | 1 | Karmada priority queue #7802 |
| 技术汇报 | 1 | Karmada Descheduler Style A presentation |

PR #7800 的 Review 以 delete / recreate sequence 和 waiting store key 为证据；Issue #7802 的结论只覆盖确定性实验，没有外推为生产事故。Descheduler 报告保留了源码未验证项，后续需要继续纠偏。

## 失败、处理与边界

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| PR #7791 merge CI 出现 chart registry failure | shared registry / workflow failure 与 scheduler test 无关 | 不改 regression；等待 authoritative upstream rerun，最终 merge |
| Descheduler 初稿把对象写成 Pod | Karmada 实际调度单位是 ResourceBinding / Work | 下一周回到源码重建整任务 requeue 模型 |
| Issue #7802 只有局部 queue 实验 | 尚无生产事件或全局公平性测量 | 用 `observed in this setup` 表述，不写成 confirmed root cause |

## 证据索引

- [Day 35：Unavailable / Pending semantics](day35-pr7662-workload-unavailable-pending-research.md)
- [Day 36：ResourceDetector waiting store Review](day36-pr7800-waiting-store-deep-review.md)
- [Day 36：Priority queue experiment](day36-issue7802-priority-queue-experiment.md)
- [Day 37：Selector / unschedulable Review](day37-pr7662-selector-unschedulable-review.md)
- [Day 38：Karmada Descheduler study](day38-karmada-descheduler-special-study.md)
