# Day 36：Issue #7802 调度优先级队列确定性实验

## 先说人话

本轮要验证的不是“priority 有没有用”，而是更窄的一个问题：多个 blocked binding 重新进入可调度队列时，调度器是否一定有机会把它们放在一起比较优先级。

具体例子是 `low-A`、`low-B`、`high-C` 都因容量不足而等待。容量释放后，如果三者先全部进入按 priority 排序的 `activeQ`，`high-C` 会先出来；如果 flush 每放入一个 binding，scheduler worker 就能立刻 `Pop` 一个，那么第一个迁入的低优先级 binding 可能在 `high-C` 尚未进入 `activeQ` 时被取走。后者不是 priority heap 排错，而是“比较发生前，候选集合还没有形成”。

当前只做 source-proven 的队列实验，不改产品逻辑，不承诺 per-namespace `queueingStrategy`，也不把构造的 interleaving 写成已经发生的线上故障。

## 问题与现有责任边界

- 目标 Issue：[karmada-io/karmada#7802](https://github.com/karmada-io/karmada/issues/7802)
- 实验基线：`upstream/master` `ce2a7b869477272202095282251afe490c38d525`
- 生产对象：调度队列（`prioritySchedulingQueue`）负责保存、退避和重新激活 binding；单个 scheduler worker 负责从 `activeQ` 取一个 binding 并执行 scheduling。
- 已知合同：`activeQ` 只对“同时存在于该 heap 的 binding”按 priority 排序；`backoffQ` 先按 backoff completion time 排序；`unschedulableBindings` 是 map。
- 本轮验证问题：flush 的逐项 `Push` 与并发 `Pop` 是否允许 worker 在整个 eligible batch 迁入前取走首项，以及这个事实能证明 issue 的哪些部分。

## 修改范围

| 文件 / 区域 | 改动类型 | 原因 | 风险 | 验证 |
| --- | --- | --- | --- | --- |
| `/tmp/karmada-issue7802-review/pkg/scheduler/internal/queue/issue7802_review_test.go` | 临时 review-only test | 注入受控 `ActiveQueue`，固定 `Push -> Pop -> remaining Push` 时序 | 只验证队列机制，不能代表线上频率 | focused test、race、重复运行 |
| `internship-reports/day36-issue7802-priority-queue-experiment.md` | 本地证据记录 | 保存设计、失败实验、源码和结论 | 无产品行为变化 | Markdown/link/diff check |
| `internship-reports/day36-issue7802-comment.md` | 已发布英文评论原文 | 给 issue 作者可独立理解的证据边界 | 后续编辑或回复仍需重新授权 | concise metrics、远端逐字回读 |
| `internship-reports/day36-issue7802-queue-reentry.mmd/.png` | canonical Mermaid + render | 展示 flush、activeQ、worker 的真实时序 | 图不能把可能 interleaving 画成固定线上频率 | `mmdc` render + 图片检查 |

## 明确不改

| 文件 / 区域 | 原因 |
| --- | --- |
| `pkg/scheduler/internal/queue/*.go` | 尚未确定缺陷合同和可接受方案，不先改锁、批量接口或排序 |
| `pkg/scheduler/event_handler.go` | “容量释放由谁唤醒 blocked binding”是独立 ownership 问题，本轮先证明现状 |
| API、CRD、feature gate | maintainer 尚未确认 per-namespace strategy 或新的用户合同 |
| 现有 upstream tests | review-only 实验在结论形成后删除，不把未批准方案伪装成回归测试 |

## 实验矩阵

| 场景 | 固定条件 | 要区分的结论 |
| --- | --- | --- |
| `activeQ` 已同时包含 high/low | 两个对象先 `Push`，再 `Pop` | 基础 priority heap 是否正确 |
| 相同 backoff completion | high/low 同时 eligible，worker 在首个 `Push` 后立刻 `Pop` | `backoffQ` tie-breaker 是否先迁 high |
| 错峰 backoff completion | low completion 更早，但 flush 时 high/low 都已 eligible；首个 `Push` 后立刻 `Pop` | earlier completion 是否能在 batch 未形成时越过 high |
| 错峰 completion、无并发 Pop | flush 完成后才 `Pop` | 一旦候选全部进入 `activeQ`，priority 是否恢复正确 |
| `unschedulableBindings` 到期 | 多个对象均超过 5 分钟，worker 等待首个 `Push` | map 顺序与逐项迁移是否存在相同窗口；区分机制可能性和稳定顺序 |
| wake-up 来源 | source trace，不注入虚构事件 | backoff timer、5 分钟 sweep、Cluster update、binding delete 各自能否触发 re-admission |

## 实验设计

1. 先运行现有 `go test ./pkg/scheduler/internal/queue -count=1` 建立 baseline。
2. 临时 test 使用 fake clock 控制 eligibility，使用包装的 `ActiveQueue` 在第一次 `Push` 后暂停 flush。
3. 用真实 `prioritySchedulingQueue.Pop()` 取首项，不能直接读取 heap 来代替 worker 行为。
4. focused test 运行 `-count=100`，再用 `-race -count=20` 检查测试自身没有 race。
5. 删除临时 test 后重跑原包测试，确保 review worktree 干净。
6. 对 source trace 和测试结论做独立反证；只将稳定结论写入 upstream 草稿。

## 结论

Issue #7802 找到的是一个真实但需要收窄的边界：priority heap 没有排错；问题发生在一批 blocked bindings 逐项回到 `activeQ` 时，worker 可以在候选集合尚未完整形成前取走第一项。

- `backoffQ` 中，如果 low 的 backoff completion 更早，而且 flush 时 low/high 都已经到期，low 会先迁入。等待中的 worker 可以在第一次 `Push` 后立刻 `Pop` low；如果 flush 先把两者都迁完，`activeQ` 仍会正确地先返回 high。
- `unschedulableBindings` 先按 Go map 的未定义迭代顺序收集到 slice，再逐项迁入，因此也存在同一个窗口。
- 该窗口在一次周期性 flush 中最多提前取走一个 binding，不是 Issue 所说的 worker 把整批对象持续逐个 drain。唯一 worker 要进入下一次 `Pop`，必须先完成会获取外层锁的 `handleErr`；这次加锁不可能早于 flusher 释放同一把锁，所以剩余 eligible bindings 会先迁完。
- 容量或 quota 释放没有直接唤醒这些 blocked bindings，这是另一条独立问题；不能用 readmission 顺序修复替代事件唤醒设计。
- 当前官网明确写了资源竞争下的 `strict priority order`，所以用户期待有依据；但仓库内已合入的原 proposal 又明确说 unschedulable high 在未启用 preemption 时不一定先于 low。社区需要先明确合同，再决定修实现还是修文档。

因此本轮不建议直接提产品 PR，也不建议先把方案绑定到 #7485。更合适的下一步是在 #7802 提供这个有边界的验证，请 maintainer 决定 priority 合同究竟只覆盖“同时位于 `activeQ` 的对象”，还是覆盖“同一次重新可调度机会中的所有 blocked bindings”。

## 一个具体例子

假设 low 的退避结束时间是 `10:00:01`，high 是 `10:00:02`。flush 在 `10:00:03` 执行，因此两者现在都具备重试资格：

1. `backoffQ` 先取出 completion 更早的 low。
2. flusher 把 low 放进 `activeQ`，`activeQ.Push` 立即唤醒 worker。
3. 如果 worker 先抢到 `activeQ` 自己的锁，它此时只能看到 low，于是 `Pop` low。
4. flusher 随后才把 high 放进 `activeQ`。

反过来，如果第 2 步后 flusher 继续运行，先把 high 也放进去，`activeQ` 同时看到 high/low，就会按 priority 先返回 high。

> 注释：这里的 priority 只比较“当前已经在候选集合里的对象”。high 还在 `backoffQ` 时，`activeQ` 无法拿一个尚不存在的对象参与排序。

受控时序见 [Mermaid 源码](day36-issue7802-queue-reentry.mmd) 和 [PNG](day36-issue7802-queue-reentry.png)。canonical source 是 `.mmd`，PNG 由项目 `render_mermaid.py` 通过固定的 `@mermaid-js/mermaid-cli@11.16.0` npx backend 生成。

## 运行过程与锁边界

### 三种保存位置

| 名称 | 人话含义 | 主要排序 | 何时回来 |
| --- | --- | --- | --- |
| `activeQ` | 现在就可以交给 scheduler 尝试的 bindings | priority 降序，同 priority 按当前入队时间 | `Push` 后立即 signal worker |
| `backoffQ` | 出现普通 error 后，先等短暂退避再重试 | backoff completion 升序；completion 相同才比较 priority | 每 1 秒周期性 flush，默认退避 1 至 10 秒 |
| `unschedulableBindings` | scheduler 明确判断当前没有可行集群的 bindings | Go map，没有队列顺序 | 外部事件 `Push`，或超过 5 分钟后由 30 秒 sweep 兜底 |

> 注释：binding 是 Karmada 给一个待传播 workload 生成的调度对象。这里讨论的不是 member cluster 内 Kubernetes Pod 的 `Pending`，而是 Karmada 控制面决定 binding 应该放到哪些集群之前的队列。

### 两把锁没有形成批量屏障

1. `flushBackoffQCompleted`、`flushUnschedulableBindingsLeftover`、`Push`、`handleErr` 的重新入队操作使用 `prioritySchedulingQueue.lock`。
2. `activeQ` 有另一把 `sync.Cond` mutex，单次 `Push` 和 `Pop` 分别获取它。
3. `prioritySchedulingQueue.Pop` 不获取外层 lock，直接进入 `activeQ.Pop`。
4. `moveToActiveQ` 先执行一次 `activeQ.Push`，该调用插入一个对象并 `Signal`，然后才从 blocked stores 删除它。
5. 因此外层 lock 能阻止其他 producer 和另一轮 flush 干扰，却不能阻止 worker 在同一批的两次 `Push` 之间执行一次 `Pop`。

竞态可达来自 flush goroutine 与 worker 并发运行，而且 `Pop` 不获取外层 lock。生产调度器只有一个 serial worker，这个事实只负责限制影响范围：worker 提前拿到首项后要完成 `doSchedule -> handleErr`，而 `handleErr` 的 `Forget`、`PushUnschedulableIfNotPresent`、`PushBackoffIfNotPresent` 都会再次获取外层 lock。无论 `handleErr` 到达时是否真的发生等待，它都不能在本轮 flusher 释放锁前完成加锁并进入下一次 `Pop`。

## 确定性实验

实验使用 package-local fake clock 固定 eligibility，并用一个包装真实 `ActiveQueue` 的 gate 在第一次 delegated `Push` 完成后暂停 flusher。主测试仍调用真实 `prioritySchedulingQueue.Pop()`，没有直接读取 heap 冒充 worker 行为。

| 场景 | 首个 `Pop` | 说明 |
| --- | --- | --- |
| high/low backoff completion 完全相同，首个 `Push` 后插入 `Pop` | high | `backoffQ` 的 completion tie-breaker 已按 priority 选 high，Issue 不能泛化为“backoff 一律忽略 priority” |
| low completion 更早、两者在同一 flush 都已到期，首个 `Push` 后插入 `Pop` | low | 证明不完整候选集合下的反转顺序可达 |
| 同样的错峰 completion，但等待整批 flush 后才 `Pop` | high | 证明 `activeQ` heap 本身正确 |
| 两个对象都超过 unschedulable 期限，首个 `Push` 后插入 `Pop` | 第一个 map entry | 证明 map 决定第一个暴露给 worker 的对象；实验观察到 low-first，但具体 map 顺序不是稳定测试合同 |

执行结果：

```text
go test ./pkg/scheduler/internal/queue -count=1
PASS

go test ./pkg/scheduler/internal/queue -run '^TestReviewIssue7802' -count=100
PASS

go test -race ./pkg/scheduler/internal/queue -run '^TestReviewIssue7802' -count=20
PASS

# 删除 review-only test 后
go test ./pkg/scheduler/internal/queue -count=1
PASS；review worktree clean
```

`unschedulableBindings` 测试的通过条件是确定性的：`Pop` 必须返回本轮 map 实际选出的第一个 entry，而不要求这个 entry 必须是 low。low-first 只作为重复运行中的观测统计，不参与 pass/fail。这个边界避免让概率决定测试结果；稳定结论只是“迭代顺序未定义且首个 entry 可先被 Pop”，不是每次一定 low-first。临时测试只作为 review evidence，任务结束前删除，不进入 upstream commit。

在当前 Go runtime 上单独重复该测试 100 次，观测为 `low-first=100`、`high-first=0`。这是环境观测，不是 Go map 的排序合同，也不用于证明生产发生频率。

## 调试过程与失败记录

| 步骤 | 失败现象 | 原因 | 处理 |
| --- | --- | --- | --- |
| 首次 Mermaid render | `Parse error` 指向第一条 Note 之后 | Note 文本中的 `;` 被 Mermaid 当作语句分隔符 | 改为 `<br/>`，使用 pinned npx backend 重渲并人工检查 PNG |
| 首次 map 观测统计 | `awk: backslash not last character on line` | 嵌套 shell 中的 `$0` 被提前展开 | 改用不含 shell 变量的 `rg -o -> sort -> uniq -c` 管道 |
| 初版 unschedulable test | 100 次内未遇到 low-first 就 fail | pass/fail 依赖未定义的 map 顺序，属于概率测试 | 改为确定性断言 `firstPopped == firstPushed`，priority 只写日志 |
| 首次远端正文 `cmp` | 评论内容相同但 `cmp` 返回 1 | `gh api --jq .body` 在正文自带结尾换行后又输出一个换行 | 改用 `gh api | jq -j .body` 保留原始 body bytes，哈希和 `cmp` 均一致 |

这些失败没有改变产品结论。前三项暴露了两个测试纪律：解析器保留符号必须以真实 render 验证；未定义顺序可以作为观测，不能成为回归测试的通过条件。远端回读还说明 CLI 展示格式与 stored body bytes 要分开验证，精确比较应使用不追加换行的 raw 输出。

## 反证：Issue 哪些话成立，哪些需要收窄

| Issue 表述 | 判定 | 证据边界 |
| --- | --- | --- |
| priority 只比较同时位于 `activeQ` 的 bindings | 确认 | `activeQ` 无法比较仍在 blocked store 的对象 |
| earlier backoff expiry 可使 low 先于 high | 有条件确认 | 两者同时 eligible，且 worker 在第一、第二次 `Push` 之间运行时成立；若仅 low 到期，则属于正确 eligibility policy |
| unschedulable map 顺序可影响首个调度对象 | 确认可达 | map entry 逐项 `Push`，`Pop` 绕过外层 lock；线上发生频率未知 |
| worker 持续把整批 activeQ 逐个 drain，priority 几乎没有比较机会 | 需要收窄 | 单 worker 在一次 flush 最多提前取一个；第二次 `Pop` 必须晚于 flusher 释放外层 lock |
| quota/capacity 释放会立即重新激活 blocked bindings | 否定 | 当前没有对应 scheduler binding requeue event；依赖外部相关事件或周期性兜底 |
| 所有 FederatedResourceQuota 失败都进 `backoffQ` | 尚未完整证明 | generic patch/status error 会走 backoff；estimator 返回的明确 `Unschedulable` 结果可走 unschedulable，不能按 quota 名称一概而论 |
| 当前行为确定违反了唯一明确的社区合同 | 尚待 maintainer 决策 | 官网与 merged proposal 的表述强度不一致 |

> 分析：确定性队列测试证明的是 concurrency schedule 的可达性，不是 Spark 生产环境的发生概率、SLA 损失大小或 quota 释放后的最终成功顺序。要证明这些，还需要真实 cluster trace 或最小集成复现。

## 事件唤醒是另一条问题

- `ResourceBinding` 删除 handler 只更新 workload-affinity / overcommit cache，没有遍历并重新激活其他 blocked bindings。
- 启用 scheduler estimator 时，每次 `Cluster` update 都会 enqueue estimator worker；但 binding requeue 只在 deletion 开始、labels 变化或 `Generation` 变化时触发。纯 `Status.ResourceSummary` 变化不会调用 `enqueueAffectedBindings`。
- `PushBackoffIfNotPresent` 和 `PushUnschedulableIfNotPresent` 本身不会 signal `activeQ`。
- backoff 由 1 秒周期检查兜底，completion 结束后通常在下一次检查获得迁入机会；锁竞争、上一轮 flush 耗时、`activeQ` backlog 和忙碌 worker 都意味着实际开始调度没有 1 秒上界。unschedulable 路径使用严格的 `age > 5m`，达到条件后还要等一次 30 秒周期检查，并受同样的队列/worker 延迟影响。

这说明两个设计问题不能混为一个：

1. **何时重新有资格尝试**：容量/配额变化由谁拥有、谁发事件、哪些 bindings 受影响。
2. **同一次机会先尝试谁**：需要比较的候选集合和 priority 合同是什么。

增加 event-driven wake-up 会改善等待时间，但如果 event handler 仍逐项 `Push`，worker 仍可能在第一项后运行；增加 batch/atomic admission 会改善同批排序，却不会让 5 分钟内没有事件的对象更早回来。

## 文档与历史合同

### 支持 Issue 用户期待的证据

- [当前 Priority Scheduling 用户指南](https://karmada.io/docs/userguide/scheduling/priority-scheduling/) 明确写了 resource contention、`strict priority order` 和 priority 只影响 scheduling order。该页面来自 [website PR #822](https://github.com/karmada-io/website/pull/822)，由 maintainer review、`/lgtm`、`/approve` 后合并，不只是 Issue 作者自己的解释。
- API 注释写明 higher/lower priority 可控制哪些 workloads 先被调度。
- merged proposal 的 user story 也要求资源竞争时 high-priority workloads ahead of others，test plan 包含 bindings scheduled by priority。

### 限制严格保证的证据

- 同一个 [binding priority proposal](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/docs/proposals/scheduling/binding-priority-preemption/README.md#effect-of-priority-on-scheduling) 在 design details 又写明 high priority 只是有更高机会；如果 high 因资源不足 unschedulable 且未启用 preemption，Karmada 会继续尝试 low。
- 这不是偶然措辞：在 [Proposal #4993 的 maintainer 讨论](https://github.com/karmada-io/karmada/pull/4993#discussion_r1797541929) 中，社区明确选择“不让一个当前不可行的 high 阻塞其后的 low”，以避免没有 preemption 时的全局 head-of-line blocking。
- 这项 alpha feature 没有定义“同时 eligible”“同时 resident in activeQ”“一次容量释放机会”或 blocked queue readmission 的正式范围。

因此不能简单回答“实现肯定符合合同”或“实现肯定违反合同”。现行用户文档确实比实现和原 proposal caveat 更强，最先需要的是 maintainer 明确语义。

## Prior Art 与 #7485

- [Issue #6986](https://github.com/karmada-io/karmada/issues/6986) 是源码阅读发现、不是生产 incident；它证明旧 `backoffQ` priority-first heap 会让尚未到期的 high 卡住已经到期的 low。[PR #6987](https://github.com/karmada-io/karmada/pull/6987) 因此有意改为 completion-first、priority tie-breaker。任何方案都不能重新引入 head-of-line blocking。
- #6987 的 [maintainer review](https://github.com/karmada-io/karmada/pull/6987#discussion_r2580444735) 还明确保留了原生产 flush loop，只把便于测试的提取逻辑放回单测。这体现了“先维护 eligibility、不要为了测试引入生产抽象”的既有偏好，但它没有评审过本轮发现的 `flush -> activeQ -> Pop` 并发边界。
- [PR #7485](https://github.com/karmada-io/karmada/pull/7485) 是一个 open proposal，目标是 per-tenant queue sharding、cross-tenant fairness，以及 `BestEffortFIFO` / `StrictFIFO` 的 head-of-line 行为。它当前没有 human design review、`lgtm` 或 `approved`；两位参与者只执行了 `/assign`。
- #7485 自己把 backoff/unschedulable 数据结构变化列为 non-goal。它的 `queueingStrategy` 回答“同一 tenant 遇到 unschedulable head 后是否继续尝试后项”，并不自然等于“blocked batch 回来时是否做全局 priority barrier”。

所以 #7485 可以作为未来多租户上下文，但目前不是已经认可、也不是明显正确的 #7802 修复接口。

## 方案空间与建议顺序

| 方向 | 能解决什么 | 主要代价 / 未决问题 | 当前建议 |
| --- | --- | --- | --- |
| 只修文档，明确 priority 仅保证当前 `activeQ` | 消除过强承诺 | 用户在 contention 下的核心需求仍未满足 | 仅在 maintainer 明确拒绝全局合同后 |
| flush 先收集、批量放入 `activeQ`，再唤醒 worker | 同一 flush batch 可以完整比较 priority | 需要新的 batch API/锁边界；不解决事件唤醒；要保持 #6986 eligibility | 合同确认后可做最小原型 |
| 容量/quota 释放时 event-driven requeue | 缩短 timer 等待 | 需要 authoritative event、affected-binding 范围和风暴控制；逐项 `Push` 仍有 interleaving | 独立 proposal/issue，先定 ownership |
| per-tenant `queueingStrategy` | tenant isolation / HOL policy | API 面大；与 readmission priority 不是同一维度 | 不作为首个修复 |
| preemption | high 可腾出运行容量 | Issue 已说明 Spark batch 不适合直接丢弃运行工作；功能也尚不可用 | 非本 Issue 首选 |

已发布 [英文评论原文](day36-issue7802-comment.md)，请求 maintainer 定义合同。若答案要求“同一轮已经 eligible 的 blocked bindings 严格比较 priority”，再以 batch admission 为最小实验，不先扩展 API。

## 技术证据索引

- 队列默认时间、flush、comparator 和迁移：[scheduling_queue.go](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/internal/queue/scheduling_queue.go#L38-L52)、[flush and Pop](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/internal/queue/scheduling_queue.go#L184-L299)、[moveToActiveQ](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/internal/queue/scheduling_queue.go#L342-L347)
- 单项 signal 和独立 `Pop` mutex：[active_queue.go](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/internal/queue/active_queue.go#L72-L125)
- 单 worker 与 error 分类：[scheduler.go](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/scheduler.go#L327-L381)、[handleErr](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/scheduler.go#L933-L945)
- binding delete / cluster update event：[event_handler.go](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/scheduler/event_handler.go#L248-L353)
- API priority 注释：[propagation_types.go](https://github.com/karmada-io/karmada/blob/ce2a7b869477272202095282251afe490c38d525/pkg/apis/policy/v1alpha1/propagation_types.go#L204-L216)

## Upstream 发布记录

- 目标：[karmada-io/karmada#7802](https://github.com/karmada-io/karmada/issues/7802)
- 已发布评论：[issuecomment-5114587741](https://github.com/karmada-io/karmada/issues/7802#issuecomment-5114587741)
- 发布者与时间：`@ranxi2001`，2026-07-29 15:37:57（Asia/Shanghai）
- 发布规模：179 visible words；Issue 发布后仍为 Open、无 assignee，评论数从 0 变为 1。
- 原文校验：本地文件与 GitHub remote body 的 SHA-256 均为 `af24238b28472b6be7b0f65deac0638a4f650f62ade42eba091e5e02d20ade74`；`jq -j .body` 后 `cmp` 通过。
- 边界：这条评论请求 maintainer 明确合同，没有承诺实现、认领 Issue、提出 API 或请求特定 reviewer。

## 未决边界与下一步

1. 等 Issue 作者或 maintainer 回复并明确 strict priority 的候选范围；未确认前不改 scheduler queue/API。
2. 若需要实现保证，先写一个 tracked regression test，固定 `eligible batch -> admission barrier -> Pop`，同时保留 #6986 的 completion eligibility。
3. 将 capacity/quota event-driven wake-up 作为独立 ownership 调研，不用一个锁或 retry patch 同时承担两项合同。
4. 后续任何 follow-up、maintainer mention 或实现承诺，仍需用户确认新的 exact target/text。
