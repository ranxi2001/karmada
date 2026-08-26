# Day 53：Karmada Community PR #216 Agent Skills 范式复核

- 日期：2026-08-25
- 评审对象：[karmada-io/community#216](https://github.com/karmada-io/community/pull/216) `Agent skills for Karmada users`
- 合并提交：[`c720c1307133b139d9f2a16d297b857f34e00087`](https://github.com/karmada-io/community/commit/c720c1307133b139d9f2a16d297b857f34e00087)
- PR head：`83d5397c2b5087f05d55051e32d700f859c75781`
- 当前边界：本文只保存本地技术分析；是否向 upstream 发送 comment，后续单独决定。

## 先说人话

这套 skills 的目录结构、任务拆分、触发描述和安全边界都做得比较规范，可以作为 Karmada 社区的高质量 beta 基线；但它附带的评测门禁还不能可靠证明“skill 被正确触发，而且所有答案都通过了 grader”。因此，“符合 Agent Skills 文件范式”和“评测已经足以证明效果”是两个不同结论。

最直接的例子是：假设一次评测产生两份答案，一份 grader 返回通过，另一份 grader 超时。当前统计逻辑只把 `status == "completed"` 的 grading 放进分母，超时项会被排除；只要其余一份通过，output gate 仍可能显示通过。另一个例子是答案记录了 `target_triggered=false`，表示目标 skill 没有被观测到加载，但当前 output gate 不检查这个字段，仍可以通过。

所以本轮结论是：

- Agent Skills 格式与组织方式：符合主流范式，完成度高；
- skill 本身的任务边界与安全约束：总体合理，少数规则仍偏硬；
- eval harness 的结果可信度：存在两个会产生假阳性的门禁缺口；
- 当前定位：适合作为社区可用的 beta 版本，不宜直接当成 Agent Skills 评测的 gold-standard reference；
- 社区动作：PR 已合并，本轮不准备、不发布 upstream comment。

## 背景与评审问题

PR #216 新增 68 个文件，约 `+9319/-0`，主要交付 7 个 Karmada skills、配套 references/scripts，以及 deterministic、routing、output、comparison 四类评测工具。7 个 skills 分别是：

| Skill | 主要职责 |
| --- | --- |
| `karmada-knowledge` | 回答 Karmada 概念、架构与能力边界问题 |
| `karmada-create-policy` | 根据用户目标创建传播与调度策略 |
| `karmada-audit-policy` | 静态审计现有策略的选择器、依赖与风险 |
| `karmada-explain-placement` | 解释 workload 为什么被放置到当前 member clusters |
| `karmada-debug-propagation` | 排查资源传播失败或状态不一致 |
| `karmada-search` | 使用 Karmada Search 查询多集群资源 |
| `karmada-controller-manager` | 指导 controller manager 配置、运行和故障排查 |

本轮回答的问题不是“PR 是否已经 merge”，而是以下三项：

1. skill package 是否符合 [Agent Skills specification](https://agentskills.io/specification) 的结构与渐进披露原则；
2. 描述、任务边界、安全约束是否适合作为 Karmada 用户工作流；
3. eval harness 是否能支持“skill 被触发并改善结果”这一更强结论。

## 评审范围与证据

### 已检查

- 阅读 PR body、commit history、conversation、line review 和最终 merged diff；
- 检查 7 个 `SKILL.md` 的 frontmatter、目录命名、正文长度、references/scripts 组织和触发描述；
- 对每个 skill 运行 OpenAI `skill-creator` 的 `quick_validate.py`，7 个目录均返回 `Skill is valid!`；
- 在 merged commit 上运行作者提供的 deterministic suite：

```bash
python3 skills/evals/scripts/run_deterministic.py \
  --root . \
  --output /tmp/community216-deterministic.json
```

结果为 `passed: true`、`safety_failures: 0`，其中 `script unit and scenario tests` 与 `collection validator` 均通过；
- 直接调用 merged code 的 gate functions 构造最小输入，复现 grader error 被排除、`target_triggered=false` 仍通过 output gate 两个行为；
- 对照 Agent Skills 官方规范、[Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) 和 [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) 的当前建议。

### 没有验证

- 没有运行完整 Codex + Claude 多轮非确定性评测，也没有复核模型供应商账单、速率限制或重复运行方差；
- PR 没有提交可供复核的完整 eval reports、raw traces 或 grading artifacts；
- 没有在真实 Karmada source checkout 或 live cluster 上验证源码导航、策略 admission、调度解释和故障诊断效果；
- PR 页面可见 checks 主要是 DCO 与 Tide，不能替代这套 eval harness 的运行证据。

直接执行 `python3 -m unittest discover -s skills/evals/scripts/tests -v` 会因测试模块导入路径报 `ModuleNotFoundError`；作者提供的 canonical wrapper 会设置所需路径并通过。因此这被记录为直接 discovery 不受支持，而不是产品缺陷。

## 结论总览

| 维度 | 评分 | 结论 |
| --- | ---: | --- |
| Agent Skills 格式 | 9/10 | 7 个 package 均通过标准 validator；名称、描述、目录和正文规模符合规范 |
| Skill 设计与边界 | 8/10 | 任务拆分清晰，evidence boundary 和 mutation safety 较完整；少量 always-read references 与硬编码交互规则仍可优化 |
| Eval gate 可信度 | 5/10 | deterministic 基础扎实，但 grader 完整性、真实 activation、baseline 和 checkout coverage 不足 |
| 综合判断 | 7/10 | 可作为高质量 beta/community baseline；暂不建议视为 gold-standard reference |

评分用于表达成熟度差异，不代表 upstream 的正式质量等级，也不代表 maintainer 已认可本文判断。

## 符合范式的部分

### 1. Package 结构符合 Agent Skills 规范

7 个 skill 的目录名与 frontmatter `name` 一致，均提供 `name` 和 `description`。描述长度为 326 至 601 个字符，低于规范的 1024 字符限制；正文为 72 至 120 行，低于官方建议的 500 行。标准 validator 全部通过。

这说明 PR 不是只把提示词集中放进若干 Markdown 文件，而是按 skill package 组织入口、references 和 scripts，基础结构是合格的。

### 2. 任务拆分和负向路由边界清楚

7 个 skill 分别处理知识问答、策略创建、策略审计、placement 解释、传播排障、资源搜索和 controller manager 运维。description 不只列出“什么时候使用”，还区分了相邻 skill 不应接管的场景，能降低多个 Karmada skill 同时匹配时的路由歧义。

例如，`karmada-create-policy` 负责产生配置，`karmada-audit-policy` 负责审计已有配置，`karmada-explain-placement` 解释已有 placement，三者虽然都会读取 policy，但最终产物不同。这种按用户目标拆分的方式符合 Agent Skills 的 trigger design 思路。

### 3. 证据边界和安全边界较完整

skill 文本区分了三类证据：仅凭 package 内 reference 能回答的内容、需要 Karmada source checkout 才能确认的实现细节、需要 runtime/cluster evidence 才能判断的实际状态。对 destructive command、mutation、缺失输入和版本差异也设置了 fail-closed 规则。

这部分最有价值的不是“提醒用户小心”，而是约束 Agent 不把静态知识写成 live cluster 事实，也不在缺少目标对象、context 或授权时直接生成可执行变更。

### 4. Deterministic suite 提供了可重复的基础检查

评测工具覆盖 package validator、script unit tests、scenario tests、source-claim 与 safety 检查。merged commit 上的 deterministic suite 完整通过，说明基础脚本、fixture 和 collection schema 至少在作者支持的入口下保持一致。

这个结果能证明静态与确定性检查可运行，但不能单独证明模型实际触发了 skill，也不能证明 skill 相比无 skill baseline 带来改进。

## 关键问题

### 1. 高：grader error 会被静默移出统计分母

[`grading_summary()`](https://github.com/karmada-io/community/blob/c720c1307133b139d9f2a16d297b857f34e00087/skills/evals/scripts/lib/grading.py) 只汇总 `grading.status == "completed"` 的记录；[`evaluate_output()`](https://github.com/karmada-io/community/blob/c720c1307133b139d9f2a16d297b857f34e00087/skills/evals/scripts/evaluate_gates.py#L123-L170) 检查 agent/model result 是否完成，却没有要求每个预期 grading 都完成。

最小复现输入包含两次已完成的 agent run：一次 grading 为 `completed/pass`，另一次 grading 为 `error/grader timed out`。当前 gate 输出仍为：

```text
all output runs completed: 2 == 2, pass
critical assertion rate: 1.0, pass
required assertion rate: 1.0, pass
safety failures: 0, pass
source claim failures: 0, pass
```

这里的信号是“已完成 grading 的断言通过率为 100%”，不能推出“所有预期 grading 都通过”。grader timeout、解析失败或供应商错误会缩小分母，产生假阳性。

最小修正方向：output gate 应按 scenario/run 计算预期 grading 数量，要求每一项 `grading.status == "completed"`；任何 missing/error/timeout 都应使 gate 失败，并单独报告 infrastructure failure。

### 2. 高：output gate 不要求目标 skill 实际触发

runtime result 会记录 `target_triggered`，但 `evaluate_output()` 没有检查它。最小复现中，唯一一份答案设置 `target_triggered=false`，其他 grading 与 safety 字段均通过，output gate 仍全部通过。

此外，[Claude runtime 的 `activation_evidence()`](https://github.com/karmada-io/community/blob/c720c1307133b139d9f2a16d297b857f34e00087/skills/evals/scripts/lib/runtime.py#L367-L390) 在 wrapper prompt 强制指定 skill 时就返回 `triggered: true`，这更接近“评测框架要求使用该 skill”，不是对 `SKILL.md` 实际加载的独立观测。

当前结果最多证明“带有 skill 上下文的答案符合断言”，不能证明“客户端正确选择并加载了目标 skill”。对于一套同时强调 routing 和 skill effectiveness 的评测，这个缺口会让最终 pass 状态高估实际集成效果。

最小修正方向：with-skill output gate 必须要求来自 runtime observation 的 `target_triggered == true`；wrapper 注入只能记录为 `requested_skill`，不能替代 observed activation。

### 3. 中：routing eval 更接近分类题，不是原生隐式触发

routing prompt 明确告诉模型这是 `routing-only evaluation`，要求加载一个 skill，并只返回 skill name；Claude 路径还使用 JSON schema 约束名称。这个设计能测试“自然语言意图映射到哪个 skill 名称”，但没有完整复现用户直接提问后客户端自动发现和加载 `SKILL.md` 的过程。

官方 trigger guidance 更强调使用自然、全新的 held-out prompts，并观察目标 `SKILL.md` 是否实际加载。当前 routing score 可以作为 intent classifier 指标，不宜直接命名为 native activation 成功率。

改进方向：保留现有分类题用于快速回归，再增加 raw user prompt 模式；不给 skill list、不要求返回名称，直接从 runtime trace 观测 activation，并加入未出现在调优集合中的 held-out queries。

### 4. 中：baseline comparison 与 checkout/live 行为不是 release gate

`skills/evals/gate.json` 的 required sections 只包含 deterministic、core routing 和 package-only output。comparison 在 CLI 中是可选项，README 也只在声明 improvement 时建议比较。

22 个 output cases 主要覆盖 missing evidence、source boundary、mutation safety 和 version boundary。它们适合验证“不会乱说、不会越权”，但没有要求真实 source checkout、policy admission、controller/scheduler execution 或 live cluster diagnosis。

因此现有门禁能证明 package-only 安全性，不能证明以下能力：

- skill 相比 without-skill baseline 稳定提高任务完成率；
- Agent 能在 Karmada checkout 中找到正确源码与调用链；
- 生成的 policy 能通过当前版本 schema/admission；
- placement/propagation 解释与真实集群状态一致。

改进方向：对 release 或 improvement claim 强制 baseline comparison；为 source-aware skills 增加 pinned checkout cases；把 live cluster cases 作为单独 tier，明确成本与环境要求。

### 5. 中低：自定义 frontmatter validator 比标准规范更窄

[`verify.py`](https://github.com/karmada-io/community/blob/c720c1307133b139d9f2a16d297b857f34e00087/skills/evals/scripts/verify.py#L203-L214) 用逐行 `:` 切分解析 frontmatter，并要求字段集合恰好为 `{"name", "description"}`。Agent Skills specification 允许 `license`、`compatibility`、`metadata`、`allowed-tools` 等可选字段，也允许合法 YAML 表达方式。

当前 7 个 package 都能通过，所以这不是现有内容的失败；风险在于未来添加标准允许的 metadata 或 block scalar 时，community validator 会把合法 skill 判为无效。

改进方向：使用 YAML parser 或官方 `skills-ref`/validator 作为结构真值；项目自定义规则只添加 Karmada 特有约束，不重新定义标准 frontmatter 子集。

### 6. 低：部分 always-read references 削弱渐进披露

主 `SKILL.md` 本身长度合格，但部分入口要求每次都读取较大的 reference。例如 `karmada-debug-propagation` 总是读取约 348 行的 `references/triage.md`，`karmada-controller-manager` 总是读取约 244 行 checklist，`karmada-explain-placement` 默认读取两份 reference。

这不会破坏格式兼容性，但会增加简单问题的固定 context 成本。更符合 progressive disclosure 的做法是按阶段或模式拆分 reference，例如先读最小入口，再根据 `package-only`、`source checkout`、`live cluster` 分支加载对应材料。

## PR Review 与合并状态的解释边界

PR 经过了实际 review，但现有讨论不能被写成“评测设计已经获得充分验证”：

- `RainbowMango` 询问了 WIP 状态、eval 复杂度和演示，并在作者解释与补充 demo 后给出 `/lgtm`、`/approve`；
- Gemini bot 提出的 stream hashing、runner executable 和 scenario directory 问题已在最终 commit 修正；
- Copilot 提出的未知 `expected_skill` 也已修正；
- 现有 human review 没有深入检查 grader denominator、activation gate 和 baseline requirement。

因此，merge 证明社区接受了当前交付，不自动证明评测门禁没有逻辑缺口。本文的两个高优先级结论来自 merged SHA 上的源码检查和最小函数级复现，不是对 review 人员的评价。

## 仍待讨论的设计边界

部分 skill 把多轮 mutation safety 写成固定交互流程，例如第一轮只给分析、后续再允许命令。这个方向有利于跨客户端安全，但在用户已经明确授权、输入完整且任务可逆时，可能比实际需要更严格。

当前没有足够的真实误操作数据或用户体验对比来判定这属于缺陷。更合适的后续问题是：哪些操作必须二次确认，哪些操作可以在已有明确授权下直接执行。该问题不列为当前 finding，也不作为发 comment 的理由。

## 是否发 upstream comment

本轮不做决定，也不准备或发布 comment。PR 已在 2026-08-24 合并，当前报告先作为内部技术记录。

如果后续决定反馈，建议只聚焦两个会让 gate 假通过的问题：

1. grader error/timeout 被排除后，output gate 仍可能通过；
2. `target_triggered=false` 时，output gate 仍可能通过。

这两点有 merged SHA、具体函数和最小复现，适合整理成一个简短 follow-up issue/comment。routing 设计、baseline、validator 和 progressive disclosure 更适合作为后续增强建议，不应与两个 correctness 问题混在同一条长评论中。

任何 upstream comment 仍需重新核对当时的 `main`，准备 exact target/text，并获得用户确认后才能发送。

## 下一步

1. 保留本报告作为 PR #216 的 canonical 本地复核记录。
2. 暂不追踪或推动社区动作，等待是否反馈 comment 的明确决定。
3. 若决定反馈，先在最新 `karmada-io/community` 主分支重跑两个最小复现，再压缩为 reviewer 可独立理解的英文文本。
4. 若后续要把这套 eval 当成 release gate，优先补 grader completeness 和 observed activation，再讨论 baseline 与 live tiers。
