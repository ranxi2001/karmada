# Day 14：知名开源维护者 Agent Skills 调研

日期：2026-07-13

## 目标

寻找由知名开源个人或成熟开源组织公开维护的 Agent Skills，判断哪些内容能帮助 Karmada junior 学习工程判断、源码分析、调试和 review，而不是只收集 GitHub star 或未经验证的 prompt。

本轮只读仓库、作者资料、`SKILL.md`、manifest、hooks 和 executable tree；没有安装第三方 skill，也没有运行第三方脚本。

## 一页结论

确实能找到，而且最有价值的部分是维护者长期形成的工作方法：如何先取证、如何处理 review、如何验证“真的完成”、如何从官方源码和文档约束判断。对当前 Karmada 实习，优先级是：

1. Jesse Vincent / [`obra/superpowers`](https://github.com/obra/superpowers) 的 `systematic-debugging` 与 `verification-before-completion`。
2. Addy Osmani / [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) 的 `source-driven-development`。
3. Trail of Bits / [`trailofbits/skills`](https://github.com/trailofbits/skills) 的 `differential-review`，只用于安全、证书、XXL 或高 blast-radius PR。
4. `receiving-code-review`、`planning-and-task-breakdown`、`audit-context-building` 适合借鉴局部规则，不建议原样全局启用。

不建议整包安装。名人作者、官方 marketplace 和高 star 都不能替代逐文件审计；skills 可以携带 scripts、hooks、network command 和写操作。当前更稳妥的策略是固定 commit SHA，先读单个 skill，再用历史案例做 forward test，最后把通过的原则合并到 repo-local skills。

## 个人维护者来源

| 作者 / 仓库 | 一手身份与维护证据 | 与 Karmada 的关系 | 当前判断 |
| --- | --- | --- | --- |
| Jesse Vincent / [`obra/superpowers`](https://github.com/obra/superpowers) | [个人介绍](https://blog.fsck.com/about/)记录 Request Tracker、K-9 Mail 等开源经历；Codex manifest 标明 author 为 Jesse Vincent；MIT，审计 commit `d884ae04` | 系统调试、验证、review、worktree、计划和 TDD | 方法论最强；只选单项，不启用整套强制流程 |
| Addy Osmani / [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) | [GitHub 账号](https://github.com/addyosmani)和 Codex manifest 均绑定 Addy；MIT，审计 commit `98967c45` | source-driven、任务拆解、debugging、review、CI/CD | `source-driven-development` 很契合“不要推断”；其他内容与现有 skill 重叠 |
| Anthony Fu / [`antfu/skills`](https://github.com/antfu/skills) | [个人介绍](https://antfu.me/about)列出 Vue/Nuxt/Vite/Vitest/UnoCSS 等开源工作；MIT 主仓，审计 commit `a74f281a` | 主要是 Vue/Vite/Nuxt 前端上下文 | 当前 Karmada 不安装；其“稳定规则放 AGENTS、按需知识放 skills”的观点值得保留 |
| Simon Willison / [`simonw/skills`](https://github.com/simonw/skills) | [个人介绍](https://simonwillison.net/about/)记录 Django、Datasette 开源工作；审计 commit `a6579982` | 4 个 Python/GitHub Actions 个人工作流 | 适合阅读，不建议安装：仓库无明确 license，部分规则会自动 push 或扩大修改范围 |
| Sindre Sorhus | [`sindresorhus/skills`](https://github.com/sindresorhus/skills) 当前为 404，公开索引未找到其本人 skills 仓库 | 无可验证来源 | 不因作者知名而虚构推荐 |

## 最值得试用的 Skills

### 1. `systematic-debugging`

来源：[`obra/superpowers@d884ae04`](https://github.com/obra/superpowers/tree/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/systematic-debugging)

可复用价值：

- 先读取完整错误和 first hard failure，再讨论修复。
- 对多组件系统在每个边界采集输入、输出和状态。
- 从错误点沿 call/data flow 向上追到产生坏状态的位置。
- 一次只验证一个 hypothesis，失败后回到取证，不叠加补丁。
- 使用 condition-based wait，不用 sleep 掩盖时序问题。

这与 #7719 的教训高度一致，但我们现有 E0-E4 gate 更严格地补上了 queue/recovery/no-self-heal。建议吸收它的通用 debugging 阶段和 `root-cause-tracing.md`，不覆盖本地 flake gate。

需要裁剪：它要求所有 bug 都先有稳定复现、所有 fix 都先写 failing test，成熟分布式项目的真实 flake 有时无法达到确定性 E4；此时应记录限制并接受 maintainer direction，而不是假装可稳定复现。

### 2. `verification-before-completion`

来源：[`obra/superpowers@d884ae04`](https://github.com/obra/superpowers/tree/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/verification-before-completion)

可复用价值：

- 每个完成声明先回答“哪条命令能证明”。
- 必须读取 exit code、失败数和完整相关输出。
- agent/subagent 报告成功后，主 agent 仍要查 diff 和独立验证。
- regression test 需要 red/green 或等价 counterfactual，单次通过不代表测试有效。

它与当前 Karmada 工作流兼容度最高，可以作为第一个 controlled trial 候选。

### 3. `source-driven-development`

来源：[`addyosmani/agent-skills@98967c45`](https://github.com/addyosmani/agent-skills/tree/98967c45a42b88d6b8fb3a88b7ff6273920763d6/skills/source-driven-development)

可复用价值：

- 先从 `go.mod`、`.go-version` 和实际依赖锁定版本。
- 对版本相关行为查官方文档、官方 changelog 和实际源码，不从模型记忆推断。
- 文档与仓库现有代码冲突时，把冲突显式交给 reviewer，而不是静默选择。
- 找不到一手依据时明确标注 `UNVERIFIED`。

需要适配：Karmada 的内部 controller/scheduler 行为往往没有外部文档，权威来源应扩展为“当前 commit 的源码、测试、生成 API 和维护者说明”。引用放在 Day 报告、issue/PR 文案或 review 证据中，不要为了 skill 要求在 Go 源码里塞 URL comment。

### 4. `differential-review`

来源：[`trailofbits/skills@cfe5d7b1`](https://github.com/trailofbits/skills/tree/cfe5d7b1619e47fb5b38b7e2561dad7e5f1e89af/plugins/differential-review)

可复用价值：

- 按风险而不是 diff 行数分配 review 深度。
- 用 git history / blame 理解被删除校验和旧设计原因。
- 追调用者和状态消费者，明确 blast radius。
- 将缺少测试作为风险证据，不把 CI 全绿当成 correctness 证明。
- 每个 finding 给具体场景、行号、commit 和覆盖限制。

适用范围：证书、认证、webhook、scheduler queue、跨组件状态和 XXL PR。普通 docs/XS 变更不应套完整安全审计流程。

需要裁剪：原 skill 带 `allowed-tools: Read Write Grep Glob Bash`，要求自动写完整报告，并包含许多智能合约/攻击者假设；本地应只吸收 risk-first、history、blast-radius 和 coverage 四个部分。

### 5. `receiving-code-review`

来源：[`obra/superpowers@d884ae04`](https://github.com/obra/superpowers/tree/d884ae04edebef577e82ff7c4e143debd0bbec99/skills/receiving-code-review)

值得保留的原则：完整读取 review、用自己的话复述、对照当前代码验证、技术上不成立时给证据化 pushback、逐项实现和测试。#7732 的 Gemini nil-pointer 评论正是该流程的正例。

不应原样采用的部分：它把“不说 thanks”和特定回复语气写成硬规则，这不是 correctness invariant，也可能不符合 Karmada 社区礼仪。我们只保留技术验证流程。

## 知名组织来源

| 仓库 | 实际内容 | 对当前工作的价值 | 注意事项 |
| --- | --- | --- | --- |
| [`openai/plugins`](https://github.com/openai/plugins) | 当前 Codex plugin catalog；已收录 Superpowers 和 GitHub plugin | provenance 清楚，可参考 Codex manifest 和单 skill 包装方式 | 收录不等于所有行为都适合本项目；仍需审计 scripts/hooks |
| [`trailofbits/skills`](https://github.com/trailofbits/skills) | 安全 review、static analysis、PBT、supply-chain 等真实 skills | 证书、安全边界和高风险 diff 很有价值 | CC-BY-SA-4.0；改写/再分发要保留归属和 share-alike 要求 |
| [`github/awesome-copilot`](https://github.com/github/awesome-copilot) | 大量 community-contributed skills、agents 和 instructions | 可按问题检索 `code-tour`、`acquire-codebase-knowledge` | community-created 不等于 GitHub 工程师背书；不能整仓安装 |
| [`anthropics/skills`](https://github.com/anthropics/skills) | 文档、artifact、skill creator、web testing | proposal/report/skill 设计可参考 | 部分 skill 依赖 Claude artifacts/connectors，且各目录 license 不同 |
| [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) | React、Web、Vercel、写作规范 | 前端任务可用 | 与 Go/Karmada 关联弱，不应覆盖 Karmada 模板 |
| [`cloudflare/skills`](https://github.com/cloudflare/skills) | Workers、Wrangler、Durable Objects、Cloudflare One | Cloudflare 项目专用 | 当前主线不需要 |

[`openai/skills`](https://github.com/openai/skills) 的 README 已明确标记 deprecated，当前入口是 `openai/plugins`。内置 `skill-installer` 仍可列出旧 curated 目录，但新调研和新 plugin 应优先看 Plugins 仓库。

## 为什么不能直接整包安装

Agent Skills 不只是 Markdown。根据 [Agent Skills specification](https://agentskills.io/specification) 和 [OpenAI Plugins 结构](https://github.com/openai/plugins)，一个 package 还可以包含 scripts、hooks、agents、commands、MCP、assets 和 tool permission。

本轮固定 SHA 的 tree 审计显示：

- `obra/superpowers@d884ae04` 有 42 个 executable blobs；Codex manifest 的 `hooks` 当前为空，但其他宿主存在 session-start 注入，brainstorming 还包含本地 HTTP/WebSocket visual companion。
- `addyosmani/agent-skills@98967c45` 有 7 个 executable blobs；Codex manifest hooks 为空，但 Claude `hooks/hooks.json` 有 `SessionStart` command。
- `antfu/skills@a74f281a` 没有 executable blob，但 README 自称 PoC，部分 skill 会拉 mutable remote instructions，开发安装还包含 package lifecycle/git-hook 行为。
- `simonw/skills@a6579982` 没有明确 license；个别个人 workflow 包含自动 push 或无关版本升级，不应交给 junior 自动执行。

所以“作者知名”只提高 provenance，不自动降低 behavior risk。

## 安装前审计清单

1. 只选单个 skill，不装 `--all`、整 plugin 或全局 `-g`。
2. 固定完整 commit SHA，记录仓库、目录、license 和审计日期。
3. 读取完整 `SKILL.md` 及其直接引用的 references/scripts。
4. 扫 executable、symlink、binary、manifest、hooks 和 package lifecycle scripts。
5. 搜 push/deploy/delete、`sudo`、`kubectl`、Docker、Terraform、网络下载和依赖安装。
6. 搜 `.env`、tokens、SSH、cloud credentials、kubeconfig 和浏览器 profile 访问。
7. 检查 skill 是否从 mutable `main` 动态获取远端 Markdown。
8. 首次 forward test 使用历史公开案例或无凭据临时目录，不接入真实 fork/upstream 权限。
9. 不自动更新；升级时 diff 旧 SHA 与新 SHA。
10. 与 `AGENTS.md`、repo-local skills 和社区 posting gate 冲突时，以本项目规则为准。

## 建议的 Controlled Trial

暂不安装，先做三个只读测试：

| Skill | 历史输入 | 合格标准 |
| --- | --- | --- |
| `systematic-debugging` | #7719 在维护者 RCA 之前的 E1/E2 证据 | 必须拒绝直接加 wait，要求 producer/status/consumer/queue/recovery 链 |
| `verification-before-completion` | #7697 “unit tests 通过，是否可称证书轮换完成” | 必须要求真实过期、恢复、key/CA invariant 和 PR head 绑定证据 |
| `source-driven-development` | `WaitCRDPresentOnClusters` 名称与实现不一致 | 必须读取 helper/plugin 源码并纠正“scheduler 直接查 member API”的错误 |

只有 forward test 明显补强现有能力、且不制造冲突，才考虑将单个 skill 固定 SHA 安装到隔离位置，或把最小规则合并到现有 repo-local skill。安装和任何第三方脚本执行都需要用户再次确认。

## 未执行的安装命令

以下仅记录可复现形式，本轮没有执行：

```bash
python3 /root/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo obra/superpowers \
  --ref d884ae04edebef577e82ff7c4e143debd0bbec99 \
  --path skills/systematic-debugging skills/verification-before-completion

python3 /root/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo addyosmani/agent-skills \
  --ref 98967c45a42b88d6b8fb3a88b7ff6273920763d6 \
  --path skills/source-driven-development
```

Trail of Bits skill 位于 plugin 深层目录，且 license/引用文件更多；在完成单独 license 和 dependency 审计前不准备安装命令。
