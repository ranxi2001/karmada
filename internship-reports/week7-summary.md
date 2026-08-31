# Week 7 总结：Scheduler Review、Remedy 修复合入与两项回归提交

日期：2026-07-20 至 2026-07-24

证据截止：2026-07-24 23:59 CST

## 主管摘要

### 本月目标

| 目标 | 状态 |
| --- | --- |
| 提高 Karmada scheduler 与 controller PR Review 的生产路径覆盖 | 进行中 |
| 将可复现的 E2E flake 根因转成小范围修复或回归测试 | 进行中 |
| 收敛 WorkloadRebalancer 完整重调度和副本保留的职责边界 | 进行中 |

### 本周进展

| 工作项 | 结果、价值或剩余风险 | 状态 |
| --- | --- | --- |
| RemedyActions 状态修复（Karmada PR #7777） | 状态变化触发 reconcile 的两文件修复于 7 月 21 日 merge，关闭 Remedy 删除后 status 可能不再收敛的问题 | 已完成并 merge |
| Scheduler health 与 Cluster 删除保护 PR Review（Karmada PR #6863、#7779） | 分别证明 health capacity 判断过晚会跳过健康 overflow cluster，以及 `DeleteCollection` 可绕过单对象 deletion protection；两条 inline comments 已发布 | 已完成；等待作者处理 |
| Full reschedule 与 affinity reset（Karmada Issue #5070、PR #7791） | 确认完整重调度还需重置 affinity cursor；提交 focused scheduler regression，保持 6 行生产改动边界 | 已完成当周提交；等待审核 |
| `karmadactl top` E2E fixture（Karmada PR #7795） | 将短生命周期 Pod 替换为稳定 fixture，避免指标采集前对象消失；PR 已提交 | 已完成当周提交；等待审核 |

### 收获与分享

1. Karmada scheduler 的 health capacity 必须在 cluster selection 前确定；在 assignment 阶段再置零会让前一层错误地消耗全部需求，健康 overflow cluster 没有机会被尝试。
2. Karmada aggregated API storage 覆盖 `Delete` 不等于覆盖 `DeleteCollection`。以后 Review Kubernetes REST storage 时按公开 verb 列表逐项检查，而不是只看 helper tests。
3. WorkloadRebalancer 的 `Full` 同时涉及副本分配和 affinity 搜索游标；以后看到“完整重调度”先列出需要丢弃的所有历史状态。

### 疑惑与问题

1. Karmada WorkloadRebalancer 的完整重调度是否应明确从第一个 `clusterAffinities` term 重新搜索？该决定影响 Issue #5070 和 Feature Proposal PR #7662 的验收范围。
2. `PreserveAvailableReplicas` 应由 scheduler 独占写 Binding，还是允许 controller 预先改写副本？双 writer 会扩大中间缩容窗口，需要维护者确定 authoritative state。

### 下周计划

| 任务 | 可检查结果 |
| --- | --- |
| ResourceDetector waiting store PR Review | 输出删除、重建、同名对象 identity 与 cleanup 的完整 Review 结论 |
| Priority queue 调度实验 | 用确定性输入证明 retry / re-entry 是否改变 queue ordering，并形成可答复的 Issue 评论 |
| Descheduler 专项调研 | 输出 Karmada Descheduler 与 Kubernetes Descheduler 的职责、触发和状态差异 |

## 先说人话

本周把三个“看起来只是小改动”的问题放回完整调用链验证：scheduler 的健康判断必须早于选集，Cluster 删除保护必须覆盖所有公开 delete verb，完整重调度必须同时忘掉旧副本和旧 affinity 书签。结果是一个已 merge 修复、两个已发布 PR Review 和两项新回归提交。

## 主要输出与证据

| 类型 | 数量 | 对象 |
| --- | ---: | --- |
| 本周新开 PR | 2 | Karmada scheduler affinity reset #7791、`karmadactl top` E2E fixture #7795 |
| 本周 merge 的本人 PR | 1 | Karmada RemedyActions 状态修复 #7777 |
| 已发布实质 PR Review | 2 | Karmada scheduler health #6863、Cluster deletion protection #7779 |
| Issue / Feature Proposal 深度分析 | 2 | Karmada Full reschedule #5070、WorkloadRebalancer #7662 |

关键验证包括 scheduler package tests、health overflow counterexample、Cluster storage tests，以及 PR #7777 的 red/green/reverse-patch evidence。PR #7791 和 #7795 在本周仍开放，不能写成已 merge。

## 失败、处理与边界

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| PR #6863 的局部 arithmetic test 通过 | 测试绕过 filter、selection 和 overflow tiering | 增加 production-path counterexample，证明 late health check 的实际后果 |
| PR #7791 初版职责过宽 | 把 API 演进和 cursor reset 混在一起 | 收敛为 scheduler regression，只验证 Full reset 行为 |
| PR #7795 CI 后续出现共享 chart registry failure | 与 fixture 行为无直接因果 | 单独分类基础设施失败，不通过扩 timeout 修改产品逻辑 |

## 证据索引

- [Day 28：Scheduler Health Review](day28-pr6863-scheduler-health-review.md)
- [Day 29：Full / Fresh semantics](day29-issue5070-pr7662-fresh-rescheduling-research.md)
- [Day 30：Cluster deletion protection Review](day30-pr7779-cluster-deletion-protection-review.md)
- [Day 31：WorkloadRebalancer API plan](day31-workload-rebalancer-api-development-plan.md)
- [Day 33：PR #7791 E2E flake RCA](day33-pr7791-e2e-flake-root-cause-analysis.md)
