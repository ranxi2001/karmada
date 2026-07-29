# Day 36：2026-07-23 至 2026-07-29 Karmada Issue / PR Review 候选

## 先说人话

这一周真正值得投入 review 时间的，不是 33 个有更新的 PR 全部过一遍，而是先选“正常生产路径会遇到、目前缺少 human review、我们能补充源码或测试证据”的对象。

结论是：**PR #7800 是当前第一 review 候选，Issue #7802 是第一讨论候选。** PR #7794 也有真实问题，但核心缺陷已经被 Copilot 指出，应该等作者更新后复查，不重复留言。PR #7663 生产影响很高，但已有明确 owner、assignee 和多位 requested reviewer，本周不抢占。

> 注释：这里的 `review` 不是“看完标题留一句赞同”，而是核对当前 head、行为合同、并发/生命周期边界和测试能否证明改动没有回归。本文只形成候选和 review 入口，没有发布任何 upstream 评论。

## 扫描范围

- 时间窗口：2026-07-23 至 2026-07-29，按 GitHub `updated` 时间筛选仍为 Open 的对象。
- 扫描时点：2026-07-29（Asia/Shanghai）。
- 结果：5 个 Issue、33 个 PR。
- 排除：自己的 PR #7791、#7795；仅批量补单测、无生产行为变化的 PR；已经有密集 owner/reviewer 处理的对象；mock-only、非法输入或缺少正常生产触发路径的候选。

第一次使用 `gh pr list --json ...` 的 GraphQL 查询失败，因为当前 token 缺少 `read:org` scope。随后改用公开仓库 REST Search/Pulls API，完成相同时间窗口、状态、head、review 和 checks 核对；这不影响公开仓库扫描结论。

## 结论

