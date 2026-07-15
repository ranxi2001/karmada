# Day 23：PR #7662 2026-06-30 社区会议全量转录与对齐

日期：2026-07-15

来源：[Karmada Bi-Weekly Meeting(Asia) for 20260630](https://www.youtube.com/watch?v=y-r0o2kDRXs)

视频总时长：`57:08`

#7662 有效讨论范围：`00:37-54:34`；`54:45` 后转为无关的 release CI/image tag 问题。

## 一页结论

这场录像几乎完整记录了 proposal PR #7662 的介绍和第一次长讨论。它不是一段 10 分钟补充材料，而是判断三条 user story 是否对齐的核心会议证据。

- `Story 1 / Full`：会议没有实质评审，只按“保留现有 Fresh 全量重调度”介绍。旧 API 默认、成功状态时机、failback 是否回 primary 等合同仍未确认。
- `Story 2 / PreserveReady`：讨论中的初步评价是方向可行，因为它仍由 WR 触发 scheduler，只增加“保留 Ready、重调 Pending”的指示；但它与 Descheduler 的分工、ready freshness、支持哪些 replica mode 和 scheduler 是否真能守住 ready 下界仍未闭合。
- `Story 3 / SafeMigration`：需求真实，但当前 controller-only 设计没有对齐。会议明确提出 `PropagationPolicy` 与 WR 同时定义目标会产生“双重真相”，scheduler 与 WR controller 同时改副本也会冲突；更通用的渐进式增删可能应放在 PropagationPolicy/传播链路，WR 只表达迁移意图或排除 source。
- `Cancel/Rollback`：人工取消是合理需求，但 `spec.cancel` 的含义、安全终态、reconcile 观察时机和通用 rollback 条件都未定义；delete + finalizer 只被作为候选思路提出。

最重要的状态事实是：PR 当前唯一 head commit `586f6fc3508e` 提交于 `2026-06-23`，会议发生在 `2026-06-30`，截至 `2026-07-15` head 仍未变化。也就是说，会议中对 Story 3、双写、rolling 所属层级和 cancel 的核心反馈尚未写回 proposal。明天不应把 720 行文档当成已对齐设计，而应先要求收敛这些架构边界。

## 方法与可靠性

本文是 `ASR/官方录像证据`，不是正式会议纪要或 maintainer approval。

- YouTube 元数据确认标题、ID `y-r0o2kDRXs` 和时长 `57:08`。
- 视频没有公开人工字幕或自动字幕。
- 使用本地开源 `faster-whisper large-v3-turbo`、中文、CUDA `float16` 转录。
- 第一轮 57 分钟粗稿用于定位；第二轮加入 `Karmada`、`WorkloadRebalancer`、`PreserveReady`、`SafeMigration`、`ResourceBinding`、`PropagationPolicy` 等提示词，并设置 `condition_on_previous_text=False`。
- 第二轮得到 1193 个 cue，覆盖 `00:00:04.080-00:57:00.400`；已知视频时长 `3428s`，没有时间戳越界。validator 只提示开场 cue 长 37 秒，需要人工拆句，不影响后续会议时间轴。
- 第一轮未关闭上下文继承的稿件尾部延伸到 `57:27`，超过真实视频时长，已判定为尾部幻觉，不作为证据。
- 没有执行说话人分离。下文只用“提案方/讨论方/另一位参与者”等编辑角色，不归因具体 maintainer。
- 明显术语按 proposal 和源码校正；无法确认的内部 CRD 名称统一写成“顶层业务 CR / shard child resource”。

原始本地产物：

- `_tmp/youtube-transcribe/y-r0o2kDRXs-full.m4a`
- `_tmp/youtube-transcribe/large-v3-turbo-prompted/y-r0o2kDRXs-full.srt`
- `_tmp/youtube-transcribe/large-v3-turbo-prompted/y-r0o2kDRXs-full.txt`

## 全场时间索引

| 视频时间 | 内容 | 结论强度 |
| --- | --- | --- |
| `00:00-00:37` | 开场、共享屏幕 | 背景 |
| `00:37-07:03` | proposal 背景、scope、三类 strategy | 提案方设计陈述 |
| `07:03-09:08` | 三条 user story 和 Deployment 数字示例 | 提案方设计陈述 |
| `09:08-19:00` | controller/executor、API、status、unit、cancel 状态机 | 提案方设计陈述 |
| `19:06-27:16` | 真实在线/离线场景，明确 Story 2/3 映射 | 需求对齐 |
| `27:16-31:34` | Story 2、scheduler 参与、Descheduler 分工 | 初步方向 + 未决边界 |
| `31:36-38:48` | Story 3 的 policy/WR 双重真相、rolling 所属层级 | 核心架构质疑 |
| `38:48-44:20` | Pod/shard 迁移 unit 与顶层 CR 分发边界 | 扩展面质疑 |
| `44:28-49:20` | 内部排期、离线 GPU 优先级、在线低频 | 需求方项目计划，不是社区承诺 |
| `49:42-50:50` | scheduler/controller 双写、WR 字段不可变 | 第二次架构质疑 |
| `50:50-54:34` | cancel、rollback、安全终态、delete + finalizer 候选 | 需求成立，设计未闭合 |
| `54:45-57:00` | release CI/image tag | 与 #7662 无关 |

## 清理版逐段记录

以下是忠于讨论含义的清理版记录，不是逐字引语。精确原始 cue 保留在 SRT 中。

### `00:37-02:26`：只做 execution side

提案方说明：目标是把 `WorkloadRebalancer` 从单一 Fresh scheduling trigger 扩展为基于策略的重调度框架。覆盖 Full reschedule、保留 Ready 只重调 Pending，以及 source-preserving SafeMigration。

在线 workload 在重调度中需要保持 source 继续服务。本 proposal 不讨论自动决策和水位计算，只设计 execution side。

### `02:28-07:03`：三类 strategy

背景包括集群恢复、成员集群资源不足、长期 Pending、副本从高水位迁到低水位、新增或扩容集群。现有 WR 会完整重新计算，不能保留已经稳定的实例。

设计新增 `strategy`：

- `Reschedule/Full`：保留现有 Fresh 全量重调度；
- `Reschedule/PreserveReady`：保留每个 member cluster 已 Ready 的副本，只释放 unavailable delta；
- `SafeMigration`：target 先启动并稳定，再减少 source；业务 unit 由 workload-specific executor 扩展。

### `07:03-09:08`：数字示例

Story 2 示例：Deployment desired 10；`member1 assigned=6, ready=4`，`member2 assigned=4, ready=4`。只释放并重调 `member1` 的 2 个 unavailable replicas。

Story 3 示例：`member1=5/member2=3/member3=2`，把 `member1` 的 5 个单位迁到 `member4`，其他两个 member 不变。示例要求 target 连续 Ready 60 秒、每次一个 unit、一小时无进展则失败。这些是示例参数，不是经会议批准的默认值。

### `09:08-19:00`：controller、executor 与状态机

WR controller 按 strategy 分发 executor。Reschedule 触发 scheduler；SafeMigration 再分发 workload-specific unit executor。草案新增 `strategy`、`mode`、`from/to`、`stableWindow`、`maxInFlightUnits`、`noProgressTimeout`、`cancel`，并扩展 phase/result/reason/progress。

提案方设想取消时由业务 executor 把已迁移的副本或分片恢复到原集群的安全状态。这里描述的是意图，尚未证明 checkpoint、资源和 ownership 足以实现回滚。

### `19:06-27:16`：真实场景映射

在线场景：业务增长后原集群资源不足，需要低频地迁到其他集群；也可能为了水位均衡而迁移。

离线场景：长期运行、可中断、甚至持续不退出的“刷库”类任务，希望夜间利用跨集群空闲 Spot GPU。当前任务被固定在一个集群，其他集群即使有空闲资源也不能接收其 Pending 实例。

双方在对话中明确：离线 Pending 部分对应 Story 2；在线安全迁移对应 Story 3。离线业务是需求方本期更高优先级，希望把 GPU 利用率从约 80% 提升到 90% 以上；自动水位决策仍不在本 proposal 中。

### `27:16-31:34`：Story 2 初步可行，但 Descheduler 分工未定

讨论先澄清：`Reschedule` 仍需 scheduler 重新计算分配，SafeMigration 的当前设想则主要由 controller 操作。

对 Story 2 的表述是“初步感觉方向 OK”：WR 本来就是指示 scheduler 重调度，PreserveReady 只是增加“尽量保留已有 Ready 结果、重调其他部分”的指示。这不是正式批准。

随后指出 Descheduler 已经发现 unavailable replicas 并触发处理，功能存在重叠。候选分工是 Descheduler 周期检测并创建 WR，所有重调度任务由 WR 执行和展示状态；最终 ownership、去重和重试合同仍需线下研究。

### `31:36-38:48`：Story 3 的双重真相

讨论提出最核心的 concern：如果 `PropagationPolicy` 允许的集群不包含 `member4`，而 WR 又指定 `to=member4`，Policy 与 WR 会同时定义 workload 目的地，形成两套规则和不可预期结果。

更通用的候选方向是：WR 表达“从 source 迁走”或显式排除 source，target 仍由 scheduler 按 `PropagationPolicy` 和当前集群状态选择。对于用户显式指定 target 的模式，也必须定义它与 Policy 的优先级和校验。

讨论进一步把 target-first 提升为通用传播变更：当 Policy 目标从 `member1/2/3` 改成 `member4/5/6` 时，当前也会先删旧侧、再慢慢拉新侧。渐进式增删可能更适合放进 PropagationPolicy/Binding/Work 传播链路，使所有 policy update 受益；Story 3 可拆成“WR 迁移意图”和“通用 rolling primitive”两部分。

### `38:48-44:20`：迁移 unit 跨越 Karmada 当前对象边界

多分片 workload 的顶层业务 CR 在 member cluster 中创建多个 shard child resources，每个 shard 下再有 CloneSet/Pod。迁移不能只按 Pod，应按 shard/DataApp 这类业务 unit；普通 workload 才可能按 Pod。

当前 `PropagationPolicy` 传播的是顶层 CR，child resources 由 member-side controller 拥有。因此 unit executor 要如何稳定识别、操作并持久化 member 侧 shard 状态仍未回答。讨论认可需要 workload-specific unit 抽象，但没有决定 unit 配置属于 WR、Policy 还是单独的 interpreter/executor contract。

### `44:28-49:20`：排期和价值，不是社区承诺

需求方内部已完成详细设计，计划一两个月开发、测试、上线；本期先做 execution side，优先离线 GPU 和多分片应用，在线迁移低频且不做自动决策。

讨论中只表示开源侧一两个月未必能完成全部实现，希望先把 API 约束设计好。这不能写成 Karmada 社区交付承诺。

### `49:42-50:50`：第二次确认双写风险

另一位参与者再次指出：scheduler 和 WR controller 一起控制副本会冲突或出现异常，倾向让 WR 只负责触发，真正执行仍交给 scheduler。

同时提出 WR 是一次性 workflow resource，关键 spec 字段创建后就应 immutable，而不是只在 Running 期间禁止修改。这比 proposal 当前约束更严格，仍未形成最终 API 结论。

### `50:50-54:34`：Cancel 需求成立，API 仍不成立

需求方需要人工介入：迁到一半出问题、想暂停或业务需要发布时，取消并把已经迁出的部分回到原集群。其内部环境会预留 source 资源，因此认为可以回滚。

讨论认可需求合理，但追问：cancel 到底取消什么、当前中间状态如何处理、安全稳定态是什么、通用环境能否回滚，以及一次 reconcile 已做完不可逆操作后下一次才看到 `spec.cancel` 是否太晚。

结论是当前设计欠完善，需要继续在 PR 讨论。delete WR + finalizer 拦截删除并执行恢复只是一条候选方向，没有成为合同。

## 三条 User Story 的精确边界

### Story 1：Full rebalance after cluster recovery

`PROPOSAL`：failover 后 Deployment 离开 `member1`；`member1` 恢复后，管理员希望重新计算 placement 并再次使用所有 eligible clusters。`Reschedule/Full` 保留现有 WR 行为。

验收下界：

- 明确触发一次 Fresh/full scheduler computation；
- eligibility 仍由当前 Policy 和 cluster state 决定；
- 不保证回到特定 primary，也不保证分布一定变化；
- 必须先确定 WR `Successful` 是“trigger 已写入”还是“scheduler 已处理”；
- 旧对象不带 strategy 时的 default 和 TTL/status 时序必须兼容。

会议状态：没有实质 review。不能从沉默推断批准。

颠覆度：`中`。核心调度算法可复用，但 API/default/status/TTL 合同发生变化。

### Story 2：Preserve ready replicas

`PROPOSAL`：保留 `member1 ready=4` 和 `member2 ready=4`，只释放并重调 2 个 unavailable replicas；scheduler 再按当前 placement 和 cluster state 放置 delta。

验收下界：

- 已 Ready 副本在原 cluster 的数量是硬下界，不只是 best effort；
- 只释放 `assigned-ready` delta；
- ready 数据必须属于当前 workload generation/lifecycle；缺失或陈旧时 fail closed；
- scheduler 完成后 released delta 重新 Ready，任务才完成；
- 必须列出支持的 replica scheduling type/mode。

独立 scheduler matrix 已证明：Duplicated、Static Weighted 不满足这一不变量；Aggregated/Dynamic 也只在 Steady 且 Ready clusters 仍 eligible 等前提下成立。

会议状态：真实需求和 scheduler 参与已对齐，方向得到初步正面信号；Descheduler 分工、支持矩阵和 freshness 尚未对齐。

颠覆度：`高`。它不是单纯 WR controller 改动，而是改变 Binding assignment 与 scheduler 的合同。

### Story 3：SafeMigration

`PROPOSAL`：从一个明确 source 迁到一个明确 target，其他 clusters 不变；target-first，稳定后缩 source；支持 workload-specific unit、cancel 和 progress。

验收下界：

- source 在对应 target unit Ready 且连续稳定前不得下降；
- 明确 target 权威：显式 `to`、排除 `from` 后 scheduler 选择，或两种模式及其优先级；
- Policy、scheduler、WR、failover 之间必须只有一个 authoritative desired state；
- operation ID、unit identity、ReadySince、partial commit 和原始 plan 必须可持久化恢复；
- cancel/delete 必须定义 safe terminal state、补偿能力和 source capacity 不足行为；
- 顶层 CR 与 member-side shard child resource 的 ownership 必须可实现。

会议状态：需求和 target-first 行为成立，但当前 controller-only 方案受到根本性质疑；建议拆分通用 rolling primitive。没有设计批准。

颠覆度：`很高`。若按当前 proposal 直接实现，会跨 WR API/controller、scheduler、PropagationPolicy、Binding、Work、status/readiness、GracefulEviction 和 workload-specific child resource 边界。

## 对现有系统的总体冲击

| 层面 | 冲击 | 原因 |
| --- | --- | --- |
| Proposal PR 本身 | 低 | 当前只新增文档，没有 runtime 代码 |
| Story 1 实现 | 中 | 调度路径复用，但 status/default/TTL 兼容合同改变 |
| Story 2 实现 | 高 | scheduler 需理解或守住 Ready preservation；与 Descheduler ownership 重叠 |
| Story 3 按当前文档实现 | 很高 | `from/to` 与 Policy 冲突，WR/scheduler 多写 Binding，target-first 缺 durable encoding |
| Story 3 按会议建议拆分 | 很高但更合理 | 通用 rolling primitive 进入传播层，WR 收缩为 intent/task；影响更广但职责更一致 |
| 自动水位/收益决策 | 本 PR 低 | 明确排除；未来是独立 decision layer |

总体不是替换 Karmada scheduler，而是把一次性 trigger 升级为跨组件、长时间、可恢复的操作。组件替换幅度中等，运行时合同风险高到很高。

## 明天建议先问的七个问题

1. `Story 2` 精确支持哪些 scheduling type/mode？Duplicated、Static、Fresh 和 ready cluster 失去 eligibility 时是否明确 reject？
2. `Story 3` 的 target 权威到底是显式 `to`，还是 `from/exclude` 后由 scheduler 按 PropagationPolicy 选择？若两者都支持，冲突规则是什么？
3. target-first rolling primitive 属于 WR executor，还是 PropagationPolicy/Binding/Work 的通用传播更新能力？是否接受把 Story 3 拆成两部分？
4. WR controller、scheduler、Descheduler、failover 谁是 Binding desired state 的唯一写者？其他组件如何 queue/reject？
5. 哪个对象持久化 operation ID、unit identity、ReadySince、原始 plan 和 partial commit，controller restart 后如何恢复？
6. cancel 是 mutable boolean、独立 subresource，还是 delete + finalizer？safe terminal state 和 rollback capacity 是 Karmada 通用保证还是内部前提？
7. omitted strategy 默认 `Full` 还是 `PreserveReady`？旧 WR 的 Successful/TTL 时序是否保持兼容？

建议开场表述：

> 我听完 6 月 30 日完整讨论后的理解是：Story 2 可以在明确 supported scheduling modes 和 Descheduler 分工后继续细化；Story 3 仍需要先决定 Policy/scheduler/WR 的 authoritative state，以及通用 rolling primitive 属于哪一层。否则现在直接进入 executor 实现，会把会议中已经指出的双写和多脑风险固化进 API。这个判断是否准确？

## 证据边界

录像能证明：

- proposal 的三条 story、execution-only scope 和示例参数在会上被完整介绍；
- Story 2 获得初步方向信号；
- Story 3 的双重真相、传播层 rolling、unit 边界、scheduler/controller 冲突和 cancel 语义被明确提出；
- 需求方内部优先级和排期。

录像不能证明：

- 任何具体发言属于哪位 maintainer；
- proposal 已批准、API 已稳定或有人承诺实现；
- target-first、rollback、scheduler coexistence 或 persistence 已有可行实现；
- 内部资源预留能力是 Karmada 通用能力；
- 会议意见已经写入 PR。当前 head 未更新反而说明尚未完成这一步。
