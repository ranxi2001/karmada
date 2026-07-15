# 实习任务 TODO

更新时间：2026-07-15

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
| P0 | 9 月前拿到 AgentCube Karmada 项目社区席位 | DOING | 高 | 中 | 7-8 周 | upstream issue/PR/review/CI/会议材料证据链；每周 mentor 可检查总结 | 以 #7621/#7662 为战略 review/实现主线，以 #7697 为持续交付维护线；每周至少沉淀 1 个 upstream-visible 证据 |
| P0 | 跟进 #7621 / proposal PR #7662 复杂工作负载安全重调度 | REVIEW | 高 | 高 | 本周主线，先拿到独立 review/test slice | [Day 15 尽调](day15-issue-7621-safe-rescheduling-feature.md)；[6 月 16 日文字稿](day22-karmada-meeting-2026-06-16-rescheduling-transcript.md)；[6 月 30 日全量转录与对齐](day23-pr7662-meeting-2026-06-30-transcript-and-alignment.md)；PreserveReady 8-case matrix、SafeMigration scheduler collision、direct-delete/finalizer falsification；[target-first review](https://github.com/karmada-io/karmada/pull/7662#discussion_r3576720182) 已发布 | 明天先确认 Story 2 supported modes/Descheduler 分工，以及 Story 3 的 target authority、rolling owner、durable state 和 cancel/delete 合同；候选 B 发布前仍需用户确认 exact target/text |
| P0 | 建立 Karmada 实习基础仓库结构 | DONE | 低 | 低 | 0.5 天 | `AGENTS.md`、`PROGRESS.md`、`internship-reports/`、`.agents/skills/open-source-onboarding/`、[Day 1 日报](day1-karmada-7598-default-version-pr.md) | 后续按 dayN 文件继续记录 |
| P0 | 迁移并 Karmada 化本地 skills | DONE | 中 | 低 | 0.5 天 | `.agents/skills/drawio-skill/`、`.agents/skills/karmada-pr-management/`、`.agents/skills/karmada-issue-discussion/`；4 个 skills 均通过 `quick_validate.py`，Karmada GitHub 脚本 smoke test 通过 | 后续画图、issue 分析、PR 准备分别使用这些 skills |
| P0 | 配置 upstream 远程和分支卫生规则 | DONE | 低 | 低 | 0.5 天 | `upstream=https://github.com/karmada-io/karmada.git`；upstream PR 分支从 `upstream/master` 创建；`intern` 只放学习记录 | 后续 upstream 改动继续使用独立 topic branch |
| P0 | 跑通或预检 Karmada Quick Start | TODO | 中 | 中 | 1 天 | Day 1 报告、命令日志、kubeconfig/context 记录 | 运行或拆解 `hack/local-up-karmada.sh`，记录 host cluster、control plane、member clusters |
| P0 | 梳理 Karmada 项目结构和核心组件 | DONE | 中 | 低 | 1 天 | [Day 2 项目理解](day2-karmada-project-understanding.md)、[PNG 架构图](day2-karmada-architecture.png)、[draw.io 架构图](day2-karmada-architecture.drawio) | Day 3 深追 `samples/nginx` 真实传播链路 |
| P0 | 梳理 ResourceTemplate -> PropagationPolicy -> ResourceBinding -> Work -> member cluster 数据流 | DONE | 中 | 低 | 1 天 | [Day 2 项目理解](day2-karmada-project-understanding.md) 中的 Mermaid 流程图和源码入口 | 继续读 `pkg/detector/`、`pkg/controllers/binding/`、`pkg/controllers/execution/` 的 reconcile 细节 |
| P0 | 建立 Karmada 术语表 | DOING | 低 | 低 | 0.5 天 | [intern-glossary.md](intern-glossary.md) | 随源码阅读补充 Cluster、Work、Binding、PropagationPolicy、OverridePolicy、interpreter、estimator 等术语 |
| P0 | 跑基础测试命令并记录成本 | TODO | 中 | 低 | 0.5-1 天 | `make test` / 聚焦 `go test` 结果 | 先跑轻量目标，再决定是否跑完整 `make test` 和 `make verify` |
| P0 | 建立提交前 lint 检查习惯 | DOING | 低 | 低 | 0.5 天 | [Day 3 CI lint 失败复盘](day3-certificate-management-task-triage.md#ci-lint-失败复盘) | 新增 Go 包或导出 API 后，提交前必须跑 `golangci-lint run ./pkg/karmadactl/cmdinit/...`，不要只跑 `go test` |
| P1 | 分析 Karmada 社区 issue / PR 动态 | REVIEW | 中 | 低 | 0.5-1 天 | [Day 12 新 Issue / PR 机会扫描](day12-new-issue-pr-opportunities.md)；[#7757 复现/review 评论](https://github.com/karmada-io/karmada/issues/7757#issuecomment-4953788174)；[#7692 flake comment review](https://github.com/karmada-io/karmada/pull/7692#pullrequestreview-4681354181)；失败产物时序、代码 review 和 compile/CI 验证已归档 | #7692 等作者或 test OWNERS 回复，不重复催促；#7757 等维护者确认与作者 PR |
| P1 | 调研证书管理相关 issue / PR 并拆任务 | DONE | 中 | 低 | 0.5 天 | [Day 3 证书管理任务整理](day3-certificate-management-task-triage.md) | 优先跟进 #6051 Helm 证书命名规范；先做差距表，不直接改代码 |
| P1 | 准备证书 layout upstream 提案 | DONE | 中 | 低 | 0.5 天 | [Upstream issue #7690](https://github.com/karmada-io/karmada/issues/7690)；[Day 3 发布记录](day3-certificate-management-task-triage.md#upstream-issue-发布记录) | 等 maintainer review；回复前不急着开 PR |
| P1 | 持续维护 `karmadactl init` 证书轮换 PR #7697 直到 merge | REVIEW | 高 | 中 | 持续至 merge | [Upstream issue #7693](https://github.com/karmada-io/karmada/issues/7693)；[Upstream PR #7697](https://github.com/karmada-io/karmada/pull/7697)；[Day 13 持续合并维护](day13-pr7697-review-and-merge-maintenance.md)；远端 head `4b6fa135f`，4 个 P1 已修复，聚焦/cmdinit/完整 karmadactl CLI tests、lint、docs/import-alias/diff check 和 exact-SHA 17/17 checks 全部通过；隔离 kind v1.36.1 的 10m leaf 真实过期、rotate、7 workload rollout、旧 SA token 和最终恢复断言均通过；241 词精简 body 已发布并逐字回读 | 等待 human review；评论、thread resolve 或 reviewer request 分别取得 exact text 授权后再执行，PR 未 merge 前不标记 `DONE` |
| P1 | 跟进 estimator / FlinkDeployment / ResourceQuota e2e flake | DONE | 中 | 低 | 0.5-1 天 | [Upstream issue #7719](https://github.com/karmada-io/karmada/issues/7719) 已关闭；[Upstream PR #7732](https://github.com/karmada-io/karmada/pull/7732) 已 `/lgtm`、`/approve` 并合并为 `d0714678`；[Day 11 维护者 RCA、纠偏与 Mermaid](day11-ci-flake-statistics.md#维护者-rca-与原分析纠偏) | 归档完成；后续 flake 强制使用 E0-E4 证据等级、源码时序和 no-self-heal 分析，不再从 rerun/timing 推测直接提出补丁 |
| P1 | 建立 Karmada CI flake 专项台账 | REVIEW | 中 | 低 | 0.5-1 天 | [Day 11 CI flake 专项统计](day11-ci-flake-statistics.md)；GitHub Actions 2026-06-26 至 2026-07-09 run/job 统计；#6841/#7388/#7719/#7691/#7692/#5323/#3667 等关联台账 | 补最近 schedule workflow artifacts，把 37 个 schedule e2e/setup 失败按具体 Ginkgo spec 或 setup 阶段归类；如每周复用则沉淀脚本 |
| P1 | 调研知名开源维护者公开 Agent Skills | DONE | 中 | 低 | 0.5 天 | [Day 14 Expert Skills 调研](day14-expert-agent-skills-research.md)；已核验作者、固定 SHA、license、hooks 和 executable tree；最小规则已合并进 repo-local `code-review-growth` / `karmada-pr-management` 并通过 forward tests | 不整包安装；以后只在出现新真实 review lesson 时增量更新本地 skill |
| P1 | 建立 YouTube 本地开源转录 + Agent 校对 skill | DONE | 中 | 低 | 0.5 天 | 全局 `~/.codex/skills/youtube-transcript-proofread/` 与 repo-local `.agents/skills/youtube-transcript-proofread/`；本地 Whisper、duration validator、review chunk、校对规则；两份内容哈希一致；57:08 真实会议 forward test 通过 | 后续会议先确认 title/duration，再区分 raw ASR、corrected transcript 和 digest；受限视频不得自动导入浏览器 cookies |
| P1 | 建立 Karmada issue / PR 简洁起草规范 | DONE | 中 | 低 | 0.5 天 | [Day 16 写作风格审计](day16-karmada-upstream-writing-style.md)；抽样 `RainbowMango`、`zhzhuang-zju`、`FAUST-BENCHOU`、`hzxuzhonghu`；两个 skill 新增 concise-first gate/reference，`draft_metrics.py` 和两次 fresh-context tests 通过 | 后续每次 upstream exact text 审批都报告 visible words；只有 RCA/proposal/API/security 等明确原因才保留长文 |
| P1 | 升级 GitHub Actions Ubuntu runner | DONE | 低 | 低 | 0.5 天 | [Upstream PR #7728](https://github.com/karmada-io/karmada/pull/7728) 已 merged；[Day 10 调研记录](day10-ci-ubuntu-runner-upgrade.md)；分支 `chore/update-github-runner-ubuntu-24`；commit `0f62fd62b`；fork push CI 和 upstream PR CI 已全绿 | merge 后 master push CI 命中 Remedy + Flink 两个 e2e flake，已记录到 Day 10 / Day 11；不视为 runner 升级确定性失败 |
| P1 | 准备 `karmadactl init` split Secret layout PR | BLOCKED | 中 | 中 | 0.5-1 天 | [Day 3 PR 审阅准备](day3-certificate-management-task-triage.md#pr-审阅准备)；[Day 4 gap 分析](day4-certificate-layout-issue-follow-up.md)；fork push CI 已通过 | 根据 #7693 维护者方向，旧 split layout prototype 暂时不作为第一优先级 PR；后续只作为证书 Secret 映射参考 |
| P1 | 验证 #7643 FlinkDeployment memory issue 是否真实存在 | DONE | 中 | 低 | 0.5 天 | [Day 5 验证报告](day5-issue-7643-flink-memory-verification.md)；临时函数级和默认 Flink interpreter 测试日志 | 若要回复 upstream issue，先让用户确认英文评论；当前结论是不建议开重复 PR |
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

## 9 月社区席位目标拆解

目标：在 2026 年 9 月前拿到 AgentCube Karmada 项目社区席位。

判断标准不是“本地学了多少”，而是是否形成 Karmada 社区可见、mentor 可复查的稳定贡献能力。

### 可检查证据

- upstream PR：至少有持续推进中的高质量 PR，最好能合并；如果未合并，也要有清晰 review 响应、CI 记录和拆分计划。
- upstream issue：能独立完成 issue 真实性验证、复现/不可复现说明、英文评论草稿和后续行动建议。
- review 响应：评论区每条有效意见都能转化为代码、测试、文档或清晰解释，避免只口头说明。
- 测试能力：新增功能必须有函数级和关键路径测试；CI 失败要能定位到 lint、unit、e2e、环境差异或 flake。
- 社区表达：能用英文/中文讲清楚提案 scope、non-goals、风险、后续 PR 拆分和需要 maintainer 决策的问题。
- 复盘材料：每周有一份可给 mentor 看的短总结，链接到 issue/PR/commit/CI/report。

### 每周节奏

- 周初：选定 1 条 upstream 主线和 1 个备选小任务，明确 expected evidence。
- 周中：推进代码、测试或 issue 验证，至少完成一次本地验证或社区反馈响应。
- 周末：写 mentor-facing 总结，记录本周证据、未解决问题、下周最小行动。

### 当前双主线

战略主线是 #7621 / #7662 复杂工作负载安全重调度：

- 当前阶段：proposal review，不抢实现。
- 近期可检查产出：PreserveReady scheduler compatibility matrix、SafeMigration crash-point ledger、source-backed upstream review。
- 进入代码的条件：作者和 maintainer 明确 API compatibility、GracefulEviction relationship 和持久化边界，并确认独立切片。

交付维护线是 `karmadactl init` 证书轮换 PR #7697：

- 最终 head `4b6fa135f` 已推送，真实过期恢复验证和 17/17 checks 已完成。
- 精简 PR body 已发布并回读验证；当前等待 human review，PR merge 前持续维护但不再扩大 scope。

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
| 完成 #7690 后续 gap 分析 | 输出 [Day 4 gap 分析](day4-certificate-layout-issue-follow-up.md)，确认当前 prototype branch 覆盖第一版 `karmadactl init` subset，但 intentional defer 长期证书管理系统、RBAC 收窄、Helm/operator、rotation 和真实 smoke test |
| 完成 #7643 bug 真实性验证 | 输出 [Day 5 验证报告](day5-issue-7643-flink-memory-verification.md)，函数级和默认 Flink interpreter 路径均显示 `100m` 保持为 `100m`、汇总为 `200m`，当前 upstream master 未复现 issue 描述的错误 |
