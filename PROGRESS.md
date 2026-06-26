# PROGRESS.md

这个文件是给 Agent 工作循环用的短记忆，不是日报。每次开始工作先读这里，每次结束只更新关键状态，避免下一轮从零开始。

## Goal

当前主线：在 `intern` 分支建立 Karmada 项目实习学习仓库，先完成项目结构、核心概念、构建测试、社区流程和可贡献点的入门梳理，再逐步进入源码阅读、issue/PR triage、测试设计和小型 upstream 贡献。

## Last Run

- 2026-06-26：从 `master` 新建并切换到本地 `intern` 分支。
- 2026-06-26：参考 AgentCube 实习记录结构，开始为 Karmada 建立基础文件：根目录 `AGENTS.md`、`PROGRESS.md`、`internship-reports/README.md`、`internship-reports/todo.md`、`internship-reports/intern-glossary.md`，以及本地可复用 skill `.agents/skills/open-source-onboarding/`。
- 当前仓库 `origin` 是个人 fork：`https://github.com/ranxi2001/karmada`。尚未配置 `upstream` 远程。

## Current Blockers

- 尚未实际运行 `hack/local-up-karmada.sh`，因此本机 kind / Docker / kubeconfig / 多集群环境是否可用还没有验证。
- 尚未跑 `make test` 或 `make verify`，当前只建立学习和记录骨架。
- 尚未配置 `upstream` 远程，不能直接执行规范的 upstream sync 或基于 upstream `master` 创建官方 PR 分支。

## Ruled Out

- 不改写根 `README.md` 作为实习导航，避免污染上游项目介绍。
- 不把实习报告、中文学习笔记、本地 benchmark 原始数据或本地 skills 放到 upstream-facing topic branch。

## Next

- 先补 `upstream` 远程：`git remote add upstream https://github.com/karmada-io/karmada.git`，然后 `git fetch upstream master`。
- 阅读 Karmada 官方入口：`README.md`、`CONTRIBUTING.md`、`docs/README.md`、`docs/images/architecture.png`、`samples/nginx/README.md`。
- 做 Day 1 报告：跑通或预检 `hack/local-up-karmada.sh`，记录环境、失败命令、错误、绕过方式和最终结果。
- 做 Day 2 源码地图：按 API types、controller-manager、scheduler、agent、execution controller、work API、CLI、operator、e2e 测试梳理目录职责。
- 如果要找第一个贡献点，先从 docs、tests、good first issue、flaking test、CLI help 或小型 validation/test gap 入手。

## Stop Conditions

- 同一个本地环境问题连续失败 3 次，例如 kind 集群创建、Docker 镜像拉取、证书生成或 kubeconfig 上下文混乱，就停止硬调，记录 BLOCKED 并换路径。
- 如果某个 issue 已有人明确认领并正在修改同一问题，不开重复 PR，只做复现、测试、review 或文档补充。
- 如果只能基于猜测发社区评论，先停止，补源码证据、官方文档引用或本地验证结果后再讨论。
