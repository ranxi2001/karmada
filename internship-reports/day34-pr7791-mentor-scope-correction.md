# Day 34：PR #7791 线下评审后的职责边界纠偏

## 结论

线下 mentor review 指出，我们把一个“调度器应该从第一个 `clusterAffinities` term 重新评估”的局部状态问题，扩大成了“调度器必须绕过 informer cache 读取最新 Cluster”的一致性问题。这是评审方向错误：可达的跨 informer 时序只能证明存在观察窗口，不能自动证明 freshness、重试或自动收敛属于 scheduler 的职责。

PR #7791 应回到原始 6 行生产代码，保留围绕这 6 行建立的 RB/CRB 单测和 A -> B -> A E2E。当前 8 文件版本中的 direct Cluster API List、request-scoped snapshot 和相关 cache/core 改动应全部撤销。

> 反思：此前 review 先追求“任何事件顺序都一次自动成功”，再反推 scheduler 必须读取最新 Cluster，缺少了组件职责门禁。正确顺序应是先确认组件契约，再判断时序窗口由调用方等待、已有事件重试、人工重试，还是状态所有者修复。

## Scheduler 的职责契约

本次接受的职责范围如下：

- scheduler 使用既有 cache/snapshot 作为本轮调度输入，并负责计算 placement 结果。
- `status.schedulerObservedAffinityName` 是 scheduler 持久化的顶层 affinity 搜索游标。
- 当 `RescheduleTriggeredAt > LastScheduledTime` 时，显式重调度应把本轮搜索起点改为第一个 term。
- scheduler 不在本 PR 中承担跨 informer freshness 验证，不绕过 cache 直接 List Cluster，也不新增一次请求必须自动等到所有异步状态收敛的承诺。
- 如果恢复 Cluster 状态尚未进入 scheduler cache，调用方等待、再次触发或人工重试可以接受；E2E 可以用有界同步建立“恢复状态已经可见”的前置条件。

## 3 文件最小范围

| 文件 | 保留内容 | 不再承担的职责 |
| --- | --- | --- |
| `pkg/scheduler/scheduler.go` | RB 和 CRB 路径各 3 行：显式重调度时把 `affinityIndex` 设为 `0` | 不直读 Cluster API，不构造 freshness snapshot |
| `pkg/scheduler/scheduler_test.go` | 对称验证显式重调度从第一个 term 开始；普通调度仍从已观察 term 继续 | 不测试 API List/cache override |
| `test/e2e/suites/base/clusteraffinities_test.go` | A -> B -> A 用户场景；时钟精度 barrier；在创建 WorkloadRebalancer 前有界等待 scheduler 已看到恢复状态 | 不把跨 informer 任意顺序自动收敛写成本 PR 产品承诺 |

明确不改：

- `pkg/scheduler/cache/cache.go`
- `pkg/scheduler/cache/cache_test.go`
- `pkg/scheduler/cache/snapshot.go`
- `pkg/scheduler/core/generic_scheduler.go`
- `pkg/scheduler/core/generic_scheduler_test.go`

## 与 PR #5425 合并贡献的方式

