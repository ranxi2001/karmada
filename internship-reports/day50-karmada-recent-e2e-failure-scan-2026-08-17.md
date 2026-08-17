# Day 50：Karmada 近期 E2E 失败归并分析

## 先说人话

截至 2026-08-17，Karmada 周末 E2E 矩阵看起来有很多测试同时失败，但这些红灯不能按 job 数量理解成同样多的独立缺陷。

最近一个周末的 4 次定时 workflow 一共有 32 个红 job。其中 16 个都落在 Job 状态聚合与 Kubernetes 版本偏差上，但不是同一条单向错误，而是两个相反方向：普通矩阵的旧 member cluster 不提供 `JobSuccessCriteriaMet=True`，较新的 Karmada API server 拒绝只有 `Complete=True` 的聚合状态；compatibility 矩阵的较新 member cluster 会提供该 condition，旧的 Karmada API server v1.30 又拒绝普通 NonIndexed Job 携带它。其余 16 个主要分布在 control-plane etcd 延迟、Kind 集群创建/删除和动态 member cluster 就绪阶段；失败的业务 spec 会变化，说明这些 spec 多数只是当时撞上环境异常的受影响方。

这也不是本周突然恶化。最近 3 个周末，普通矩阵每次红 4-5/10，APIServer compatibility 矩阵每次红 10-12/40。当前最值得单独跟进的是仍未解决的 Job version-skew 问题，而不是逐个给所有红色 spec 提业务修复。

## 范围与口径

