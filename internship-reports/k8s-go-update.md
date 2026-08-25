# Work API Kubernetes 与 Go 版本升级

- 日期：2026-08-25
- 任务来源：[work-api `go.mod@9710f2f`](https://github.com/kubernetes-sigs/work-api/blob/9710f2f9d7c6359c76d501104df86e1278942772/go.mod#L11-L16)
- 参考 PR：[kubernetes-sigs/work-api#49](https://github.com/kubernetes-sigs/work-api/pull/49) `Bump Kubernetes dependencies to v1.31.6`
- 参考 PR：[kubernetes-sigs/work-api#66](https://github.com/kubernetes-sigs/work-api/pull/66) `Bump Kubernetes dependencies to v1.35.0`
- 当前边界：fork topic branch 已推送并通过 push CI；未创建 upstream PR 或 comment。

> 原始任务：这个 K8s 依赖，以及 Golang 版本帮忙升级一下。大版本号参考 Karmada，小版本号选最新就行。

## 先说人话

当前 work-api 使用 Go `1.25.0`、toolchain `go1.25.8` 和 Kubernetes modules `v0.35.0`。2026-08-25 核对 Karmada `upstream/master` 后，Karmada 使用 Go `1.26.7` 和 Kubernetes `v0.36.2`；Go 目标因此取 `1.26.7`，Kubernetes 保持 `v0.36` minor line 并取当前最新稳定 patch `v0.36.4`。

这不能只改 `go.mod` 中几个版本号。Kubernetes code-generator 升级可能改变 generated clients、listers 和 informers；controller-runtime/controller-tools 也要升级到与 Kubernetes 1.36 对应的版本。PR #49 的做法正是“升级依赖后重新生成并提交必要兼容改动”，本任务沿用这个边界。

## 版本基线

| 项目 | 当前 work-api | 目标 | 依据 |
| --- | --- | --- | --- |
| Go language version | `1.25.0` | `1.26.0` | Go directive 保留 major/minor 语言基线 |
| Go toolchain | `go1.25.8` | `go1.26.7` | Karmada `upstream/master/.go-version` |
| Kubernetes modules | `v0.35.0` | `v0.36.4` | Karmada 使用 `v0.36`，当前该 minor line 最新稳定 patch 为 `.4` |
| controller-runtime | `v0.23.1` | `v0.24.1` | 与 Kubernetes 1.36 对应的稳定版本，Karmada 也使用该版本 |
| controller-tools | `v0.20.0` | `v0.21.0` | 与新 code generation / CRD generation 依赖对齐 |

## L11-L16 严格下限复核

用户进一步明确：work-api `go.mod` L11-L16 的 6 个直接依赖必须逐项 `>=` Karmada 对应版本。2026-08-25 刷新 Karmada `upstream/master@b6c92395e6e9e0678452f22ce2d7242693fb881c` 后，正式分支 `cf1bfed` 全部满足：

| work-api `go.mod` | Karmada 基线 | `cf1bfed` | 结果 |
| --- | --- | --- | --- |
| `k8s.io/api` | `v0.36.2` | `v0.36.4` | 满足，work-api patch 更高 |
| `k8s.io/apimachinery` | `v0.36.2` | `v0.36.4` | 满足，work-api patch 更高 |
| `k8s.io/client-go` | `v0.36.2` | `v0.36.4` | 满足，work-api patch 更高 |
| `k8s.io/code-generator` | `v0.36.2` | `v0.36.4` | 满足，work-api patch 更高 |
| `sigs.k8s.io/controller-runtime` | `v0.24.1` | `v0.24.1` | 满足，版本相等 |
| `sigs.k8s.io/controller-tools` | `v0.21.0` | `v0.21.0` | 满足，版本相等 |

前 5 项来自 Karmada `go.mod`；Karmada 没有在主 `go.mod` 直接 require `controller-tools`，其对应基线来自 `hack/update-crdgen.sh` 的 `CONTROLLER_GEN_VER="v0.21.0"`，并由当前生成 CRD 的 `controller-gen.kubebuilder.io/version: v0.21.0` annotation 交叉确认。

为避免把约束扩大成“所有同名 indirect module 都必须对齐”，还做过一次全量 shared-module 对比：74 个共同 module 中有 9 个 work-api 版本低于 Karmada，另有 Ginkgo v1/v2 module-path 差异。其中 8 个较高版本来自 Karmada 的 metrics-server 依赖图，并非 L11-L16 的 Kubernetes/controller 兼容下限。对应的 Ginkgo v2 与 indirect dependency 探索没有推送，保留在本地 `scratch/work-api-shared-deps-20260825@55e06d8`；正式分支和 fork 均保持 `cf1bfed`。

## #49 的做法

PR #49 只有一个 signed-off commit，但不是纯 `go.mod/go.sum` 更新。它修改 14 个文件：

1. 更新 Kubernetes、controller-runtime/controller-tools 和 Go patch 版本；
2. 同步 GitHub Actions 使用的 Go patch 版本；
3. 重新运行 codegen，接受 typed clients、fake clients、listers 和 informer 的生成差异；
4. 重新生成 CRD schema；
5. 按 controller-runtime 新要求为两个 controller 添加显式名称；
6. 通过后将依赖、兼容代码和生成物放在同一个升级 commit 中。

本任务采用同一策略，但不会机械复制 #49 的历史 diff；所有生成结果以 `upstream/master@9710f2f` 和新依赖实际输出为准。

## #66 补充的经验

PR #66 是当前代码基线之前最近一次 Kubernetes minor 升级，只包含一个 signed-off commit、8 个文件、`+147/-148`。它提供了三条更接近本任务的证据：

1. PR body 明确写明 Go 1.26 推迟到 Kubernetes 1.36，说明本次同时升级 Go 1.26 与 Kubernetes 1.36 符合前一次升级留下的版本计划；
2. 从 Kubernetes `v0.34.3` 升到 `v0.35.0` 时，同时升级 controller-runtime `v0.22.4 -> v0.23.1`、controller-tools `v0.19.0 -> v0.20.0`，本次继续采用相邻兼容版本 `v0.24.1` 与 `v0.21.0`；
3. 它运行 codegen 后只提交实际变化的 register、fake client 和 informer 文件，没有为了与旧 PR 对齐而强制制造 lister、controller 或 CRD diff。

因此，本次生成物范围以实际 generator 输出为准：#49 说明可能出现较大的 client API 迁移，#66 说明相邻 minor 升级也可能只有少量生成差异。两者共同支持“运行完整生成与验证，但只提交真实变化”的做法。

## 文件范围

| 文件 / 区域 | 变化类型 | 原因 | 风险 | 验证 |
| --- | --- | --- | --- | --- |
| `go.mod`、`go.sum` | 依赖升级 | 更新 Go、Kubernetes、controller-runtime 和 controller-tools | transitive dependency 不一致、编译失败 | `go mod tidy`、`go mod verify`、unit tests |
| `.github/workflows/ci.yml` | CI 版本同步 | 4 个 job 的 Go 版本必须与 toolchain 一致 | CI 与本地结果漂移 | YAML diff、GitHub CI 后续验证 |
| `pkg/client/**`、`pkg/apis/**` | 生成物 | Kubernetes `v0.36.4` code-generator 可能改变 client/lister/informer/deepcopy/register | 生成差异遗漏或混入手改 | `hack/update-codegen.sh`、`hack/verify-codegen.sh` |
| `config/crd/**` | 生成物 | controller-tools `v0.21.0` 可能改变 CRD schema | CRD 意外语义变化 | `make manifests`、`hack/verify-crds.sh`、人工 diff |
| `pkg/controllers/**` | 最小兼容修正 | 仅在 controller-runtime API/validation 要求变化时修改 | 无关行为改动 | focused unit tests、人工 diff |
| `Makefile` / E2E workflow version fields | 版本一致性 | 只在现有 tests 明确要求 Kubernetes 1.36 环境时调整 | 扩大环境变更和镜像供应风险 | 先运行现有验证，再决定是否纳入 |

## 非目标

- 不修改 Work/AppliedWork API 字段或用户可见语义。
- 不重构 controller、client 或生成脚本。
- 不借依赖升级清理旧测试、格式或目录结构。
- 不升级到 Kubernetes `v0.37` prerelease。
- 不在缺少可用 `kindest/node` digest 证据时猜测 E2E node image。
- 不将实习记录带入 work-api topic branch。

## 实施顺序

1. 从 `upstream/master@9710f2f` 创建本地 topic branch。
2. 更新 Go、Kubernetes、controller-runtime/controller-tools 与 CI Go 版本。
3. 运行 `go mod tidy`，检查 direct/indirect dependency 变化。
4. 运行 `hack/update-codegen.sh` 和 `make manifests`，只保留新工具产生的必要差异。
5. 处理编译或 controller-runtime compatibility error；若需要原范围外产品改动，停止并更新设计。
6. 运行 `go mod verify`、`make verify`、`make test`，必要时补充 `make controller`。
7. 检查 diff、签名和生成物一致性，形成一个本地 signed-off commit。

## 验收边界

- 依赖解析和 module checksum 完整；
- committed codegen 与 CRD artifacts 能由当前脚本重现；
- verify、unit tests 和 controller build 通过；
- diff 只包含版本同步、生成物和由新依赖直接要求的兼容修改；
- live E2E 未运行时必须明确披露，不能用 unit tests 替代；
- fork push 与 upstream PR title/body 等外部动作只在用户明确确认后执行。

## 实现结果

- work-api branch：`deps/kubernetes-1.36-go-1.26`
- base：`upstream/master@9710f2f9d7c6359c76d501104df86e1278942772`
- commit：[`cf1bfed`](https://github.com/ranxi2001/work-api/commit/cf1bfed10c700e66adb5792c1cad9f906e0b2e66) `Bump Kubernetes dependencies to v1.36.4`
- fork branch：[`ranxi2001/work-api:deps/kubernetes-1.36-go-1.26`](https://github.com/ranxi2001/work-api/tree/deps/kubernetes-1.36-go-1.26)，remote head 与本地 commit 一致。
- commit 状态：包含 `Signed-off-by: ranxi2001 <ranxi169@163.com>`；未创建 upstream PR。
- diff：8 files、`+366/-230`。

实际变更与 #66 一样保持在依赖、CI 和生成物边界：

| 文件组 | 实际结果 |
| --- | --- |
| `go.mod`、`go.sum` | Go `1.26.0` / toolchain `go1.26.7`；4 个 direct Kubernetes modules `v0.36.4`；controller-runtime `v0.24.1`；controller-tools `v0.21.0`；`go mod tidy` 更新 transitive dependencies |
| `.github/workflows/ci.yml` | 4 个 job 使用 Go `1.26.7`；golangci-lint `v2.8.0 -> v2.13.1` |
| fake client | `NewSimpleClientset` 的过期 deprecation 文案移除，watch-list marker 注释名称修正；方法签名未变化 |
| generated informers | 新增 context/options/informer identity API，并保留原有 channel-based constructors 与 methods |
| CRD 与 hand-written controller | 没有 diff；不需要产品代码兼容修正 |

`k8s.io/apiextensions-apiserver`、`k8s.io/apiserver`、`k8s.io/component-base` 等 tool-only transitive modules 由 controller-tools/controller-runtime 解析为 `v0.36.0`。L11-L16 的严格下限只约束上述 6 个直接依赖；这些 indirect modules 不在该矩阵中。direct runtime/codegen modules 使用任务要求的最新 `v0.36.4`，没有人为强制所有间接模块到 `.4`。

## 依赖接口变化

本轮用 `golang.org/x/exp/cmd/apidiff` 对 base 与 current module export data 做了完整比较。没有发现旧 exported function 删除或旧 method signature 修改。工具报告 4 条 source-incompatible entries，对应 3 个不同的 interface methods；`InformerName` 因 public interface embedding 被报告两次：

```text
externalversions.SharedInformerFactory.StartWithContext: added
externalversions.SharedInformerFactory.WaitForCacheSyncWithContext: added
internalinterfaces.SharedInformerFactory.InformerName: added
externalversions.SharedInformerFactory embeds the added InformerName method
```

> 分析：Go interface 增加 method 会让旧的外部自定义实现不再满足该 interface，因此 apidiff 正确将它标为 incompatible。普通消费者如果只调用 `NewSharedInformerFactory*` 获取 generator 提供的实现，不需要改代码；风险集中在自行实现或 mock `SharedInformerFactory` 的消费者。

旧入口仍保留：

- `Start(stopCh <-chan struct{})` 内部转调 `StartWithContext(...)`；
- `WaitForCacheSync(stopCh <-chan struct{}) map[reflect.Type]bool` 内部转调 context 版本；
- `NewWorkInformer`、`NewFilteredWorkInformer`、`NewAppliedWorkInformer`、`NewFilteredAppliedWorkInformer` 均保留；
- 新增 `NewWorkInformerWithOptions`、`NewAppliedWorkInformerWithOptions`、`WithInformerName` 和 `InformerOptions`；
- `InformerName` 未配置时是 `nil`，client-go 的 `WithResource()` 与 `Release()` 都有显式 nil guard，旧 constructor 路径不会 panic。

另外有 compatible additions：`WorkList` 与 `AppliedWorkList` 通过新版 `metav1.ListMeta` 获得 `ShardInfo`，以及对应 `GetShardInfo` / `SetShardInfo` methods。`make manifests` 没有产生 CRD diff，Work/AppliedWork schema 未改变。

Karmada `upstream/master` 没有引用 `sigs.k8s.io/work-api` module 或这些 generated informer interfaces，因此上述 source incompatibility 不会直接破坏 Karmada 当前编译。其他 work-api library consumers 是否存在自定义实现，仍需依赖 downstream CI 或后续代码搜索确认。

## 验证结果

| 检查 | 结果 | 边界 |
| --- | --- | --- |
| `go mod tidy` | 通过 | 使用自动下载的 Go `1.26.7` toolchain |
| `go mod verify` | 通过 | `all modules verified` |
| `hack/update-codegen.sh` | 通过 | 产生 5 个 generated Go file changes |
| `make manifests` | 通过 | 无 CRD diff |
| `go test -run '^$' ./...` | 通过 | 全 package 编译，不运行 test bodies |
| `make test` | 通过 | generate、gofmt、go vet、manifests、Kubernetes `1.34.0` envtest 和 `go test ./pkg/...`；controller coverage 72.2% |
| `make controller` | 通过 | 生成、vet 并构建 `bin/manager` |
| `make verify` | 通过 | codegen、CRD、gofmt、boilerplate 全通过；本机通过临时 `python -> python3` shim 补齐环境 |
| golangci-lint `v2.13.1` | 通过 | 官方 release binary，`0 issues` |
| module `apidiff` | 完成 | 4 条 incompatible entries、3 个不同 method additions；其余为 compatible additions |
| [fork push CI `32801974517`](https://github.com/ranxi2001/work-api/actions/runs/32801974517) | 通过 | exact SHA `cf1bfed10c700e66adb5792c1cad9f906e0b2e66`；`lint`、`verify`、`unit test`、`e2e` 全部 success |
| `git diff --check` | 通过 | 无 whitespace error |

### 失败命令与原因

第一次运行 `go test ./...` 时，所有 package 已完成编译，但 test execution 失败：controller suite 找不到 `/usr/local/kubebuilder/bin/etcd`，E2E suite 没有 kubeconfig。后续使用仓库标准 `make test` 下载 envtest assets 并仅运行 `pkg/...`，测试通过。本地没有运行 live E2E；fork push CI 随后完成 kind 环境搭建并通过 `e2e` job。

第一次运行 `make verify` 时，只有 boilerplate check 失败：`/usr/bin/env: 'python': No such file or directory`。直接运行 `python3 hack/boilerplate/boilerplate.py` 通过；使用临时 PATH shim 后完整 `make verify` 通过，没有修改仓库脚本。

官方 golangci-lint `v2.8.0` binary 用 Go `1.25.5` 构建，对本分支返回：

```text
the Go language version (go1.25) used to build golangci-lint is lower than the targeted Go version (1.26.7)
```

因此按 #66 的同批升级方式改为当前稳定 `v2.13.1`。其官方 binary 用 Go `1.27.0` 构建，本地 lint 返回 `0 issues`。

## 当前结论

work-api `go.mod` L11-L16 已逐项达到或超过 Karmada 对应基线，且依赖升级可以在不修改 hand-written API/controller 逻辑的情况下完成。fork push CI 的 build、lint、verify、unit test 与 live E2E 均通过。该结果证明 work-api 当前仓库能够使用这组版本完成生成、编译和测试，但不覆盖外部消费者自行实现 `SharedInformerFactory` 的场景；后续 PR body 或 reviewer notes 仍需披露新增 interface methods 的 source incompatibility，不能只写“依赖升级，无接口影响”。

当前不需要追加代码修改。upstream PR 的 exact title/body 草案见下节；发布前仍需用户再次确认 target 与全文。本轮没有创建 PR、发布 comment 或请求 reviewer。

## Upstream PR 文案草案

- Target：`kubernetes-sigs/work-api:master`
- Head：`ranxi2001:deps/kubernetes-1.36-go-1.26@cf1bfed10c700e66adb5792c1cad9f906e0b2e66`
- 状态：仅本地草案，未创建 upstream PR。

### Title

```text
Bump Kubernetes dependencies to v1.36.4
```

### Body

<!-- work-api-pr-body:start -->
```markdown
This PR bumps Kubernetes dependencies to v1.36.4 and completes the Go 1.26 update deferred in #66. The Go directive moves to 1.26.0, while the toolchain and CI use Go 1.26.7. `controller-runtime`, `controller-tools`, generated clients and informers, and golangci-lint are updated accordingly.

Compatibility note: the regenerated `SharedInformerFactory` interfaces add `StartWithContext`, `WaitForCacheSyncWithContext`, and `InformerName`. Custom implementations must provide these methods. Existing users of the generated factories can continue using the channel-based methods and constructors. CRD manifests and hand-written controller behavior are unchanged.

Tests: `go mod verify`, `hack/update-codegen.sh`, `make manifests`, `go test -run '^$' ./...`, `make test`, `make controller`, `make verify`, and golangci-lint v2.13.1 passed.

This PR was written in part with the assistance of generative AI.
```
<!-- work-api-pr-body:end -->

### 写法依据

- 标题沿用 #49、#66 及该仓库连续 Kubernetes 升级 PR 的 `Bump Kubernetes dependencies to vX.Y.Z` 格式。
- #66 明确把 Go 1.26 推迟到 Kubernetes v1.36，因此首段直接说明本次完成该计划。
- 当前仓库以及 #49、#66 对应 base 均没有 PR template；不额外添加不存在的 issue、kind 或 release-note 字段。
- 旧 PR body 很短，但本次 generator 给 public Go interface 新增 methods。该 source compatibility 边界会影响自定义实现，必须保留在 reviewer-facing 文案中。
- 不在正文引用动态 fork CI 状态；正文只列可复核的本地命令。fork exact-SHA CI 证据继续保留在本报告的“验证结果”中。
- 最后一句遵循 [Kubernetes AI Guidance](https://www.kubernetes.dev/docs/guide/pull-requests/#ai-guidance) 的披露要求；AI 不列为 co-author，也不写 commit trailer。
