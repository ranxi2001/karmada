# Day 48：EstimatorAssumption 跨用例清理隔离与 PR #7827

- 日期：2026-08-13
- Issue：[`karmada-io/karmada#7826`](https://github.com/karmada-io/karmada/issues/7826)
- Pull Request：[`karmada-io/karmada#7827`](https://github.com/karmada-io/karmada/pull/7827)
- 修复提交：`ba531a9a1e57e164488c9ce84b8549273a844b11`
- 基线：`upstream/master@09c08f405b2f0b53106b1947e08a82d4cc94de28`
- 证据等级：E3；尚未达到 E4

## 先说人话

`EstimatorAssumption` 用例本来要证明“它自己创建的工作负载已经占满集群”。失败时，上一条用例留下的
Deployment 也被 scheduler estimator 算了进去，于是第一次估算得到 no-fit。大约五分钟后，这个外来
assumption 过期，随后创建的 200m 探针 Deployment 又可以调度；测试却还在等待它变成
`Scheduled=False`，最终等待 420 秒超时。

具体例子是：上一条 taint/toleration 用例先恢复了 member cluster 的 taint，再开始删除自己的
Deployment。恢复 taint 触发了一次新的调度，旧 ResourceBinding 在删除过程中仍成功写回结果并刷新
assumption。只等待 Deployment 消失不够，因为官方日志里 Deployment 已经 NotFound 后，
ResourceBinding 仍成功完成了最后一次 patch。

PR #7827 把修复放在产生污染的 E2E cleanup，而不是 scheduler 的生产 cache：用例结束时先删除
Deployment，等待 Deployment 和生成的 ResourceBinding 都 NotFound，再恢复共享 taint；另一个 PDB
用例遗漏的 Deployment 也按同样合同清理。这样切断的是“上一条用例把工作负载带进下一条用例”的路径，
不改变 scheduler、estimator、cache TTL、retry 或测试 timeout。

当前主结论仍是 E3：官方失败提供了完整的真实 CI 日志、源码顺序和 producer-to-impact 时间线。fork
attempt 1 另外证明 PDB fixture 存在独立 cleanup 缺口，并失败在同一个 NodeResource spec；但该 run 后续
rerun 覆盖了 attempt-1 component artifact，所以它应作为第二个 producer 的支持证据，不再与官方链并列
充当 cache transition 的 timestamp anchor。本地没有 Karmada 多集群环境，也没有在同一受控环境完成
“补丁前稳定失败、补丁后稳定通过”的 counterfactual，因此尚未达到 E4。

## 官方失败链

官方证据来自 [run `28998390044`](https://github.com/karmada-io/karmada/actions/runs/28998390044)
的 [Kubernetes v1.34.0 job](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911)，
head 为 `3d4d14d746de507164abf40c1017b1f2b0e47e3a`。失败用例是：

```text
[EstimatorAssumption] NodeResource plugin assumption testing
[It] FlinkDeployment should be unschedulable when assumed workloads exhaust cluster resources
```

终点错误是 `assertSingleTemplateDeploymentUnschedulable` 等待 420.001 秒后超时。向前追踪得到：

| UTC 时间 | 已观察行为 | 对失败链的意义 |
| --- | --- | --- |
| `07:10:24.054` | 前一条 taint/toleration spec 开始恢复 taint | 共享集群状态先于 workload cleanup 改变 |
| `07:10:24.148` | 源 Deployment 开始删除 | 删除和新一轮调度发生重叠 |
| `07:10:24.1608308` | controller 首次报告 Deployment NotFound | 仅等待 source NotFound 仍不足以阻止后续写入 |
| `07:10:24.1951045` | 排队中的 cluster-change schedule 将 binding 从 `{member1:3}` 扩为 `{member1:3, member2:3, member3:3}` | 旧 workload 重新进入调度结果 |
| `07:10:24.2396594` | ResourceBinding result patch 成功，scheduler 更新 assumptions | 外来 assumption 的最后一次已确认生产点 |
| `07:10:24.3467832` | controller 报告 ResourceBinding NotFound | binding 删除晚于最后一次成功 patch |
| `07:15:22.9974473` | Flink estimator 请求仍包含 `deploy-wbch9`，返回 no-fit | 当前用例的第一次 no-fit 被外来 workload 污染 |
| `07:15:24.6655476` | 200m probe 不再包含该 assumption，并返回 fit | 外来条件消失，测试前提不再成立 |
| `07:15:24.6677764` | probe binding 变为 `Scheduled=True` | 测试等待的 `Scheduled=False` 不会出现 |

`07:15:24.2396594` 是“最后一次成功 patch 加源码定义的五分钟 TTL”得到的推断过期点；日志没有直接输出
expiry timestamp。因此可以确认时序和机制相符，但不能把推断时间写成日志原文。

Ginkgo v2 的 static `AfterEach` 早于动态注册的 `DeferCleanup` 执行。源码顺序因此能解释为什么恢复 taint
发生在 Deployment 和 PropagationPolicy cleanup 之前。

## Fork 的独立失败链

[fork attempt-1 job](https://github.com/ranxi2001/karmada/actions/runs/31573625648/job/94042457609)
运行在 `8770a193a7a0c6f20dd3a1ea3ac9ff979df2730f`。它暴露的是第二个 producer：PDB collection
spec 在 `07:52:45.778` 创建了 `poddisruptionbudget-xw489` Deployment，却只在 `07:53:06` 清理了
PropagationPolicy 和 PDB，没有注册 Deployment cleanup。`08:12:18` 开始的 NodeResource spec 与它复用
同一个 Ginkgo process namespace，并在 `08:19:43.613` 失败于同一个 420 秒 probe 断言。

该 Deployment 是 member workload 对应的真实容量占用，不是官方链中五分钟后过期的 scheduler
assumption。它改变了后续 NodeResource spec 看到的 available-capacity state，使“首个 multi-component
Flink no-fit”不能证明仅由本用例的 assumptions 耗尽；single-template 200m probe 仍可能在不同资源形状下
fit。原始分析时 component log 显示该 fixture 进入后续 estimator 观察；但 GitHub rerun 会用 attempt 2 的
同名 artifact 覆盖 run 级下载结果，当前重新下载已不能独立复核 attempt 1 的每个 estimator 时间点。因此
这条证据现在只承担“第二个 cleanup producer + 同一失败 consumer”的支持作用，不再写成“该 fixture
恰好在五分钟 TTL 边界消失”。

## Issue #7826 文案复盘

原 issue 的主要问题不是时间戳不够，而是按全局时间顺序讲了两个 run，却没有先回答 reviewer 最需要的
映射问题：哪个 producer spec 留下哪个对象，污染了哪个 consumer spec 的哪个断言。读者看到
`deploy-wbch9`、PDB fixture、Flink 和 probe 混在连续段落里，容易误以为它们属于同一次执行，或者误以为
两个残留分别导致两个不同测试失败。

第一版修订稿改为以下顺序：

1. 先声明两个 job 都失败在同一个 NodeResource spec 和同一个 420 秒断言。
2. 用 producer/残留/consumer/result 四列把两个 run 一一对应。
3. 分别绘制 official run 和 fork run 的时序图，不跨 run 拼接时间线。
4. official run 承担 E3 根因链；fork run 只证明第二个 cleanup producer 和同一 consumer，不借已被 rerun
   覆盖的 artifact 扩大 cache/TTL 结论。
5. 最后才给统一 cleanup contract 与明确 non-goals。

该版本于 2026-08-13 按用户确认替换到 upstream Issue #7826，发布后逐字校验一致。但第二次复盘确认，
它虽然补全了对象和状态链，图的主角仍是对象与组件，没有让 reviewer 第一眼看到“哪个 E2E spec 的
cleanup 出错，哪个 E2E spec 被影响并报红”。

因此当前 [`day48-issue7826-revised-body-draft.md`](day48-issue7826-revised-body-draft.md) 已进一步改为
测试用例因果版：两张图都直接使用 producer spec、producer cleanup hook、failing consumer spec 和 failed
assertion 作为参与者。它明确指出 producer spec 自身可以通过，缺陷发生在随后 cleanup；真正报红的是
`estimator_test.go` 中的 NodeResource spec。两张 exact Mermaid 图已用 Mermaid CLI 11.16.0 渲染通过。
该版已于 2026-08-13 按用户确认再次替换到 #7826，线上正文与本地定稿 SHA-256 均为
`af91232173404d5604308da604c3714db73d9bd74c1fe59627a3297e2ea5fa09`。

第三次复盘发现，测试用例因果版又丢掉了时间证据。正确做法不是在“对象时序”和“测试关系”之间二选一，
而是用一张图同时表达四层关系：

| 泳道 | 回答的问题 | #7826 中的实例 |
| --- | --- | --- |
| Producer E2E spec | 哪个用例产生了污染 | `tainttoleration_test.go:140` / `resource_test.go:606` |
| Cleanup code | 哪段清理代码有缺口 | `AfterEach:104 + DeferCleanup:134` / `DeferCleanup:601-603` |
| Residual object/state | 缺口通过什么状态传播 | Deployment -> ResourceBinding -> assumption / retained Deployment -> available capacity |
| Consumer E2E spec | 哪个后续用例读取了污染状态 | `estimator_test.go:419` / `estimator_test.go:425` |
| Failed assertion | 最终哪个检查报红 | `assertSingleTemplateDeploymentUnschedulable` |

时间不是第六条泳道，而应写在每条事件箭头上。纵向顺序证明先后关系，横向泳道证明责任和传播边界。例如
official run 的主链应同时显示：`07:10:24.030` producer cleanup 先恢复 taint，`07:10:24.239`
旧 binding patch 刷新 assumption，`07:15:22.998` consumer 的 Flink no-fit 仍读到它，`07:15:24.668`
probe 变为 `Scheduled=True`，最终 `07:22:24.642` 断言超时。

图中的证据也要分层：`[OBS]` 只用于 job/component log 的时间戳事件，`[CODE]` 用于源码证明但无独立
运行时间的事实。fork attempt-1 可画创建、cleanup、consumer start 和 timeout 的 `[OBS]` 时间，但
“没有注册 Deployment cleanup”必须标 `[CODE]`；artifact 被 rerun 覆盖后，不再补完整 cache transition。
两个 run 必须分图，避免把不同日期、不同 namespace 和不同 producer 拼成一条伪时间线。Issue 第一屏继续
保留 producer/consumer 索引表，让 reviewer 先知道谁影响谁，再沿图核对代码、对象和时间证据。

按该合同生成的五泳道带时间正文已写入
[`day48-issue7826-revised-body-draft.md`](day48-issue7826-revised-body-draft.md)。两张 exact Mermaid 图已用
Mermaid CLI 11.16.0 和现有 Chromium 渲染检查通过；正文 SHA-256 为
`f0c8a4855de6dde08a74ac2595ac26a6087a1e370c14f2c964c5f4593e08f328`。该英文正文已于 2026-08-13
获得用户 exact-text 确认并替换到 upstream #7826；发布后逐字 diff 为空，线上与本地 SHA-256 一致。

第四次复盘定位到 target 语义仍写偏了。真正固定目标的是 `estimator_test.go`：`targetCluster` 为
`member1`，Flink CRD 的 `ClusterPropagationPolicy`、每个 Flink workload 的 `PropagationPolicy` 和最后
200m probe 都复用该值。官方 scheduler 日志在 `07:15:22.996` 明确因 `ClusterAffinity` 排除 member2/3，
只有 member1 进入 estimator；member1 estimator 请求在 `07:15:22.997` 含 5 项 assumptions，其中
`deploy-wbch9` 为 3 副本 x 10m，`07:15:24.665` probe 请求只剩 4 项且不再含该 workload。

因此三集群重排的意义只是证明 cleanup 触发了新一轮 schedule。它对 consumer 的因果作用是同一次成功
patch 再次调用 member1 的 `Assume`，覆盖同一 binding/cluster entry 并重置五分钟 TTL；member2/3 的
assumptions 不会进入该测试。2026-08-14 已发布的第一条 comment 把用户指出的 hard-coded target 误读成
taint 用例的 `targetClusterNames` 断言，第二条虽限定 member1 为相关 30m，却仍把三集群 90m 放在开头。
两条 comments 已按新的 exact-text 确认原位替换为 member1-only 解释，远端正文与本地草稿逐字一致；
最终 SHA-256 分别为 `9b6cd18259091bfae25001c282fd80a7df7a0a49e8fca22e72053a6139bb7c6b` 与
`af711b11d816aa4f0b6ac27f84564af5db2b6be93aaa737130a913118f8ed52b`。

## Skills 优化提案

这次连续经历“只有对象时序 -> 只有测试关系 -> 补时间 -> 合并代码/对象/测试/时间”和多次 upstream body
替换，说明缺口不是某一句话，而是 workflow 没有在发布前冻结四类视图和 approval 状态。按
`$e2e-root-cause-analysis` 的 Step 5，本轮只提出、不直接修改 skill。

### P0：`e2e-root-cause-analysis`（主归属）

1. 在收集 artifact 前强制读取 job/run 的 `run_attempt`，并核对 artifact `created_at`。GitHub rerun 后，
   run-level 同名 artifact 可能只对应最新 attempt；如果与失败 job attempt 不一致，应停止拼接证据，并在
   rerun 前固化失败 attempt 的 job/component logs。
2. 对跨 spec 污染先生成一行 causal tuple，再写叙述：
   `producer spec + source -> cleanup hook + source -> residual object/state -> consumer spec + source -> assertion + source`。
   必须明确“producer 自身是否通过”和“最终哪个 consumer 报红”。
3. 多个 CI run 必须分别画五泳道时间线：producer spec、cleanup code、residual object/state、consumer spec、
   assertion。时间写在事件箭头上，而不是单独做时间泳道；不能为了突出对象而丢测试，也不能为了突出测试
   而删时间。
4. 图中每条物质性边标证据类型：`[OBS]` 为 job/component log，`[CODE]` 为 exact-SHA 源码，
   `[INFERENCE]` 为尚未闭合的连接。只有 `[OBS] + [CODE]` 闭合主链时才继续使用 root cause/E3 表述。

建议新增 `scripts/audit_run_attempt.py <job-url>`，一次输出 repository、run ID、job ID、`run_attempt`、job
timestamps、artifact name/ID/`created_at`/expiry，以及“artifact 是否可归属该 attempt”的结论。验收用例至少
覆盖普通 run、失败 job rerun 后同名 artifact 覆盖、artifact 已过期三种情况。

### P1：`karmada-issue-discussion`（发布状态机）

1. 把 exact-text gate 明确成内容哈希状态机：`drafted -> rendered -> approved(hash) -> published ->
   remote hash verified`。用户的批准只绑定批准时展示的 target 和 hash；批准后正文再变更，必须重新确认。
2. 编辑已有 issue 前记录 title/body hash/`updatedAt`，发布后验证 title 不变、正文逐字一致、remote hash 与
   approved hash 一致。只有尾部换行差异时用不自动补换行的模板输出复核。
3. 在请求确认时一次性给出 target、正文文件链接、visible words、长文例外原因、hash 和 Mermaid 校验结果，
   避免用户只能确认抽象方向却没有确认 exact body。

该规则不应复制到所有 GitHub skills；`karmada-issue-discussion` 负责 issue/comment，PR body 的同类状态机继续由
`karmada-pr-management` 按自身 gate 管理。

### P1：`project-mermaid`（最终正文校验工具）

1. 新增 `scripts/render_markdown_mermaid.py <draft.md> --output-dir <dir>`：按出现顺序抽取最终 Markdown 中所有
   `mermaid` fence，生成临时 `.mmd`，逐块调用现有 renderer，并返回 fence index、行号、尺寸和失败原因。
   这能避免手工复制“相似草图”通过、最终正文却未验证。
2. 在 sequence reference 增加 RCA 五泳道模式，但作为条件模板而非通用强制：当问题同时涉及跨测试污染、
   cleanup 代码、残留状态和超时时采用五泳道；普通组件调用仍保持 3-8 participant 的现有规则。
3. 明确 Mermaid sequence message 中的 `;` 可能被解析为语句分隔符，发布前必须用目标 Mermaid 版本渲染
   exact fence；render success 之后仍要做语义审计，检查测试、代码、对象、时间和证据标签是否齐全。

### 不建议修改

- `code-review-growth`：现有 Flake Root-Cause Gate 已定义 E0-E4、`OBS/CODE/INFERENCE` 和时间/代码表，
  这次只需由 RCA skill 调用，不应重复五泳道模板或发布状态机。
- `humanizer-cs`：它负责 claim strength 和 exact literal，不负责 RCA 证据收集、Mermaid 渲染或 GitHub 发布授权。
- 不创建新 skill：三项缺口分别属于现有 RCA、issue publishing 和 Mermaid validation 边界；新建 skill 会增加
  触发冲突和上下文成本。

建议实施顺序为：先改 `e2e-root-cause-analysis` 的 causal tuple/五泳道合同和 attempt 审计，再补
`project-mermaid` 的 Markdown fence renderer，最后补 `karmada-issue-discussion` 的 hash approval 状态机。
前两项阻止错误正文形成，最后一项阻止未确认的新版本被发布。

## Skills 更新实施结果

### 先说人话

这次绕圈不是单纯的画图问题，而是三个检查点彼此脱节：RCA 只说明对象如何变化，没有强制写清哪条 E2E
留下状态、哪条 E2E 失败；Mermaid 校验的是复制出来的片段，不一定是最终 issue 正文；发布确认没有绑定
正文版本，用户确认后正文仍可能继续变化。

现在三个检查点已经连成一条链：先证明
`producer spec -> cleanup code -> residual state -> consumer spec -> failed assertion`，再从最终 Markdown 原文
渲染所有 Mermaid，最后用 `target + SHA-256` 请求确认并核对远端正文。对象交互仍然保留，但只作为五段因果链
中的状态证据，不再作为主叙事。

### 实际改动

1. `e2e-root-cause-analysis`
   - 新增跨 spec 污染证据合同，要求 producer、cleanup、残留状态、consumer 和 assertion 都有精确 spec/源码位置；
   - 主图固定为五泳道带时间时序，并用 `[OBS]`、`[CODE]`、`[INFERENCE]` 区分证据强度；
   - 新增 `scripts/audit_run_attempt.py`，读取 job/run/artifact API，区分 `attempt_compatible`、
     `not_attributable` 和 `ambiguous`，同时单列 expired 可用性；attempt 兼容只证明时间不冲突，仍需按 artifact
     名称和 upload step 复核 matrix job 所有权。
2. `project-mermaid`
   - 新增 `scripts/render_markdown_mermaid.py`，直接从最终 Markdown 抽取所有 `mermaid` fence，逐图调用现有
     renderer，并返回行号、输出路径、字节数和尺寸；
   - sequence reference 增加条件式五泳道 RCA 模板，普通 sequence diagram 不受影响；
   - rendering reference 增加 exact-draft 校验和分号解析风险，render success 后仍必须检查标签是否被截断。
3. `karmada-issue-discussion`
   - 新增 `drafted -> exact Mermaid rendered -> approved(target + SHA-256) -> published -> remote SHA-256 verified`
     状态机；
   - target、title action、正文或 Mermaid 任一变化都会让旧确认失效；
   - 发布前记录 title/body hash/`updatedAt`，发布后验证 title、目标和正文 bytes，避免 shell 尾部换行造成假一致。

### 验证证据

- 两组脚本单测共 10 项通过，包括普通 attempt、旧 attempt、缺失 attempt、expired artifact、URL/API ID
  不一致、两种 Markdown fence、未闭合 fence 和 PNG 尺寸读取。
- `skill-creator` 的 `quick_validate.py` 对三个 skill 均返回 `Skill is valid!`，`git diff --check` 通过。
- 使用 #7826 最终正文直接渲染出 2 张图：Markdown `28-49` 行为 `1584x641`，`55-75` 行为
  `1584x563`；逐图目检确认五条泳道、spec、源码位置和时间标签可读。
- 官方 job `86054168911` 与 run 均为 attempt 1，对应 `karmada_e2e_log_v1.34.0` 判为
  `attempt_compatible`；fork 失败 job `94042457609` 为 attempt 1，而 run 当前为 attempt 2，同名 artifact 判为
  `not_attributable`。这与 #7826 正文中“官方链承担 E3、fork 链只作支持证据”的边界一致。

本轮没有再次编辑 #7826 或发布上游内容。远端发布状态机已经写入 skill，但本轮只验证规则和既有正文，没有
为了测试发布 gate 而制造新的 upstream edit。

## 为什么是三文件 test-only cleanup

补丁只修改三个 E2E 文件，共 `+53/-23`：

| 文件 | 改动 | 切断的路径 |
| --- | --- | --- |
| `test/e2e/framework/resourcebinding.go` | 新增 `WaitResourceBindingDisappear` | 为 cleanup 提供 ResourceBinding API NotFound barrier |
| `test/e2e/suites/base/tainttoleration_test.go` | 利用 `DeferCleanup` 的 LIFO 顺序，让 workload cleanup 先于 taint restore；分别注册 policy 和 Deployment cleanup | 阻止 taint 变化在旧 binding 删除窗口触发成功写回 |
| `test/e2e/suites/base/resource_test.go` | 删除 PDB spec 遗漏的 fixture Deployment，并等待 Deployment 和 binding 消失 | 清除 fork 日志确认的第二个 producer |

没有修改 production cache，原因有三点：

1. 已确认的污染源属于测试资源生命周期；最早且职责明确的切断点是产生 workload 的 spec cleanup。
2. 仅等待 Deployment NotFound 无法覆盖官方时序；等待 ResourceBinding NotFound 后，旧 scheduler item 不能再
   成功 patch 该 binding，而现有路径只在 patch 成功后更新 assumptions。
3. 调整 TTL、增加 retry 或延长 timeout 只会改变污染持续时间。此前评估的 Healthy-target assumption guard
   也缺少 generation/placement 作用域，可能抑制仍然有效的 reservation，风险超过本次 E2E 问题边界。

因此，PR #7827 修复的是两条已确认的跨 spec 隔离路径，不宣称解决 production 中所有 delete/reschedule
竞态，也不扫描并同步化全部 E2E cleanup。

## 2026-08-14：专用 Kind 集群方案

### 先说人话

#7827 当前补丁要求每个已知 producer 在退出前完成 cleanup，但 `EstimatorAssumption` 仍使用共享的
`member1`。新的方案把 NodeResource assumption spec 放到测试期间临时创建的真实 Kind 集群中：该集群只有
这一个 serial spec 使用，测试结束后执行 unjoin 并删除。这样后续再出现新的共享集群残留，也不会改变该
spec 的 node allocatable、Pod 用量或 estimator assumption。

Karmada base E2E 已有这种生命周期，不需要新增 framework 文件：

- [`suite_test.go`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/test/e2e/suites/base/suite_test.go#L238-L273)
  已提供同包可复用的 `createCluster` 和 `deleteCluster`，底层通过 Kind provider 创建、删除真实集群，并把
  kubeconfig server 改为 Docker 网络内可访问的地址。
- [`rescheduling_test.go`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/test/e2e/suites/base/rescheduling_test.go#L43-L152)
  已使用 `member-e2e-*` 随机名执行 `create -> join -> wait Ready -> test -> unjoin -> delete`。
- [`federatedresourcequota_test.go`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/test/e2e/suites/base/federatedresourcequota_test.go#L112-L190)
  一次创建两个临时成员集群，并在 policy 中只显式使用需要的集群，证明动态集群可以不加入
  `framework.ClusterNames()` 的默认列表。
- [`framework.SerialDescribe`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/test/e2e/framework/ginkgo_decorator.go#L21-L24)
  给该 spec 添加 Ginkgo `Serial`。Ginkgo 在并行 specs 完成后才运行 serial specs，因此临时 `Cluster` 对象
  存在期间不会有并行 spec 向它调度；只依赖 `framework.ClusterNames()` 的启动时缓存不能提供这个保证。

### 为什么主修复只需一个测试文件

NodeResource spec 与 `suite_test.go` 同属 `base` package，可以直接调用已有的未导出 helper。建议只修改
`test/e2e/suites/base/estimator_test.go`，在该文件内完成以下生命周期：

1. 生成 `member-e2e-*` 名称，调用 `createCluster`，并取得该集群的独立 kubeconfig。
2. 为 Kind 生成的 `kind-member-e2e-*` context 添加一个与 Karmada cluster name 同名的 alias。现有
   [`deploy-scheduler-estimator.sh`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/hack/deploy-scheduler-estimator.sh#L24-L93)
   同时把第四个参数当作 kubeconfig context 和 estimator cluster name；alias 可避免修改脚本接口。
3. 从该测试文件调用现有部署脚本，在 host cluster 创建 `<cluster>-kubeconfig` Secret、estimator Deployment
   和 Service，并等待 Deployment available。
4. 使用现有 `karmadactl join` 代码路径注册集群，等待 `ClusterConditionReady=True`。scheduler 的
   [cluster add/update handler](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/pkg/scheduler/event_handler.go#L314-L341)
   会为新集群排队建立 estimator 连接。随后通过该 spec 的 kube client 调用
   `WaitNamespacePresentOnClusterByClient`，确认 suite 的 `testNamespace` 已同步到新集群。
5. 把 NodeResource spec 的 `targetCluster` 从常量 `member1` 改为该随机集群名。CRD present wait 可继续读取
   `Cluster.status.apiEnablements`；CRD delete wait 需使用本 spec 通过 `util.NewClusterClientSet` 创建的 dynamic
   client，因为 framework 的 member client cache 只在 suite 启动时初始化。
6. 依赖 `DeferCleanup` 的 LIFO 顺序，先清理 workload、policy 和 CRD，再 unjoin，随后删除 estimator 的
   Deployment、Service、Secret，最后删除 Kind 集群和 kubeconfig。

这个设计不要求改 `suite_test.go`、framework 或 `hack/deploy-scheduler-estimator.sh`。它是基于现有源码可达
路径形成的实现方案，尚未在本地多集群环境运行，因此不能写成 E4 验证结果。

### PR 范围边界

专用集群只解决 `EstimatorAssumption` 的隔离，主修复最终可以只有
`test/e2e/suites/base/estimator_test.go` 一个文件。PDB spec 遗漏 Deployment cleanup 是另一项真实缺口；若
继续把它留在 #7827，最终 diff 至少还会包含 `resource_test.go`。2026-08-14 发布到 #7827 的新评论已明确
建议将 PDB cleanup 单独处理，因此“一文件 PR”成立的前提是从 #7827 移出当前 PDB 改动。

当前还需在真实 E2E 中验证两个连接边界：动态 estimator Pod available 后 scheduler 是否在测试 timeout 内
完成 gRPC 连接，以及失败 cleanup 是否总能删除 host 侧 estimator 资源。未完成该验证前，不应删除旧分支
改动或改写 PR body 的验证声明。

## 代码与验证状态

分支 `test/estimator-assumption-isolation` 只有一个 DCO commit：
`ba531a9a1e57e164488c9ce84b8549273a844b11`。本地执行结果：

```text
go test -count=1 ./test/e2e/framework ./test/e2e/suites/base -run '^$'
PASS

go test -race -count=1 ./test/e2e/framework ./test/e2e/suites/base -run '^$'
PASS

golangci-lint run ./test/e2e/framework/... ./test/e2e/suites/base/...
PASS (0 issues)

go vet ./test/e2e/framework ./test/e2e/suites/base
PASS

PATH=/root/go/bin:$PATH make verify
PASS

make test
PASS

git diff --check
PASS
```

第一次 `make verify` 在下载安装 `golangci-lint` 时因 curl error 28 退出。本机已经有项目要求的
`/root/go/bin/golangci-lint v2.12.2`，把 `/root/go/bin` 加入 `PATH` 后完整 verifier 通过，失败尝试没有
修改源码。

本机没有 Karmada kubeconfig 或可用的多集群 control plane。尝试运行真实 suite 时失败在
`SynchronizedBeforeSuite`，274 个 spec 中执行 0 个。因此 compile/race-compile 结果不能替代真实 E2E。

## Issue 与 PR 状态

- Issue #7826 已于 2026-08-13 创建并分配给 `ranxi2001`；同日经复盘将正文最终替换为五泳道带时间版，
  同时表达 producer/consumer spec、cleanup 代码、残留对象/状态和 UTC 时间。创建时模板 metadata 没有
  自动添加 `kind/flake`；后续添加 label 因上游权限不足而失败。
- 2026-08-14 在 #7826 发布 [target 语义澄清](https://github.com/karmada-io/karmada/issues/7826#issuecomment-5290948445)
  与 [taint 规模说明](https://github.com/karmada-io/karmada/issues/7826#issuecomment-5290950443)，随后按复核结果
  原位替换：前者说明 `estimator_test` 的 CRD、Flink workload 和 probe 都固定到 member1；后者只量化
  member1 estimator 实际消费的外来 30m，不再用三集群 90m 解释失败。最终远端 SHA-256 分别为
  `9b6cd18259091bfae25001c282fd80a7df7a0a49e8fca22e72053a6139bb7c6b` 与
  `af711b11d816aa4f0b6ac27f84564af5db2b6be93aaa737130a913118f8ed52b`，均与用户确认草稿逐字一致。
- PR #7827 于 2026-08-13 创建，base 为 `master`，head 为
  `ranxi2001:test/estimator-assumption-isolation@ba531a9a1`，状态为 Open、非 Draft、Mergeable。
- 2026-08-14 已在 #7827 发布
  [专用 member cluster 方案](https://github.com/karmada-io/karmada/pull/7827#issuecomment-5291634887)：
  NodeResource assumption spec 改用临时独立集群并单独部署 scheduler-estimator，PDB cleanup 移出主隔离机制。
  本轮只完成既有 E2E 先例与单文件可行性研究，尚未修改 PR head。
- PR body 包含 `/kind cleanup` 和 `/kind flake`，当前标签为 `kind/cleanup`、`kind/flake`、`size/M`。
- 截至 2026-08-13 CI 复核，DCO、codegen、compile、lint、unit test、三组普通 Kubernetes test 和
  `e2e test (v1.34.0/v1.35.0/v1.36.1)` 均通过；Tide 仅等待 `lgtm` 和 `approved`。2026-08-14 只补充
  上述 issue evidence comment，没有触发 retest。

这表示本地实现和大部分 upstream gate 已完成，外部 acceptance 仍由 E2E 结果和 maintainer review 决定。

## 残余风险与证据边界

1. 当前没有受控的 patch 前失败、patch 后通过实验，证据保持 E3；upstream 单次绿灯也只能验证该 SHA 在
   当次环境通过，不能单独证明所有污染 producer 已消失。
2. API NotFound barrier 阻断的是已确认的 late ResourceBinding patch 路径，不直接观测 estimator 进程中
   每一项内部状态；结论依赖已核对的“成功 patch 后才更新 assumption”生产链。
3. 修复覆盖 taint/toleration 和 PDB 两个已确认 cleanup producer。official run 已闭合到 E3；fork run
   attempt-1 的 component artifact 已被 rerun 覆盖，当前只能从保存的分析结论、job timeline 和源码复核
   第二条 producer/consumer 映射，不能重新制造其完整 cache timestamp chain。
4. 本 PR 不改变 production 的 delete/reschedule 竞态、五分钟 TTL 或 cache 语义；这些问题需要独立的
   生产可达性和 ownership contract，不能从本次 test-only patch 推导。

## 下一步

1. 若决定实施新方案，只修改 `estimator_test.go`：先在当前 topic worktree 完成临时 Kind、estimator、join、
   dynamic client 和 LIFO cleanup，再跑 compile/race-compile。更新开放 PR branch 和 PR body 前仍需单独确认
   exact diff/action；本轮未获得该发布授权。
2. 若需要把证据升级为 E4，在同一可控多集群环境复现污染，再对同一场景应用补丁并验证失败消失；普通
   绿色 rerun 不足以升级证据等级。
3. PDB fixture cleanup 作为独立 cleanup 问题处理，不再作为 `EstimatorAssumption` 的隔离机制；若保留在同一
   PR，需明确接受最终 diff 不再是单文件。
4. #7827 进入外部等待后，工作主线回到 #7492 PR1：完成 legacy-write safety guard、RB/CRB 真实 API
   Server 回归和 rebase 后验证，再准备正式 PR。
