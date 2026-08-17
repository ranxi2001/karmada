# Day 51：Karmada 近期 PR CI E2E 失败归并分析

## 先说人话

2026-08-10 至 2026-08-17，共有 51 次由 `pull_request` 触发的 `CI Workflow`：24 次成功、12 次失败、14 次取消，另有 1 次校验时尚未结束。12 次失败 workflow 中，11 次包含 E2E 红灯，共有 19 个失败 E2E job。

这 19 个红 job 不代表 19 个独立 flake。12 个来自三个确定性的 PR 代码或测试契约问题：#7824 的同一断言在两个 head、三个 Kubernetes 版本上失败 6 次；#7837 的同一编译错误在三个版本上失败 3 次；#7832 的同一状态 reason 变化让三个版本分别卡在两个 estimator spec 中，又失败 3 次。一个错误同时击中三个并行 E2E job，就会把一处问题显示成三处红灯。

另外 1 个红 job（#7835 当前 head）已经闭合到处理请求的 estimator 没有使用已经创建的 `ResourceQuota`，但底层原因只能暂定为 informer 可见性时序；剩余 6 个红 job 才是 Kind、Docker 或 control plane 失效。这批 PR CI 没有呈现一个共同的 Kubernetes 版本兼容问题，也不能用一次统一重跑解释完。

当前最直接的行动是修正 #7832 与 #7824 的 E2E 预期，并为 #7835 在 estimator 行为边界补同步。#7837 已在后续 commit 修复；其余环境类失败先重跑，只有同一阶段重复出现时再下载 artifact 深挖。

## 范围与统计口径

