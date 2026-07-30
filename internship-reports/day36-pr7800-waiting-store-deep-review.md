# Day 36：PR #7800 ResourceDetector waiting store 深度 Review

> 2026-07-30 更新：作者在新 head `038e34d0d134` 中采用稳定候选指针和紧凑 name-index slice，并补充 forced-GC retained-heap 数据。本地同规模复测与作者结果一致，原 non-blocking finding 已得到实质处理；详见文末更新复核。

## 先说人话

结论：对 [PR #7800](https://github.com/karmada-io/karmada/pull/7800) current head `dc1b9c4a8aa5` 完成源码、并发、语义和性能复核后，**没有找到可以证明会造成永久漏匹配或错误绑定的 correctness blocker**。新 store 把一次 exact-name 查询从约 70 ms 降到约 1.4 us，方向和收益都成立。

但它不是“只加几个索引、几乎没有代价”。用 PR 自己采用的 24,564 个等待对象规模复测：旧 key-only map 常驻约 3.15 MB，新 store 保存一个 label 并维护三类索引后常驻约 40.56 MB，增加约 37.41 MB。即使不保存 label，新索引仍约 32.30 MB；清掉 `byGVKName` 后只剩约 9.64 MB，说明每个唯一对象名对应的 singleton set 是主要内存来源。

具体例子：24,564 个 Deployment 都先于 PropagationPolicy 到达，因而暂存在 waiting store。新实现之后，policy 按 namespace + name 查一个 Deployment 几乎立即返回；但每个 waiting object 同时都进入 GVK、GVK/namespace、GVK/name 三个索引。PR 的 exact namespace + name 快路径实际只读 primary `objects` map，仍为另外 24,564 个唯一 name 保留了 24,564 个小 set。跨 namespace 的同名选择器确实需要 name lookup，所以这里不是要求直接删索引，而是要求把常驻内存代价量化清楚，或改用更紧凑的数据结构。

> 注释：`waiting object` 是“暂时还没匹配到传播策略、等待策略到来后重新触发处理”的资源。它不是 member cluster 里的 Pod，也不是失败资源；这里保存的是控制面中待重新匹配的 resource key 和 label 快照。

## Review 范围

- PR：`Optimize GetMatching for waiting objects in ResourceDetector`
- Base：`ce2a7b869477272202095282251afe490c38d525`
- Head：`dc1b9c4a8aa55100e6b35dfda4cefff82725e469`
- Diff：4 files，`+877/-49`
- 当前讨论：没有 human review finding；Copilot 只有 summary，Gemini 是 sunset bot，另有 approval/Codecov bot。
- 当前 CI：DCO、compile、unit、lint、codegen、3 组 Kubernetes version tests 和 3 组 e2e 均通过；`tide` 仅因缺少 `lgtm/approve` pending。

本轮使用独立 worktree `/tmp/karmada-pr7800-review`，没有把上游源码或临时测试混入 `intern` 分支。

## 改动模型

| 行为面 | 旧实现 | 新实现 | Review 结论 |
| --- | --- | --- | --- |
| 等待状态 | `map[ClusterWideKey]struct{}` | primary map 保存 immutable label snapshot | label 通过 `maps.Clone` 隔离，更新时替换指针 |
| 候选查找 | 遍历全部 key，再通过 informer/API 取对象和 deep copy | GVK、GVK/namespace、GVK/name 三类索引缩小候选 | 查询成本显著下降，索引常驻内存增加 |
| exact namespace + name | 仍遍历全部 waiting key | 直接查 primary map | 语义等价，约 5 万倍量级加速 |
| label selector | 每个对象走 `ResourceMatches` | selector 编译一次，对 label snapshot 匹配 | differential test 覆盖正常 selector 语义 |
| 新增/label 变化 | 第一次进入 waiting 后重试一次 | 新增或 labels changed 都让 resource reconcile 重试 | 能修复 policy/resource 同时到达和 stale label 窗口 |
| 删除 | 从单 map 删除 | 在一把写锁下删除 primary 和三类索引 | 未发现 index/primary 可永久分叉的路径 |

## 运行过程

资源先到而 policy 尚未可见时，`propagateResource` 调用 `AddWaiting(key, labels)`。第一次插入或 label snapshot 变化会返回 error，使 workqueue 按原有合同重试。policy 后续出现时，policy reconcile 用 selector 查询 waiting store，先删除命中的 waiting key，再把资源重新放入 resource worker；创建 ResourceBinding 的权威路径仍是 resource reconcile，policy reconcile 不越权创建 binding。

以下路径会清理 waiting state：

1. 资源已经删除，resource reconcile 收到 NotFound。
2. 资源带有 `ResourceTemplateClaimedByLabel`，已由其他控制器接管。
3. resource reconcile 找到匹配的 PP/CPP。
4. policy reconcile 匹配 waiting object 并将其重新入队。

并发方面，`Upsert/Delete` 在同一写锁内同步更新 primary 和索引；`candidates` 在读锁内复制 key 与 immutable object pointer，再释放锁做 label 匹配。更新不会原地修改 map，而是替换 `waitingObject` 指针，因此 race detector 未发现并发读写。

## 技术证据

### 正确性与并发

- `go test ./pkg/detector -count=1`：通过，`ok ... 1.216s`。
- `go test -race ./pkg/detector -run '^(TestWaitingObjectStore|TestResourceDetectorWaiting)' -count=10`：通过，`ok ... 26.693s`。
- 新增测试覆盖 lifecycle、四类 index path、name precedence、label selector、invalid selector、multi-selector union/dedup、随机 differential、concurrent access、stale label race 和 policy requeue ownership。
- `git diff --check upstream/master...HEAD`：通过。

### 查询性能

命令：

```bash
go test ./pkg/detector -run '^$' \
  -bench 'Benchmark(LegacyWaitingExactName24564|WaitingObjectStoreExactName24564|LegacyWaitingLabelSelector24564|WaitingObjectStoreLabelSelector24564|WaitingObjectStoreMatchAll24564)$' \
  -benchmem -benchtime=10x -count=3
```

| 场景 | 旧实现 | 新实现 |
| --- | --- | --- |
| exact namespace + name | 68.1-73.7 ms/op；约 25.15 MB/op；196,513 allocs/op | 1.28-1.52 us/op；272 B/op；3 allocs/op |
| namespace + label | 75.99-76.76 ms/op；约 25.44 MB/op；约 199,725 allocs/op | 246.6-388.6 us/op；143,484 B/op；27 allocs/op |
| GVK match-all | 本轮未重复旧实现 | 32.86-35.50 ms/op；约 10.42 MB/op；147 allocs/op |

这些数据证明 PR 的查询优化不是噪声。尤其 exact-name lookup 已从全表扫描变成 primary map lookup。

### 常驻内存反证实验

review-only 测试在构建输入之后采样 HeapAlloc，并用 `runtime.KeepAlive` 保持输入夹具存活，避免把输入回收误算成实现收益。每个场景使用独立 `go test` 进程，重复 5 次：

| 24,564 waiting objects | 5 次范围 | 相对旧 map |
| --- | --- | --- |
| 旧 `map[ClusterWideKey]struct{}` | 3.145-3.151 MB | baseline |
| 新 store，nil labels，三类索引 | 32.304-32.306 MB | +约 29.16 MB |
| 新 store，一个 label，三类索引 | 40.558-40.559 MB | +约 37.41 MB |
| 新 store，nil labels，GC 前仅清掉 `byGVKName` | 9.638-9.639 MB | +约 6.49 MB |

构建 benchmark 也显示旧 map 约 6.29 MB/op、144 allocs/op，新 store 约 52.62 MB/op、123,409 allocs/op。它衡量构建期总分配，不等于常驻内存；上表才用于说明 persistent footprint。

最开始的组合测试曾得到约 30 MB 和一次约 40 MB 的不一致结果。原因是多个 store 在同一测试函数顺序测量，编译器栈存活期可能让前一个值跨入后一个样本。拆成独立 test process 后，又发现旧 map 不引用输入 labels，GC 会提前回收测试夹具，甚至产生负 delta；补上 `runtime.KeepAlive(inputs)` 后，三组数据才稳定。这个失败过程保留在记录里，避免把有污染的漂亮数字当证据。

## Finding

### Non-blocking：PR 缺少常驻内存边界

源码锚点是 `pkg/detector/waiting_store.go:102-106`：每个新 waiting object 都会进入 primary map 和三个 secondary indexes。`byGVKName` 为大量唯一 name 建立 singleton set；在本轮分布中，它单独贡献约 22.67 MB。与此同时，PR 的 exact namespace + name benchmark 在 `candidates` 中直接查询 `objects`，不读取 `byGVKName`。

这不推翻优化：旧实现每次查询产生约 25 MB 临时分配，新实现在频繁查询下显著降低 CPU 和 GC 压力。缺口是 PR body 的 `alloc_space` 查询 profile 没有展示“很多资源等待 policy 时”会持续保留多少 heap，maintainer 无法从现有数据判断这项 trade-off 的峰值是否可接受。

建议请求作者补同规模 `inuse_space` 或 retained-heap 数据，并在以下两种行动中至少完成一种：

1. 记录和接受有 workload 分布依据的容量上界。
2. 将高基数 name bucket 改为更紧凑表示，或只在确实需要无 namespace name selector 时承担该索引成本。

英文 line-comment 原文保存在 [day36-pr7800-review-comment.md](day36-pr7800-review-comment.md)，并已发布为 [discussion_r3671589022](https://github.com/karmada-io/karmada/pull/7800#discussion_r3671589022)。该 finding 定为 non-blocking evidence gap，不表述成已发生 OOM，也不要求未经证明的具体数据结构。

## 独立反证与未决边界

本轮专门尝试把两个候选风险推翻，而不是为了留下评论硬造 blocker：

- **stale label 永久漏匹配**：resource label update 会通过 `SpecificationChanged` 入队；`Upsert` 看到 label 变化会再次 retry。policy 与 update 穿插时可能短暂读取旧 snapshot，但能由资源事件或 retry 收敛，未构造出 no-self-heal 路径，因此不发布为 finding。
- **多个 selector 读取非线性快照**：`Match` 每个 selector 分别取候选，理论上可跨越一次并发 `Upsert/Delete`。但 insert/label change 会触发 resource retry，Delete 对应资源删除、claimed 或已匹配路径；现有合同下未证明会永久错误，因此不升级为 blocker。
- **常驻内存 finding**：通过独立进程、5 次重复、nil-label 对照和移除 name-index 对照后仍稳定；同时明确承认旧实现的每次查询临时分配远大于新实现。这使结论保持为“需要量化的 CPU/内存 trade-off”，而不是片面否定 PR。

剩余风险是实际 heap 取决于 GVK、namespace、name 基数、label 数量和 waiting duration。本轮没有运行完整 live cluster，也没有长时间 churn 后的 heap profile；因此不声称 40.56 MB 是所有集群的固定值。

## 下一步

1. 已在 PR #7800 `waiting_store.go` 的 `byGVKName` 插入行发布 non-blocking comment；作者回应和新实现已于 2026-07-30 复核。
2. 当前不追加 correctness 或 memory review finding；closure reply 已发布，等待作者或 maintainer resolve thread，并等待 current-head CI 和 maintainer review。
3. 不把本地微基准写成线上 OOM 证明；实际 heap 仍取决于 GVK、namespace、name、label 基数和等待时长。

## 2026-07-30 作者回应与新 Head 复核

### 结论

作者先在 [line thread](https://github.com/karmada-io/karmada/pull/7800#discussion_r3679458690) 明确认可这个问题：原 profile 是累计 `alloc_space`，没有覆盖 retained heap；同时确认 `byGVKName` 的高基数 singleton set 是当前结构的主要来源。随后将 PR force-update 到 `038e34d0d13443f3471ddf152a82fcaca34f7375`，并在 [follow-up comment](https://github.com/karmada-io/karmada/pull/7800#issuecomment-5128747070) 发布同规模 forced-GC 数据。

这次回应满足原评论提出的两项请求：既量化了常驻内存，也改掉了主导内存的索引表示。原 finding 仍然说明了真实 trade-off，但不再是 current head 的未处理缺口。

本地复核后已发布 [closure reply](https://github.com/karmada-io/karmada/pull/7800#discussion_r3681520974)，说明复测数字一致且没有剩余 concern。尝试调用 GitHub `resolveReviewThread` 时返回 `ranxi2001 does not have the correct permissions`；回复本身已成功，thread 需要由 PR 作者或有权限的 maintainer resolve。

### 实现变化

- primary `objects` 保存稳定 `*waitingCandidate`；`byGVK`、`byScope` 共享候选指针，不再重复完整 `ClusterWideKey`。
- label 更新只替换 candidate 中的 immutable `*waitingObject`，在读锁下抓到的旧快照仍可安全完成匹配。
- `byGVKName` 从每个 `(GVK,name)` 一个 `Set[ClusterWideKey]` 改为紧凑 `[]*waitingCandidate`；删除通过同名小 bucket 线性扫描并清空尾部指针。
- cluster-scoped 对象不进入 namespace/name index；name-only selector 先用 namespace 为空的完整 key 解析 cluster-scoped 对象，再回退到 namespaced name index。
- 新 match plan 按 GVK/namespace/name 分组、去重等价 selector，并让同组 match-all selector 覆盖其他 selector，避免对重叠 selector 重复 snapshot/scan。

### 独立验证

- `go test -race ./pkg/detector`：通过，`ok ... 10.774s`。
- 24,564 objects、100 namespaces、一个 label、forced GC、独立进程重复 5 次：full store retained delta 为 `18,854,672-18,860,696 bytes`，约 `17.98 MiB`。
- 清除 `byGVKName` 前后 forced-GC 差值重复 5 次为 `3,343,536-3,343,568 bytes`，约 `3.19 MiB`，与作者报告的 `3.19 MiB` 一致。
- 本机 5 轮 benchmark 中，1 个 match-all selector 为 `30.4-37.4 ms/op`，100 个重复 selector 为 `29.5-38.9 ms/op`；两者均约 `10.42 MB/op`、`153 allocs/op`。绝对时间受机器影响，但 selector 数量不再放大 snapshot/scan 成本。
- 跨 namespace name slice 的插入、重复 Upsert、label replacement、中间/首/末删除和 cluster-scoped exact-name 都有 current-head 回归测试覆盖。

### 仍需保留的证据边界

新 full store 仍明显高于旧 key-only map 的约 `3.15 MB`，因为它有 label snapshot、GVK index 和 scope index；作者也明确披露了这一点。当前结论是 CPU/临时分配与常驻内存的 trade-off 已被量化并显著改善，不是“没有内存成本”。

作者新增的 selector-scaling 表使用的是 1/10/100 个完全相同的 match-all selector，因此它准确证明去重与 match-all subsumption，不证明 100 个彼此不同的 label selector 都能保持常数时间。评论已明确工作负载，没有过度外推；这不构成新的 review finding。

PR body 在 `Mixed-selector evidence attachments` 后意外重复了一段已出现的 mixed-selector 文案，并带有格式损坏。这不影响实现判断，属于合并前可直接清理的 reviewer-facing 文案问题，本轮不占用内存 review thread 追加评论。
