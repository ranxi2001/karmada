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

修订稿改为以下顺序：

1. 先声明两个 job 都失败在同一个 NodeResource spec 和同一个 420 秒断言。
2. 用 producer/残留/consumer/result 四列把两个 run 一一对应。
3. 分别绘制 official run 和 fork run 的时序图，不跨 run 拼接时间线。
4. official run 承担 E3 根因链；fork run 只证明第二个 cleanup producer 和同一 consumer，不借已被 rerun
   覆盖的 artifact 扩大 cache/TTL 结论。
5. 最后才给统一 cleanup contract 与明确 non-goals。

可直接替换 issue body、但尚未发布的英文稿见
[`day48-issue7826-revised-body-draft.md`](day48-issue7826-revised-body-draft.md)。

本轮还发现两条适合补入 `$e2e-root-cause-analysis` 的通用规则，但按 skill 的 Step 5 只提出、不直接修改：

1. 下载 artifact 前先读取 job 的 `run_attempt`，并核对 artifact `created_at`。GitHub rerun 后，run-level
   同名 artifact 可能只对应最新 attempt；如果与失败 job attempt 不一致，应停止拼接证据，并在 rerun 前
   固化失败 attempt 的 job/component logs。
2. 当一个 issue 合并多个 CI run 或多个 producer 时，报告必须先列出
   `failing spec -> assertion -> producer spec -> residual object/state -> causal effect` 映射，再分别画每个 run
   的时间线；不能只按全局时间顺序叙述。

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

- Issue #7826 已于 2026-08-13 创建并分配给 `ranxi2001`。创建时模板 metadata 没有自动添加
  `kind/flake`；后续添加 label 因上游权限不足而失败，issue 内容未因此改变。
- PR #7827 于 2026-08-13 创建，base 为 `master`，head 为
  `ranxi2001:test/estimator-assumption-isolation@ba531a9a1`，状态为 Open、非 Draft、Mergeable。
- PR body 包含 `/kind cleanup` 和 `/kind flake`，当前标签为 `kind/cleanup`、`kind/flake`、`size/M`。
- 截至 2026-08-13 本轮复核，DCO、codegen、compile、lint、unit test、三组普通 Kubernetes test 和
  `e2e test (v1.34.0/v1.35.0/v1.36.1)` 均通过；Tide 仅等待 `lgtm` 和 `approved`。没有发布额外
  comment 或触发 retest。

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

1. 等待 PR #7827 三组 upstream E2E 和 maintainer review；只有 current SHA 出现失败或 reviewer 提出新问题
   时再做定向分析，不在无新信号时重复 retest 或 comment。
2. 若需要把证据升级为 E4，在同一可控多集群环境复现污染，再对同一场景应用补丁并验证失败消失；普通
   绿色 rerun 不足以升级证据等级。
3. #7827 进入外部等待后，工作主线回到 #7492 PR1：完成 legacy-write safety guard、RB/CRB 真实 API
   Server 回归和 rebase 后验证，再准备正式 PR。
