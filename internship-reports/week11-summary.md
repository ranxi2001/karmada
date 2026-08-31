# Week 11 总结：多组件 PR 栈验证、Accepted Result 交付与 CI 归因

日期：2026-08-17 至 2026-08-21

证据截止：2026-08-21 23:59 CST

## 主管摘要

### 本月目标

| 目标 | 状态 |
| --- | --- |
| 完成 Karmada 多组件 scheduling 的 PR 栈和失败保护 | 进行中 |
| 让 accepted component result 能被 scheduler 写入并被 Work delivery 安全消费 | 进行中 |
| 对 PR CI failure 给出 source-backed 分类，不按失败 job 名修改产品逻辑 | 进行中 |

### 本周进展

| 工作项 | 结果、价值或剩余风险 | 状态 |
| --- | --- | --- |
| Accepted component result（Karmada PR #7833） | scheduler 持久化 per-cluster component result 的 PR 于 8 月 20 日 merge，建立后续 scale 判断的 authoritative snapshot | 已完成并 merge |
| Failure-safe rescheduling（Karmada PR #7841） | 新 PR 覆盖 accepted target、scale failure 和旧 Work 保留；expanded E2E 增加 scale-up、scale-down、quota/no-fit、taint 和 pinned target 场景 | 已完成当周提交；等待审核 |
| Karmada multi-component PR stack Review 与答辩 | 对 #7830 / #7835 / #7841 的 API、producer、planner 和 delivery 依赖做 code rationale；发现职责仍重叠，下一周需重构 | 已完成当周复核；继续收敛 |
| Karmada PR CI E2E failure scan | 区分 Kubernetes Job status version skew、API/etcd stall、Docker lifecycle 和 interrupted run，避免把共享基础设施失败归为 PR regression | 已完成 |

### 收获与分享

1. accepted result 只有在 scheduler 成功后写入，才能作为下一轮 source change 的比较基线；desired input 不能替代 accepted snapshot。
2. planner activation 与 failure protection 必须同时出现。只接入 delta estimator 而不保护旧 result，会在 `FitError` 时清空已接受状态。
3. E2E matrix 多个 spec 同时失败时，先找共同 control-plane signal；失败测试名称只说明最后观察点，不说明根因。

### 疑惑与问题

1. Karmada multi-component PR #7835 是否应保持 calculation-only、完全没有 production caller，并由 failure-safe PR #7841 同时接入 planner 和 failure protection？
2. Karmada accepted snapshot `TargetCluster.Components` 没有保存 component requirements，replicas 与 requirements 同时变化时应新增 provenance API，还是明确保持 unsupported？

### 下周计划

| 任务 | 可检查结果 |
| --- | --- |
| Karmada Issue #7492 PR responsibility refactor | 将 #7830/#7835/#7841 重构为 trigger、calculation、failure-safe delivery 三个唯一职责，删除重复或提前实现 |
| Karmada PR stack official CI follow-up | 只处理与 current diff 有因果关系的 lint/test failure，不因 pending job 重复 push |
| External review | 选择一个 Karmada code PR 和一个 skill / process PR 做 evidence-first Review，并发布用户确认的最小评论 |

## 先说人话

本周把多组件 scale 的“旧结果”真正变成 scheduler accepted state。PR #7833 merge 后，后续代码可以判断 `TM=4 -> 6`；但只有在容量计算失败时仍保留 `TM=4` result 和旧 Work，整个功能才不会把未接受配置提前下发。因此 planner 与 failure guard 的职责拆分成为下一周重点。

## 主要输出与验证

| 类型 | 数量 | 对象 |
| --- | ---: | --- |
| 本周新开 Karmada PR | 1 | failure-safe component rescheduling #7841 |
| 本周 merge 的本人 PR | 1 | accepted component result #7833 |
| PR 栈 | 4 | #7830 trigger / API、#7833 result、#7835 calculation、#7841 failure protection |
| E2E 场景扩展 | 5 | scale-up、scale-down、quota/no-fit、target taint、pinned target rejection |

验证覆盖 affected package race tests、base E2E compile 和多场景分支 tests。live multi-cluster E2E 仍主要依赖 upstream workflow；本地没有把 package compile 写成 live behavior proof。

## 失败、处理与边界

| 现象 | 分类 | 处理 |
| --- | --- | --- |
| PR #7833 E2E 出现失败 | 后续确认与 component result diff 无直接因果 | 保持实现不变，按日志和 affected path 分类；PR 最终 merge |
| #7841 早期 scope 含 API、interpreter、delivery 和 planner | Review surface 过大且职责重复 | 下一周按 trigger / calculation / failure protection 重构 |
| Job status fixture 与 API Server validation 不一致 | Kubernetes version / native controller output 影响 condition combinations | 使用真实 controller producer，不手工构造 API Server 会拒绝的状态 |

## 证据索引

- [Day 49：PR #7830 Review](day49-7830-review.md)
- [Day 50：Recent E2E failure scan](day50-karmada-recent-e2e-failure-scan-2026-08-17.md)
- [Day 51：PR CI failure classification](day51-karmada-recent-pr-ci-e2e-failures-2026-08-17.md)
- [Day 52：Multi-component PR design defense](day52-issue7492-multi-component-pr-design-defense.md)
