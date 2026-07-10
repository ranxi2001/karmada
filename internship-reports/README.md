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
- [Day 11：Karmada CI Flake 专项统计](day11-ci-flake-statistics.md)
- [实习任务 TODO](todo.md)
- [实习生术语扫盲](intern-glossary.md)

## 建议记录格式

每篇日报优先回答这些问题：

- 今天的目标是什么？
- 读了哪些官方文档、源码文件、issue 或 PR？
- 跑了哪些命令？成功和失败分别是什么？
- 学到了哪些 Karmada / Kubernetes / 多集群控制面的概念？
- 哪些结论有源码或测试证据？
- 哪些只是推测，需要后续验证？
- 下一步最小行动是什么？

遇到失败时不要只写“失败了”。至少记录命令、错误现象、初步原因、尝试过的方案、临时绕过方式和后续需要。

## 文档分工

- 长期协作规则：写到根目录 `AGENTS.md`。
- 短期循环状态：写到根目录 `PROGRESS.md`。
- 当前任务和优先级：写到 `todo.md`。
- 反复出现的术语：写到 `intern-glossary.md`。
- 当天学习、调试、源码阅读、社区分析：新建 `dayN-*.md`。
- 可复用工作流：沉淀到 `.agents/skills/<skill-name>/SKILL.md`。
