# PROGRESS.md

这个文件是给 Agent 工作循环用的短记忆，不是日报。每次开始工作先读这里，每次结束只更新关键状态，避免下一轮从零开始。

## Goal

当前主线：在 `intern` 分支建立 Karmada 项目实习学习仓库，先完成项目结构、核心概念、构建测试、社区流程和可贡献点的入门梳理，再逐步进入源码阅读、issue/PR triage、测试设计和小型 upstream 贡献。

## Last Run

- 2026-06-30：分析 fork push CI 结果。`feature/cert-manager-layout` commit `651cbec29` 的 push CI 已全部结束，只有 `CI Workflow / lint` 失败；compile、unit test、codegen、3 个 e2e、CLI / Chart / Operator Kubernetes 矩阵均通过或 skipped。失败根因是新增 `pkg/karmadactl/cmdinit/certmanager` 包未满足 `.golangci.yml` 静态检查：导出符号缺 Go doc、Secret 名称常量触发 gosec G101 误报、测试循环可改 `slices.Contains`、`legacyCertificateNames` 参数未使用。已把复盘和提交前 lint checklist 写入 Day 3，并在 TODO 加入 P0 lint 习惯项。
- 2026-06-29：完成 Day 3 证书管理方向任务整理。新增 `internship-reports/day3-certificate-management-task-triage.md`，梳理 community#69、#6091、#6269、#6670、#6788、#6553 和 #6051 的关系；结论是优先跟进 #6051 中 Helm 证书 Secret / volume / mount path naming convention 的 `help wanted` 空位。随后按“不要为了改代码而改代码，先抽象证书管理层”的反馈，追加了批量系统证书替换分发的初步设计，包括证书身份、layout plan、Secret plan、组件 kubeconfig 分发和验证计划，并加入 Mermaid 前后对比图说明抽象层引入后的变化。同步更新 `internship-reports/README.md` 和 `internship-reports/todo.md`。
- 2026-06-29：按用户反馈修整 `internship-reports/day2-karmada-architecture.drawio`。改为真正用 draw.io CLI 导出并视觉检查，入口流程调整为 User -> Karmada API Server，Admission Webhook 画成 API Server 的 admission 调用；移除长边标签，用编号 1-6 + 底部图例表达流程；重新导出 `day2-karmada-architecture.png`、`day2-karmada-architecture.drawio.png`、`day2-karmada-architecture.drawio.svg`，`validate.py` 结果为 `0 error(s), 0 warning(s)`。当前 Day 2 相关文件已暂存，尚未 commit/push，等待用户确认图。
- 2026-06-29：完成 Day 2 Karmada 项目理解。新增 `internship-reports/day2-karmada-project-understanding.md`，面向首次接触 Karmada、仅有基础 K8s 概念的读者，用 Mermaid 梳理控制面、ResourceTemplate -> PropagationPolicy -> ResourceBinding -> Work -> member cluster 传播链路、nginx 样例和源码目录地图；新增 `internship-reports/day2-karmada-architecture.drawio` 作为可编辑架构图源文件，并导出 `internship-reports/day2-karmada-architecture.png`、`internship-reports/day2-karmada-architecture.drawio.png`、`internship-reports/day2-karmada-architecture.drawio.svg`。
- 2026-06-28：处理 GitHub fork sync 提示。`origin/master` 曾比 `upstream/master` 多 1 个 personal fork PR #1 merge commit `410202123`，同时落后 upstream 3 个 commit；已按 fork `master` 镜像规则把本地/远端 `master` force-with-lease 重置到 `upstream/master` `56d5d87ec`。当前 `origin/master` 与 `upstream/master` 一致，`intern` 保留实习记录不受影响。
- 2026-06-28：按 mentor 反馈同步修正 Karmada CI 验证规则：以后不再向个人 fork 仓库提 PR 来跑 CI。Karmada 与 AgentCube 不同，`.github/workflows/ci.yml` 已经明确支持 `push` 到 fork 分支触发 CI（排除 `dependabot/**`），所以预提交 upstream 前直接 push topic/validation branch 到 `origin` 并查看 commit SHA Actions/checks；如失败先分类为代码问题、fork 环境差异、缺少 tag/history、CI flake 或 upstream-only gate。已更新 `AGENTS.md` 和 `.agents/skills/karmada-pr-management/SKILL.md`。
- 2026-06-26：从 `master` 新建并切换到本地 `intern` 分支。
- 2026-06-26：参考 AgentCube 实习记录结构，开始为 Karmada 建立基础文件：根目录 `AGENTS.md`、`PROGRESS.md`、`internship-reports/README.md`、`internship-reports/todo.md`、`internship-reports/intern-glossary.md`，以及本地可复用 skill `.agents/skills/open-source-onboarding/`。
- 2026-06-26：从 AgentCube 迁移 3 个本地 skills 到 Karmada：`.agents/skills/drawio-skill/` 保留通用绘图能力；`agentcube-pr-management` 改造为 `.agents/skills/karmada-pr-management/`，默认 repo 为 `karmada-io/karmada`、基线分支为 `upstream/master`、测试命令按 Karmada `make test` / `make verify` / `hack/update-*`；`agentcube-issue-discussion` 改造为 `.agents/skills/karmada-issue-discussion/`，脚本默认 repo 改为 `karmada-io/karmada`。4 个本地 skills 已通过 `quick_validate.py`。
- 2026-06-26：配置 `upstream=https://github.com/karmada-io/karmada.git`，从 `upstream/master` 创建 topic branch `test/update-default-control-plane-images`，完成 #7598 follow-up：同步 Helm chart、`karmadactl init`、`karmada-operator`、raw deploy manifest 和 `hack/deploy-karmada.sh` 的默认 Kubernetes / etcd 版本，并提交 upstream PR #7666。

