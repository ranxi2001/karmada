# Week 10 总结：#7492 API 拆分、E2E 因果模型与四个 PR 提交

日期：2026-08-10 至 2026-08-14

证据截止：2026-08-14 23:59 CST

## 主管摘要

### 本月目标

| 目标 | 状态 |
| --- | --- |
| 为 Karmada 多组件 workload 建立可持久化 scheduling result 和 scale rescheduling 路径 | 进行中 |
| 将 E2E flake 报告从 spec 名称归因升级为跨用例因果时间线 | 进行中 |
| 推进已验证 fixture 和 cleanup 修复进入 upstream | 进行中 |

### 本周进展

| 工作项 | 结果、价值或剩余风险 | 状态 |
| --- | --- | --- |
| `karmadactl top` fixture（Karmada PR #7795） | 稳定 Pod fixture 修复于 8 月 10 日 merge；无关 registry / infrastructure failure 单独分类 | 已完成并 merge |
| Multi-component scheduling（Karmada Issue #7492、PR #7830、#7833、#7835） | 根据 maintainer Draft 拆出 result API、scheduler accepted result 和 scale estimation；三个 PR 已提交，完整 failure-safe path 尚未完成 | 已完成当周提交；继续实现 |
| EstimatorAssumption E2E isolation（Karmada Issue #7826、PR #7827） | 证明前一 spec 的 cluster/taint residue 可污染后一 spec，Issue 和 dedicated-cluster test PR 已提交 | 已完成当周提交；等待审核 |
| Legacy API compatibility | 真实 API Server 实验证明旧 v1alpha1 status write 可静默丢弃新 `spec.clusters[].components`，形成 read-modify-write protection 设计 | 已完成风险验证 |

### 收获与分享

1. 多组件 scheduling 的 request、accepted result 和 delivered Work 是三个状态层；只新增 API 字段不能证明 scale failure 时旧 Work 被保护。
2. E2E 失败不能按最终报错 spec 直接归因。需要记录 producer spec、cleanup、shared state、consumer spec 和 failed assertion 的时间顺序。
3. Kubernetes served version 的旧 client 写 status 时可能覆盖新字段。API 兼容 Review 必须包含真实 API Server 的 round-trip，而不只比较 Go struct。

### 疑惑与问题

1. Karmada component scheduling result 在新一轮调度失败时应保留最近一次 accepted snapshot，还是清空并阻止 Work 更新？
2. Karmada multi-component PR #7830/#7833/#7835 应按 API、producer、estimator 继续堆叠，还是先合并最小 result API 后再公开后续 PR？该决定影响 Review surface。

### 下周计划

| 任务 | 可检查结果 |
| --- | --- |
| Failure-safe rescheduling PR | 提交一个在 estimator failure 时保留 accepted result 和旧 Work 的独立 Karmada PR，并给出 package tests / E2E boundary |
| Karmada multi-component PR stack defense | 为 #7830/#7833/#7835 逐一写清唯一职责、依赖、non-goal 和 review entry point |
| CI failure classification | 归并近期 Karmada PR E2E failure，区分 product regression、version skew、shared control-plane collapse 和 interrupted run |

## 先说人话

本周从“给 Binding 加一个 Components 字段”推进到完整状态链：source 提出 desired components，scheduler 写 accepted result，binding controller 只有在新结果被接受后才应更新 Work。与此同时，E2E cleanup residue 的复现说明测试也有跨用例状态，需要同样明确 producer、owner 和 cleanup。

## 主要输出与证据

| 类型 | 数量 | 对象 |
| --- | ---: | --- |
| 本周新开 Karmada PR | 4 | E2E isolation #7827、component result #7830 / #7833、scale planning #7835 |
| 本周 merge 的本人 PR | 1 | `karmadactl top` fixture #7795 |
| 本周新开 Issue | 1 | EstimatorAssumption cleanup contamination #7826 |
| 主要设计报告 | 5 | Day 42-49 的 intake、API、state reproduction、compatibility 和 E2E isolation |

本地验证覆盖 API/codegen、webhook、scheduler core、binding controller 和 E2E package compile。PR #7827 后续使用 dedicated assumption cluster，避免仅靠清理顺序继续共享污染面。live multi-cluster E2E 尚未覆盖整个 #7492 stack。

## 失败、处理与边界

| 现象 | 根因或边界 | 处理 |
| --- | --- | --- |
| EstimatorAssumption 后一 spec 读取到旧 target | 前一 spec 的 cluster / taint cleanup 未完全隔离 | 新增 dedicated cluster fixture；Issue body按 timed causality 重写 |
| v1alpha1 status update 丢失 Components | 旧 served version 不认识新字段，status read-modify-write 覆盖 | 设计 legacy projection protection；不把 API field addition 写成 compatibility complete |
| #7492 早期 integration branch 过大 | API、estimator、delivery、failure semantics 同时变化 | 拆 PR 并保留 non-goal；未验证部分不写成已完成 |

## 证据索引

- [Day 42：#7492 intake](day42-issue7492-multi-component-scale-rescheduling-intake.md)
- [Day 43：Implementation plan](day43-issue5115-evolution-and-7492-implementation-plan.md)
- [Day 44：Component result API](day44-issue7492-component-scheduling-result-api-design.md)
- [Day 46：State handoff reproduction](day46-issue7492-mszacillo-state-reproduction.md)
- [Day 48：EstimatorAssumption isolation](day48-estimator-assumption-e2e-isolation-pr7827.md)
- [Day 49：PR #7830 compatibility](day49-issue7492-pr1-api-compat-pr7830.md)
