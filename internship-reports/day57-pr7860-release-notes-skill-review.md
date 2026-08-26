# Day 57：PR #7860 Release Notes Skill 完整性 Review

## 先说人话

结论：[#7860](https://github.com/karmada-io/karmada/pull/7860) 把 release-note 人工流程沉淀成 skill 的方向有实际价值，但 current head `2e7ae712e2940ac29a8ddb3819fb1e1bc43ada5c` 还不能用于正式发版。问题不在文案，而在收集器会失败或静默漏数据。

一个具体例子是 `v1.18.0-alpha.2 -> v1.18.0-beta.0`：PR [#7298](https://github.com/karmada-io/karmada/pull/7298) 的 release-note fence 有一段摘要和四条 deprecated field。当前解析器只输出第一段，四条字段变更全部消失；现有 [`CHANGELOG-1.18.md`](https://github.com/karmada-io/karmada/blob/v1.18.0/docs/CHANGELOG/CHANGELOG-1.18.md) 则保留了它们。

另一个例子是 minor release：`v1.18.0-alpha.0..v1.18.0` 有 285 个 commit，而 Python 收集器没有分页，只拿到默认上限 250 个后退出。也就是说，文档明确支持的 minor release 路径在最近一个完整 minor release 上不能运行。

已给作者发布 4 条 blocking inline finding；没有附带 `/lgtm` 或 `/approve`。后续只在作者更新 head 后复查这四个完整性边界。

## PR 与 Review 边界

- PR：[#7860 add generating release notes skills](https://github.com/karmada-io/karmada/pull/7860)
- 作者：`@zhzhuang-zju`
- Base：`karmada-io/karmada:master@b6c92395e6e9e0678452f22ce2d7242693fb881c`
- Head：`zhzhuang-zju:releasenote-skills@2e7ae712e2940ac29a8ddb3819fb1e1bc43ada5c`
- Diff：4 个新文件，`+653/-0`
- 内容：skill 主流程、Karmada format plugin、PR metadata Python collector、contributor Bash collector
- 当前状态：17 个 checks success；`@ranxi2001` 已通过 [comment](https://github.com/karmada-io/karmada/pull/7860#issuecomment-5413148977) `/assign`，并提交包含四条 blocker 的 [`COMMENTED` review](https://github.com/karmada-io/karmada/pull/7860#pullrequestreview-5021435325)
- Review 深度：完整读取 PR body、4 个文件、5 条 Copilot inline comments 和 review summary；用历史 release range 做真实 API 回归
- 未做：没有修改作者分支，没有提交 `/lgtm` 或 `/approve`，没有运行与这 4 个文件无关的 Go/e2e 矩阵

## 实际运行过程

### 1. 小区间可以得到正确主列表

在 current head 上运行：

```bash
GITHUB_TOKEN=<local-token> python3 fetch_pr_info.py \
  v1.19.0-beta.0 v1.19.0-rc.0 \
  --repo karmada-io/karmada
```

结果：24 commits、10 merged PRs、4 个带 user-facing change 的 PR。#7663、#7792、#7814、#7815 与现有 v1.19.0-rc.0 changelog 主条目一致。

这证明基础 merge/squash PR number 提取和单行 release note 路径可用；不能外推到长区间、多行 fence 或失败路径。

### 2. Minor release 被 250-commit 默认页阻断

```text
Comparing v1.18.0-alpha.0...v1.18.0
Error: GitHub returned only 250 of 285 commits; refusing to generate incomplete release notes
exit status: 1
```

代码证据：

- `get_commit_comparison()` 没有传 `page` / `per_page`。
- `comparison_is_truncated()` 发现 `total_commits > len(commits)` 后只会退出。
- GitHub 官方 [Compare two commits](https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28#compare-two-commits) 文档说明：不传分页参数时 commits 最多 250；endpoint 支持 `page` 和 `per_page`。
- 同 PR 的 `fetch_contributors.sh` 已使用 `per_page=100&page=N`；live API 的 page 1 和 page 2 返回了不同 commit，Copilot 关于 compare endpoint 不支持分页的旧评论不成立。

### 3. 多行 release note 被静默截断

真实输入是 PR #7298 的 release-note fence：第一段包含 inline code，后续还有一段说明和四条带 inline code 的 bullet。

current parser 的输出只有：

```text
`scheduler-estimator`: Migrated to standard protoc-gen-go for gRPC API generation to support Kubernetes 1.35+. Introduced peer `bytes` fields for K8s types to ensure compatibility.
```

它丢失：

- `ReplicaRequirements.resourceRequest`
- `ComponentReplicaRequirements.resourceRequest`
- `NodeClaim.nodeAffinity`
- `NodeClaim.tolerations`

根因是 `extract_user_facing_change()` 的第一条 regex 排除任何 backtick；fallback regex 在后续行遇到 backtick 时停止，却不要求匹配完整 closing fence。函数因此返回一个看似正常但不完整的字符串，不报错。

### 4. Contributor login 无法映射时被静默跳过

`fetch_contributors.sh` 使用：

```bash
jq -r '.commits[].author.login // empty'
```

commit `248997cd6376dbd0d316c970ce41d60590e63a36` 在 `v1.18.0-alpha.0..v1.18.0` 内，commit author 是 `sdutta133 <sdutta133@bloomberg.net>`，GitHub compare API 的 `.author` 为 `null`。这个 commit 属于 PR [#7372](https://github.com/karmada-io/karmada/pull/7372)，PR author 是 `@SujoyDutta`；现有 v1.18.0 Contributors 也包含 `@SujoyDutta`。当前脚本输出中没有该用户。

这不是要求强行把所有 commit author 改成 PR author。最小合同是：遇到无法映射的 commit 时不能 `// empty` 后继续成功；应输出 unresolved SHA 供人工处理，或用可验证的 PR 映射补回 login。

### 5. PR metadata 请求失败后仍可返回成功

`github_request()` 在 HTTP/URL error 时返回 `None`；`get_pr_details_batch()` 又把无响应或 GraphQL errors 统一变成 `{}`。`main()` 随后把 `{}` 当成“没有 PR 有 release note”，打印 0 条并返回 0。

受控失败测试给一个合法 comparison、让后续 GraphQL request 返回 `None`，得到：

```text
No PRs with user-facing changes found.
Total PRs with user-facing changes: 0
EXIT_STATUS 0
```

这与 Gate 2 的“collection fails 时停止”矛盾。生产 reachability 来自脚本自己处理的 HTTP、URL 和 GraphQL error 边界；受控测试只证明错误传播分支，未声称观察到 GitHub 线上事故。

## Findings

| 优先级 | 位置 | 结论 | 证据 | 最小修改 |
| --- | --- | --- | --- | --- |
| Blocking | `fetch_pr_info.py:127-134` | 多行 fenced release note 遇到后续 inline backtick 会被截断 | #7298 preview range 真实运行；现有 changelog 保留被丢字段 | 解析完整 closing fence，保留多行结构；用 #7298 形状做 regression |
| Blocking | `fetch_pr_info.py:66-72,243-251` | minor range 超过 250 commits 时必然失败 | v1.18.0 为 285 commits；current script exit 1；官方 endpoint 支持分页 | 分页收齐全部 commits，并验证页间去重/总数 |
| Blocking | `fetch_contributors.sh:67-69` | `.author.login == null` 的真实 contributor 被静默漏掉 | commit `248997cd6`、PR #7372、v1.18.0 Contributors 三方一致 | 显式报告 unresolved commit，或基于 PR 映射补 login |
| Blocking | `fetch_pr_info.py:96-111,265-272` | PR metadata 请求失败被折叠成空成功结果 | 受控 failure 返回 0；源码允许 HTTP/GraphQL error 进入该分支 | 区分 error 与 empty，向 `main()` 传播 non-zero status |

四条都影响 release artifact 的完整性。它们是局部数据边界，逐条 prose 比图更清楚，因此 Review Visualization Gate 不要求 Mermaid。

## 已发布的英文 Inline Comments

以下四条原文已在 exact head `2e7ae712e2940ac29a8ddb3819fb1e1bc43ada5c` 上作为同一个 `COMMENTED` review 发布，并通过 GitHub API 回读正文。

### 1. 完整 fenced block

锚定 `fetch_pr_info.py:128` 的 `release_note_patterns`：[upstream comment](https://github.com/karmada-io/karmada/pull/7860#discussion_r3855128290)

```text
blocking: This truncates a real Karmada release note when a later line contains inline code. For PR #7298, the current parser returns only the first paragraph and drops the four deprecated-field bullets that appear in the v1.18.0 changelog. Could this parse the complete fenced block, including backticks and line breaks, and add a regression test with that multi-line shape?
```

### 2. Compare pagination

锚定 `fetch_pr_info.py:244` 的 `comparison_is_truncated()` 调用处：[upstream comment](https://github.com/karmada-io/karmada/pull/7860#discussion_r3855128301)

```text
blocking: This makes the documented minor-release workflow fail for a normal release range instead of collecting all commits. `v1.18.0-alpha.0...v1.18.0` contains 285 commits, so the current script receives the default 250 and exits with status 1. The compare endpoint supports `page`/`per_page`, as `fetch_contributors.sh` already uses. Could this collector paginate too and cover a range above 250 commits?
```

### 3. Unresolved contributor identity

锚定 `fetch_contributors.sh:69` 的 `jq -r '.commits[].author.login // empty'`：[upstream comment](https://github.com/karmada-io/karmada/pull/7860#discussion_r3855128308)

```text
blocking: `// empty` silently drops contributors whose commit email is not linked to a GitHub account. In the v1.18.0 range, commit `248997cd6` has `author: null`; it belongs to PR #7372 by `SujoyDutta`, who is present in the published v1.18.0 Contributors section but absent from this script's output. Could this report unresolved commits or recover the login through a verified PR mapping instead of succeeding with an incomplete list?
```

### 4. API failure propagation

锚定 `fetch_pr_info.py:100` 的 `get_pr_details_batch()` error return：[upstream comment](https://github.com/karmada-io/karmada/pull/7860#discussion_r3855128320)

```text
blocking: An HTTP or GraphQL failure here becomes `{}`, and `main()` then prints "No PRs with user-facing changes found" and exits 0. That turns a collection failure into a successful but incomplete release-note result, contrary to Gate 2. Could the batch helper return an explicit error and make `main()` fail non-zero, with a focused request-failure test?
```

### 发布校验

- Review：[`5021435325`](https://github.com/karmada-io/karmada/pull/7860#pullrequestreview-5021435325)，state `COMMENTED`，commit `2e7ae712e2940ac29a8ddb3819fb1e1bc43ada5c`
- 四条 remote body 的 SHA-256 依次为 `ba6168ff3e921bed254531a34e344485e77521d5838cc26e7be085a4ed31638a`、`47c4743da0d9661e7e3d20e0878a569f40699296eff0476e3e2279cc2c0a3756`、`c9c78abeeb786e4d6d6abd870f03c58bc61f3fcb1b68b99805251e0e8195a7ef`、`9cc6c7701b5d92d8d73bb1078302f51bbfb195dc2d70e3f6f31944ad1e939342`，与获准草稿一致
- GitHub REST 回读的 diff position 依次为 `128`、`244`、`69`、`100`；这四个文件均为本 PR 新增文件，因此 position 与目标新文件行号一致

## Copilot Comments 复核

| Copilot 意见 | Current head 状态 | 本次判断 |
| --- | --- | --- |
| `.github/skills` 路径错误 | 已改成 `.claude/skills` | 已解决，不重复评论 |
| compare 截断且只识别 merge commit | 已增加截断 guard 和 squash pattern | squash 已补；截断处理仍使 minor workflow 不可用 |
| `--repo` 未做 allowlist | 未改 | plugin 固定提供 `karmada-io/karmada`，属于低价值 CLI hygiene；不抢占 release correctness |
| Gate 7 使用 diagnosis 且标题不一致 | 已修 | 已解决，不重复评论 |
| compare endpoint 不支持分页 | author 未改 shell loop | Copilot 判断错误；官方文档和 live page 1/page 2 均证明支持分页 |

## 验证记录

| 检查 | 结果 | 能证明什么 |
| --- | --- | --- |
| `git diff --check upstream/pr-7860^..upstream/pr-7860` | 通过 | patch 没有 Git whitespace error |
| `python3 -m py_compile fetch_pr_info.py` | 通过 | Python 语法可编译，不证明行为完整 |
| `bash -n fetch_contributors.sh` | 通过 | Bash 语法可解析，不证明 API/identity 行为 |
| v1.19 beta -> rc live collection | 通过，4 条 user-facing PR | 小区间与单行 note 主路径可用 |
| v1.18 alpha.0 -> stable live collection | 失败，250/285 | minor workflow 当前不可用 |
| v1.18 alpha.2 -> beta live collection | #7298 只输出首段 | 真实多行 note 被静默截断 |
| v1.18 contributor live collection | 漏 `@SujoyDutta` | null GitHub author identity 会被静默过滤 |
| injected GraphQL failure | exit 0、0 notes | 请求失败未向调用者传播 |
| exact-head upstream checks | 17 success | Karmada 通用 CI 通过；PR 没有新增 collector behavior tests，因此不能覆盖上述问题 |

## 已确定、未决边界与下一步

已确定：四条 findings 均能由 current head 源码和历史真实 release data 复现；PR 现在不满足自身 Gate 6 的“no user-facing change is duplicated or omitted”。

未决边界：没有证明历史 changelog 本身绝对无人工误差；contributor finding 只依赖一个三方一致的 `@SujoyDutta` 样本，不用总人数差异推导全部遗漏原因。

下一步：等待作者回复或更新；新 head 到来后只复查 parser 完整 fence、commit pagination、unresolved identity、request error propagation 及对应 tests。修复前不根据 17 个通用 checks 给出正面 review decision。


豆包分析，需要验证 ## 我额外发现的问题（建议顺手提，都不算 blocking 但值得说）

1. **两个脚本的失败哲学完全相反，是核心设计不一致**：`fetch_contributors.sh` 对传输层是 fail-closed（`curl --fail` + `set -o errexit` + `jq -e`），但对你第 3 条说的空 author 是 fail-open；`fetch_pr_info.py` 对 compare 步骤 fail-closed（第 2 条），但对 GraphQL 步骤 fail-open（第 4 条）。四个问题本质上都是 "**静默数据丢失 vs. 显式失败**" 的选择没做统一。
2. **GraphQL 成功响应下仍会静默丢 PR**：`if pull_request: result[...] = ...` + main 里 `continue`，某个 PR 在批量响应里缺失（被删 / 别名报错）时既无报错也无数量对账。建议加一个 `pr_numbers` 与取回数目的核对。
3. **bot 过滤只有文档层、没有执行层**：format 文档说 Contributors 要排除 `[bot]`，但 `fetch_contributors.sh` 会原样输出 `karmada-bot` 这类登录名（真实 285 commit 范围里就有），SKILL Gate 3 第 4 步也只说 "去重排序" 没说过滤 ——bot 过滤完全依赖下游手工。这条最好固化到脚本或 Gate 3 指令里。
4. **GraphQL 单查询别名数量**：minor 范围 285 个 PR 会拼成约 285 个别名的单条 GraphQL 查询，GitHub 有 query cost / 复杂度上限，建议作者拿真实范围跑一次确认不触发；必要时分批（如每 50 个一组）。
5. 小问题：`normalize_release_note` 里 `len(normalized) <= 3` 会把真实 3 字符 note 丢掉（概率极低）；`github_request` 无 timeout、无限流重试；`release-note` 匹配大小写敏感且要求围栏后必须换行。

另外你 PR 页面里 Copilot 那条 " 路径用了 `.github/skills/...`" 的评论已标记 Outdated—— 我看当前版本 SKILL.md 里 Gate 2/3 都已是 `.claude/skills/...`，作者改过了，这条不用再提。

复现脚本我放在了 `C:\Users\r50059641\Doubao\chats\2026-08-26\new-chat\review7860\`（`fetch_pr_info.py` + `repro_test.py`），你可以直接重跑或改参数复验。

需要的话我可以接着做两件事之一：① 为这 4 条各出一份可直接贴到 PR 上的修复 diff（含第 1 条的回归测试）；② 帮你起草对 zhzhuang-zju 的跟进回复（把你的 4 条 + 我上面补充的几点整理成一条完整 review 总结）。你要哪个？