## Current Blockers

- `feature/cert-manager-layout` fork push CI 目前只有 lint 失败，修复前不要开 upstream PR；下一轮先修 `certmanager` 包 lint，再 force-with-lease 推 fork。
- 尚未实际运行 `hack/local-up-karmada.sh`，因此本机 kind / Docker / kubeconfig / 多集群环境是否可用还没有验证。
- 尚未跑完整 `make test` 或 `make verify`。本次 PR 只跑了相关范围的 `go test`、`hack/verify-command-line-flags.sh`、Helm lint、脚本语法和 YAML 解析。
- upstream PR #7666 的 GitHub Actions 仍需继续观察。
- GitHub CLI 当前未登录，匿名 GitHub API broad search 已遇到 rate limit；后续继续做 issue/PR 批量检索时应配置 `GH_TOKEN` 或改用浏览器页面。
- 当前 Windows 电脑上 draw.io 已安装但未加入 PATH：`drawio` / `draw.io` 命令不可用，系统级路径 `C:\Program Files\draw.io\draw.io.exe` 也不存在；实际可用路径是 `C:\Users\ranxi\AppData\Local\Programs\draw.io\draw.io.exe`，版本 `30.2.6`。这个路径只适用于当前 Windows 机器；macOS 或其他机器仍按 drawio-skill 的正常探测顺序处理。

## Ruled Out

- 不改写根 `README.md` 作为实习导航，避免污染上游项目介绍。
- 不把实习报告、中文学习笔记、本地 benchmark 原始数据或本地 skills 放到 upstream-facing topic branch。

## Next

- 修复 `feature/cert-manager-layout` 的 lint：导出符号补注释或降为未导出、处理 gosec G101 误报、删除未用参数、测试 helper 改 `slices.Contains`；通过 `golangci-lint run ./pkg/karmadactl/cmdinit/...` 后再推 fork CI。
- 继续观察 upstream PR #7666 的 CI 和 review；如果失败，先区分代码问题、环境抖动和 CI 环境差异。
- 阅读 Karmada 官方入口：`README.md`、`CONTRIBUTING.md`、`docs/README.md`、`docs/images/architecture.png`、`samples/nginx/README.md`。
- 补 Quick Start 预检报告：跑通或拆解 `hack/local-up-karmada.sh`，记录环境、失败命令、错误、绕过方式和最终结果。
- Day 3 深追 `samples/nginx` 传播链路：从 `Deployment` + `PropagationPolicy` 到 `ResourceBinding`、`Work` 和 member cluster manifest，重点读 `pkg/detector/`、`pkg/controllers/binding/`、`pkg/controllers/execution/`。
- 证书方向下一步：先把证书管理层设计收敛成更小的代码边界，避免在部署代码里散落 `split` 判断；再根据 mentor 方向决定是继续 `karmadactl init` split layout，还是回到 #6051 Helm 证书 Secret / volume / mount path 差距表。
- 如果要找第一个贡献点，先从 docs、tests、good first issue、flaking test、CLI help 或小型 validation/test gap 入手。
- 需要绘制 Karmada 架构图、传播链路图或调度流程图时，使用 `.agents/skills/drawio-skill/`。
- 分析 Karmada issue/PR 或准备 upstream PR 时，优先使用 `.agents/skills/karmada-issue-discussion/` 和 `.agents/skills/karmada-pr-management/`。

## Stop Conditions

- 同一个本地环境问题连续失败 3 次，例如 kind 集群创建、Docker 镜像拉取、证书生成或 kubeconfig 上下文混乱，就停止硬调，记录 BLOCKED 并换路径。
- 如果某个 issue 已有人明确认领并正在修改同一问题，不开重复 PR，只做复现、测试、review 或文档补充。
- 如果只能基于猜测发社区评论，先停止，补源码证据、官方文档引用或本地验证结果后再讨论。
