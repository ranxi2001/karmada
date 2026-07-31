# Week 6 总结：从架构 Review 与证书收敛走向可验证的 Flake 修复

日期：2026-07-13 至 2026-07-18

证据截止：2026-07-18 15:20 CST

## 第一层：可汇报成果

这一部分只保留经理可以快速读取的结果、状态和下一步。完整源码推理、失败过程和验证证据放在第二层及对应 Day 报告。

### 1. 本月目标

| 目标 | 状态 |
| --- | --- |
| 在 2026 年 9 月前形成稳定、可复查的 Karmada 社区贡献能力 | 进行中 |
| 持续维护证书轮换 PR #7697 直到合并 | 代码和 CI 已收敛，等待真人 review |
| 围绕 #7621 / #7662 建立安全重调度设计判断 | 已完成源码、调度矩阵和会议证据 review |
| 将 CI flake 推进到 E3 RCA、最小修复和 E4 反证 | #7776 / #7777 进行中 |

### 2. 本周进展

| 工作项 | 结果、价值或剩余风险 | 完成时间 | 状态 |
| --- | --- | --- | --- |
| 收敛证书轮换 PR #7697 | 修复 SAN、集群身份、external-etcd trust 和操作合同；增加 11 Secret 部分写入后的重跑收敛测试，当前 head 17 个 checks 全绿 | 7/17 | 等待 human review |
| 建立安全重调度 review 主线 | 完成 #7621 / #7662 源码、8-case 调度矩阵和两场会议对齐；发布 target-first/single-writer review | 7/15 | 等待设计方向 |
| 完成 Flink cleanup flake 闭环 | Week 5 创建的 #7732 于 7/13 合并并关闭 #7719；同步屏障与真实 consumer 所需状态一致 | 7/13 | 已完成 |
| 提交 Remedy flake 修复 | 证明 stale-cache/event-filter 因果链，创建 [Issue #7776](https://github.com/karmada-io/karmada/issues/7776) 和 [PR #7777](https://github.com/karmada-io/karmada/pull/7777)；接受 Gemini 的 generic set/empty fast-path 建议并推送 `13645be77` | 7/17-7/18 | 14 success、3 E2E 运行中 |
| Review #7764 E2E RCA skill | 用真实 artifact 验证命令和推理边界，目录布局与换行建议被采纳 | 7/17 | PR 已合并 |
| Review controller 错误边界 | #7623 发布 cache 过早提交导致重试失效的阻塞 finding；#7774 纠正“进程 crash”的过强表述 | 7/15-7/17 | #7623 等待作者；#7774 评论完成 |
| 外部工具链贡献 | drawio-skill [PR #94](https://github.com/Agents365-ai/drawio-skill/pull/94) 修复 marketplace version sync 并于 7/14 合并；发布 [openai/codex#33051](https://github.com/openai/codex/issues/33051) 描述 Responses stream 300 秒 silent wait 机制 | 7/14 | 1 个已合并，1 个 issue open |

### 3. 收获与分享

Controller 和 CI flake 的共同难点是找到最后一个恢复事件为何丢失。一次读取、快速等待、日志命中或绿色重跑都只是信号；必须串起权威状态、缓存、消费者、队列和恢复事件，才能形成根因并设计最小补丁。

### 4. 疑惑与问题

- #7662 仍未明确 Binding 的唯一写者、迁移持久化、GracefulEviction、删除恢复和兼容合同，因此不应进入 executor 实现。
- #7697 全套 CI 已绿，但 final head 未重跑完整过期集群实验；当前边界是历史运行证据加最新 focused regressions。
- #7777 的完整 stale-cache lifecycle 和 restart convergence 属于独立 follow-up，不扩大当前两文件修复。
- Migration health wait 已在 fork `8ef8a08c6` 验证，但样本有限，尚未获 upstream 发布确认。

### 5. 下周计划

| 任务 | 可验收结果 |
| --- | --- |
| 跟进 #7777 | 等待三版本 E2E，分类红灯并处理真人 review；不混入 lifecycle/restart follow-up |
| 推进 #7697 | 基于全绿 head 处理 human review，保持 CLI-only、preserve-only 和手动 restart 边界 |
| 继续 #7662 review | 等 Story 2 支持模式和 Story 3 状态所有权明确，再决定是否认领 contract tests |
| 处理 migration patch | 准备一文件 diff、失败样本和 exact-state wait 草稿，发布前单独确认 |
| 保持价值门槛 | 不把 recovered panic、刻意非法输入或 mock-only 分支包装成战略任务 |

### 活动指标

| 指标 | 数量 | 去重对象 |
| --- | ---: | --- |
| 周内创建的 PR | 2 | drawio-skill #94、Karmada #7777 |
| 周内合并的本人 PR | 2 | Karmada #7732、drawio-skill #94 |
| 周内创建的 issue | 2 | Karmada #7776、openai/codex #33051 |
| 实质 Review 的 PR | 4 | Karmada #7662、#7764、#7623、#7774 |
| 持续维护的本人 PR | 1 | Karmada #7697 |
| 社区扫描条目 | 23 | 17 个更新 open 条目、6 个关闭或合并条目；新增高价值目标为 0 |
| CI runs 审计 | 83 | PR `CI Workflow` runs |
| Flake-only runs | 23 | 排除确定性代码错误后的 runs，覆盖 18 个 PR |
| Flake jobs | 29 | 其中 25 jobs 保持 `NEEDS_RCA` |

> 注释：指标按唯一 issue / PR / run object 去重，不把 commit 数、bot 评论、格式 nit、CI rerun 或普通 LGTM 当成独立工程影响。

## 第二层：学习与工程记录

### 本周工程主线

Week 6 的工作由三条线收束到同一个方法：复杂设计先找 authoritative state，证书恢复先守住 identity/trust boundary，CI flake 先证明最后一个 recovery edge。结果不是同时开更多 PR，而是把高风险 review、已有 PR 维护和一个新的最小 flake 修复都推进到可验证状态。

```text
源码和会议对齐安全重调度合同
  -> 高风险 differential review 收敛 #7697
  -> flake 台账筛出可修复候选
  -> E3 因果链 + focused red/green regression
  -> #7776 / #7777 独立交付
```

### 需求拆分与架构边界

| 问题 | 本周决定 | 证据 | 未解决部分 |
| --- | --- | --- | --- |
| #7697 应轮换哪些证书 | 只做显式 CLI leaf renewal；保留 CA、persisted SAN、`karmada.key`、Secret metadata 和 external-etcd credentials | 证书解析/identity/no-mutation tests，完整 CLI tests，17/17 checks | automatic restart、HA runbook、CA/caBundle/external-etcd rotation 不在当前 PR |
| PreserveReady 是否通用 | 只在部分 Aggregated/Dynamic Steady 条件成立；Duplicated、Static、Fresh 或旧集群失去 eligibility 时不能保证 ready 下界 | 真实 `core.AssignReplicas` 8-case matrix | supported modes、Descheduler 分工和 freshness contract 待 maintainer 方向 |
| SafeMigration 如何 target-first | 不能让 WR 与 scheduler 同时无约束写 `Binding.spec.clusters`；需要唯一 desired state 或 scheduler exclusion | Binding generation/requeue、scale-down 路径、会议双写 concern | target authority、durable operation/unit state、rolling primitive owner、cancel/delete |
| Remedy cleanup 为什么卡住 | post-delete reconcile 读 stale empty actions 并跳过写入；较早 action write 到 cache 后又被 Conditions-only predicate 过滤，且无 periodic requeue | timestamped logs、status helper、event handler、queue/requeue 源码 | restart/startup convergence 是独立问题 |
| Migration E2E 应等待什么 | 等待测试最终断言依赖的 ResourceBinding `Applied && Healthy`，不是 Deployment ready 后立即单次 GET | 失败样本与现有 `WaitResourceBindingFitWith` | 需要更多样本或 upstream direction 证明长期价值 |
| 哪些新社区条目值得投入 | 先看普通生产触发、最终影响、恢复路径、fix leverage 和复杂度；允许扫描结果为 0 | #7774 recovered panic、#7647 invalid quantity 复盘 | 后续新样本仍需逐项判断，gate 不是 merge veto |

### 本周实际完成

#### 1. 将 #7697 从“功能可运行”收敛为可审查的恢复合同

第二次 full-diff review 找到三条普通恢复路径上的 P1 风险：rotation 从当前机器重建 SAN 会丢失已有 endpoint identity；只比较 CA 会在共享企业 CA 的两个真实集群之间混写 admin credentials；external-etcd replacement 会改变 apiserver 的 datastore trust boundary。

修复后，rotation 从已有证书保留 SAN，用 CA 和稳定 client public key 双重绑定本地 kubeconfig，并把 external-etcd 改成 parsed preserve-only contract。随后又移除可复用 config 中的 operation mode，确保 rotate 只能由一次性 CLI flag 选择；新增最终一个 Secret timeout 后重跑 11 个 Secret 全部收敛的测试。

当前 PR head `bf24e47ce` 为一个 signed-off commit，8 files、`+2031/-28`。完整 `go test ./pkg/karmadactl/... ./cmd/karmadactl/... ./cmd/kubectl-karmada/... -count=1`、cmdinit lint、flag/import verifier、focused identity/convergence tests 和全部 17 个 GitHub checks 通过。PR body 与历史评论已同步当前 CLI-only、preserve-only、rerun-before-restart 合同；GitHub 当前列出 requested reviewers `@prodanlabs`、`@Tingtal`，尚未获得 human approval。

#### 2. 用源码、调度矩阵和会议证据 review #7621 / #7662

两场社区会议的本地 Whisper 转录分别覆盖 6 月 16 日目标片段和 6 月 30 日 `57:08` 全场。证据支持 Story 2 的真实需求与初步方向，也明确记录 Story 3 的 Policy/WR 双重真相、scheduler/controller 双写、rolling ownership、unit boundary 和 cancel 语义仍未闭合；这些都不能写成 maintainer 已批准。

临时 detached worktree 中的 8-case matrix 进一步证明 PreserveReady 不是通用模式。Duplicated、Static Weighted、Fresh mode 或 ready cluster 不再 eligible 时都会破坏下界；只有部分 Aggregated/Dynamic Steady 场景条件成立。基于源码发布的 target-first review 要求 proposal 定义 authoritative migration state 或 scheduler exclusion，作者和 maintainer 尚未给出技术结论。

#### 3. 把 Review 质量问题变成可复用门禁

对 #7764 的 review 使用真实 #7719 artifact，而不是只读 Markdown：job logs endpoint 返回 plain text；artifact 根目录只有 `karmada-host/`、`member3/` 和 `karmada.config`；flat glob 找到 0 个 scheduler logs，递归搜索找到 8 个。作者后来修正 member layout 和系统性 hard-wrap，PR 于 7 月 17 日合并。

两条关于 fast wait 和 single grep hit 的评论虽然技术方向成立，但作者明确表示难懂。复盘后把复杂 review 固化为 `observation -> concrete counterexample -> reasoning -> specific action`，并为多 actor、分支、retry 和时序关系增加 inline Mermaid visualization gate。这个结果比继续堆术语更重要：review comment 必须在没有本地报告和聊天上下文时仍能独立理解。

#7623 则提供了 controller transaction 的另一类实例：PR 在完整 reconcile 成功前推进派生 cache，后续 status write 失败时，错误重试会被新 cache 值变成成功 no-op。故障注入和撤销新增赋值的 counterfactual 证明 finding 由 cache commit timing 引入；对应阻塞 review 已发布，作者尚未更新 head。

#### 4. 从 83 个 CI runs 中筛出可修复的 Flake

Day 11 之后严格纳入 83 个 PR `CI Workflow` runs，其中 23 个 runs、29 个 jobs 在排除确定性代码错误后归为 flake。Remedy cleanup 跨窗口出现三条新样本，#7697 v1.36 artifact 提供了完整 stale-cache/event-filter/no-requeue 链，达到 E3。

最小修复只让 `RemedyActions` 变化触发 cluster reconcile，并保留 set semantics，避免 nil/empty 或顺序差异造成无意义入队。focused test 在旧 predicate 下得到 `queue length = 0, want 1`，修复后通过；reverse-patch 再次失败，形成局部 E4。随后接受 Gemini 建议，将废弃方向的 string set 用法切换为 generic `sets.New`，并优化空 actions 常见路径，没有增加测试或文件范围。

发布前 exact-SHA fork CI 的 lint、codegen、compile、unit 和 v1.34/v1.35/v1.36 E2E 全绿；#7776 和 #7777 均已创建并回读验证。最新 commit `13645be77` 推送后，DCO、lint、codegen、compile、unit 和 CLI/Chart/Operator 三版本 matrix 已绿，base E2E 三版本在证据截止时仍运行。

#7777 首轮 v1.35 红灯没有执行 Remedy Serial spec。三个独立 etcd 在 435ms 内出现 6.7-9.4 秒 `fdatasync` stall，随后 ReadIndex/API/control-plane collapse；这条 in-run chain 达到 E3，但 shared-runner 的物理 trigger 仍只有 E2，缺少 `iostat`、PSI、`vmstat` 和 kernel/hypervisor 证据。因此正确动作是重跑和补 observability，不修改 Remedy 产品逻辑。

#### 5. 交付两个外部工具链问题

drawio-skill 升级到 v1.34.0 时发现 top-level version 已更新，但 marketplace workflow 仍读取旧 metadata version。修复 PR #94 统一 canonical version、增加失败门禁和 regression test，129 tests 通过、7 个 optional-tool skips，并在提交后三分钟内由维护者合并。

Codex CLI issue #33051 则将“卡住 5-10 分钟”的症状收敛到一个可测试机制：HTTP/SSE 与 WebSocket 都可能在首个 request-correlated event 前使用 300 秒 idle timeout，并允许 5 次 retry。现有本地日志只能证明重复 stream failure/recovery，不能证明某次故障一定走满 300 秒；issue 因此把 paused Tokio 双 transport regression 写成 acceptance criterion，而没有把 backend、代理或网络推断成已证 root cause。

#### 6. 接受没有新任务的社区扫描结果

Day 25 扫描 17 个更新 open 条目和 6 个关闭/合并条目。初版曾把 #7774 和 #7647 因“真实可达、CI 绿、无人 review”排为机会；补查 recovery 和最终结果后撤回：前者 panic 已被 controller-runtime recover，补丁只改善诊断且资源仍 stuck；后者是用户显式非法 quantity 的窄 CLI UX hardening。

最终只对 #7774 发布一条影响表述纠正，不继续扩展 mock 防御，也不介入已有 owner 的 #7771/#7767。这个 gate 只决定我们的注意力，不表示小型正确补丁不应合并。

### Review 与测试映射

| 风险 | Review / 修复决定 | 验证证据 | 残余风险 |
| --- | --- | --- | --- |
| #7697 rotation 改变集群身份或 trust root | 保留 SAN、CA、stable client key、external-etcd credentials；CLI-only operation | focused cert/no-mutation tests、partial timeout rerun、完整 CLI suite、17 checks | 未在 final head 重跑完整 live expiry；manual restart/HA runbook 在 PR 外 |
| #7662 target-first 被 scheduler 提前缩 source | 要求 authoritative state 或 scheduler exclusion | Binding generation/requeue 和 8-case AssignReplicas matrix | proposal 尚未更新，无 maintainer direction |
| #7623 error retry 变成功 no-op | cache 只能在完整 reconcile side effects 成功后 commit | injected Status.Update error + revert-sensitive second reconcile | 作者尚未修复，未观察生产事故 |
| #7764 从 signal 过度推出 RCA | fast time / grep count 只能作为 lead，需 lifecycle 或 queue evidence | 真实 artifact、源码、review comprehension/diagram gate | compatibility artifact、flat glob 和两条 inference wording 在 merge 时仍有缺口 |
| Remedy status cleanup 永久不收敛 | watch Conditions 与 RemedyActions，保留 set equivalence | E3 log/code chain、red/green/reverse-patch、package/race tests、fork CI | startup/restart convergence 不在当前 PR |
| Migration 读取尚未聚合的 Binding health | 复用 exact `Applied && Healthy` wait | 单文件 patch、package compile、fork 三版本 E2E | 样本量有限，尚未 upstream |
| v1.35 多 spec 同时失败 | 先追 etcd WAL/ReadIndex/API collapse，不按 spec 名改业务逻辑 | 三个独立 etcd 同窗口 fdatasync stall、matrix 反证 | host physical trigger 仍缺观测 |

### 卡点、失败与处理

| 失败或误判 | 现象 | 原因 | 处理与当前状态 |
| --- | --- | --- | --- |
| #7697 首轮 lint | 两个函数 cyclomatic complexity 18，超过 15 | identity/trust checks 聚集在入口函数 | 拆成 contract-specific helpers，lint 0 issues，focused tests 重跑通过 |
| #7764 评论作者难以理解 | 技术术语齐全，但 signal 与 claim 的桥需要本地调查上下文 | line anchor 和礼貌问句不能替代具体反例 | 建立 standalone comprehension 和 visualization gates；旧评论不直接重复发布 |
| 会议 ASR 尾部幻觉 | 首轮 cue 越过视频时长 | previous-text conditioning 传播错误上下文 | 关闭 conditioning、加入术语提示和 duration validator 后重跑 |
| draw.io 直接 PNG export | 容器返回 `Empty export data` | 当前 Linux GUI/CLI 导出路径不稳定 | 保留 SVG/draw.io 为主源，用 Chromium 无裁切生成 PNG 预览 |
| 新任务价值初筛误判 | 把 production reachability 当成 contribution priority | 未追最终结果和 framework recovery | 增加 Contribution Value / Production Relevance Gate，最终候选为 0 |
| #7777 首轮 v1.35 红灯 | 4 个并行 spec failure，末尾大量 cleanup error | 多 etcd I/O stall 导致 control-plane collapse；Remedy spec 未执行 | 不改 PR 逻辑，只重跑并记录需要的 host observability |

### 开源协作记录

| 对象 | 本人角色 | 本周动作 | 证据截止状态 |
| --- | --- | --- | --- |
| Karmada #7697 | author / reviewer / tester | 修复 identity/trust/operation blockers，更新 body 与历史说明，完成 full CI | open，17 checks success，等待 human review |
| Karmada #7662 | reviewer / researcher | 完成源码、scheduler matrix、两场会议对齐，发布 target-first review | open，等待设计方向 |
| Karmada #7764 | reviewer / artifact validator | 发布 4 条 review 与 hard-wrap 证据回复，复盘可理解性 | 7/17 merged，member layout 与 hard-wrap 已采纳 |
| Karmada #7623 | reviewer / tester | 发布 cache commit timing blocking finding 和 E4 evidence | open，作者未更新 |
| Karmada #7732 / #7719 | author / tester | 跟进 flake 修复合并与 issue 关闭 | 7/13 completed |
| Karmada #7776 / #7777 | issue author / PR author / tester | 发布 Remedy RCA、两文件修复和 reviewer cleanup commit | open，CI 进行中 |
| Karmada migration patch | author / tester | 一文件 exact-state wait，fork CI 三版本全绿 | 仅 fork，未 upstream |
| drawio-skill #94 | author / tester | 修复 distribution version sync | 7/14 merged |
| openai/codex #33051 | issue author / source analyst | 发布 silent stream watchdog 机制与回归要求 | open |

### 本周形成的可复用工程判断

1. **Authoritative state 必须唯一。** Controller、scheduler、policy 或 migration executor 同时写 desired state 时，先解决 ownership，再讨论状态机实现。
2. **派生 cache 是 commit marker。** 依赖副作用尚未全部成功时不能推进 cache，否则 error retry 会退化成 no-op。
3. **Fresh read 不等于 lifecycle freshness。** 复用名称和异步 status 需要 UID、generation、resourceVersion 或 old-to-new transition 证明。
4. **Signal 不等于 diagnosis。** elapsed time、grep count、rerun green 和失败 spec 名都不能单独证明 stale state、no retry、root cause 或代码回归。
5. **Flake 修复必须和因果边对齐。** 测试、实现和验证要覆盖同一个 producer-consumer-recovery edge；timeout、sleep 和通用 retry 不能替代 RCA。
6. **证书轮换首先是身份与 trust boundary 问题。** 生成新证书只是动作，真正合同是哪些 key、SAN、CA、Secret metadata 和 external credentials 必须保持不变。
7. **没有合适任务也是有效结果。** Triage 的产出是减少冲突和无效工作，不是增加 issue/PR 数量。

### 证据索引

| 结论或工作流 | 本地证据 |
| --- | --- |
| 第三方 Agent Skills 审计与 evidence/review gates | [Day 14](day14-expert-agent-skills-research.md) |
| #7621 / #7662 源码、调度矩阵和 participation strategy | [Day 15](day15-issue-7621-safe-rescheduling-feature.md) |
| Karmada concise-first 写作门禁 | [Day 16](day16-karmada-upstream-writing-style.md) |
| #7764 artifact review 与 comment comprehension miss | [Day 17](day17-pr7764-e2e-root-cause-skill-review.md) |
| drawio-skill v1.34.0 与 PR #94 | [Day 18](day18-drawio-skill-v1.34-upgrade.md) |
| Codex CLI stream stall issue | [Day 19](day19-codex-cli-stream-stall-issue.md) |
| #7623 cache commit timing review | [Day 20](day20-pr7623-reconcile-cache-review.md) |
| Mermaid/draw.io authoring boundary | [Day 21](day21-drawio-authoring-and-clarity-analysis.md) |
| 6 月 16 日重调度会议证据 | [Day 22](day22-karmada-meeting-2026-06-16-rescheduling-transcript.md) |
| 6 月 30 日 #7662 全量会议对齐 | [Day 23](day23-pr7662-meeting-2026-06-30-transcript-and-alignment.md) |
| Karmada 资源传播和两级调度组件图 | [Day 24](day24-karmada-resource-propagation-scheduling-components.md) |
| 社区机会筛选与 relevance gate | [Day 25](day25-karmada-community-scan-2026-07-17.md) |
| #7697 certificate identity/trust repairs | [Day 26](day26-pr7697-targeted-certificate-rotation-fixes.md) |
| CI flake census、Remedy/Migration patches 与 #7777 stall classification | [Day 27](day27-pr7697-e2e-flake-root-cause-analysis.md) |
| #7776 / #7777 exact upstream publication record | [Day 27 upstream drafts](day27-remedy-flake-upstream-drafts.md) |

### 一句话总结

Week 6 把复杂架构 review、证书恢复合同和 CI flake 调查统一成“先确认状态来源和恢复边，再用 counterfactual 验证最小改动”的工程方法，并形成两个已合并 PR、一个新 Karmada flake issue/PR 和多条可复用 review 规则。
