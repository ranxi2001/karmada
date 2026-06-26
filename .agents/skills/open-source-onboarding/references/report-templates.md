# Report Templates

Use these templates when creating a new onboarding workspace. Adapt names and sections to the repository.

## PROGRESS.md

```markdown
# PROGRESS.md

这个文件是给 Agent 工作循环用的短记忆，不是日报。每次开始工作先读这里，每次结束只更新关键状态，避免下一轮从零开始。

## Goal

当前主线：

## Last Run

-

## Current Blockers

-

## Ruled Out

-

## Next

-

## Stop Conditions

-
```

## internship-reports/README.md

```markdown
# <Project> 实习报告

这个目录用于记录我在 <Project> 项目实习期间的学习、调研、源码阅读、实验、社区观察和问题。

## 日报列表

- [实习任务 TODO](todo.md)
- [实习生术语扫盲](intern-glossary.md)

## 建议记录格式

- 今天的目标是什么？
- 读了哪些官方文档、源码文件、issue 或 PR？
- 跑了哪些命令？成功和失败分别是什么？
- 哪些结论有源码或测试证据？
- 下一步最小行动是什么？
```

## internship-reports/todo.md

````markdown
# 实习任务 TODO

更新时间：YYYY-MM-DD

## 使用规则

- 状态只保留当前结论：`TODO`、`DOING`、`BLOCKED`、`REVIEW`、`DONE`。
- 每个任务都要有可检查的产出。
- 遇到卡点时记录失败命令、错误现象、初步原因和临时绕过方式。

## 当前优先级

| 优先级 | 任务 | 状态 | 难度 | 成本 | 预计时间 | 产出/证据 | 下一步 |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 卡点记录模板

```text
任务：
日期：
环境：
失败命令/步骤：
错误现象：
初步原因：
已尝试方案：
临时绕过方式：
后续需要：
```
````

## Daily Report

````markdown
# Day N：<主题>

日期：YYYY-MM-DD

## 今日目标

-

## 阅读材料

-

## 操作记录

```bash
<commands>
```

## 关键理解

-

> 注释：

## 问题与卡点

-

## 证据与结论

-

## 下一步

-
````
