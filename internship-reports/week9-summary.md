# Week 9 总结：Descheduler 代码契约与 Binding 更新 Review

日期：2026-08-03 至 2026-08-07

证据截止：2026-08-07 23:59 CST

## 主管摘要

### 本月目标

| 目标 | 状态 |
| --- | --- |
| 完成 Karmada Descheduler 的代码级职责和可实施方案研究 | 已完成第一版 |
| 识别 scheduler 时间窗口补丁的实际保证和失败路径 | 已完成本周 Review |
| 为长期 Unschedulable 副本重调度定义可审查 API 边界 | 进行中 |

### 本周进展

| 工作项 | 结果、价值或剩余风险 | 状态 |
| --- | --- | --- |
| Karmada Descheduler source study | 修正“直接调 Pod”的误解，确认 current implementation 对 NotStarted Binding 做整任务重新入队，并比较整任务、部分副本和显式 request 三条路线 | 已完成 |
| Binding update coalescing PR Review（Karmada PR #7810） | 证明 `AddAfter` 是 fixed-window delay，不是 trailing-edge debounce；其他 producer 可提前入队，ownership change 也不会取消旧 key，公开 Review 已发布 | 已完成；等待作者处理 |
| Unschedulable replica rescheduling（Karmada PR #7662） | 定义 V1 只处理 Deployment、长期 Unschedulable 和 estimator 可证 capacity 的 first phase，并列出 10 个 stop gates | 已完成设计基准；等待维护者方向 |

### 收获与分享

1. 时间窗口只能降低中间态被处理的概率，不能替代跨对象 transaction。以后看到 debounce / coalescing 参数时，先检查所有 enqueue producer 和 leader restart。
2. Karmada Descheduler 当前按整个 Binding 重新进入 scheduler，不具备只迁移单个 unavailable replica 的内建 operation state。
3. API 设计的 stop gate 必须早于实现：source freshness、request ID、ack、pinned target 和 Descheduler precedence 未定义时，不应先扩 controller 职责。

### 疑惑与问题

1. Karmada PR #7810 应收窄为 best-effort fixed-window coalescing，还是实现真正的 per-key trailing-edge debounce？两者都不能单独关闭原子性问题。
2. 长期 Unschedulable 副本应由 WorkloadRebalancer、Descheduler 还是独立 operation owner 驱动？该选择决定状态、重试和取消语义。

### 下周计划

| 任务 | 可检查结果 |
| --- | --- |
| Multi-component scheduling intake | 恢复 Karmada Issue #7492 的 accepted design、缺失 result API 和失败状态机，并等待维护者资料后再实现 |
| E2E flake cleanup | 完成 `karmadactl top` fixture PR 的 CI 分类并推动 merge，不用全局 timeout 掩盖 |
| Component result API | 若 maintainer Draft 明确，输出 API、producer、Work delivery 和 failure protection 的分 PR 计划 |

## 先说人话

本周把两个容易被 timer 名称误导的问题说清：Descheduler 重新提交的是整份 Karmada 调度任务，PR #7810 的 delay 只是一个从首次更新开始计时的窗口。它们都没有提供跨对象原子提交，因此后续设计必须显式定义 accepted state 和 failure owner。

## 主要输出与验证

| 输出 | 证据 | 边界 |
| --- | --- | --- |
| Descheduler 16 页汇报稿 | source path、Mermaid flow、Style A HTML | 没有真实 YAML 和 live cluster 行为 |
| PR #7810 Review | delayed-key race、multiple producer、priority queue 和 metric audit | published root comment；不是 maintainer decision |
| PR #7662 API plan | V1/V2 boundary、10 stop gates、request/ack questions | proposal open；尚未批准 |

PR #7810 的作者实验能证明 legacy queue + stable leader + no fast-path producer 时，窗口通常读到最终 Binding；不能证明任意 GitOps backlog、ownership change 或 leader restart 下保持同一行为。

## 失败、处理与边界

| 失败或误判 | 处理 |
| --- | --- |
| Descheduler 初稿沿用 Pod-level 语言 | 改为 Binding / Work 整任务模型，并明确 member Pod 是 downstream result |
| 把 `AddAfter(D)` 理解为每次更新重置 deadline | 对照 client-go delaying queue，确认已有 key 只保留更早 deadline |
| 计划用 timer 解决跨对象更新 | 保留 staged barrier / revision contract 作为强保证方案，不把 best-effort window 写成原子性 |

## 证据索引

- [Day 39：Descheduler code contracts](day39-karmada-descheduler-code-contracts-and-options.md)
- [Day 40：Unschedulable replica API plan](day40-pr7662-unschedulable-replica-rescheduling-api-plan.md)
- [Day 41：Binding update coalescing Review](day41-pr7810-binding-update-coalescing-review.md)
