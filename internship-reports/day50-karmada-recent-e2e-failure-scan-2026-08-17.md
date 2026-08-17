# Day 50：Karmada 近期 E2E 失败归并分析

## 先说人话

截至 2026-08-17，Karmada 周末 E2E 矩阵看起来有很多测试同时失败，但这些红灯不能按 job 数量理解成同样多的独立缺陷。

最近一个周末的 4 次定时 workflow 一共有 32 个红 job。其中 16 个来自同一个已经可以落到源码和组件日志的版本偏差问题：Kubernetes v1.27-v1.30 member cluster 的 Job 状态不包含 `JobSuccessCriteriaMet=True`，Karmada 聚合后却向较新的 control-plane kube-apiserver 提交 `Complete=True`，更新被校验规则拒绝。其余 16 个主要分布在 control-plane etcd 延迟、Kind 集群创建/删除和动态 member cluster 就绪阶段；失败的业务 spec 会变化，说明这些 spec 多数只是当时撞上环境异常的受影响方。

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
| Job 状态聚合的 Kubernetes version skew | 16 | 确定性产品兼容问题，E3：时间日志和源码闭合了写入被拒到断言超时的因果链 | 最高，应单独建立新的跟踪 issue 或重新明确 #6414 的未解决边界 |
| Karmada control-plane API / etcd 延迟 | 8 | 直接原因到 E3：API timeout 与同时间 etcd 慢写吻合；runner I/O 等上游物理原因仍为 E2 假设 | 高，但需要按 runner、时间和 artifact 继续归并，不能修业务 spec |
| Kind / Docker 生命周期失败 | 5 | E1 环境 flake：同一 SHA 的失败落在不同 `kind create/delete`、`kubeadm init` 或 `docker rm` 阶段；物理原因未查明 | 中，先改进诊断和重跑样本，再判断是 runner 还是 Kind helper |
| 动态 member cluster 就绪超时 | 2 | E1 重复症状：取 impersonation ServiceAccount Secret 超时，尚未闭合 member apiserver 原因 | 中，需要 member apiserver artifact 才能继续归因 |
| ResourceInterpreter 请求被 client rate limiter 截止 | 1 | E0 单样本 | 低，等待重复样本，不建议现在改产品代码 |

## 一个具体例子：为什么 16 个 Job 红灯其实是同一个问题

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

## Job version-skew 的源码链路

运行 SHA 的 [`ParseJobStatus`](https://github.com/karmada-io/karmada/blob/a957f64d50213729b4d34f3c298ca3630e1c9127/pkg/util/helper/job.go#L102-L123) 有两个不同条件：

1. `successfulJobs == len(status)` 时，无条件生成聚合后的 `JobComplete=True`。
2. 只有每个 member status 本来就带有 `JobSuccessCriteriaMet=True` 时，才生成聚合后的 `JobSuccessCriteriaMet=True`。

老版本 member Job 可以完成，但不会提供新 condition。Karmada 因而构造出“有 `Complete=True`、没有 `SuccessCriteriaMet=True`”的聚合状态；较新的 control-plane kube-apiserver 拒绝这个状态转换，源 Job 保留上一次成功写入的状态，E2E 最终读到 2 而不是 3。

这条链路在两个 workflow 中都会被放大：

- 普通矩阵：v1.27.3、v1.28.0、v1.29.0、v1.30.0 连续两天各失败一次，共 8 个 job。
- compatibility 矩阵：v1.30.0 member 分别配 master、release-1.16、release-1.17、release-1.18，两天各失败 4 个，共 8 个 job。

## 与历史 #6414 / #6964 的关系

[Issue #6414](https://github.com/karmada-io/karmada/issues/6414) 记录过相同的 300 秒超时和相同 kube-apiserver 校验错误。[PR #6964](https://github.com/karmada-io/karmada/pull/6964) 在 2025-11-29 合入后，为一致版本的 member Job 聚合 `JobSuccessCriteriaMet`。

但该 PR 的 maintainer review 已明确保留 version-skew 边界：这个修改不能完全解决 #6414，只能在 control plane 与 member Kubernetes 版本一致时正常工作，[#6414 仍可能需要另一种方案](https://github.com/karmada-io/karmada/pull/6964#issuecomment-3591045723)。当前日志正好命中了这个当时已经声明、但 issue 关闭后未继续跟踪的边界。

建议方向是让 Karmada 生成的终态满足目标 kube-apiserver 的校验合同，而不是依赖旧 member status 已经携带新 condition。是否可以在“所有 member Job 都已成功”的聚合结论成立时直接合成 `JobSuccessCriteriaMet=True`，还需要同时验证旧 control-plane kube-apiserver 的兼容行为；这部分目前是实现方向，不是已经验证的修复。

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

- Job status collection 是确定性的 version-skew 兼容缺陷，不应继续标为普通 flake。
- 当前 #6414 的关闭状态没有覆盖 maintainer 当时明确保留的旧 member 版本场景。
- 多个看似不同的业务 spec 由 control-plane etcd 延迟或 Kind 生命周期错误共同影响。
- [PR #7827](https://github.com/karmada-io/karmada/pull/7827) 当前 head `6ebc4b459` 的全部 3 个 E2E jobs 均通过，与本轮定时矩阵失败没有直接关系。

仍待确认：

- Job 聚合修复是否应无条件合成 `JobSuccessCriteriaMet=True`，还是需要根据 control-plane 能力选择输出。
- etcd 慢写的上游原因是 GitHub runner I/O、同一 job 内资源竞争，还是测试环境参数；artifact 已证明 etcd 延迟，但还没有 runner 级反事实。
- Kind 创建/删除失败是否能由重跑稳定消失，以及是否集中在特定 runner image、Kind 或 Docker 版本。
- `resourceinterpreter_test.go:538` 的 client rate limiter 超时目前只有一个样本，不足以提出代码修改。

## 下一步

1. 优先为 Job version-skew 建立一条新的 upstream 跟踪记录，明确它与已关闭 #6414、已合入 #6964 的“同症状、未覆盖场景”关系，并链接当前两天的 job 与运行 SHA。发布前仍需确认 exact issue text。
2. 对基础设施失败按“首个失败操作 + artifact 时间窗口”继续收集，不按业务 spec 名称建多个 issue。若下一周仍出现 etcd `slow fdatasync`，再形成独立的 CI 环境 issue。
3. 后续矩阵扫描先按 run SHA、matrix 轴和首个非 `INTERRUPTED` 失败归并，再统计根因数量，避免把 40-way matrix 的同一缺陷报告成几十个 flake。
