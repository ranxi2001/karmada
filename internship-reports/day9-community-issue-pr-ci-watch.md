# Day 9：社区 issue / PR 扫描与 PR #7697 CI 复盘

日期：2026-07-06

## 今日目标

先不继续修改 #7697 代码，等待空提交触发的新一轮 CI 跑完，并在 CI 完成后复盘最终结果。等待期间做一次 Karmada 社区 issue / PR 扫描，判断：

- 当前有没有和 #7697 或证书轮换主线相关的新讨论。
- 最近 open issues 里哪些已经有人认领或已有 PR，避免重复抢任务。
- 哪些 PR 值得后续学习、review 或作为 flake / hot reload 设计参考。

本轮没有发布 upstream comment，没有创建 issue/PR，也没有请求 maintainer review。

## #7697 CI 最终快照

已通过空提交触发新一轮 CI：

```text
PR:        #7697 feat: support rotating init-managed certificates
Head SHA:  93eaf7e57515c959fe30fa2aba387ce10029046d
Commit:    test: trigger ci
```

最终状态快照：

```text
DCO        pass
lint       pass
codegen    pass
compile    pass
unit test  pass
Chart      pass for v1.34.0 / v1.35.0 / v1.36.1
CLI        pass for v1.34.0 / v1.35.0 / v1.36.1
Operator   pass for v1.34.0 / v1.35.0 / v1.36.1
e2e        pass for v1.34.0 (53m44s) / v1.35.0 (50m14s) / v1.36.1 (48m52s)
tide       pending, needs approved / lgtm labels
```

> 注释：`tide` pending 不是 CI 失败，而是合并门禁还缺 review 相关标签。当前 #7697 的 GitHub Actions 已经全绿，下一步不是继续改代码触发 CI，而是等待 maintainer review、`/lgtm` 和 `/approve`。

Codecov 评论仍提示 patch coverage 为 `62.31884%`，但 project coverage 从 `42.05%` 到 `42.22%`，且 `gh pr checks` 中没有失败的 Codecov required check。当前将它记录为非阻塞覆盖率提示。

## 近期 issue 扫描