PR [#5425](https://github.com/karmada-io/karmada/pull/5425) 由 `@bharathguvvala` 在 2024 年提出了相同的 6 行核心修复。其历史提交 `292904e022dea71d12187b0469e8297aeafa798c` 中，RB/CRB 两条路径均包含正确的游标归零逻辑，并带有作者本人的 DCO sign-off。

但是 #5425 当前 head `a37e17d098e66ff8436df7fd3f0ed927389901de` 是污染过的 merge history，当前 commit author 还显示为 `karmada-bot`，且 CRB 代码存在错误变量引用，不能直接 rebase 或 cherry-pick 整个提交。维护者此前也建议基于最新 master 手工保留那 6 行。

因此本地重建采用两个干净提交：

1. 第一个提交只含 6 行生产修复，author 保留为 Bharath，使用其真实 signed historical commit 作为来源并保留其 sign-off；当前提交者同时 sign off。
2. 第二个提交由 `ranxi2001` 提交，只包含新增/增强的单测和 E2E。

这样既不继承 #5425 的污染历史，又在 Git 历史中把原始实现贡献和我们补充的测试贡献分开。远端 force-push、PR body 更新以及是否在 #5425 留言，仍需用户逐项确认后执行。

## 验证计划

- 比较最终 tree 与 #7791 原始 6 行版本 `1117aa6e20`：功能代码和回归场景保持一致，但排除其中与本功能无关的 `assert.Len` 防 panic 清理。
- `git diff --check upstream/master...HEAD`。
- scheduler 定向单测及 `go test ./pkg/scheduler/...`。
- `go test ./test/e2e/suites/base -run '^$'`，验证 E2E package 编译。
- 独立 review：确认生产 diff 只有 6 行，RB/CRB 对称，普通路径语义不变，测试没有重新要求 scheduler 承担 cache freshness。

## 本地重建与验证结果

本地 clean worktree：`/tmp/karmada-5070-six-line`，branch：`rewrite/reset-affinity-six-lines-final`，基线：`upstream/master@eb2e7c75ff828afbb34f625a105a24f5a973c1cc`。

提交历史：

1. `b41507b1f4bcbc7d4964fc39ba262dc8b3df42da`：只改 `pkg/scheduler/scheduler.go`，`+6/-0`。Author 为 Bharath，AuthorDate 保留为 `2024-12-13T12:52:40+05:30`。`git interpret-trailers --parse` 能连续识别 Bharath 和当前 committer 的两条 sign-off。
2. `41ed652725fc9169cab111cb0793ff135a037ba7`：只改两个测试文件，由 `ranxi2001` author/sign-off。

最终 diff 为 3 文件 `+294/-13`：生产代码严格 `+6/-0`；单测 `+200/-13`；E2E `+88/-0`。五个 cache/core 文件相对 master 的 diff 为空。

单测明确三个合同：

- pending trigger、已观察 B、A 成功：`[A]`。
- 没有 pending trigger、已观察 B：`[B]`。
- 原有“从第一个 term 开始、A 失败后 B 成功并更新 observed status”的 fallback case 保持不变，没有为了新增测试而牺牲旧覆盖。

本地验证：

- `go test -race ./pkg/scheduler -run '^TestSchedule(ResourceBinding|ClusterResourceBinding)WithClusterAffinities$' -count=1`：通过。
- `go test ./pkg/scheduler/... -count=1`：通过。
- `go test ./test/e2e/suites/base -run '^$' -count=1`：通过，仅验证 package 编译；本轮未声称重跑真实集群 E2E。
- `git diff --check upstream/master...HEAD`：通过。
- 反向验证：在临时 detached worktree 只删除 6 行后，新增 RB case 精确失败为 `actual [affinity2], expected [affinity1]`，并且没有预期 patch；恢复后 worktree clean 并已删除。这证明测试与生产修复处于同一 causal edge。

调试过程也保留：曾尝试把原 fallback case 改为 pending `[A, B]`，第一次还把 `Status` 误放进 `ResourceBindingSpec`，定向 race 编译报 `unknown field Status in struct literal of type ResourceBindingSpec`。修正结构后虽能通过测试，但 final review 指出这会丢失“空/首 term 游标 fallback 后更新 observed status”的原覆盖，因此最终撤销该试验，恢复原 case，不为补充边界而扩大测试改动。

final provenance review 还发现第一版 clean commit 的两条 `Signed-off-by` 之间存在空行，`git interpret-trailers --parse` 只识别 ranxi。最终提交已改为连续 trailers，并再次核对 author、AuthorDate、direct parent 和六行 hunk 来源。

fresh-context skill forward test 在不读取本轮聊天结论的情况下，正确把 direct Cluster List/request snapshot 判为 blocking ownership expansion，把 6 行 cursor reset 判为完整 production scope，并允许 E2E 使用有界 cache precondition。说明新增门禁能够复现本次 mentor review 的核心判断。

用户确认执行 1、2、3 后，已用锁定旧 SHA `b2cf85aa3075f4975fe389c65bdd2e1d1648d65e` 的 force-with-lease，把 `origin/feature/reset-affinity-on-reschedule` 和 upstream PR #7791 更新到 `41ed652725fc9169cab111cb0793ff135a037ba7`。PR body 已替换为本页批准稿；原 [scope clarification comment](https://github.com/karmada-io/karmada/pull/7791#issuecomment-5053932300) 已原位编辑为 superseded 说明。逐行回读只有 GitHub API 保留的末尾空行差异，标题和 open/non-draft 状态未变；DCO success，新 upstream checks 已启动。按用户要求没有执行第 4 项，#5425 未评论。

## Upstream 发布记录与批准稿

以下保留已批准并执行的 PR body、旧评论替换稿，以及明确未执行的 #5425 协调评论，便于后续审计。

### PR #7791 body

````markdown
**What type of PR is this?**

/kind feature

**What this PR does / why we need it**:

A WorkloadRebalancer requests complete rescheduling by updating a binding's `spec.rescheduleTriggeredAt`. With multiple `clusterAffinities`, however, the scheduler still starts term evaluation from `status.schedulerObservingAffinityName`, so a recovered earlier term is not reconsidered.

When a timestamp-triggered explicit reschedule is pending, this change restarts top-level `clusterAffinities` evaluation from the first term in policy order, using the scheduler's existing informer-backed snapshot. Scheduling without a pending trigger continues from the observed term.

This fixes the retained affinity-cursor behavior only. It does not add direct Cluster API reads, cache validation, automatic failback, or a one-attempt freshness guarantee. If a recent Cluster update is not yet visible to the scheduler, the caller can wait and issue a newer rescheduling trigger.

**Which issue(s) this PR fixes**:

Fixes #5070

Based on #5425 by @bharathguvvala. The six-line implementation commit preserves Bharath's authorship and sign-off; the tests are kept in a separate commit.

**Special notes for your reviewer**:

- Scope: current `spec.rescheduleTriggeredAt` multi-`clusterAffinities` path only; no API, CRD, generated-code, controller, scheduler-cache, or scheduler-core changes.
- Tests: `go test -race ./pkg/scheduler -run '^TestSchedule(ResourceBinding|ClusterResourceBinding)WithClusterAffinities$' -count=1`, `go test ./pkg/scheduler/... -count=1`, and `go test ./test/e2e/suites/base -run '^$' -count=1` passed. The unit tests cover explicit reset and normal resume for both binding kinds while retaining the existing fallback-to-second-term cases; the E2E covers A -> B -> A after a bounded cache-convergence precondition.
- AI assistance: Codex helped inspect the change and draft tests/text; I reviewed the code and validation results.

**Does this PR introduce a user-facing change?**:

```release-note
`karmada-scheduler`: WorkloadRebalancer-triggered rescheduling now reevaluates multiple `clusterAffinities` in policy order starting from the first term.
```
````

### 旧 scope clarification comment 替换稿

目标：[PR #7791 comment 5053932300](https://github.com/karmada-io/karmada/pull/7791#issuecomment-5053932300)。

```markdown
Update (2026-07-24): this comment described an earlier revision and is superseded by the current diff.

After an offline scope review, I narrowed #7791 back to component-owned behavior: explicit multi-affinity rescheduling resets the persisted top-level affinity cursor, while the scheduler continues to use its normal informer-backed snapshot. The direct Cluster API List, request-scoped snapshot, and all cache/core changes have been removed.

The E2E now establishes a bounded cache-convergence precondition before the one-shot trigger. This PR does not promise API-fresh inputs or one-attempt automatic failback; if a recent Cluster update is not yet visible, waiting and issuing a newer trigger is acceptable.

The current PR body and diff are canonical.
```

### PR #5425 coordination comment（未执行）

```markdown
Hi @bharathguvvala, thank you for the original fix in #5425.

To move this forward on the current master with regression coverage, #7791 has been rebuilt around the same six-line ResourceBinding/ClusterResourceBinding affinity-cursor reset. The implementation commit preserves your authorship, original author date, and sign-off; a separate commit adds current-master unit and E2E tests. I did not import #5425's merge ancestry or unrelated files.

#5425 is explicitly credited in the #7791 body. We can leave this PR open until maintainers decide how to close the duplicate.
```

## Review skill 修正

本次经验同步到：

- `code-review-growth`：新增 Component Responsibility Gate，并把原先“test cache barrier 应推动生产组件保证所有事件顺序收敛”的错误 pattern 改为“时序证据不等于职责归属”。
- `karmada-pr-management`：在设计、文件说明和高风险差分审阅中，要求逐项说明 direct API read、cache validation、retry、watch 和 synchronization 的现有 owner；测试变得稳定不能作为职责转移证据。
- 两项 skill 同时增加 prior-authorship 规则：clean rebuild 必须从 signed historical patch 验证来源，保留原作者和真实 sign-off，把新适配/测试拆到自己的提交，并在 PR body 明确 credit；不能为了保留 credit 而继承污染 ancestry，也不能伪造 sign-off。
