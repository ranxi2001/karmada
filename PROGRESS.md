# PROGRESS.md

这个文件是给 Agent 工作循环用的短记忆，不是日报。每次开始工作先读这里，每次结束只更新关键状态，避免下一轮从零开始。

## Goal

当前主线：在 `intern` 分支建立 Karmada 项目实习学习仓库，先完成项目结构、核心概念、构建测试、社区流程和可贡献点的入门梳理，再逐步进入源码阅读、issue/PR triage、测试设计和小型 upstream 贡献。

## Last Run

- 2026-06-28：按 mentor 反馈同步修正 Karmada CI 验证规则：以后不再向个人 fork 仓库提 PR 来跑 CI。Karmada 与 AgentCube 不同，`.github/workflows/ci.yml` 已经明确支持 `push` 到 fork 分支触发 CI（排除 `dependabot/**`），所以预提交 upstream 前直接 push topic/validation branch 到 `origin` 并查看 commit SHA Actions/checks；如失败先分类为代码问题、fork 环境差异、缺少 tag/history、CI flake 或 upstream-only gate。已更新 `AGENTS.md` 和 `.agents/skills/karmada-pr-management/SKILL.md`。
- 2026-06-26：从 `master` 新建并切换到本地 `intern` 分支。
- 2026-06-26：参考 AgentCube 实习记录结构，开始为 Karmada 建立基础文件：根目录 `AGENTS.md`、`PROGRESS.md`、`internship-reports/README.md`、`internship-reports/todo.md`、`internship-reports/intern-glossary.md`，以及本地可复用 skill `.agents/skills/open-source-onboarding/`。
- 2026-06-26：从 AgentCube 迁移 3 个本地 skills 到 Karmada：`.agents/skills/drawio-skill/` 保留通用绘图能力；`agentcube-pr-management` 改造为 `.agents/skills/karmada-pr-management/`，默认 repo 为 `karmada-io/karmada`、基线分支为 `upstream/master`、测试命令按 Karmada `make test` / `make verify` / `hack/update-*`；`agentcube-issue-discussion` 改造为 `.agents/skills/karmada-issue-discussion/`，脚本默认 repo 改为 `karmada-io/karmada`。4 个本地 skills 已通过 `quick_validate.py`。
- 2026-06-26：配置 `upstream=https://github.com/karmada-io/karmada.git`，从 `upstream/master` 创建 topic branch `test/update-default-control-plane-images`，完成 #7598 follow-up：同步 Helm chart、`karmadactl init`、`karmada-operator`、raw deploy manifest 和 `hack/deploy-karmada.sh` 的默认 Kubernetes / etcd 版本，并提交 upstream PR #7666。

## Current Blockers

- 尚未实际运行 `hack/local-up-karmada.sh`，因此本机 kind / Docker / kubeconfig / 多集群环境是否可用还没有验证。
- 尚未跑完整 `make test` 或 `make verify`。本次 PR 只跑了相关范围的 `go test`、`hack/verify-command-line-flags.sh`、Helm lint、脚本语法和 YAML 解析。
- upstream PR #7666 的 GitHub Actions 仍需继续观察。

## Ruled Out

- 不改写根 `README.md` 作为实习导航，避免污染上游项目介绍。
- 不把实习报告、中文学习笔记、本地 benchmark 原始数据或本地 skills 放到 upstream-facing topic branch。

## Next

- 继续观察 upstream PR #7666 的 CI 和 review；如果失败，先区分代码问题、环境抖动和 CI 环境差异。
- 阅读 Karmada 官方入口：`README.md`、`CONTRIBUTING.md`、`docs/README.md`、`docs/images/architecture.png`、`samples/nginx/README.md`。
- 补 Quick Start 预检报告：跑通或拆解 `hack/local-up-karmada.sh`，记录环境、失败命令、错误、绕过方式和最终结果。
- 做 Day 2 源码地图：按 API types、controller-manager、scheduler、agent、execution controller、work API、CLI、operator、e2e 测试梳理目录职责。
- 如果要找第一个贡献点，先从 docs、tests、good first issue、flaking test、CLI help 或小型 validation/test gap 入手。
- 需要绘制 Karmada 架构图、传播链路图或调度流程图时，使用 `.agents/skills/drawio-skill/`。
- 分析 Karmada issue/PR 或准备 upstream PR 时，优先使用 `.agents/skills/karmada-issue-discussion/` 和 `.agents/skills/karmada-pr-management/`。

## Stop Conditions

- 同一个本地环境问题连续失败 3 次，例如 kind 集群创建、Docker 镜像拉取、证书生成或 kubeconfig 上下文混乱，就停止硬调，记录 BLOCKED 并换路径。
- 如果某个 issue 已有人明确认领并正在修改同一问题，不开重复 PR，只做复现、测试、review 或文档补充。
- 如果只能基于猜测发社区评论，先停止，补源码证据、官方文档引用或本地验证结果后再讨论。