- 重点窗口：2026-08-10 至 2026-08-17。
- 当前样本：2026-08-15 和 2026-08-16 的 [CI Schedule Workflow](https://github.com/karmada-io/karmada/actions/workflows/ci-schedule.yaml) 与 [APIServer compatibility](https://github.com/karmada-io/karmada/actions/workflows/ci-schedule-compatibility.yaml)。
- 当前运行：[普通矩阵 08-15](https://github.com/karmada-io/karmada/actions/runs/31899968536)、[普通矩阵 08-16](https://github.com/karmada-io/karmada/actions/runs/31963367769)、[compatibility 08-15](https://github.com/karmada-io/karmada/actions/runs/31905566319)、[compatibility 08-16](https://github.com/karmada-io/karmada/actions/runs/31969323652)。
- 趋势对照：额外统计 2026-08-01/02、2026-08-08/09 的相同 workflow。
- 当前 4 次运行都基于 commit [`a957f64d5`](https://github.com/karmada-io/karmada/commit/a957f64d50213729b4d34f3c298ca3630e1c9127)，`run_attempt=1`，不存在把 rerun artifact 混入原始 attempt 的问题。
- 计数只采用每个 Ginkgo process 的首个非 `INTERRUPTED` 失败。另一个并行 process 被中断、`AfterEach` 或 `SynchronizedAfterSuite` 清理失败不再重复算作独立根因。

## 结论

| 类别 | 最近周末红 job | 判断 | 当前行动价值 |
| --- | ---: | --- | --- |
| Job 状态聚合的 Kubernetes version skew | 16 | 两个相反方向的确定性兼容问题，均达到 E3：组件错误、矩阵角色和源码闭合了写入被拒到断言超时的因果链 | 最高，应新建一个聚焦聚合状态跨版本合同的 issue，并明确 #6414 / #6964 只覆盖了部分矩阵 |
| Karmada control-plane API / etcd 延迟 | 8 | 直接原因到 E3：API timeout 与同时间 etcd 慢写吻合；runner I/O 等上游物理原因仍为 E2 假设 | 高，但需要按 runner、时间和 artifact 继续归并，不能修业务 spec |
| Kind / Docker 生命周期失败 | 5 | E1 环境 flake：同一 SHA 的失败落在不同 `kind create/delete`、`kubeadm init` 或 `docker rm` 阶段；物理原因未查明 | 中，先改进诊断和重跑样本，再判断是 runner 还是 Kind helper |
| 动态 member cluster 就绪超时 | 2 | E1 重复症状：取 impersonation ServiceAccount Secret 超时，尚未闭合 member apiserver 原因 | 中，需要 member apiserver artifact 才能继续归因 |
| ResourceInterpreter 请求被 client rate limiter 截止 | 1 | E0 单样本 | 低，等待重复样本，不建议现在改产品代码 |

## 两个具体例子：为什么 16 个 Job 红灯属于同一问题族

以 2026-08-16 普通矩阵的 [v1.30 job](https://github.com/karmada-io/karmada/actions/runs/31963367769/job/95204623803) 为例：

1. 18:15:41 创建源 Job `karmadatest-nhmzv/job-lggmk` 和 `PropagationPolicy`。
2. 测试按 [`len(framework.Clusters())`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/test/e2e/suites/base/resource_test.go#L385-L400) 计算期望值 3，然后轮询源 Job 的 `Status.Succeeded`。
3. member1、member2、member3 的 Job Pod 都实际运行并完成；问题不在 workload 没有传播。
4. 源 Job 的 `Status.Succeeded` 在 18:16:22 变为 2，之后一直停在 2，18:20:42 达到 300 秒超时。
5. 同一时间，`karmada-controller-manager` 持续报告：

   ```text
   Job.batch "job-lggmk" is invalid: status.conditions: Invalid value: cannot set Complete=True condition without the SuccessCriteriaMet=true condition
   ```

因此，E2E 断言是受影响点，失败操作是 control plane 更新聚合 Job status，拒绝者是 Karmada 使用的 kube-apiserver。

但 compatibility 矩阵不是上述配置的重复执行。以 2026-08-16 的 `v1.30.0 + release-1.17` job 为例：

1. workflow 的 `kubeapiserver-version: v1.30.0` 被写入 `KARMADA_APISERVER_VERSION`，所以 v1.30.0 是 Karmada API server，不是 member cluster。
2. release-1.17 的默认 Kind 镜像是 Kubernetes v1.35.0；artifact 的 `inspect.json` 也记录了 `kindest/node:v1.35.0`。
3. 三个 member Job 都完成，并向聚合器提供 `JobSuccessCriteriaMet=True`。
4. Karmada API server v1.30.0 在 22:02:51 开始持续拒绝聚合状态：

   ```text
   Job.batch "job-5lc4d" is invalid: [status.conditions: Invalid value: cannot set SuccessCriteriaMet to NonIndexed Job, status.conditions: Invalid value: cannot set SuccessCriteriaMet=True for Job without SuccessPolicy]
   ```

5. 源 Job 的 `Status.Succeeded` 同样卡在 2，E2E 在 300 秒后超时。

两边共享同一个聚合函数和同一个最终症状，但 API server 要求正好相反。这个差异决定了修复不能是“始终添加”或“始终删除”一个 condition。

## 先把矩阵里的版本角色说清楚

| Workflow | 矩阵版本代表什么 | member cluster 版本 | Karmada API server 版本 | 被拒绝的聚合状态 |
| --- | --- | --- | --- | --- |
| `CI Schedule Workflow` | `CLUSTER_VERSION`，同时用于 host Kind 和 3 个 member Kind cluster | v1.27.3-v1.30.0 | 默认 v1.36.2 | `Complete=True`，缺少 `SuccessCriteriaMet=True` |
| `APIServer compatibility` | `KARMADA_APISERVER_VERSION` | 各 Karmada 分支的默认版本；master v1.36.1、release-1.18/1.17 v1.35.0、release-1.16 v1.34.0 | v1.30.0 | 普通 NonIndexed、无 `successPolicy` 的 Job 携带 `SuccessCriteriaMet=True` |

这里曾发生一次分析误差：最初只按矩阵显示的 `v1.30.0` 归并，误把 compatibility 轴也当成 member 版本。workflow 环境变量、Kind `inspect.json` 和 Karmada API server 启动日志证明该解释错误，现已按运行时角色纠正。

## Job version-skew 的源码链路

运行 SHA 的 [`ParseJobStatus`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/pkg/util/helper/job.go#L102-L123) 有两个不同条件：

1. `successfulJobs == len(status)` 时，无条件生成聚合后的 `JobComplete=True`。
2. 只有每个 member status 本来就带有 `JobSuccessCriteriaMet=True` 时，才生成聚合后的 `JobSuccessCriteriaMet=True`。

老版本 member Job 可以完成，但不会提供新 condition。Karmada 因而构造出“有 `Complete=True`、没有 `SuccessCriteriaMet=True`”的聚合状态；较新的 Karmada API server 拒绝这个状态转换。反过来，较新 member Job 都提供该 condition 时，当前实现会原样合成 `SuccessCriteriaMet=True`，旧 Karmada API server v1.30 又按当时的 Job 合同拒绝它。两种情况下，源 Job 都保留上一次成功写入的状态，E2E 最终读到 2 而不是 3。

这条链路在两个 workflow 中都会被放大：

- 普通矩阵：v1.27.3、v1.28.0、v1.29.0、v1.30.0 连续两天各失败一次，共 8 个 job。
- compatibility 矩阵：Karmada API server v1.30.0 分别配 master、release-1.16、release-1.17、release-1.18 的代码与默认 member 版本，两天各失败 4 个，共 8 个 job。

## 与历史 #6414 / #6964 的关系

[Issue #6414](https://github.com/karmada-io/karmada/issues/6414) 记录过相同的 300 秒超时和相同 kube-apiserver 校验错误。[PR #6964](https://github.com/karmada-io/karmada/pull/6964) 在 2025-11-29 合入后，为一致版本的 member Job 聚合 `JobSuccessCriteriaMet`。

但该 PR 的 maintainer review 已明确保留 version-skew 边界：这个修改不能完全解决 #6414，只能在 control plane 与 member Kubernetes 版本一致时正常工作，[#6414 仍可能需要另一种方案](https://github.com/karmada-io/karmada/pull/6964#issuecomment-3591045723)。当前两套日志分别命中了“新 API server + 旧 member”和“旧 API server + 新 member”两个方向，正是当时已经声明、但 issue 关闭后未继续跟踪的边界。

### 为什么 #6964 当时没有一次修完

现有讨论能证明这是有意识的窄修复，不是完全遗漏：

1. 当时的直接任务是让 [#6960](https://github.com/karmada-io/karmada/pull/6960) 把 compatibility 测试扩展到 Kubernetes v1.34；#6964 的 body 明确说补丁已在该 PR 验证，并准备回移 release branch。
2. #6964 只在“所有 member 已经报告 `SuccessCriteriaMet=True`”时聚合该 condition。它没有为旧 member 合成新语义，也没有把目标 API server 的版本或 feature-gate capability 传入 `ParsingJobStatus`。
3. #6964 的 body 在 review 前已经警告：`karmada-apiserver@v1.30.0` 管理 v1.32+ member 的场景可能失败，值得后续研究。维护者合入时再次明确该补丁只覆盖版本一致的组合。
4. 完整修复不是再加一个 `if`：同一个普通 JobStatus 在新 API server 上必须带 condition，在旧 v1.30 API server 上又不能带。代码需要先有“按哪个目标能力生成合法终态”的合同，而当时的 thread 没有形成这个设计。

#6414 随带有 `Fixes #6414` 的 #6964 合并而自动关闭。关闭动作证明该窄补丁完成了当时绑定的 PR，不证明 maintainer 评论中保留的 version-skew 场景已经解决。现有证据不能说明为什么此后没有人继续实现，例如优先级或人力原因；能确定的是风险已被明确记录，但没有留下独立 open issue 继续跟踪。

修复合同应当是：Karmada 根据 member 状态得出统一的完成语义，同时向目标 Karmada API server 写入该版本允许的 JobStatus 表示。代码如何获知或规避版本化校验仍未确定；无条件合成 `JobSuccessCriteriaMet=True` 已被 v1.30 compatibility artifact 直接证伪，无条件删除也会重新触发较新 API server 的错误。因此目前可以写 issue，但还不能声称已有可提交的最小 PR 方案。

## 其余失败为何不应按业务 spec 归因

### Karmada API / etcd 延迟

两天内受到影响的首个失败点包括 `Aggregated Kubernetes API Endpoint`、`karmadactl register`、`karmadactl join/unjoin` 和 rescheduling。它们最终都出现以下一组错误：

```text
the server is currently unable to handle the request
etcdserver: request timed out
context deadline exceeded
```

在 [v1.35 master compatibility job](https://github.com/karmada-io/karmada/actions/runs/31969323652/job/95219145029) 中，测试在 01:03:30 首先因读取 `Cluster` 返回 `ServiceUnavailable` 而失败。对应 artifact 的 Karmada host etcd 在同一时间段记录了数百毫秒到数秒的 `apply request took too long`、`waiting for ReadIndex response took too long`，并在 01:03:43 记录：

```text
"msg":"slow fdatasync","took":"2.331012521s","expected-duration":"1s"
```

因此该 job 的 `aggregatedapi_test.go` 是失败承载点，不是现有证据支持的根因位置。

### Kind / Docker 生命周期

这类失败发生在业务断言之前或清理阶段，代表错误包括：

```text
could not find a log line that matches "Reached target .*Multi-User System.*|detected cgroup v1"
failed to init node with kubeadm
failed to delete nodes: command "docker rm -f -v ..." failed
```

相同 Kind 启动错误可以落在 `FederatedResourceQuota`，Docker 删除错误可以落在 namespace 或 rescheduling 的 `AfterEach`。测试名称随执行顺序变化，不能据此给 FederatedResourceQuota、namespace 或 rescheduling 产品逻辑加 retry。

### 后续失败与 `INTERRUPTED`

当一个并行 Ginkgo process 首先失败后，其他 process 会停止，日志会列出多个 `[INTERRUPTED]` spec。动态集群已损坏时，后续 `AfterEach` 和 `SynchronizedAfterSuite` 还会出现 namespace 删除失败、cluster 读取失败或 connection refused。这些记录说明清理不完整，但不增加独立根因数量。

## 最近三周趋势

| 周末 | 普通矩阵失败 | compatibility 矩阵失败 |
| --- | ---: | ---: |
| 2026-08-01/02 | 8/20 | 21/80 |
| 2026-08-08/09 | 9/20 | 21/80 |
| 2026-08-15/16 | 9/20 | 23/80 |

三个周末的失败规模基本持平。普通矩阵中，每次稳定失败的 4 个旧 Kubernetes 版本解释了 24/26 个红 job；compatibility 矩阵中，每次稳定失败的 4 个 v1.30 组合解释了 24/65 个红 job。后一个矩阵仍有较高比例的环境型失败，需要单独治理，但没有证据表明本周发生了新的突增。

## 已确定与仍待确认

已确定：

- Job status collection 是确定性的 version-skew 兼容缺陷族，不应继续标为普通 flake。
- 普通矩阵与 compatibility 矩阵分别证明两个相反方向；它们共享聚合边界和 E2E 症状，但不能合并成同一条单向错误。
- 当前 #6414 的关闭状态没有覆盖 maintainer 当时明确保留的 control-plane/member 版本不一致场景。
- 多个看似不同的业务 spec 由 control-plane etcd 延迟或 Kind 生命周期错误共同影响。
- [PR #7827](https://github.com/karmada-io/karmada/pull/7827) 当前 head `6ebc4b459` 的全部 3 个 E2E jobs 均通过，与本轮定时矩阵失败没有直接关系。

仍待确认：

- Karmada 应通过 API server 版本、功能能力、Job spec 形态还是另一种稳定规则，选择合法的终态表示。
- 最小 PR 能否只改 `pkg/util/helper/job.go` 及其单测，还是需要把目标 API server capability 传入聚合边界。
- etcd 慢写的上游原因是 GitHub runner I/O、同一 job 内资源竞争，还是测试环境参数；artifact 已证明 etcd 延迟，但还没有 runner 级反事实。
- Kind 创建/删除失败是否能由重跑稳定消失，以及是否集中在特定 runner image、Kind 或 Docker 版本。
- `resourceinterpreter_test.go:538` 的 client rate limiter 超时目前只有一个样本，不足以提出代码修改。

## 下一步

1. 优先为 Job version-skew 建立一条新的 upstream 跟踪记录，明确两个方向的矩阵角色、相反校验错误，以及它与已关闭 #6414、已合入 #6964 的“同一聚合边界、未覆盖版本偏差”关系。发布前仍需准备并确认 exact issue text。
2. issue 讨论先确认跨版本聚合合同，再决定实现。回归至少覆盖 `old member -> new API server` 和 `new member -> old API server`；在合同未定前不提交无条件增删 condition 的 PR。
3. 对基础设施失败按“首个失败操作 + artifact 时间窗口”继续收集，不按业务 spec 名称建多个 issue。若下一周仍出现 etcd `slow fdatasync`，再形成独立的 CI 环境 issue。
4. 后续矩阵扫描先把每个版本轴绑定到运行时角色，再按 run SHA 和首个非 `INTERRUPTED` 失败归并，避免把同名版本误当成同一组件。