| Issue | 类型 | 当前状态 | 判断 |
| --- | --- | --- | --- |
| [#7717](https://github.com/karmada-io/karmada/issues/7717) WorkloadRebalancer failback with clusterAffinities | `kind/bug` | maintainer 已回复这是预期行为，应使用 `overflowAffinities` | 不适合作为 bug 实现；可作为 WorkloadRebalancer / scheduler 文档理解材料 |
| [#7702](https://github.com/karmada-io/karmada/issues/7702) reduce deprecated Node.js 20 runtime | `kind/feature` | 已由 `Smitbafna`、`SipengShen01` 认领 | 不重复实现 |
| [#7698](https://github.com/karmada-io/karmada/issues/7698) ServiceAccount pruning skips consecutive token secrets | `kind/bug` | 已有 PR [#7699](https://github.com/karmada-io/karmada/pull/7699)，CI 通过 | 不重复实现，可观察 review |
| [#7695](https://github.com/karmada-io/karmada/issues/7695) `InternetIP()` no timeout | `kind/bug` | 已有 PR [#7696](https://github.com/karmada-io/karmada/pull/7696) | 同属 `karmadactl init` 周边，但不和 #7697 直接冲突 |
| [#7693](https://github.com/karmada-io/karmada/issues/7693) certificate rotation capability | `kind/feature` | 我们当前主线，PR [#7697](https://github.com/karmada-io/karmada/pull/7697) CI 已全绿，等待 review | 等 maintainer review、`lgtm` 和 approval |
| [#7691](https://github.com/karmada-io/karmada/issues/7691) ClusterResourceBinding e2e flake | `kind/flake` | 已有 PR [#7692](https://github.com/karmada-io/karmada/pull/7692) | 和 #7697 CI 失败同属 e2e timing 类问题，可学习其修复模式 |
| [#7688](https://github.com/karmada-io/karmada/issues/7688) nil `TolerationSeconds` validation | `kind/bug` | 已有 PR [#7689](https://github.com/karmada-io/karmada/pull/7689) | 不重复实现 |
| [#7676](https://github.com/karmada-io/karmada/issues/7676), [#7673](https://github.com/karmada-io/karmada/issues/7673), [#7672](https://github.com/karmada-io/karmada/issues/7672) util unit tests | unlabeled / test | 已有对应测试 PR，如 [#7677](https://github.com/karmada-io/karmada/pull/7677)、[#7675](https://github.com/karmada-io/karmada/pull/7675)、[#7674](https://github.com/karmada-io/karmada/pull/7674) | 不重复实现；这些 PR 多数卡在 commit message 或 DCO |
| [#7670](https://github.com/karmada-io/karmada/issues/7670) duplicate objects in `FetchResourceTemplatesByLabelSelector` | `kind/cleanup` | 已有 PR [#7671](https://github.com/karmada-io/karmada/pull/7671) | 不重复实现 |
| [#6051](https://github.com/karmada-io/karmada/issues/6051) certificate secret/path naming convention umbrella | `help wanted` | 长期 umbrella，已有多个历史子任务和人员参与 | 仍是证书方向背景材料；当前不从这里另开 split-layout PR |

> 分析：近期看起来“未认领”的 issue 中，有不少已经通过 PR 标题、评论或作者行为形成事实上的实现路径。Day 9 不适合再抢新实现，重点应放在 #7697 review 响应，以及挑一个相关 PR 做高质量阅读。

## 近期 PR 扫描

### #7692：e2e flake 修复

PR：[test(e2e): synchronize ClusterRole propagation before cleanup](https://github.com/karmada-io/karmada/pull/7692)

改动范围：

```text
test/e2e/suites/base/clusterresourcebinding_test.go
```

核心思路：在测试结束前显式等待 `ClusterRole` 已传播到 member clusters，再进入清理阶段。这个修复没有改生产代码，只补了 e2e 同步屏障。

对我们的价值：

- 和 #7697 此前失败的 `e2e v1.34.0` 一样，都是异步系统里“测试先进入下一阶段，但控制面/成员集群状态还没同步完”的问题。
- 如果 #7697 后续或其他 PR 再次出现类似 e2e timeout，应优先找缺失的等待条件，而不是直接假设业务改动有问题。

### #7663：push-mode informer token rotation hot reload

PR：[fix: push-mode informers pick up rotated bearer token without restart](https://github.com/karmada-io/karmada/pull/7663)

改动范围：

```text
pkg/util/membercluster_client.go
pkg/util/membercluster_client_rotation_test.go
pkg/util/round_trippers.go
pkg/util/round_trippers_token_test.go
test/e2e/suites/base/token_rotation_test.go
```

核心问题：push-mode informer 在启动时持有静态 bearer token；token rotation 后，长连接 watch 可能继续使用旧 token，导致部分控制链路失效。

PR 的方向：把 token 注入从静态 `rest.Config.BearerToken` 移到 transport wrapper 中，按 TTL 重新读取 Secret。

对 #7697 的价值：

- #7697 处理的是 `karmadactl init` 管理的证书数据轮换，以及 Secret/kubeconfig 更新。
- #7663 处理的是运行中客户端如何加载 rotated credential。
- 两者正好对应“轮换凭据数据”和“运行中组件加载新凭据”的能力边界。后续如果解释 #7697 为什么不承诺所有组件热加载，可以引用这个方向作为社区正在独立处理运行态 credential reload 的证据，但不能把 #7663 的 bearer token 行为直接等同于 X.509 证书热加载。

> 分析：#7663 值得后续深读代码。它可能帮助我们把“客户端 token 热加载”和“组件证书重启/热加载边界”讲得更严谨。

### #7662：WorkloadRebalancer strategy proposal

PR：[[Proposal]: Extend WorkloadRebalancer with Strategy-based Rebalancing](https://github.com/karmada-io/karmada/pull/7662)

状态：proposal PR，`RainbowMango` 已在 assignees。该 PR 和今天新 issue [#7717](https://github.com/karmada-io/karmada/issues/7717) 相关，都是 WorkloadRebalancer / failback / rescheduling 语义。

观察点：

- Bot review 已指出 proposal 中 `strategy` 字段应考虑 optional / default，避免破坏已有 `WorkloadRebalancer` manifest。
- `ttlSecondsAfterFinished` 语义也有现有 API 行为兼容性问题。

对我们的价值：

- 适合作为 scheduler/rebalancer 设计阅读材料。
- 不建议在没有完整读 proposal 和现有 controller 实现前参与评论。

### 同属安装或 `karmadactl init` 周边的 PR

| PR | 状态 | 对 #7697 的影响 |
| --- | --- | --- |
| [#7696](https://github.com/karmada-io/karmada/pull/7696) add timeout to `InternetIP()` | 改 `pkg/karmadactl/cmdinit/utils/format.go`；有 e2e v1.35.0 失败 | 同属 init 周边，但文件不和 #7697 当前改动重叠，暂不处理 |
| [#7705](https://github.com/karmada-io/karmada/pull/7705) handle nodes without addresses during init | 改 `pkg/karmadactl/cmdinit/kubernetes/node.go` 和 operator util | 可能影响安装健壮性，不和证书轮换主路径直接冲突 |
| [#7706](https://github.com/karmada-io/karmada/pull/7706) handle deployments without command in patcher | operator patcher | 不影响 #7697 |

这些 PR 当前都有作者在推进，且已有 bot review comments。除非用户要求做 review，否则先不介入。

## 当前判断

1. #7697 新一轮 CI 已全绿。此前失败的 `e2e test (v1.34.0)` 在空提交 `93eaf7e57515c959fe30fa2aba387ce10029046d` 上通过，因此目前更适合归类为 e2e timing flake，而不是 #7697 代码缺陷。
2. 当前剩余阻塞不是 CI，而是 `tide` 合并门禁：缺 `approved` / `lgtm` 标签，需要 maintainer review。
3. 今天不建议新开实现任务。近期小 issue 多数已有 PR 或认领，重复实现风险高。
4. 下一步最有价值的社区阅读对象是 #7663，因为它直接补充 credential rotation 的运行态 reload 边界；其次是 #7692，用来学习 e2e flake 的最小修复方式。

## 建议下一步

- 等 #7697 maintainer review；如果 reviewer 继续追问运行态 reload 或证书重启边界，可以结合 #7663 的 token refresh 设计和本 PR 的运行态验证结果解释。
- 如果后续同一个 PR 又出现 e2e 失败，按 flake 分析流程处理：定位 job、失败用例、日志证据、是否与本 PR diff 有路径交叉、是否其他 Kubernetes 版本通过。
- 不主动评论 #7717、#7692、#7663，除非已经完整读代码并形成具体、可验证的 review point，再让用户确认英文评论。

## 深读 #7692：e2e flake 的同步屏障

PR：[test(e2e): synchronize ClusterRole propagation before cleanup](https://github.com/karmada-io/karmada/pull/7692)

关联 issue：[ClusterResourceBinding e2e test misses propagation synchronization before cleanup](https://github.com/karmada-io/karmada/issues/7691)

### 问题复原

失败用例是：

```text
ClusterResourceBinding test permanent id label testing
creates work with permanent ID label
```

原测试流程：

```text
Create ClusterPropagationPolicy
Create ClusterRole
Wait ClusterResourceBinding has permanent ID label
Wait Work objects created in control plane
Test ends
DeferCleanup:
  Remove ClusterPropagationPolicy
  Remove ClusterRole
  Wait ClusterRole disappear on member clusters
```

这里的关键问题是：`Work` 出现在 control plane 只说明 binding / execution 已经生成了分发载体，不代表 member cluster 上的 `ClusterRole` 已经实际创建完成。

如果测试刚等到 `Work` 就结束，`DeferCleanup` 马上开始删除 policy 和源资源，然后调用：

```go
framework.WaitClusterRoleDisappearOnClusters(...)
```

那么这个 disappearance wait 可能在 member cluster 从未出现过该 `ClusterRole` 时就返回成功。也就是说，测试没有证明资源经历过：

```text
not exist -> present -> disappear
```

而是可能只证明了：

```text
not exist -> still not exist
```

这会让异步传播链路处在半完成状态，后续 controller reconcile 和清理动作容易互相穿插，形成 e2e flake。

### PR 的最小修复

#7692 只改了一个文件：

```text
test/e2e/suites/base/clusterresourcebinding_test.go
```

新增 4 行，在 `creates work with permanent ID label` 里等 member cluster 真正出现 `ClusterRole`：

```go
framework.WaitClusterRolePresentOnClustersFitWith(framework.ClusterNames(), clusterRole.Name, func(_ *rbacv1.ClusterRole) bool {
	return true
})
```

修复后的状态机变成：

```text
Wait Work objects created in control plane
Wait ClusterRole present on every member cluster
Test ends
Cleanup removes source objects
Wait ClusterRole disappear on every member cluster
```

这个修复没有改变生产代码，也没有扩大断言范围，只补了一个 e2e 同步屏障。

### 为什么这个修复合理

同类测试已经有这个模式。例如：

```text
test/e2e/suites/base/clusterpropagationpolicy_test.go
test/e2e/suites/base/workloadrebalancer_test.go
```

这些测试会先等 member cluster 上的资源存在，再进入后续步骤或清理。#7692 是把 `clusterresourcebinding_test.go` 里的第一个 `It` 补齐到相同模式。

CI 结果：

```text
DCO        pass
lint       pass
codegen    pass
compile    pass
unit test  pass
e2e        pass for v1.34.0 / v1.35.0 / v1.36.1
Chart/CLI/Operator matrices pass
tide       pending, needs approved / lgtm
```

### 对 #7697 CI 分析的启发

#7692 和 #7697 此前的失败不是同一个用例，也不是同一段代码。

但它们同属一个测试设计问题：

```text
Karmada e2e 不能只等 control plane 中间态；
如果后续动作依赖 member cluster 或 scheduler discovery 已经完成，
测试必须显式等待那个真实外部状态。
```

对 #7697 的 `FlinkDeployment` CI 失败，这个思路可以迁移为：

```text
CRD propagated to member cluster
  != scheduler 已经发现该 API
  != cluster APIEnablements 已经更新
```

因此如果 #7697 新 CI 再次在 estimator / FlinkDeployment 处失败，第一优先级不是改证书轮换代码，而是查 e2e 是否缺少：

- member cluster CRD Established wait
- Karmada `Cluster` status APIEnablements wait
- scheduler requeue / discovery 更新后的 scheduled wait

> 分析：#7692 的价值在于提供了一个很清晰的 flake 修复模板：找到测试依赖的异步外部状态，补一个最小、已有 helper 风格的 wait，而不是用 sleep 或扩大生产代码。

## 深读 #7663：push-mode token rotation 热加载

PR：[fix: push-mode informers pick up rotated bearer token without restart](https://github.com/karmada-io/karmada/pull/7663)

### 问题背景

这个 PR 处理的是 push-mode member cluster credential rotation。

旧逻辑在 `BuildClusterConfig()` 中这样构造 member cluster client config：

```go
clusterConfig := &rest.Config{
	BearerToken: string(token),
	Host:        apiEndpoint,
	Timeout:     defaultTimeout,
}
```

这意味着：

- client 创建时从 `Cluster.Spec.SecretRef` 指向的 Secret 读一次 token。
- token 固定在 `rest.Config.BearerToken` 里。
- 长生命周期 informer / watch 复用同一个 client。
- Secret 里的 token 后续被更新后，已经创建好的 client 不会重新读取 Secret。

因此 token rotation 后会出现一种危险状态：

```text
short-lived health check:
  重新建 client 或重新走读 Secret 路径
  -> 可能仍然工作
  -> Cluster Ready=True

long-lived informer/watch:
  持有旧 token
  -> watch 重连后仍用旧 token
  -> 资源状态收集失效
  -> 控制面局部失明
```

### PR 的设计

#7663 不再把 token 放到 `rest.Config.BearerToken`，而是把 token 注入下沉到 `http.RoundTripper`：

```go
clusterConfig := &rest.Config{
	Host:    apiEndpoint,
	Timeout: defaultTimeout,
}

clusterConfig.Wrap(NewTokenRefreshingRoundTripperWrapperConstructor(
	secretGetter,
	cluster.Spec.SecretRef.Namespace,
	cluster.Spec.SecretRef.Name,
	string(token),
))
```

新增的 `tokenRefreshingRoundTripper` 做三件事：

1. 每次请求前 clone request，设置：

   ```go
   Authorization: Bearer <cached token>
   ```

2. token 有 30s TTL：

   ```go
   tokenCacheTTL = 30 * time.Second
   ```

   TTL 未过期时不读 Secret，避免每个请求都访问缓存。

3. TTL 过期后重新通过 `secretGetter(namespace, name)` 读 Secret：

   - 如果 Secret 读取失败：保留上一个可用 token，5s 后重试。
   - 如果 Secret 中 token 为空：保留上一个可用 token。
   - 如果读到新 token：更新 cached token。

### 为什么要清空 `BearerToken`

我查了 client-go 的 wrapper 顺序：

```text
custom WrapTransport 先应用
debug wrappers
built-in bearer token wrapper 后应用
user-agent / impersonation wrappers
```

如果同时保留 `rest.Config.BearerToken`，client-go 会再包一层内置 bearer auth wrapper，可能把旧 token 固定进更外层的认证逻辑。

所以 #7663 的关键设计是：

```text
不要再让 client-go 内置 BearerToken 机制持有静态 token；
只让自定义 tokenRefreshingRoundTripper 注入 Authorization。
```

这和 PR 注释里的“replaces the built-in bearerAuthRoundTripper position”是一致的。

### 测试覆盖

新增测试分三层。

#### 1. RoundTripper 单测

文件：

```text
pkg/util/round_trippers_token_test.go
```

覆盖：

- 能注入 `Authorization: Bearer token-A`
- 不修改调用方原始 request
- TTL 过期后读到 `token-B`
- Secret 读取失败时保留旧 token
- Secret token 为空时保留旧 token
- 能和 proxy header wrapper 串联
- 并发过期请求只触发一次 Secret 读取

#### 2. BuildClusterConfig 长生命周期 client 单测

文件：

```text
pkg/util/membercluster_client_rotation_test.go
```

它启动一个只接受当前 token 的 `httptest` TLS server：

```text
server accepts token-A
client request succeeds
Secret 更新为 token-B
server 改为只接受 token-B
同一个 long-lived client 再请求
最终请求成功，并且服务端看到 Bearer token-B
```

作者在 review comment 里记录过：去掉修复时该测试会失败，看到的仍是 `Bearer token-A`。

#### 3. e2e

文件：

```text
test/e2e/suites/base/token_rotation_test.go
```

流程：

```text
选择 push-mode member cluster
创建 Deployment + PropagationPolicy
确认 workload 已传播并收集状态
解析 member cluster Secret 里的 ServiceAccount token
删除并重建对应 ServiceAccount，使旧 token 失效
创建新 token，写回 Karmada control plane 的 Secret
等待 apiserver token revocation cache flush
docker restart member kind control-plane，强制 watch 断开重连
确认 Cluster 重新 Ready
扩容 Deployment
等待 Karmada control plane 收集到新的 readyReplicas
```

这个 e2e 的核心是验证 long-lived informer/watch 在 token rotation 后能恢复，而不是只验证短连接 health check。

### 本地验证

我在临时 worktree `/tmp/karmada-pr7663` 上跑了新增 token refresh 相关单测：

```bash
go test ./pkg/util -run 'Test(TokenRefreshingRoundTripper|BuildClusterConfig_LongLivedClientPicksUpRotatedToken)' -count=1
```

结果：

```text
ok  	github.com/karmada-io/karmada/pkg/util	0.230s
```

没有本地跑 #7663 e2e，因为它依赖真实 kind / docker restart / Karmada 多集群环境；upstream CI 中该 PR 的 e2e v1.33/v1.34/v1.35 已通过。

### 当前状态

#7663 当前 CI 全绿：

```text
DCO        pass
lint       pass
codegen    pass
compile    pass
unit test  pass
e2e        pass for v1.33.0 / v1.34.0 / v1.35.0
Chart/CLI/Operator matrices pass
tide       pending, needs approved / lgtm
```

仍没有 human maintainer review。已有 review comments 主要来自 Gemini / Copilot。作者已回应：

- function signature 多行格式：作者认为同文件已有类似风格，lint 不报错。
- lock during Secret getter：作者认为 production `secretGetter` 是 controller-runtime cache read，成本很低。
- e2e parse token 防御：作者已补早失败断言，并改用 `clusterv1alpha1.SecretTokenKey`。

### 能力边界

#7663 的能力边界很重要：

它覆盖：

- push-mode member cluster bearer token
- `Cluster.Spec.SecretRef` 指向的 Secret 中 `token` 字段
- 已创建的 long-lived client / informer 在后续请求或 watch reconnect 时加载新 token

它不覆盖：

- pull-mode agent 侧 credential reload
- X.509 client certificate reload
- serving certificate reload
- CA bundle / CAData reload
- API endpoint / proxy / TLS config 变化
- 不重连的既有 watch 立即切换 token

> 注释：token refresh 不是“所有证书热加载”。它只解决 bearer token 这一类 credential，而且恢复通常发生在请求重新发起或 watch 重连时。已建立的 TCP/TLS 连接不会因为 Secret 更新而在连接内部自动换 credential。

### 对 #7697 的启发

#7697 和 #7663 的关系可以这样理解：

```text
#7697:
  提供 rotate 命令
  更新 init-managed certificate Secret / kubeconfig 数据
  重点是“把新凭据写到正确位置”

#7663:
  修改运行中 client 的 credential 读取方式
  让 push-mode informer 在 bearer token rotation 后能重新读 Secret
  重点是“运行中进程如何加载新凭据”
```

也就是说，这两个 PR 正好证明了我们之前解释的边界：

```text
credential data rotation
  !=
running component credential reload
```

#7697 不承诺组件热加载，是合理的；如果某类运行态 reload 很重要，应该像 #7663 这样在对应 client / transport / controller 路径上单独设计、单独测试。

## #7697 新一轮 CI 最终结果

核对命令：

```bash
gh pr checks 7697 --repo karmada-io/karmada
gh pr view 7697 --repo karmada-io/karmada --json headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,comments
```

最终结论：

```text
PR:       #7697 feat: support rotating init-managed certificates
Head SHA: 93eaf7e57515c959fe30fa2aba387ce10029046d
Commit:   test: trigger ci

Required CI:
  DCO        pass
  lint       pass
  codegen    pass
  compile    pass
  unit test  pass
  e2e        pass for v1.34.0 / v1.35.0 / v1.36.1
  Chart      pass for v1.34.0 / v1.35.0 / v1.36.1
  CLI        pass for v1.34.0 / v1.35.0 / v1.36.1
  Operator   pass for v1.34.0 / v1.35.0 / v1.36.1

Merge gate:
  mergeable          MERGEABLE
  mergeStateStatus   UNSTABLE
  tide               pending, needs approved / lgtm labels
```

`mergeStateStatus=UNSTABLE` 这里不是代码冲突或 CI 失败，而是 Prow/Tide 语义下还缺 human review 标签。Karmada bot 已提示该 PR 目前 `NOT APPROVED`，需要 review 后获得 `lgtm`，再由 root `OWNERS` approver 执行 `/approve`。

> 分析：这次空提交没有改业务代码，只重新触发 CI。此前 `e2e test (v1.34.0)` 的 FlinkDeployment / ResourceQuota timeout 没有复现，而 v1.34.0 / v1.35.0 / v1.36.1 三个 e2e job 都通过。因此当前证据支持“原失败是 e2e 时序抖动”的判断，不支持继续为 #7697 修改证书轮换实现。

### 后续可跟进的 e2e 稳定性问题

这次结果也说明 Karmada CI 确实可能遇到偶发性 e2e 失败。这里要注意措辞：

```text
当前证据支持把 #7697 上一次失败归类为 flake；
但如果要在社区里推进，需要继续收集同类失败记录，
而不是只凭一次 rerun 通过就断言具体根因。
```

后续可以把它作为一个独立的 e2e 稳定性跟进点，方向是 `test/e2e/suites/base/estimator_test.go` 中 `[EstimatorAssumption] ResourceQuota plugin assumption testing` 相关流程。这里要和 #7692 区分清楚：

```text
#7692:
  已经在修一个 e2e flake
  文件是 test/e2e/suites/base/clusterresourcebinding_test.go
  问题是 ClusterResourceBinding 测试 cleanup 前没有等 member cluster 上的 ClusterRole 真正出现

#7697 这次失败:
  失败用例在 test/e2e/suites/base/estimator_test.go
  场景是 FlinkDeployment / ResourceQuota / estimator assumption
  日志表现是 scheduler 认为 member1 缺少 flink.apache.org/v1beta1/FlinkDeployment API
```

所以 #7692 是同类 flake 修复模式的参考，但不是覆盖 #7697 这次 estimator 失败的那个 PR。重点不是证书轮换，而是确认 estimator 这条测试是否也缺少某个异步状态等待：

- member cluster 上 FlinkDeployment CRD 是否已经 Established。
- Karmada `Cluster` status 中 APIEnablements 是否已经观察到 `flink.apache.org/v1beta1/FlinkDeployment`。
- scheduler discovery / estimator assumption 是否已经基于新 API 状态完成重试。
- `ResourceBinding` 等待 `Scheduled=True` 前，是否需要更明确的前置同步屏障。

合适的推进顺序：

1. 先把 #7692 作为同类修复模板读透，但不要把它当成 estimator 失败已修复。
2. 再检索是否已有 estimator / FlinkDeployment / ResourceQuota 相关 flake issue 或 PR。
3. 如果已有 issue，补充 #7697 的失败 job、日志现象和 rerun 通过证据。
4. 如果没有 issue，先整理最小证据包：失败 job、head SHA、失败用例、关键日志、同一提交 rerun 通过结果。
5. 再决定是否开独立 flake issue 或直接尝试补 estimator e2e 的 wait helper。

> 分析：这类工作可以作为后续社区贡献点，因为它不依赖 #7697 证书功能本身，却能提高 Karmada e2e 稳定性。要避免的做法是把 flake 修复混进 #7697 当前 PR；那会扩大 review scope。

### 本地尝试：FlinkDeployment CRD cleanup 同步屏障原型

我按上面的方向做了一次只读社区检索和本地最小修复原型。

社区检索结果：

- 没有找到直接命中 `EstimatorAssumption` 或 `ResourceQuota plugin assumption` 的 open flake issue / PR。
- 相关背景 issue 是 [#7481](https://github.com/karmada-io/karmada/issues/7481) `[Umbrella] Implementation of scheduler estimator assumption`，已关闭，说明 estimator assumption 主线任务已经完成。
- 相关实现 PR 是 [#7551](https://github.com/karmada-io/karmada/pull/7551) `Add e2e for scheduler estimator assumption`，已合并，是当前 `estimator_test.go` 多模板 e2e 的来源。
- [#7550](https://github.com/karmada-io/karmada/issues/7550) 是 #7551 过程中发现的真实 scheduler bug，不是这次的 e2e flake。
- [#7692](https://github.com/karmada-io/karmada/pull/7692) 是同类 e2e flake 修复模板，但覆盖 `clusterresourcebinding_test.go`，不覆盖 estimator / FlinkDeployment / ResourceQuota 路径。

源码观察：

- `test/e2e/framework/customresourcedefine.go` 里的 `WaitCRDPresentOnClusters()` 实际检查的是 Karmada `Cluster.Status.APIEnablements`，不是直接访问 member cluster 上的 CRD 对象。
- scheduler 的 `APIEnablement` plugin 也是根据 `Cluster.Status.APIEnablements` 判断目标 cluster 是否支持某个 GVK；#7697 失败日志中 “member1 缺少 `flink.apache.org/v1beta1/FlinkDeployment` API” 正是这条路径。
- 多个 e2e 会反复创建/删除同一个 `flinkdeployments.flink.apache.org` CRD：`estimator_test.go`、`schedule_multi_template_test.go`、`federatedresourcequota_test.go`。
- 这些测试原来在 cleanup 中删除 `ClusterPropagationPolicy` 后，没有显式等待 member cluster 上的 FlinkDeployment CRD 消失。下一条测试如果复用同一个 CRD 名称，可能遇到上一条测试的异步 cleanup / APIEnablements 更新还没完全稳定。

本地原型分支：

```text
Worktree: /tmp/karmada-estimator-flake
Branch:   test/estimator-flink-crd-flake
Base:     upstream/master @ ff8217c97
```

第一版原型改动：

```text
test/e2e/suites/base/estimator_test.go               +2
test/e2e/suites/base/federatedresourcequota_test.go  +1
test/e2e/suites/base/schedule_multi_template_test.go +1
```

第一版核心改动是在删除 FlinkDeployment CRD 的 `ClusterPropagationPolicy` 后，等待 member cluster 上对应 CRD 消失：

```go
ginkgo.DeferCleanup(func() {
	framework.RemoveClusterPropagationPolicy(karmadaClient, cpp.Name)
	framework.WaitCRDDisappearedOnClusters([]string{targetCluster}, flinkCRD.Name)
})
```

或者全量 member clusters 场景：

```go
ginkgo.DeferCleanup(func() {
	framework.RemoveClusterPropagationPolicy(karmadaClient, cpp.Name)
	framework.WaitCRDDisappearedOnClusters(framework.ClusterNames(), flinkDeploymentCRD.Name)
})
```

验证结果：

```bash
git diff --check
go test ./test/e2e/suites/base -run '^$' -count=0
```

结果：

```text
git diff --check: no output
ok  	github.com/karmada-io/karmada/test/e2e/suites/base	0.078s [no tests to run]
```

第一次 fork CI：

```text
Repo:   ranxi2001/karmada
Branch: test/estimator-flink-crd-flake
Commit: c4e514e171594c22052363b52794b203e1756e54
Run:    https://github.com/ranxi2001/karmada/actions/runs/28766135233
```

结果：

```text
Chart:        pass
CLI:          pass
Operator:     pass
FOSSA:        skipped
image-scan:   skipped
CI Workflow:  fail
```

CI Workflow 中三个 e2e job 都失败，失败点一致：

```text
e2e v1.34.0: ScheduleMultiTemplate / FlinkDeployment scheduling cleanup timeout
e2e v1.35.0: ScheduleMultiTemplate / FlinkDeployment scheduling cleanup timeout
e2e v1.36.1: ScheduleMultiTemplate / FlinkDeployment scheduling cleanup timeout
```

关键错误是：

```text
Waiting for crd(flinkdeployments.flink.apache.org) disappeared on cluster(member1)
Timed out after 420s
```

> 分析：这个失败反而说明第一版同步屏障放错了阶段。删除 `ClusterPropagationPolicy` 之后，source control plane 上的 CRD 还存在，propagation controller 仍可能维持 member cluster 上的 CRD；此时等待成员集群 CRD 消失，容易变成 cleanup timeout。正确边界不是“删 policy 后等 member 消失”，而是“删 source CRD 后，等 control plane 和 member clusters 都收敛到消失”。

修正版改动：

```text
Commit: 78d99e024daf243f941de58cf61f8677183fcbea
Branch: test/estimator-flink-crd-flake
```

修正版相对 `upstream/master` 只增加 4 行，把等待移动到源 CRD cleanup：

```go
ginkgo.DeferCleanup(func() {
	framework.RemoveCRD(dynamicClient, flinkCRD.Name)
	framework.WaitCRDDisappeared(dynamicClient, flinkCRD.Name)
	framework.WaitCRDDisappearedOnClusters([]string{targetCluster}, flinkCRD.Name)
})
```

或者全量 member clusters 场景：

```go
ginkgo.DeferCleanup(func() {
	framework.RemoveCRD(dynamicClient, flinkDeploymentCRD.Name)
	framework.WaitCRDDisappeared(dynamicClient, flinkDeploymentCRD.Name)
	framework.WaitCRDDisappearedOnClusters(framework.ClusterNames(), flinkDeploymentCRD.Name)
})
```

本地验证：

```bash
git diff --check
go test ./test/e2e/suites/base -run '^$' -count=0
```

结果：

```text
git diff --check: no output
ok  	github.com/karmada-io/karmada/test/e2e/suites/base	0.094s [no tests to run]
```

修正版 fork CI：

```text
Repo:   ranxi2001/karmada
Branch: test/estimator-flink-crd-flake
Commit: 78d99e024daf243f941de58cf61f8677183fcbea
```

结果：

```text
Chart:        pass
CLI:          pass
Operator:     pass
FOSSA:        skipped
image-scan:   skipped
CI Workflow:  pass
```

CI Workflow 明细：

```text
Run:        https://github.com/ranxi2001/karmada/actions/runs/28767618548
lint:       pass
codegen:    pass
compile:    pass
unit test:  pass
e2e v1.34:  pass
e2e v1.35:  pass
e2e v1.36:  pass
```

最终判断：

- 第一版失败不是生产代码问题，而是 e2e cleanup 屏障放在了 source CRD 删除之前。
- 修正版仍然保持独立 flake 分支，不混入 #7697。
- 第二轮 fork CI 全绿，说明这个最小修复至少没有引入新的 e2e cleanup timeout，也通过了 Karmada fork push CI。
- 这仍然只能证明“修正版通过当前 CI”，不能证明原 flake 永久消失；但它符合 #7692 的修复模式，适合作为独立 e2e flake PR 提交给 maintainer review。

### 偶发性还是可验证 bug

这里要分成两个层面判断。

第一，#7697 上原始失败本身属于偶发性 e2e failure：

- 同一个 #7697 业务提交没有改证书轮换代码，只通过空提交触发 rerun 后通过。
- 失败只出现在 `e2e test (v1.34.0)`，而 v1.35 / v1.36 当时通过。
- 失败路径在 `estimator_test.go` 的 FlinkDeployment / ResourceQuota / scheduler APIEnablement，而 #7697 diff 不触碰 scheduler、estimator 或 Flink e2e。

所以它不能被归类为 #7697 的可复现功能 bug。更准确的说法是：这是一次 e2e timing flake 现象。

第二，e2e 测试缺少 cleanup 同步屏障是可验证的测试设计问题：

- 多个 e2e 复用同一个 `flinkdeployments.flink.apache.org` CRD 名称。
- 这些测试依赖 Karmada `Cluster.Status.APIEnablements` 和 scheduler APIEnablement plugin 的异步收敛结果。
- 原 cleanup 只等 control plane CRD 消失，没有等 member clusters / APIEnablements 也收敛到消失。
- 修正版补的不是 sleep，而是等待测试真实依赖的外部状态完成收敛。

因此这不是生产功能 bug，而是“会导致偶发失败的 e2e test bug”。这种 bug 通常不要求能 100% 稳定复现原 timeout；只要能证明测试缺少必要同步点，并且最小同步修复通过完整 CI，就可以作为 flake PR 给 maintainer review。

如果想把证据强度再提高一档，可以继续做重复验证：

```text
同一代码分支连续触发 3-5 次 fork push CI
观察 e2e v1.34 / v1.35 / v1.36 是否仍稳定通过
```

判定标准：

- 同一代码不改，某个 job 有时过有时失败：flake。
- 同一代码每次都在同一测试、同一断言、同一路径失败：可复现 bug。
- 修正版多次通过，旧版或原失败日志指向缺失 wait：可归类为 e2e flake fix。

### 如何触发或证明原问题

这个问题不适合承诺“一条命令稳定复现”。原因是相关状态由多个异步环节共同决定：

```text
control plane CRD deletion
-> propagation controller 删除 member cluster CRD
-> cluster status controller 每 10s 采集 member cluster API list
-> Karmada Cluster.Status.APIEnablements 更新
-> scheduler APIEnablement plugin 用这份状态做过滤
```

`hack/run-e2e.sh` 默认使用：

```bash
ginkgo -v --race --trace --fail-fast -p --randomize-all ./test/e2e/suites/base -- --karmada-context=karmada-apiserver
```

也就是说测试本来就是并行、随机顺序执行。`federatedresourcequota_test.go` 自己也有注释：FlinkDeployment CRD 创建/清理会影响其他测试，所以设为 Serial。这个上下文本身说明 FlinkDeployment CRD 是跨测试共享的全局状态。

如果要尝试触发旧问题，可以用旧代码做 stress run：

```bash
# 在没有这 4 行 WaitCRDDisappearedOnClusters 的 upstream/master 或临时 revert 分支上
for i in $(seq 1 20); do
  echo "=== e2e stress run ${i} ==="
  export ARTIFACTS_PATH="${PWD}/_tmp/e2e-flink-crd-stress/${i}"
  hack/run-e2e.sh || break
done
```

为了降低成本，也可以只 focus 相关测试，但这会改变原 CI 的并行/随机环境，证据强度反而可能低于完整 e2e：

```bash
ginkgo -v --race --trace --fail-fast -p --randomize-all \
  --focus='FlinkDeployment|EstimatorAssumption|FederatedResourceQuota' \
  ./test/e2e/suites/base -- --karmada-context=karmada-apiserver
```

更直接的临时验证方式是加一个不会提交的 diagnostic test / log：

```text
旧代码在 RemoveCRD + WaitCRDDisappeared(control plane) 返回后，
立即查询 member clusters 上 flinkdeployments.flink.apache.org 是否仍存在，
并同时打印 Cluster.Status.APIEnablements 中 FlinkDeployment 的状态。
```

只要能观察到：

```text
control plane CRD 已消失
member cluster CRD 或 Cluster.Status.APIEnablements 仍未收敛
```

就能证明旧 cleanup 的同步边界不完整。这个证明不一定会每次触发 scheduler timeout，但足以说明测试可以把未清理完的全局状态带给下一条 FlinkDeployment e2e。

> 分析：当前 4 行修复能证明 member cluster CRD object cleanup 收敛，但它还没有显式等待 `Cluster.Status.APIEnablements` 变成 disabled/unknown。由于原失败日志来自 scheduler APIEnablement plugin，如果 maintainer 要求更强证明，下一版更严谨的方向是新增一个 inverse helper，等待 FlinkDeployment 从 `Cluster.Status.APIEnablements` 中消失，再进入下一条测试。这样证据链会直接覆盖 scheduler 使用的状态源。

### 本地复现旧 cleanup 边界

本地环境：

```text
Karmada kubeconfig: /tmp/karmada-cert-rotate-multinode-observe/data/karmada/rotated-karmada.config
member clusters: cert-rotate-mn-member1 / cert-rotate-mn-member2
member kubeconfigs:
  /tmp/karmada-cert-rotate-multinode-observe/kubeconfigs/member1.config
  /tmp/karmada-cert-rotate-multinode-observe/kubeconfigs/member2.config
```

这个环境不能直接跑原始 `estimator_test.go`，因为测试硬编码了 `member1`，而本地 cluster 名称是 `cert-rotate-mn-member1`。因此做了一个更直接的 diagnostic：模拟旧 cleanup 顺序。

步骤：

```text
1. 在 Karmada control plane 创建 flinkdeployments.flink.apache.org CRD。
2. 创建 ClusterPropagationPolicy，把 CRD 分发到 cert-rotate-mn-member1/2。
3. 等两个 member cluster 上 CRD 存在，且 Cluster.Status.APIEnablements 出现 FlinkDeployment。
4. 按旧 cleanup 顺序删除 ClusterPropagationPolicy。
5. 删除 control plane CRD。
6. 只等待 control plane CRD 消失。
7. 从“旧 cleanup 会返回”的时间点开始，每秒检查 member CRD 和 Cluster.Status.APIEnablements。
```

关键结果：

```text
[setup poll 10] api=(FlinkDeployment,FlinkDeployment)
                member_crd=(flinkdeployments.flink.apache.org,flinkdeployments.flink.apache.org)

[old-cleanup] control-plane CRD disappeared after 1s

[after 00s] api=(FlinkDeployment,FlinkDeployment)
            member_crd=(flinkdeployments.flink.apache.org,flinkdeployments.flink.apache.org)

[after 01s] api=(FlinkDeployment,FlinkDeployment)
            member_crd=(none,flinkdeployments.flink.apache.org)

[after 02s] api=(FlinkDeployment,FlinkDeployment)
            member_crd=(none,none)

[after 03s] api=(FlinkDeployment,FlinkDeployment)
            member_crd=(none,none)

[after 04s] api=(none,none)
            member_crd=(none,none)
```

这证明了旧 cleanup 的等待边界确实不完整：

- control plane CRD 消失后，member cluster CRD 仍可能存在。
- 更关键的是，member CRD 已经消失后，`Cluster.Status.APIEnablements` 还可能继续显示 `FlinkDeployment` 至少数秒。
- 下一条测试如果在这个窗口开始，`WaitCRDPresentOnClusters()` 可能因为 stale APIEnablements 立即通过，但 scheduler 随后可能看到 APIEnablements 翻转或缺失，从而出现 “missing API `flink.apache.org/v1beta1/FlinkDeployment`” 类 timeout。

复现后已清理环境：

```text
control plane CRD: NotFound
member1 CRD:      NotFound
member2 CRD:      NotFound
APIEnablements:   no FlinkDeployment entry
```

基于这个结果，当前分支已从 `78d99e024` 继续升级为：

```text
Commit: f2e7c434bad6d4a970265af79a157afb61e6182e
Branch: test/estimator-flink-crd-flake
```

当前候选修复范围：

```text
test/e2e/framework/customresourcedefine.go           +16
test/e2e/suites/base/estimator_test.go               +6
test/e2e/suites/base/federatedresourcequota_test.go  +3
test/e2e/suites/base/schedule_multi_template_test.go +3
```

新增 helper：

```go
framework.WaitCRDDisappearedFromClusterStatus(...)
```

它等待 `Cluster.Status.APIEnablements` 不再把目标 CRD 报告为 `APIEnabled`。三个 FlinkDeployment CRD cleanup 现在同时等待：

```text
control plane CRD disappeared
member cluster CRD object disappeared
Cluster.Status.APIEnablements no longer reports FlinkDeployment as enabled
```

本地验证：

```text
git diff --check: no output
go test ./test/e2e/suites/base -run '^$' -count=0: pass
```

新的 fork push CI 结果：

```text
Run: https://github.com/ranxi2001/karmada/actions/runs/28774018375
Chart:       pass
CLI:         pass
Operator:    pass
lint:        pass
codegen:     pass
compile:     pass
unit test:   pass
e2e v1.34:   pass
e2e v1.35:   pass
e2e v1.36:   pass
```

### 独立 issue 草稿

> 状态：已发布为 [karmada-io/karmada#7719](https://github.com/karmada-io/karmada/issues/7719)，并已通过 `/kind flake` 补上 `kind/flake` label。

检索结论：

```text
gh issue list --repo karmada-io/karmada --state open --search "FlinkDeployment APIEnablements": no result
gh issue list --repo karmada-io/karmada --state open --search "EstimatorAssumption FlinkDeployment": no result
gh search issues --repo karmada-io/karmada "WaitCRDDisappearedOnClusters": no result
```

相关但不重复的上下文：

- #7692：同类 e2e flake 修复，但覆盖的是 `clusterresourcebinding_test.go` 中 `ClusterRole` propagation cleanup 同步边界。
- #7551 / #7550：estimator assumption e2e 与历史 scheduler 功能 bug，不覆盖本次 FlinkDeployment CRD cleanup 时序问题。
- #7697：本次观察到失败的 PR 现场；失败路径不在 #7697 代码 diff 内，同一 PR 代码重新触发 CI 后通过。

Title:

```text
FlinkDeployment e2e cleanup can leave stale APIEnablements
```

Published issue:

```text
https://github.com/karmada-io/karmada/issues/7719
```

Body:

````markdown
#### Which jobs are flaking:

- `CI Workflow / e2e test (v1.34.0)`
- Observed in #7697 on run https://github.com/karmada-io/karmada/actions/runs/28499042349, job https://github.com/karmada-io/karmada/actions/runs/28499042349/job/84472927003, head SHA `152ab454265ac683f55f04a166e9de9aedaad94c`.
- The same PR code path passed after re-triggering CI with an empty commit, so this looks like an e2e timing flake rather than a regression from #7697.

#### Which test(s) are flaking:

The observed failure was:

```text
[EstimatorAssumption] ResourceQuota plugin assumption testing
[It] FlinkDeployment should be unschedulable when assumed workloads exhaust ResourceQuota
```

The test timed out in `WaitResourceBindingFitWith` while waiting for the first `FlinkDeployment` ResourceBinding to become scheduled:

```text
[FAILED] Timed out after 420.000s.
In [It] at: test/e2e/framework/resourcebinding.go:47
test/e2e/suites/base/estimator_test.go:350
```

This is probably not limited to one `It` block. Several e2e suites create and delete the same `flinkdeployments.flink.apache.org` CRD:

- `test/e2e/suites/base/estimator_test.go`
- `test/e2e/suites/base/schedule_multi_template_test.go`
- `test/e2e/suites/base/federatedresourcequota_test.go`

#### Reason for failure:

The scheduler log from the failed job shows that the ResourceBinding was rejected by the APIEnablement plugin because `member1` did not report the `FlinkDeployment` API:

```text
Cluster(member1) not fit as missing API(flink.apache.org/v1beta1, kind=FlinkDeployment)
ResourceBinding(karmadatest-6cw8j/flinkdeployment-5fc2b-flinkdeployment) scheduled to clusters []
0/3 clusters are available: 1 cluster(s) did not have the API resource, 2 cluster(s) did not match the placement cluster affinity constraint.
```

The current FlinkDeployment e2e cleanup path only waits for the source CRD to disappear from the Karmada control plane. CRD propagation/removal to member clusters and the `Cluster.Status.APIEnablements` collection are asynchronous.

I ran a local diagnostic that simulated the old cleanup boundary:

1. Create `flinkdeployments.flink.apache.org` on the Karmada control plane.
2. Propagate the CRD to two member clusters.
3. Wait until the member CRDs exist and `Cluster.Status.APIEnablements` reports `FlinkDeployment`.
4. Delete the `ClusterPropagationPolicy`.
5. Delete the source CRD from the control plane.
6. Wait only for the control-plane CRD to disappear, which is what the old cleanup waited for.
7. Poll member CRDs and `Cluster.Status.APIEnablements`.

The diagnostic showed that the old cleanup can return before member-cluster CRD and APIEnablement state has converged:

```text
control-plane CRD disappeared after 1s

after 00s: APIEnablements still reported FlinkDeployment and member CRDs still existed
after 01s: APIEnablements still reported FlinkDeployment; one member CRD was gone
after 02s: member CRDs were gone, but APIEnablements still reported FlinkDeployment
after 03s: member CRDs were gone, but APIEnablements still reported FlinkDeployment
after 04s: APIEnablements also converged
```

This gives a plausible race:

1. A previous FlinkDeployment e2e deletes the CRD and returns after the control-plane CRD disappears.
2. `Cluster.Status.APIEnablements` can still report `FlinkDeployment` from the previous CRD for a short time.
3. The next FlinkDeployment e2e starts and `WaitCRDPresentOnClusters()` can pass on that stale enabled status instead of a fresh status update for the newly propagated CRD.
4. The scheduler can then observe the member cluster as missing `flink.apache.org/v1beta1/FlinkDeployment`, causing the ResourceBinding to remain unscheduled until the test times out.

So the cleanup should wait for all state that later tests depend on:

- the source CRD has disappeared from the Karmada control plane;
- the propagated CRD has disappeared from member clusters;
- `Cluster.Status.APIEnablements` no longer reports `FlinkDeployment` as enabled.

This follows the same synchronization-barrier idea as #7692, but for the FlinkDeployment CRD/APIEnablements cleanup path.

#### Anything else we need to know:

I tested a small e2e-only candidate fix that waits for member-cluster CRD disappearance and for `Cluster.Status.APIEnablements` to stop reporting `FlinkDeployment` during cleanup.

Validation branch:

- Branch: [ranxi2001/karmada@test/estimator-flink-crd-flake](https://github.com/ranxi2001/karmada/tree/test/estimator-flink-crd-flake)
- Commit: [f2e7c434bad6d4a970265af79a157afb61e6182e](https://github.com/ranxi2001/karmada/commit/f2e7c434bad6d4a970265af79a157afb61e6182e)

Local validation:

- `git diff --check`
- `go test ./test/e2e/suites/base -run '^$' -count=0`

Fork push CI:

- [CI run 28774018375](https://github.com/ranxi2001/karmada/actions/runs/28774018375): passed
- Jobs: `lint`, `codegen`, `compile`, `unit test`, `e2e v1.34.0`, `e2e v1.35.0`, and `e2e v1.36.1` all passed.

I can send this as a focused e2e flake fix if this issue direction makes sense.
````

### 独立 PR 草稿

> 状态：草稿已准备，尚未发布 upstream PR。发布前需要用户确认目标分支和英文正文。

Title:

```text
test(e2e): wait for FlinkDeployment CRD cleanup
```

Body:

````markdown
**What type of PR is this?**

/kind flake

**What this PR does / why we need it**:

Several e2e suites create and propagate the same `flinkdeployments.flink.apache.org` CRD, then clean it up asynchronously. The scheduler's APIEnablement plugin also relies on `Cluster.Status.APIEnablements` to decide whether a member cluster supports `flink.apache.org/v1beta1/FlinkDeployment`.

This PR waits for the propagated FlinkDeployment CRD to disappear from member clusters and for `Cluster.Status.APIEnablements` to stop reporting `FlinkDeployment` as enabled after the source CRD has been removed from the Karmada control plane. This keeps the next test from observing stale CRD/APIEnablement state from the previous test.

**Which issue(s) this PR fixes**:

Fixes #7719

**Special notes for your reviewer**:

This follows the same synchronization-barrier pattern as #7692: wait for the external member-cluster state that the test depends on instead of changing production code or adding sleeps.

Local diagnostic evidence showed that the old cleanup boundary could return after the control-plane CRD disappeared while member-cluster CRD/APIEnablement state was still converging:

```text
control-plane CRD disappeared after 1s
after 00s: APIEnablements still reported FlinkDeployment and member CRDs still existed
after 02s: member CRDs disappeared, but APIEnablements still reported FlinkDeployment
after 04s: APIEnablements also converged
```

Validation:

- `git diff --check`
- `go test ./test/e2e/suites/base -run '^$' -count=0`

Fork push CI on `ranxi2001/karmada@test/estimator-flink-crd-flake`:

- Commit: [f2e7c434bad6d4a970265af79a157afb61e6182e](https://github.com/ranxi2001/karmada/commit/f2e7c434bad6d4a970265af79a157afb61e6182e)
- [CI run 28774018375](https://github.com/ranxi2001/karmada/actions/runs/28774018375): `Chart`, `CLI`, `Operator`, `lint`, `codegen`, `compile`, `unit test`, `e2e v1.34`, `e2e v1.35`, and `e2e v1.36` passed.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
````

后续如果 maintainer 问“为什么 rotate 后还要重启组件”，可以更具体地说：

- 对于 token，Karmada 可以在特定路径上通过 transport wrapper 做运行态 refresh，如 #7663。
- 对于 #7697 覆盖的 X.509 leaf certs，当前 PR 没有为每个组件实现统一 watcher、transport reload、serving cert reload 或 rollout orchestration。
- 因此 #7697 的能力边界仍应定义为更新证书数据；组件是否自动加载新证书取决于各组件自身的 reload 机制或后续 PR。
