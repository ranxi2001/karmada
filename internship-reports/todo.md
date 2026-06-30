# 实习任务 TODO

更新时间：2026-06-30

这个文档用于管理 Karmada 实习期间的后续任务。日报记录每天做了什么，TODO 记录现在还要做什么、优先级是什么、做到哪里、卡在哪里。

## 使用规则

- 状态只保留当前结论：`TODO`、`DOING`、`BLOCKED`、`REVIEW`、`DONE`。
- 每个任务都要有可检查的产出，例如报告、脚本、benchmark 结果、PR、issue、测试日志或代码提交。
- 遇到卡点时记录失败命令、错误现象、初步原因和临时绕过方式。
- 涉及 Karmada 本地部署或 e2e 时，必须说明本机环境、kind/Docker/kubeconfig 状态、Karmada 控制面和 member clusters 是否真实启动。
- 任务完成后保留在“已完成里程碑”里，方便周报和 mentor 同步。
- 每次新的 Agent 工作循环先读根目录 [PROGRESS.md](../PROGRESS.md)，结束时只更新关键状态；不要把它写成长日报。

## 当前优先级

| 优先级 | 任务 | 状态 | 难度 | 成本 | 预计时间 | 产出/证据 | 下一步 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | 建立 Karmada 实习基础仓库结构 | DONE | 低 | 低 | 0.5 天 | `AGENTS.md`、`PROGRESS.md`、`internship-reports/`、`.agents/skills/open-source-onboarding/`、[Day 1 日报](day1-karmada-7598-default-version-pr.md) | 后续按 dayN 文件继续记录 |
| P0 | 迁移并 Karmada 化本地 skills | DONE | 中 | 低 | 0.5 天 | `.agents/skills/drawio-skill/`、`.agents/skills/karmada-pr-management/`、`.agents/skills/karmada-issue-discussion/`；4 个 skills 均通过 `quick_validate.py`，Karmada GitHub 脚本 smoke test 通过 | 后续画图、issue 分析、PR 准备分别使用这些 skills |
| P0 | 配置 upstream 远程和分支卫生规则 | DONE | 低 | 低 | 0.5 天 | `upstream=https://github.com/karmada-io/karmada.git`；upstream PR 分支从 `upstream/master` 创建；`intern` 只放学习记录 | 后续 upstream 改动继续使用独立 topic branch |
| P0 | 跑通或预检 Karmada Quick Start | TODO | 中 | 中 | 1 天 | Day 1 报告、命令日志、kubeconfig/context 记录 | 运行或拆解 `hack/local-up-karmada.sh`，记录 host cluster、control plane、member clusters |
| P0 | 梳理 Karmada 项目结构和核心组件 | DONE | 中 | 低 | 1 天 | [Day 2 项目理解](day2-karmada-project-understanding.md)、[PNG 架构图](day2-karmada-architecture.png)、[draw.io 架构图](day2-karmada-architecture.drawio) | Day 3 深追 `samples/nginx` 真实传播链路 |
| P0 | 梳理 ResourceTemplate -> PropagationPolicy -> ResourceBinding -> Work -> member cluster 数据流 | DONE | 中 | 低 | 1 天 | [Day 2 项目理解](day2-karmada-project-understanding.md) 中的 Mermaid 流程图和源码入口 | 继续读 `pkg/detector/`、`pkg/controllers/binding/`、`pkg/controllers/execution/` 的 reconcile 细节 |
| P0 | 建立 Karmada 术语表 | DOING | 低 | 低 | 0.5 天 | [intern-glossary.md](intern-glossary.md) | 随源码阅读补充 Cluster、Work、Binding、PropagationPolicy、OverridePolicy、interpreter、estimator 等术语 |
| P0 | 跑基础测试命令并记录成本 | TODO | 中 | 低 | 0.5-1 天 | `make test` / 聚焦 `go test` 结果 | 先跑轻量目标，再决定是否跑完整 `make test` 和 `make verify` |
| P0 | 建立提交前 lint 检查习惯 | DOING | 低 | 低 | 0.5 天 | [Day 3 CI lint 失败复盘](day3-certificate-management-task-triage.md#ci-lint-失败复盘) | 新增 Go 包或导出 API 后，提交前必须跑 `golangci-lint run ./pkg/karmadactl/cmdinit/...`，不要只跑 `go test` |
| P1 | 分析 Karmada 社区 issue / PR 动态 | DONE | 中 | 低 | 0.5-1 天 | [Day 1 日报](day1-karmada-7598-default-version-pr.md)；分析 #7598 并提交 upstream PR #7666 | 继续观察 #7666 CI 和 review |
| P1 | 调研证书管理相关 issue / PR 并拆任务 | DONE | 中 | 低 | 0.5 天 | [Day 3 证书管理任务整理](day3-certificate-management-task-triage.md) | 优先跟进 #6051 Helm 证书命名规范；先做差距表，不直接改代码 |
| P1 | 准备证书 layout upstream 提案 | DONE | 中 | 低 | 0.5 天 | [Upstream issue #7690](https://github.com/karmada-io/karmada/issues/7690)；[Day 3 发布记录](day3-certificate-management-task-triage.md#upstream-issue-发布记录) | 等 maintainer review；回复前不急着开 PR |
| P1 | 准备 `karmadactl init` split Secret layout PR | REVIEW | 中 | 中 | 0.5-1 天 | [Day 3 PR 审阅准备](day3-certificate-management-task-triage.md#pr-审阅准备)；fork push CI 已通过 | 先走 issue/comment 设计 review；获得方向后再决定是否开 PR、接续 #6788 或缩小 PR |
| P1 | 对照 #6051 梳理 Helm 证书 Secret / volume / mount path 差距 | TODO | 中 | 低 | 0.5-1 天 | Helm 证书命名差距表、英文 issue 评论草稿 | 阅读 `charts/karmada/templates/`、`charts/karmada/values.yaml` 和 #6051 Task two 示例 |
| P1 | 评估是否协助 #6788 split secret layout PR | TODO | 中 | 低 | 0.5 天 | PR 状态分析、冲突/测试记录或 review 评论草稿 | 拉取 #6788 diff，先确认作者和 reviewer 是否需要协助 |
| P1 | 深读 scheduler 调度逻辑 | TODO | 高 | 低 | 1-2 天 | scheduler 源码笔记、测试矩阵 | 阅读 `pkg/scheduler/`、调度 policy、spread/weight/affinity 相关代码和单测 |
| P1 | 深读 controller-manager 传播链路 | TODO | 高 | 低 | 1-2 天 | controller 源码笔记、reconcile 流程图 | 阅读 policy、binding、execution、status、cluster controller |
| P1 | 深读 karmadactl CLI | TODO | 中 | 低 | 1 天 | CLI 命令地图、潜在 docs/test gap | 阅读 `pkg/karmadactl/` 和 `cmd/karmadactl/`，找帮助文档或测试改进点 |
| P2 | 设计 Karmada 入门 benchmark / smoke test 记录格式 | TODO | 中 | 低 | 0.5 天 | smoke test schema | 记录部署耗时、propagation 耗时、member cluster 状态、清理结果 |

## 第一周建议节奏

1. Day 1：官方 README 和 Quick Start，尽量跑通本地 Karmada。
2. Day 2：项目结构和技术栈，画组件目录地图。
3. Day 3：samples/nginx 传播链路，从用户 YAML 追到 member cluster 资源。
4. Day 4：源码深读 controller-manager 的 policy/binding/execution 关键控制器。
5. Day 5：源码深读 scheduler 和 placement policy。
6. Day 6：社区 issue/PR triage，找一个低风险贡献点。
7. Day 7：周总结，整理概念、证据、卡点、下一周目标。

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

## 已完成里程碑

| 事项 | 产出 |
| --- | --- |
| 创建本地 `intern` 分支 | 当前工作分支为 `intern` |
| 建立 Karmada 本地 skills 基础 | `open-source-onboarding`、`drawio-skill`、`karmada-pr-management`、`karmada-issue-discussion` |
| 完成第一个 upstream PR 练习 | 分析 #7598 follow-up，提交 PR #7666：同步安装入口默认 Kubernetes / etcd 版本 |
| 完成 Day 2 Karmada 项目理解 | 输出 [Day 2 项目理解](day2-karmada-project-understanding.md)，用 Mermaid 梳理控制面、资源传播链路和源码目录地图，并生成 [PNG 架构图](day2-karmada-architecture.png) 与 [draw.io 架构图](day2-karmada-architecture.drawio) |
| 完成 Day 3 证书管理任务整理 | 输出 [Day 3 证书管理任务整理](day3-certificate-management-task-triage.md)，确认 #6051 Helm 证书命名规范是当前最适合继续拆解的任务，并补充 `karmadactl init` split Secret layout 的 upstream issue 草稿 |
| 发布证书 layout upstream 提案 | 新建 [karmada-io/karmada#7690](https://github.com/karmada-io/karmada/issues/7690)，请求 `@zhzhuang-zju` review plan-based split certificate Secret layout 方向 |
