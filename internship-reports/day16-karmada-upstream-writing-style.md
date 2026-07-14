# Day 16：Karmada Upstream Issue / PR 简洁写作规范

日期：2026-07-14

## 目标

根据 Karmada 维护者和高频贡献者的历史 issue / PR 正文，修正我们“把完整本地分析复制到 upstream body”的习惯，形成可执行的简洁起草门禁。

本轮只读取公开 GitHub 数据和本地模板，没有发布 issue、PR、comment 或 reviewer request。

## 样本与口径

用户提到的 `RainBowMongo` 对应 GitHub canonical login [`RainbowMango`](https://github.com/RainbowMango)。其余账号为 [`FAUST-BENCHOU`](https://github.com/FAUST-BENCHOU)、[`zhzhuang-zju`](https://github.com/zhzhuang-zju) 和 [`hzxuzhonghu`](https://github.com/hzxuzhonghu)。

GitHub Search API 查询：

```text
repo:karmada-io/karmada author:<login> is:pr
repo:karmada-io/karmada author:<login> is:issue
```

统计规则：

- 以 2026-07-14 可见历史为准。
- 最近样本按 `created` 降序；作者样本较少时读取全部。
- 去除 GitHub 不显示的 `<!-- HTML comments -->`、CRLF 差异和空 body。
- PR 主统计排除标题为 `Automated cherry pick ...` 的固定生成正文。
- word 是空白分隔的 reviewer-visible token；line 是非空可见行。
- 统计描述风格，不证明技术质量或社区地位；`hzxuzhonghu` 在 Karmada 只有 1 个 authored PR，不能做总体量化推断。

## 统计结果

### PR

| Author | 样本 | 中位词数 | 中位非空行 | 说明 |
| --- | ---: | ---: | ---: | --- |
| `RainbowMango` | 最近 24 个普通 PR | 80.5 | 13 | 最近 30 个中排除 6 个自动 cherry-pick |
| `zhzhuang-zju` | 最近 23 个普通 PR | 74 | 11 | 最近 30 个中排除 7 个自动 cherry-pick |
| `FAUST-BENCHOU` | 全部 21 个普通 PR | 38 | 9 | 全部 27 个中排除 6 个自动 cherry-pick |
| `hzxuzhonghu` | 1 个 PR | 104 | 21 | 仅作定性样本 |

`zhzhuang-zju` 最近 30 个 PR 去除隐藏模板注释前的中位数约 210.5 词，去除后只有 65 词。说明统计 Markdown 原文会把模板注释误当成 reviewer 负担，发布检查必须计算“可见正文”。

### Issue

| Author | 样本 | 中位词数 | 观察 |
| --- | ---: | ---: | --- |
| `RainbowMango` | 最近 20 个 issues | 196.5 | umbrella、依赖升级和 flake tracker 拉高长度 |
| `zhzhuang-zju` | 最近 20 个 issues | 158 | bug issue 中位数约 318，通常包含复现、日志或源码证据 |
| `FAUST-BENCHOU` | 全部 3 个 issues | 74 | 主要是文档/CLI 小问题，样本很小 |
| `hzxuzhonghu` | 全部 7 个 issues | 71 | 主要是 CLI 安装问题，样本很小 |

> 分析：PR 与 issue 不能共用一个硬字数上限。PR 是 review 入口，通常极短；bug/flake issue 承担复现和证据，合理情况下会更长。

## 代表样本

### `RainbowMango`

- [PR #7665](https://github.com/karmada-io/karmada/pull/7665)：普通维护 PR，一段 what/why、一个特殊说明、`NONE` release note。
- [PR #7632](https://github.com/karmada-io/karmada/pull/7632)：需要解释 stale cache 语义时才增加三段 reasoning，仍无文件表和完整测试矩阵。
- [PR #7556](https://github.com/karmada-io/karmada/pull/7556)：proposal PR 只写变更摘要，详细设计留在 proposal 文件。
- [PR #7188](https://github.com/karmada-io/karmada/pull/7188)：CI 修复的长例外，只保留首个错误、runner/Docker 版本差异和 backport 要求。
- [Issue #6880](https://github.com/karmada-io/karmada/issues/6880)：bug 使用 `Description -> Current -> Expected`，示例只保留决定问题的日志。
- [Issue #6842](https://github.com/karmada-io/karmada/issues/6842)：flake 使用官方字段，长日志服务于第一硬失败。

### `zhzhuang-zju`

- [PR #7298](https://github.com/karmada-io/karmada/pull/7298)：API/兼容迁移才使用较长的背景、方案和 release note。
- [PR #7078](https://github.com/karmada-io/karmada/pull/7078)：proposal body 只给执行摘要，完整设计在文档。
- [PR #7341](https://github.com/karmada-io/karmada/pull/7341)：少数在 reviewer note 中提供明确测试报告的近期样本。
- [Issue #7693](https://github.com/karmada-io/karmada/issues/7693)：先讲证书轮换用户痛点，再给首期 CLI scope。
- [Issue #7550](https://github.com/karmada-io/karmada/issues/7550)：bug 用源码、语义和 fix/test/backport checklist 支撑结论。
- [Issue #6915](https://github.com/karmada-io/karmada/issues/6915)：focused flake 只保留 job/test、证据链接和原因假设。

### `FAUST-BENCHOU`

- [PR #7528](https://github.com/karmada-io/karmada/pull/7528)：截图加一句终端宽度原因，没有重复实现过程。
- [PR #7342](https://github.com/karmada-io/karmada/pull/7342)：只有社区决策、生成命令和 issue 关系。
- [PR #7126](https://github.com/karmada-io/karmada/pull/7126)：deprecated flags 直接在 release note 描述用户影响。
- [Issue #7542](https://github.com/karmada-io/karmada/issues/7542)：文档 bug 只给错误示例和期望命令。
- [Issue #7506](https://github.com/karmada-io/karmada/issues/7506)：较长正文来自不可省略的错误输出，而不是过程叙述。

这些 PR 中也存在空 `What/why`、空 release-note fence 或空 `Fixes #`。这不是应复制的规范；我们只吸收简洁度，不降低模板完整性。

### `hzxuzhonghu`

- [PR #108](https://github.com/karmada-io/karmada/pull/108)：一句功能摘要加用户可见 release note。
- [Issue #3611](https://github.com/karmada-io/karmada/issues/3611)：timeout 症状、一个错误片段、代码常量和配置化建议。
- [Issue #3335](https://github.com/karmada-io/karmada/issues/3335)：运行场景、错误和明确标为 guess 的原因判断。
- [Issue #97](https://github.com/karmada-io/karmada/issues/97)：无效策略导致无限 reconcile，并列出 validation/error classification 两个方向。

## 可迁移的共同模式

1. 普通 PR 严格保留官方模板，但 what/why 通常只有一段。
2. `Special notes` 只写 reviewer 会据此改变判断的信息，不做文件级讲解。
3. 复杂设计放 linked proposal；PR body 是 executive summary。
4. Bug/flake issue 按类型模板放复现和证据，不把完整调查过程搬进去。
5. 长文的合理来源是 API/兼容合同、第一失败日志、跨组件 RCA 或 umbrella checklist，不是 diff 大、测试多或使用了 AI。
6. Release note 只描述用户可见行为；没有用户影响时明确写 `NONE`。
7. 交叉链接必须写清 `Fixes`、`Part of` 或 relevance，不能只堆 URL。

## 新起草规范

### PR Body

- 普通 PR：软目标 80-250 visible words、最多约 30 个非空行。
- API/兼容/安全/多组件 PR：软目标 150-400 words、最多约 45 个非空行。
- 超过 400 words 必须再压缩，并说明为什么 detail 不能放进 linked issue/proposal/report。
- 默认删除文件表、完整 case 清单、时间线、动态 CI 状态、重复 non-goals、bot summary 和完整 RCA/proposal。
- 必须保留问题/行为、issue 关系、重要风险、核心验证、AI disclosure 和 release note。

### Issue / Comment

- Enhancement/question：80-250 words。
- Reproducible bug/flake：通常 120-400 words，必要日志/YAML 另算。
- 普通 comment/review：40-180 words；超过 250 words 做压缩检查。
- RCA/proposal/umbrella 可以更长，但必须先给结论和 requested action，再给证据。

这些都是 review trigger，不是为了字数删证据的硬门禁。

## #7697 回归样本

| 版本 | Bytes | 行 | 词 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 旧 body | 8414 | 120 | 约 1015 | 文件表、完整测试清单、动态 CI、实验时间线和多组 scope 重复 |
| 2026-07-14 body | 1821 | 30 | 241 | 保留功能、安全边界、scope、测试、真实过期恢复、AI disclosure 和 release note |

远端精简 body 与本地候选逐字一致，SHA-256 为 `9740e0ca8750fe9f70fb04bc0ecea69d8d03ba55be055f1ce0d8da891cf535af`。

## Skill 落地

- `karmada-pr-management`：新增 reviewer-attention gate、soft budgets、默认删除项和 long-form exceptions。
- `karmada-issue-discussion`：新增 type-specific concise gate、comment 默认模板和长文触发条件。
- `draft_metrics.py`：去掉 HTML comments 后计算 visible words、nonblank lines 和 soft-limit 状态。
- `AGENTS.md`：把“reviewer-facing text 是 evidence index，不是本地报告”设为稳定协作规则。

## 验证结果

- 两个 skill 均通过 `quick_validate.py`。
- `draft_metrics.py` 正确去除 HTML comments；#7697 精简稿为 241 visible words / 18 nonblank lines，历史本地长稿为 937 words / 82 lines；`--fail-over-limit` 超限时返回 exit 1。
- Fresh-context API PR 测试：输入 8 files `+920/-35` 的 synthetic API change，输出 168 words / 15 lines；保留 `/kind api-change`、旧默认行为、mixed-version 升级警告、缺少 e2e、AI disclosure 和 release note，没有生成文件表。
- Fresh-context E2 flake 测试：输入同 SHA rerun success、900ms timing observation，但缺 consumer/queue/counterfactual evidence；输出 184 words / 12 lines，明确 nondeterminism 不等于 root cause，只提出 UID/generation 与 scheduler decision/requeue instrumentation。

结论：新门禁能压缩普通正文，同时没有为了字数删除 API compatibility 或把 flake hypothesis 升格为 RCA。
