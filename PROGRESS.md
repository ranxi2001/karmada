# PROGRESS.md

这个文件是给 Agent 工作循环用的短记忆，不是日报。每次开始工作先读这里，每次结束只更新关键状态，避免下一轮从零开始。

## Goal

当前主线：在 `intern` 分支建立 Karmada 项目实习学习仓库，先完成项目结构、核心概念、构建测试、社区流程和可贡献点的入门梳理，再逐步进入源码阅读、issue/PR triage、测试设计和小型 upstream 贡献。

## Last Run

- 2026-06-30：按用户要求把 #7643 可直接复制的 upstream 评论草稿追加到 `internship-reports/day5-issue-7643-flink-memory-verification.md`，包含 Mermaid 对比图、函数级验证输出、默认 FlinkDeployment customization 路径输出和当前结论。同步更新 `AGENTS.md`：以后准备 upstream comment、PR 描述、review 文案、Mermaid 解释等可复用长文本时，必须写入报告或草稿文件，不要只在终端/chat 输出里交付。
- 2026-06-30：跟进 upstream issue #7643，按 maintainer 要求做函数级和运行路径验证。使用独立 worktree `/home/karmada-issue-7643` 基于 `upstream/master@ffbade988` 添加临时测试，确认 `kube.getResourceQuantity("100m")` 返回 Lua number `0.1`，但 Lua -> Go JSON 转换后是 `resource.Quantity("100m")`；默认 FlinkDeployment thirdparty interpreter 输出 JM/TM memory 均为 `"100m"`，`helper.CalculateResourceUsage()` 汇总为 `{"cpu":"300m","memory":"200m"}`。结论写入 `internship-reports/day5-issue-7643-flink-memory-verification.md`：当前 upstream master 未复现 issue 描述的 “100m 变成 1 并导致总量错误”；若要回复 upstream issue，先让用户确认英文评论文本。
- 2026-06-30：按用户要求阅读官方 [Certificate Framework](https://karmada.io/docs/administrator/security/cert-framework/) 并对照仓库内 `docs/proposals/cert/Self-Signed_Certificate_Content_Standardization.md`、`hack/deploy-karmada.sh`、`artifacts/deploy/*.yaml`。更新 Day 4：补充官方 cert framework 证书定义词表和与 prototype 的差异。关键修正：当前官方框架已在 `hack/deploy-karmada.sh` 落地，`karmadactl init`/operator/Helm 未来对齐；prototype 还没有完全对齐官方 CA 模型和组件覆盖范围，尤其是保留 `EtcdCA`、未覆盖 search/metrics-adapter/scheduler-estimator server cert/search etcd client 等，需要 PR 前重新注释和确认。
- 2026-06-30：用户已在 #7690 下评论 `/kind feature`，issue label 已生效为 `kind/feature`。新增 Day 4 记录 `internship-reports/day4-certificate-layout-issue-follow-up.md`，分析 `feature/cert-manager-layout` branch 与 #7690 提案之间的 gap：branch 覆盖第一版 `karmadactl init` plan-based split layout prototype，但不覆盖图片中的长期证书管理系统；主要待确认点是 maintainer 方向、是否拆小 PR、命名规范、RBAC/client identity 是否 follow-up、以及真实 split layout smoke test。
- 2026-06-30：按用户确认发布 upstream issue。使用 Day 3 中已确认的英文草稿新建 `karmada-io/karmada#7690`：`Proposal: plan-based split certificate Secret layout for karmadactl init`，正文包含 #6051/#6670/#6788 关联、scope/non-goals、两张设计图 raw 链接、prototype branch/commit/CI 证据，并 mention `@zhzhuang-zju` 请求 review。已用 `thread_brief.py 7690` 确认为 open，暂无 labels、assignees、milestone、comments。
- 2026-06-30：按“新建 issue 最好带图片引用解释”的要求，增强 Day 3 upstream issue 草稿：加入两张已推到 fork `intern` 分支的设计图 raw 链接，并验证链接返回 `200 image/png`。草稿中明确图片只作为长期方向和前后对比说明，当前 issue/PR scope 仍限于 `karmadactl init` 的 plan-based certificate Secret layout，不引入 CRD/controller/cert-manager 集成。
- 2026-06-30：按“先做成 issue、让 @zhzhuang-zju review 提案”的社区流程要求，重新核对 #6051、#6670、#6788：#6051 是证书/配置命名规范 umbrella，#6670 是证书标准化 proposal，#6788 是已有 open split secret layout PR。已在 Day 3 增加英文 upstream issue 草稿，明确该提案与三者的关系、plan-based 抽象边界、prototype branch、CI 证据和待 maintainer 确认的问题；未发布 upstream issue/comment，也未自动 mention maintainer，等待用户确认目标和完整文本。
- 2026-06-30：确认 `feature/cert-manager-layout` commit `eb02bde96` fork push CI 全绿：18 个 check runs 中 16 success、2 skipped、0 failed。新增 Day 3 的 PR 审阅准备部分，整理当前 PR 的实现边界、未实现内容、文件修改解释、reviewer 重点关注点、本地验证命令、fork CI 结果和 upstream PR 文案草稿；补充两张方案图 `Karmada证书管理方案-数据流图.png`、`Karmada证书管理方案对比分析-数据流图.png` 作为长期方案/对比说明资料。
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

- 尚未实际运行 `hack/local-up-karmada.sh`，因此本机 kind / Docker / kubeconfig / 多集群环境是否可用还没有验证。
- 尚未跑完整 `make test` 或 `make verify`。本次 PR 只跑了相关范围的 `go test`、`hack/verify-command-line-flags.sh`、Helm lint、脚本语法和 YAML 解析。
- upstream PR #7666 的 GitHub Actions 仍需继续观察。
- GitHub CLI 当前未登录，匿名 GitHub API broad search 已遇到 rate limit；后续继续做 issue/PR 批量检索时应配置 `GH_TOKEN` 或改用浏览器页面。
- 当前 Windows 电脑上 draw.io 已安装但未加入 PATH：`drawio` / `draw.io` 命令不可用，系统级路径 `C:\Program Files\draw.io\draw.io.exe` 也不存在；实际可用路径是 `C:\Users\ranxi\AppData\Local\Programs\draw.io\draw.io.exe`，版本 `30.2.6`。这个路径只适用于当前 Windows 机器；macOS 或其他机器仍按 drawio-skill 的正常探测顺序处理。

## Ruled Out

- 不改写根 `README.md` 作为实习导航，避免污染上游项目介绍。
- 不把实习报告、中文学习笔记、本地 benchmark 原始数据或本地 skills 放到 upstream-facing topic branch。

## Next

- 如需跟进 #7643 upstream，先发送 Day 5 中的英文 verification comment draft 给用户确认；当前不建议开重复 PR，因为 issue 已有 assignee，且验证结果不支持 functional bug 结论。
- 证书方向先观察 upstream issue #7690 的 maintainer review；回复前不急着开 PR。若 maintainer 认为重复，按要求转到 #6670 或 #6788；若接受方向，再基于 fork prototype 拆小 PR。
- PR 前补齐三类证据：官方 cert framework 对照表确认每个 identity/CA/Secret/flag；命名表让 reviewer 确认 Secret/volume/mount/data key；一次 `karmadactl init --secret-layout=split` smoke test 记录真实安装链路。
- `feature/cert-manager-layout` 已通过 fork push CI。若准备 upstream PR，先让用户确认 PR 标题/body，再按 `.github/PULL_REQUEST_TEMPLATE.md` 创建，不要擅自发布。
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