- 时间窗口：2026-08-10 至 2026-08-17。
- 只统计 `pull_request` 事件触发的 [`CI Workflow`](https://github.com/karmada-io/karmada/actions/workflows/ci.yml)，不混入 `schedule`、`push` 或 compatibility workflow。
- 查询口径：`gh run list --workflow 'CI Workflow' --event pull_request --created '>=2026-08-10'`。
- E2E job 是 PR CI 中并行运行的 `v1.34`、`v1.35`、`v1.36` 三个 job；本文按 job 计数，但按首个硬错误归并根因。
- Ginkgo 汇总中的 `AfterEach`、`SynchronizedAfterSuite`、并行 process 中断和 API 失联后的连锁失败不重复计算为独立根因。
- #7832 的较早一次 workflow 只有 lint/codegen 失败，没有 E2E 失败，因此计入 12 次失败 workflow，但不计入 19 个失败 E2E job。

## 具体例子：一个契约变化如何变成三个 E2E 红灯

[PR #7832 的失败 workflow](https://github.com/karmada-io/karmada/actions/runs/31751405410) 把“没有集群满足资源约束”从普通错误改成 `framework.UnschedulableError`。调度器因此把 `ResourceBinding` reason 写成 `BindingReasonUnschedulable`；现有 estimator E2E 仍等待写死的 `BindingReasonSchedulerError`。

三个 E2E job 都执行了这份过期断言，但并行执行顺序不同：v1.34 和 v1.35 最终在 `NodeResource` 场景失败，v1.36 在 `ResourceQuota` 场景失败。表面看是两个 spec、三个版本，代码链路却只有一个：生产代码按新语义写 `Unschedulable`，测试仍按旧语义等待 `SchedulerError`。继续等待不会让 reason 自行变回旧值。

## 失败归并

| PR / 失败 head | 失败 E2E job | 首个硬错误或失败阶段 | 分类 | 当前判断与行动 |
| --- | ---: | --- | --- | --- |
| [#7824](https://github.com/karmada-io/karmada/pull/7824), `f4a5663eed` / `0529298359` | 6 | `resource_test.go:261` 要求三个 member 的 `nodePort` 相同 | 确定性测试契约不匹配，E3 | PR 正在让 member 独立分配 `nodePort`，E2E 仍验证旧行为；应改断言 |
| [#7837](https://github.com/karmada-io/karmada/pull/7837), `afecff517b` | 3 | `TargetCluster does not satisfy comparable`，E2E 未开始执行 | 确定性编译回归，E3 | `TargetCluster` 新增 slice 后仍被 `slices.Contains` 使用；后续改为 `slices.ContainsFunc`，三个 job 已通过 |
| [#7832](https://github.com/karmada-io/karmada/pull/7832), `857e07bc21` | 3 | estimator spec 等待旧的 `BindingReasonSchedulerError` | 确定性状态契约不匹配，E3 | 应把相关断言更新为 `BindingReasonUnschedulable`，并搜索其他旧 reason 预期 |
| [#7835](https://github.com/karmada-io/karmada/pull/7835), `782232b7db` | 1 | v1.35 将 4 replicas 全放到 member1，未得到预期的 `2/2` | 直接机制 E3；底层同步原因 E2 | 被请求的 estimator 副本未见 member1 quota；应在 estimator 行为边界同步，而不只等待 member API 对象存在 |
| [#7840](https://github.com/karmada-io/karmada/pull/7840), `b159fec7a6` | 1 | v1.34 中 host 与 member1 API 先后失联，随后多个 spec 清理失败 | control plane 失效，E1 | 同 SHA 的 v1.35/v1.36 通过；先重跑，若重复再定位 API server/etcd 首个退出点 |
| [#7834](https://github.com/karmada-io/karmada/pull/7834), `687ad01caf` | 1 | v1.34 的动态 Kind node 未出现 systemd/cgroup 就绪日志 | Kind 启动失败，E1 | 失败发生在 PR 修改的集群创建后检查之前；相邻两个 job 通过，先重跑 |
| [#7833](https://github.com/karmada-io/karmada/pull/7833), `1d2ee95c4f` | 1 | v1.34 动态 Kind node 等待 systemd/cgroup 日志超时 | Kind 启动失败，E1 | 当前 head `98535c5413` 三个 E2E job 均通过 |
| [#7830](https://github.com/karmada-io/karmada/pull/7830), `ac32f86714` | 1 | v1.35 动态集群 `kubeadm init` 退出 | Kind 启动失败，E1 | 当前 head `6ff28fe4a1` 三个 E2E job 均通过 |
| [#7835](https://github.com/karmada-io/karmada/pull/7835), `b1c41a584c` | 1 | v1.36 在功能断言通过后执行 `docker rm`，未收到 container exit event | Docker 清理失败，E1 | 与当前 head 的 quota 同步失败是两个不同问题 |
| [#7820](https://github.com/karmada-io/karmada/pull/7820), `6d62ae223a` | 1 | v1.36 先出现 Event API 504，随后 host API connection refused | control plane 失效，E1 | 当前 head `21d759efd2` 三个 E2E job 均通过；汇总中的 8 个失败 spec 是连锁结果 |

按 job 归并后：12/19 是确定性的 PR 代码或测试契约问题，1/19 是已定位直接机制的 E2E 同步问题，6/19 是环境或控制面故障。近期红灯多，主要因为同一确定性错误会同时击中三个 E2E job，而不是因为出现了一个影响所有测试的共同 flake。

## #7832：生产代码改了 reason，E2E 仍等待旧 reason

### 运行过程

1. [`selectClusters`](https://github.com/karmada-io/karmada/blob/857e07bc21/pkg/scheduler/core/spreadconstraint/select_clusters_by_cluster.go#L37-L43) 在没有足够资源时返回 `framework.UnschedulableError`。
2. [`getConditionByError`](https://github.com/karmada-io/karmada/blob/857e07bc21/pkg/scheduler/helper.go#L113-L150) 将该错误映射为 `BindingReasonUnschedulable`。
3. [`ResourceQuota`](https://github.com/karmada-io/karmada/blob/857e07bc21/test/e2e/suites/base/estimator_test.go#L361-L369) 和 [`NodeResource`](https://github.com/karmada-io/karmada/blob/857e07bc21/test/e2e/suites/base/estimator_test.go#L489-L512) 两处测试仍把 `BindingReasonSchedulerError` 写死在 predicate 中。
4. v1.34/v1.35 日志已经出现 `failed to select clusters: no enough resource`，v1.36 的第七个 Flink workload 也进入不可调度状态；测试因 reason 不匹配继续等待，最终超时。

### 结论

失败不是 #7826 的跨 spec `EstimatorAssumption` 残留，也不是 Kubernetes 版本兼容。三个版本落到不同 spec，是并行执行顺序造成的受影响测试差异；共同的失败操作是 predicate 等待了已经不再产生的旧 reason。

最小修正是让这些断言匹配 `BindingReasonUnschedulable` 的新合同，并审计 estimator E2E 中其他 `BindingReasonSchedulerError` 预期。修正后需要重新执行三个 E2E job；当前证据还不是 E4，因为尚未观察修正前后对照。

## #7824：产品目标允许不同 nodePort，E2E 却要求完全相同

PR #7824 在下发 Service 前[移除 `spec.ports[*].nodePort`](https://github.com/karmada-io/karmada/blob/0529298359/pkg/resourceinterpreter/default/native/prune/prune.go#L183-L215)，目标是让每个 member cluster 独立分配端口。现有 [`resource_test.go`](https://github.com/karmada-io/karmada/blob/0529298359/test/e2e/suites/base/resource_test.go#L244-L261) 收集所有 member 的 `nodePort` 后仍断言 `nodePorts.Len() == 1`，等价于要求三个 member 分配相同端口。

[较早 head](https://github.com/karmada-io/karmada/actions/runs/31586146127) 与[当前失败 head](https://github.com/karmada-io/karmada/actions/runs/31590369282) 上的 v1.34、v1.35、v1.36 都在同一行、创建 Service 后约 5 至 6 秒失败，共产生 6 个红 job。这是最清楚的“一个旧断言放大成六个 CI 红灯”样本。测试应验证每个 member 得到了合法、非零的 `nodePort`，并验证传播对象没有携带源集群写入的固定值；是否要求 member 之间互不相同不能由随机分配结果保证，不应作为确定性断言。

## #7835：等待 member API 对象，不等于 estimator 已看到它

### 代码声明

[`clusteraffinities_test.go`](https://github.com/karmada-io/karmada/blob/782232b7db/test/e2e/suites/base/clusteraffinities_test.go#L501-L505) 的注释要求两个 estimator 都观察到 quota，但调用的 [`WaitResourceQuotaPresentOnCluster`](https://github.com/karmada-io/karmada/blob/782232b7db/test/e2e/framework/resourcequota.go#L57-L68) 只向 member API 执行 `GET ResourceQuota`。随后测试把 replicas 从 2 改为 4，并等待 `member1:2, member2:2`。

### 实际请求

[失败 job 与 artifact](https://github.com/karmada-io/karmada/actions/runs/31902564843/job/95056366571) 显示：member1 的 estimator 请求处理中，`ResourceQuotaEstimator` 返回 `2147483647`，即该请求未受到 quota 限制；member2 返回上限 2。调度器因此得到 member1 仍可放 4 个 replicas 的估计，并成功写入 `{member1:4}`。E2E 随后一直等不到 `2/2`，420 秒后超时。

部署中每个 member 有两个 scheduler-estimator replica。member API 已能读取 quota，只能证明权威对象已经创建，不能证明接收下一次请求的 estimator replica 的 informer cache 已经观察到它。日志能直接证明“处理该请求的 estimator 没有用上 quota”，但尚不能单靠现有 artifact 证明该副本未见 quota 的更底层原因一定是 informer 延迟，因此分别标为 E3 和 E2。

修正应放在测试同步边界：让测试在扩容前确认 estimator 的实际估算行为已经反映 quota，或给该场景提供隔离且可观测的 estimator 环境。仅增加固定 sleep 或修改生产调度逻辑，会掩盖测试声明与实际观察边界的差异。

## 环境类红灯为什么不能当成多个业务失败

#7840 与 #7820 都先出现 Karmada host/control-plane API 超时或 connection refused，之后多个并行 spec 的查询、`AfterEach` 和清理一起失败。失败列表中的 8 个 spec 只是同时失去 API server 的受影响方，不能分别归因到 CronFederatedHPA、Service 或其他业务逻辑。

#7834、#7833、#7830 均失败在动态 Kind cluster 的 node 初始化阶段；#7835 较早 head 则失败在测试已通过后的 Docker 删除阶段。这些失败点位于业务断言之前或之后，当前样本只支持环境故障分类，尚不足以确定 runner、Kind、systemd、Docker 或资源压力中的哪一层是最终物理原因。

## 已确定与仍待确认

### 已确定

- #7832、#7824、#7837 的失败都能由具体 diff、源码路径和多个失败执行闭合，不属于随机 CI flake。
- #7835 当前 head 的直接失败机制是 estimator 返回了未受 member1 quota 限制的估算，调度器据此选择 `{member1:4}`。
- 19 个红 job 中有 6 个属于 Kind、Docker 或 control-plane 失效；同一 run 后续的多个失败是连锁影响。
- 这批 PR CI 不支持“某个 Kubernetes 版本普遍不兼容”的结论：确定性问题跨三个版本失败，环境问题只在单个 job 出现且相邻 job 通过。

### 仍待确认

- #7835 中被请求的 estimator replica 为什么没有使用已经创建的 quota；informer 可见性窗口最符合代码与日志，但缺少该副本 cache 同步的直接日志。
- #7840、#7820 的 control-plane 为什么退出；需要重复样本和 API server/etcd 首个异常，而不是只看最终 connection refused。
- 三个 Kind 启动或删除失败是否共享 runner 资源压力；当前失败阶段不同，不能合并成同一物理根因。

### 移出当前范围

[Day 50](day50-karmada-recent-e2e-failure-scan-2026-08-17.md) 分析的是 `schedule` 触发的周末 workflow，其中的 Job status version-skew 结论在该范围内仍有效，但不能用来解释本报告的 PR CI 红灯。本文也不把取消的 workflow 当成测试失败。

## 下一步

1. #7832：更新 estimator E2E 的 reason 预期，搜索同类旧断言，然后用三个 E2E job 验证前后对照。
2. #7824：把 NodePort E2E 从“所有 member 值相同”改为“每个 member 获得合法分配，传播对象不固定源端口”，避免断言随机分配一定互异。
3. #7835：先设计 estimator 行为边界的同步方式，再改这一个 `clusteraffinities_test.go` 场景；不扩大 scheduler 或 estimator 的生产职责。
4. #7840 与 #7834：先重跑。只有在相同阶段重复失败时，再按 exact run attempt 下载 artifact 并追首个 control-plane 或 Kind 错误。
5. 分析流程补一条固定入口：先记录 workflow event、PR、head SHA 和 run attempt，再做失败聚类，避免把 `schedule` 与 `pull_request` 样本混在一起。
