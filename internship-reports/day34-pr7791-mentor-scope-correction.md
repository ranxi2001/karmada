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

## 2026-07-31：#5425 合并后的 rebase

### 先说人话

#5425 已经把 Bharath 的 6 行生产实现合入 `master`，因此 #7791 不应继续重复提交同一份实现。按 `@RainbowMango` 的 [maintainer 要求](https://github.com/karmada-io/karmada/pull/7791#issuecomment-5140455051)，本次把 #7791 rebase 到包含 #5425 的最新 `upstream/master`；Git 自动识别并丢弃重复实现，只重放我们补充的单元测试和 E2E。这样 #5425 记录 Bharath 的实现贡献，#7791 只记录 ranxi 的测试贡献。

### Rebase 与差分证据

- #5425 于 `2026-07-31T07:32:49Z` 合并，merge commit 为 `6de180f72ac0f740401ce4bf4114824f00d1dc90`，并自动关闭 #5070。
- 本地在 `/tmp/karmada-5070-six-line` 执行 `git fetch upstream master` 和 `git rebase upstream/master`。Git 明确报告 `b41507b1f` 的 patch contents already upstream，rebase 无冲突。
- 新 head 为 `11030fbe1816f8ba8aca13a31f2011ac17ff26b0`，只包含 `pkg/scheduler/scheduler_test.go` 和 `test/e2e/suites/base/clusteraffinities_test.go`，合计 `+288/-13`；`pkg/scheduler/scheduler.go` 不再属于 #7791 diff。
- `git range-diff eb2e7c75f..41ed65272 upstream/master..11030fbe1` 显示旧测试提交与新测试提交为 `=`，只有重复实现提交被移除；`git diff --check upstream/master...HEAD` 通过，提交仍含 ranxi 的 DCO sign-off。
- 用户明确要求不继续测试。已启动的 post-rebase race 定向命令在收到中断前打印 `PASS`，但进程最终为 `signal: interrupt` / `FAIL`，因此不把它记为一次 post-rebase pass；PR body 只保留 pre-rebase 已通过验证，并明确披露本轮未重跑。

### Upstream 更新结果

用户确认精确 target、branch、标题和正文后，使用锁定旧 SHA `41ed652725fc9169cab111cb0793ff135a037ba7` 的 `--force-with-lease`，把 `origin/feature/reset-affinity-on-reschedule` 更新到 `11030fbe1816f8ba8aca13a31f2011ac17ff26b0`。`gh pr edit` 因 token 缺少与本操作无关的 `read:org` scope 被 GraphQL 拒绝；随后改用 PR REST `PATCH` 提交同一份已批准文本，未扩大 token 权限。

GitHub 回读确认：

- 标题为 `test(scheduler): cover affinity reset on reschedule`，正文改为 test-only follow-up，关系从 `Fixes #5070` 改为 `Follow-up to #5425` / `Refs #5070`，release note 为 `NONE`。
- PR head、fork branch 和本地 head 都是 `11030fbe1`；只有一个 ranxi author/sign-off 的测试提交和两个测试文件。
- PR 为 open、non-draft、`mergeable=true`，但当前 `mergeable_state=blocked`。force-push 后旧 `lgtm` 已清除，等待新 CI 和 maintainer re-LGTM/approve；不主动发布 `/retest`、催审或标签评论。
- PR body 已写 `/kind cleanup`，GitHub 当前标签仍为旧的 `kind/feature` 与 `size/L`；把它记录为异步/maintainer gate 状态，不为标签同步单独制造 upstream 评论。
- 用户逐字确认后，已在 #7791 发布[礼貌性 rebase 回执](https://github.com/karmada-io/karmada/pull/7791#issuecomment-5140604657)：感谢 maintainer 推动 #5425 合并，并说明 rebase 已去除上游已有实现、当前只保留 unit/E2E regression tests。REST 回读确认作者、正文与批准稿一致；没有附带 `/retest`、mention 或新的 review 请求。

## 2026-07-31：合并与 post-merge Chart 红灯分类

### 先说人话

#7791 已经成功合并，PR 本身的 DCO、compile、unit、三版本 E2E、Chart、CLI 和 Operator checks 全部通过。合并后 `master` 又自动跑了一轮 push workflow，其中 Chart 的 Kubernetes v1.36.1 matrix 显示红灯；它不是 scheduler 或 E2E 回归，而是该 runner 连接 Docker Hub 下载 Helm 依赖时 30 秒 TCP 超时。当前不需要改 #7791、scheduler、tests 或 chart，分类为 `CI external registry / NO_FIX`。

具体例子：三个 runner 同时执行相同的 `helm template --dependency-update ./charts/karmada`。v1.34 和 v1.35 都在几百毫秒内成功拉到 `bitnamicharts/common:2.41.0`；只有 v1.36.1 runner 对同一 manifest 的 `HEAD` 请求一直没有响应，30 秒后报 `dial tcp ...:443: i/o timeout`。这说明依赖和模板能工作，失败的是该 runner 到 registry 的一次网络连接。

### 运行过程与技术证据

1. [PR #7791](https://github.com/karmada-io/karmada/pull/7791) 于 `2026-07-31T08:44:49Z` 合并，merge commit 为 `35ee6092e49918d8d9c1d0642ce1474e774608cc`；PR head `11030fbe1` 的 18 项 checks 全部通过。
2. merge commit 的 push 触发 [Chart run `30617396767`](https://github.com/karmada-io/karmada/actions/runs/30617396767)。v1.34 和 v1.35 jobs 完整通过 template、lint、install 与 operator chart install；[v1.36.1 job `91113656882`](https://github.com/karmada-io/karmada/actions/runs/30617396767/job/91113656882) 在 step `Run chart-testing (template)` 终止，后续步骤全部 skipped。
3. v1.36.1 于 `08:46:27Z` 发起 `HEAD https://registry-1.docker.io/v2/bitnamicharts/common/manifests/2.41.0`；`08:46:57Z` 报 `failed to do request ... dial tcp 18.232.232.248:443: i/o timeout`，随后 Helm 报 `could not download oci://registry-1.docker.io/bitnamicharts/common`。
4. 同一 merge commit 的 v1.34 在 `08:45:35Z`、v1.35 在 `08:45:55Z` 对同一 tag 收到 `200 OK`，解析到相同 digest `sha256:669301594ad66a7401a47d26c6f0b763b95e44af667c57228e552920eb8feb66` 并输出 `Pulled: registry-1.docker.io/bitnamicharts/common:2.41.0`。
5. #7791 residual diff 只有 `pkg/scheduler/scheduler_test.go` 和 `test/e2e/suites/base/clusteraffinities_test.go`；没有修改 `charts/` 或 `.github/workflows/installation-chart.yaml`。workflow 第 83-90 行本来就会在 template 阶段用 `--dependency-update` 访问外部 registry。

### 边界与下一步

这次日志直接证明 transport timeout，但不证明 Docker Hub 全局故障，也不证明 workflow 长期不稳定；当前只有单 runner 单次失败。无需为它增加 scheduler/test retry，也不应把一次外网超时包装成 #7791 产品回归。PR 已合并，不存在 merge gate 动作；等待 maintainer rerun 或下一次 `master` push 即可。只有同类 registry timeout 持续跨 runner、跨 commit 重复时，才值得单独评估 chart dependency cache、镜像源或 workflow-level retry。