| 优先级 | 对象 | 当前信号 | 决策 |
| --- | --- | --- | --- |
| P0 | [PR #7800](https://github.com/karmada-io/karmada/pull/7800) `Optimize GetMatching for waiting objects in ResourceDetector` | 4 文件 `+877/-49`，验证 checks 全绿、`tide` 等待 review labels；只有 Copilot summary、没有 human review | 现在做完整 code review |
| P0 | [Issue #7802](https://github.com/karmada-io/karmada/issues/7802) `Respecting binding priority under resource/quota contention` | 新议题，0 comment、0 assignee；生产场景和源码链路具体 | 先做最小队列复现，再准备讨论回复 |
| P1 | [PR #7794](https://github.com/karmada-io/karmada/pull/7794) shell completion timeout | 1 文件 `+46/-24`；实现存在未取消底层请求的问题，但 Copilot 已指出 | 等作者更新后做 patch-equivalent 复查 |
| WATCH | [PR #7663](https://github.com/karmada-io/karmada/pull/7663) rotated bearer token | push-mode informer 失明是高价值生产问题；已有 2 assignee、5 requested reviewer 和较长 review thread | 不抢占，只在新 patch 出现且现有 review 留出空白时补证据 |

## 第一候选：PR #7800

### 为什么值得 review

旧实现的 `ResourceDetector.GetMatching` 会遍历全部 waiting object，并逐个从 informer 取对象、deep copy、再执行 `ResourceMatches`。新实现把 waiting object 改成带 label snapshot 的索引 store，直接处理 exact-name selector，并缩小 label selector 的扫描桶。作者给出了 24,564 个资源、11,216 个 policy 的 live benchmark，说明这是正常规模下的 CPU/分配热点，不是人为构造的异常输入。

当前 head 为 `dc1b9c4a8aa5`。CI 的 compile、unit、lint、codegen 和三个 Kubernetes 版本 e2e 均通过，但还没有 human review。改动同时影响缓存状态、并发读写、资源/策略事件竞态和 selector 语义，review 的收益高于普通测试补充 PR。

### 已核对的行为

1. `waitingObjectStore` 用 primary map 保存不可变 label snapshot，并维护 GVK、GVK/namespace、GVK/name 三类索引。
2. `Name` 存在时忽略 `LabelSelector`，与旧 `ResourceMatches` 的 name precedence 一致。
3. label 变化时 `Upsert` 替换 snapshot，并让资源 reconcile 再 retry 一次，用于覆盖 policy event 与 resource event 并发发生的窗口。
4. 资源 NotFound、被其他控制器 claim、匹配到 PP/CPP，以及 policy 将资源重新入队时都有 `RemoveWaiting` 路径。
5. 新增测试覆盖 store lifecycle、selector differential、并发访问、label stale race 和 benchmark。

### 正式 review 要回答的问题

- waiting store 中的 label snapshot 是否存在无法被后续资源事件刷新、从而永久漏匹配的路径。
- 资源删除与 policy reconcile 并发时，stale key 是否会在 dependent override 检查前后产生可观察的错误重试或阻塞。
- 三类 secondary index 在 `Upsert/Delete`、cluster-scoped resource 和多版本 GVK 下是否始终与 primary map 一致。
- differential test 是否覆盖 namespace/name 不匹配、nil/empty labels、无效 selector 和多 selector 去重等旧语义边界。
- 3 倍索引和 label snapshot 的常驻内存是否有量化；性能收益是否只覆盖 exact-name workload，PR body 是否把 mixed-selector 边界说清楚。

当前初读**没有形成可发布的 blocker**。下一步应在独立 topic worktree 对 current head 运行 `go test`、race 测试和定向补充场景；有源码或测试证明后再起草 review，不能为了“完成 review”硬造问题。

## 第一讨论候选：Issue #7802

这个议题描述 Spark workload 在 capacity / quota contention 下排队：用户希望空出容量后 high-priority binding 先调度，但 binding 从 `backoffQ` 或 `unschedulableBindings` 回到 `activeQ` 的时机不完全由 priority 决定。

对 current `upstream/master` `ce2a7b869477` 的源码核对支持以下事实：

- `activeQ` 的 `Less` 确实先比较 `Priority`。
- `backoffQ` 先按 backoff completion time 排序，只在时间相同的时候用 priority 打破平局；这是为了避免未到期的高优先级对象阻塞已经可重试的对象。
- `unschedulableBindings` 是 map，默认最长停留 5 分钟；flush 时逐个 `moveToActiveQ`。
- `Cluster` update 只在删除开始、labels 或 generation 变化时触发 affected binding requeue，单纯 status/resource summary 变化不走这条路径。

> 分析：议题方向有依据，但“activeQ 总是来不及形成 batch，所以 priority 一定失效”还不能直接当作已证明事实。`flushBackoffQCompleted` 会在一次循环里移动所有已完成 backoff 的 binding；另一方面，scheduler 的 `Pop` 不持有外层 queue lock，可能在逐个 push 期间并发取走第一个元素。需要一个使用 fake clock、受控 worker 的确定性测试，分别测“同时到期”和“错峰到期”，再判断实际顺序。

建议的讨论边界是把两个问题拆开：

1. **唤醒问题**：capacity/quota 释放后，什么权威事件应重新激活 blocked binding。
2. **排序问题**：一批已经具备 retry 条件的 binding 进入 `activeQ` 时，priority 应在哪个阶段生效，同时不能恢复 #6986 修掉的 head-of-line blocking。

Issue 提到的 per-namespace `queueingStrategy` 依赖仍为 Open 且已有 owner/reviewer 的 PR #7485，不宜直接回复“方案正确”。先用测试证明当前顺序，再询问 maintainer 希望把 wake-up 和 ordering 放在 #7485、独立 proposal，还是现有 queue contract 中。

## 其余候选为什么不优先

- Issue #7801 偏 AI Agent Skills guardrail，不是 Karmada 核心运行路径。
- Issue #7793 已由 PR #7794 实现；其关键问题已被 bot review 捕获，重复评论没有新增价值。
- Issue #7768 与 PR #7771 是宽泛的对象约束/CRD 扩展，缺少比现有 owner 更强的生产需求证据，且 PR 已扩到 24 个文件。
- Issue #7562 / PR #7663 生产影响高，但 ownership 和 review 已饱和；适合观察最新 patch，不适合本周抢占。
- PR #7770、#7778 有正常环境价值，但已有 review 或合并门禁；优先级低于无 human review 的 #7800。
- 大批 `test: add unit tests` PR 主要增加覆盖率，没有清晰生产行为缺口，按 production relevance gate 不做深挖。

## 下一步

1. 从最新 `upstream/master` 创建独立 review worktree，检出 PR #7800 current head，完成 store lifecycle、事件竞态和 selector 等价性 review。
2. 为 Issue #7802 写一个不改产品代码的最小 scheduler queue 测试，记录同时到期、错峰到期和并发 `Pop` 的实际顺序。
3. PR #7794 只在作者更新后复查底层 REST request 是否真正有 timeout/cancellation，并确认没有残留 goroutine。
4. 任何 upstream review/comment 的 exact target 和英文正文先交给用户确认，再发布。
