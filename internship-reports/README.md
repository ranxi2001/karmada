# Karmada 实习报告

这个目录用于记录我在 Karmada 项目实习期间的学习、调研、源码阅读、实验、社区观察和问题。

记录方式以实习生视角为主：当天看了哪些文档，跑了哪些命令，理解了哪些概念，遇到哪些问题，以及下一步准备继续研究什么。

## 当前总目标

在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

这不是单纯的学习目标，而是社区贡献目标。后续日报和 TODO 优先围绕 upstream 可见证据组织：issue/PR 推进、CI 结果、review 响应、测试补强、会议提案和 mentor-facing 复盘。

## 日报列表

- [Day 1：Karmada #7598 依赖升级 follow-up 和 upstream PR](day1-karmada-7598-default-version-pr.md)
- [Day 2：Karmada 项目理解和源码地图](day2-karmada-project-understanding.md)
- [Day 3：证书管理相关 issue / PR 调研和任务整理](day3-certificate-management-task-triage.md)
- [Day 4：#7690 发布后的 branch / proposal gap 分析](day4-certificate-layout-issue-follow-up.md)
- [Day 5：#7643 FlinkDeployment memory 计算问题验证](day5-issue-7643-flink-memory-verification.md)
- [Day 6：证书轮换方案设计与实现准备](day6-certificate-rotation-design-implementation.md)
- [Day 7：`karmadactl init` 证书轮换社区会议提案](day7-certificate-rotation-community-proposal.md)
- [Day 8：PR #7697 后续说明图和 follow-up PR 拆分回复](day8-after-pr7697-follow-up-pr-split.md)
- [Day 9：社区 issue / PR 扫描与 PR #7697 CI 等待](day9-community-issue-pr-ci-watch.md)
- [Day 10：GitHub Actions Ubuntu runner 升级调研与候选 PR](day10-ci-ubuntu-runner-upgrade.md)
- [Day 11：Karmada CI Flake 专项统计](day11-ci-flake-statistics.md)（[#7719 Mermaid 源码](day11-flink-crd-flake-root-cause.mmd) / [SVG](day11-flink-crd-flake-root-cause.svg)）
- [Day 12：新 Issue / PR 可介入机会扫描](day12-new-issue-pr-opportunities.md)
- [Day 13：PR #7697 深度 Review 与持续合并维护](day13-pr7697-review-and-merge-maintenance.md)
- [Day 14：知名开源维护者 Agent Skills 调研](day14-expert-agent-skills-research.md)
- [Day 15：#7621 复杂工作负载安全重调度特性尽调](day15-issue-7621-safe-rescheduling-feature.md)（[#7662 本地中文 review 图](day15-pr7662-review-infographic.png) / [架构图 PNG](day15-issue-7621-current-proposed-flow.png) / [组件定位图 PNG](day15-pr7662-karmada-component-position.png) / [draw.io](day15-pr7662-karmada-component-position.drawio) / [Mermaid](day15-pr7662-karmada-component-position.mmd)）
- [Day 16：Karmada Upstream Issue / PR 简洁写作规范](day16-karmada-upstream-writing-style.md)
- [Day 17：PR #7764 E2E Root Cause Analysis Skill Review](day17-pr7764-e2e-root-cause-skill-review.md)（[fast-wait Mermaid](day17-fast-wait-signal-vs-claim.mmd) / [PNG](day17-fast-wait-signal-vs-claim.png)；[retry Mermaid](day17-retry-log-signal-vs-control-flow.mmd) / [PNG](day17-retry-log-signal-vs-control-flow.png)）
- [Day 18：drawio-skill v1.34.0 升级与版本同步缺陷](day18-drawio-skill-v1.34-upgrade.md)
- [Day 19：Codex CLI 模型流中断等待问题](day19-codex-cli-stream-stall-issue.md)
- [Day 20：PR #7623 Reconcile Cache 提交时机 Review](day20-pr7623-reconcile-cache-review.md)
- [Day 21：Day 15 绘图方式与清晰度分析](day21-drawio-authoring-and-clarity-analysis.md)
- [Day 22：2026-06-16 Karmada 社区会议重调度讨论文字稿](day22-karmada-meeting-2026-06-16-rescheduling-transcript.md)（[信息图 PNG](day22-karmada-meeting-rescheduling-infographic.png)）
- [Day 23：PR #7662 2026-06-30 社区会议全量转录与对齐](day23-pr7662-meeting-2026-06-30-transcript-and-alignment.md)
- [Day 24：Karmada 资源传播、部署与调度组件详解](day24-karmada-resource-propagation-scheduling-components.md)（[PNG](day24-karmada-resource-propagation-scheduling-components.png) / [SVG](day24-karmada-resource-propagation-scheduling-components.svg) / [draw.io](day24-karmada-resource-propagation-scheduling-components.drawio) / [Mermaid](day24-karmada-resource-propagation-scheduling-components.mmd)）
- [Day 25：2026-07-17 Karmada 社区 Issue / PR 扫描](day25-karmada-community-scan-2026-07-17.md)
- [Day 26：PR #7697 针对性证书轮转修复与 Review 收尾](day26-pr7697-targeted-certificate-rotation-fixes.md)
- [Day 27：可通过 PR 消除的 CI Flake 候选与 #7697 E2E RCA](day27-pr7697-e2e-flake-root-cause-analysis.md)（[v1.35 Mermaid](day27-pr7697-e2e-v135-etcd-io-stall-rca.mmd) / [PNG](day27-pr7697-e2e-v135-etcd-io-stall-rca.png)；[v1.36 Mermaid](day27-pr7697-e2e-v136-remedy-cache-race-rca.mmd) / [PNG](day27-pr7697-e2e-v136-remedy-cache-race-rca.png)；[migration Mermaid](day27-migration-resourcebinding-health-sync.mmd) / [PNG](day27-migration-resourcebinding-health-sync.png)）
- [Day 28：PR #6863 Scheduler Health Review](day28-pr6863-scheduler-health-review.md)（[Mermaid](day28-pr6863-late-health-capacity-flow.mmd) / [PNG](day28-pr6863-late-health-capacity-flow.png)）
- [Day 29：Issue #5070 与 PR #7662 的 Fresh / Full 语义调研](day29-issue5070-pr7662-fresh-rescheduling-research.md)（[Mermaid](day29-issue5070-pr7662-full-semantics.mmd) / [PNG](day29-issue5070-pr7662-full-semantics.png)）
- [Day 30：PR #7779 Cluster 删除保护方案与代码 Review](day30-pr7779-cluster-deletion-protection-review.md)（[已发布评论正文](day30-pr7779-review-comment.md) / [Mermaid](day30-pr7779-deletecollection-bypass.mmd) / [PNG](day30-pr7779-deletecollection-bypass.png)）
- [Day 30：PR #7662 维护者提出的 API 收敛方向](day30-pr7662-maintainer-api-direction.md)
- [Day 31：WorkloadRebalancer API 设计、分阶段开发与 #5070 第一阶段实现](day31-workload-rebalancer-api-development-plan.md)（[Mermaid](day31-workload-rebalancer-api-development-plan.mmd) / [PNG](day31-workload-rebalancer-api-development-plan.png)）
- [Day 32：PR #7791 设计边界与六行初版差异说明](day32-pr7791-scope-response-draft.md)（[泳道 Mermaid](day32-pr7791-scope-swimlane.mmd) / [PNG](day32-pr7791-scope-swimlane.png)）
- [Day 33：PR #7791 E2E 红灯分类与 `karmadactl top` Flake 修复](day33-pr7791-e2e-flake-root-cause-analysis.md)（[故障时序 Mermaid](day33-pr7791-v136-karmadactl-top-podmetrics-race.mmd) / [PNG](day33-pr7791-v136-karmadactl-top-podmetrics-race.png)；[E4 对齐 Mermaid](day33-karmadactl-top-flake-e4-alignment.mmd) / [PNG](day33-karmadactl-top-flake-e4-alignment.png)；[upstream draft](day33-karmadactl-top-flake-upstream-draft.md)）
- [实习任务 TODO](todo.md)
- [实习生术语扫盲](intern-glossary.md)

## 建议记录格式

每篇日报优先回答这些问题：

- `## 先说人话`：复杂 API、调度、controller、RCA、并发或生命周期分析，先用一个具体例子解释结论和当前能否行动，再进入字段与源码证据。
- 今天的目标是什么？
- 读了哪些官方文档、源码文件、issue 或 PR？
- 跑了哪些命令？成功和失败分别是什么？
- 学到了哪些 Karmada / Kubernetes / 多集群控制面的概念？
- 哪些结论有源码或测试证据？
- 哪些只是推测，需要后续验证？
- 下一步最小行动是什么？

日报正文和标题默认大部分使用中文；代码标识符、API 字段、命令、错误、上游标题、链接和短引用保留原文。通俗解释必须保持证据强度，不能把维护者建议写成共识、把待确认问题写成硬性要求，或把可能风险写成已经发生的故障。

遇到失败时不要只写“失败了”。至少记录命令、错误现象、初步原因、尝试过的方案、临时绕过方式和后续需要。

## 文档分工

- 长期协作规则：写到根目录 `AGENTS.md`。
- 短期循环状态：写到根目录 `PROGRESS.md`。
- 当前任务和优先级：写到 `todo.md`。
- 反复出现的术语：写到 `intern-glossary.md`。
- 当天学习、调试、源码阅读、社区分析：新建 `dayN-*.md`。
- 可复用工作流：沉淀到 `.agents/skills/<skill-name>/SKILL.md`。
