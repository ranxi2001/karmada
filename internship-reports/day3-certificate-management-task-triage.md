# Day 3：证书管理相关 issue / PR 调研和任务整理

日期：2026-06-29

## 今日目标

同事提示有一个“批量证书管理配置工具”方向的 issue / PR 可以做。今天的目标是先把社区里证书管理相关的 issue、PR 和历史 LFX 项目串起来，判断哪些是背景资料、哪些已经有人在做、哪些是真正适合作为后续贡献点的任务。

本次没有修改 Karmada 功能代码，也没有运行本地集群；结论来自本地仓库搜索、GitHub 公开 API / 页面检索和源码路径对照。

## 调研结论

最值得继续跟进的是 issue [#6051](https://github.com/karmada-io/karmada/issues/6051)：`[Umbrella] [Karmada config && certificates] secret and path naming convention`。

这个 issue 仍然 open，带 `help wanted`，并且已经拆成 config 和 certificate 两个任务。其中 Task two 是 `[Karmada Certificate] secret and path naming convention`，要求统一 Karmada 各组件证书 Secret、volume、mount path 和 secret field 命名。当前最明显的空位是：

- `helm`: `@help-wanted`
- `karmadactl`: 关联过 `#6187`
- `karmada-operator`: 关联 `#6178`

初步判断：如果我要接一个低风险但有实际价值的贡献点，优先从 `#6051` 的 Helm 证书命名规范入手，而不是直接碰正在进行的 `karmadactl` 大 PR。

## 相关背景

| 线索 | 状态 | 和当前任务的关系 |
| --- | --- | --- |
| [community#69](https://github.com/karmada-io/community/issues/69) Karmada Certificate Lifecycle Management | closed | LFX 2024 项目背景，覆盖证书可见性、手动替换指南、证书有效期配置、自动轮转 |
| [#6091](https://github.com/karmada-io/karmada/issues/6091) Self-Signed Certificate Content Standardization | closed | LFX 2025 项目，目标是 8 个 server 组件和 11 个 client 组件使用不同证书内容 |
| [#6269](https://github.com/karmada-io/karmada/pull/6269) Add component certificate identification | merged | #6091 的设计 PR，说明组件证书身份区分方向已经被社区接受 |
| [#6670](https://github.com/karmada-io/karmada/issues/6670) Proposal to Standardize Self-Signed Certificates in Karmada | open | 把 bash 部署方式里的证书标准化同步到其他部署方式 |
| [#6788](https://github.com/karmada-io/karmada/pull/6788) support split secret layout in init command | open | `karmadactl init` 支持 `--secret-layout=split`，当前 PR 仍 open 且有冲突，不适合重复开同类 PR |
| [#6553](https://github.com/karmada-io/karmada/pull/6553) helm: support rotating cert when helm upgrade | open | Helm 证书生命周期相关，但主题是 upgrade 时 rotate cert，不是命名规范 |

> 分析：同事说的“批量证书管理配置工具”不是一个我能精确匹配到的 issue 标题，更像是对证书标准化、split secret layout、证书生命周期管理这些任务的口头概括。后续和同事或 mentor 同步时，应该直接拿 `#6051`、`#6670`、`#6788` 这几个编号确认。

## 本地仓库证据

本地搜索看到证书逻辑主要分布在这些位置：

| 路径 | 作用 |
| --- | --- |
| `hack/deploy-karmada.sh` | bash 部署方式中生成 CA、server cert、client cert，并把证书写入 Secret |
| `hack/util.sh` | 证书生成辅助函数，例如 `util::create_signing_certkey`、`util::create_certkey` |
| `charts/karmada/values.yaml` | Helm chart 的 `certs.mode`、`certs.auto`、`certs.custom`、外部 etcd 证书、agent kubeconfig 等配置入口 |
| `charts/karmada/templates/_helpers.tpl` | Helm chart 中证书 Secret、volume、caBundle 相关模板 helper |
| `operator/pkg/certs/` | operator 侧证书配置、生成、存储和解析逻辑 |
| `pkg/karmadactl/cmdinit/` | `karmadactl init` 安装入口，涉及证书生成、Secret 创建和组件挂载 |
| `docs/proposals/cert/Self-Signed_Certificate_Content_Standardization.md` | 自签证书内容标准化设计文档 |

> 注释：当前证书问题横跨安装脚本、Helm chart、operator 和 CLI。做贡献时必须先选一个安装入口，不要一次性改所有部署方式，否则 review 范围会很大。

## 可选任务拆解

### 任务 A：接 `#6051` Helm 证书命名规范

优先级：最高。

目标是把 Helm chart 的证书 Secret、volume、mount path、secret field 向 issue 中的规范对齐。需要先只做调研和差距分析，再决定是否开 PR。

下一步：

1. 读 `#6051` Task two 的所有示例，提取期望命名表。
2. 对照 `charts/karmada/templates/` 当前实际 Secret、volume、mount path。
3. 输出一张差距表：组件、当前值、期望值、是否会破坏兼容、是否需要迁移策略。
4. 先在 issue 下评论英文分析和拟改范围，确认 maintainer 接受后再动代码。

风险：

- Helm chart 涉及用户升级兼容，不能轻易改现有 Secret 名称。
- 可能需要同时支持 legacy 和 standardized 两种布局，或者通过 value 开关启用。
- 证书 Secret 名称变化会影响多个 Deployment / StatefulSet / APIService / webhook 配置。

### 任务 B：帮忙 review 或续做 `#6788`

优先级：中。

`#6788` 已经实现 `karmadactl init --secret-layout=split`，但 PR 仍 open，且 GitHub API 显示 mergeable state 为 dirty。这个方向和 `#6051` 强相关，但已有作者在做。

下一步：

1. 本地拉取 PR diff，确认冲突点和测试失败点。
2. 不直接开重复 PR；先在 PR 下询问作者 / reviewer 是否接受协助。
3. 可以贡献 review、复现日志、冲突分析或补测试。

### 任务 C：调研 Helm 证书轮转 `#6553`

优先级：中低。

这个 PR 是 Helm upgrade 时是否重新生成证书的问题，属于证书生命周期管理，不是当前命名规范主线。可以作为理解 Helm 证书模板的参考。

下一步：

1. 阅读 `#6553` 改动点。
2. 判断它是否会影响 `#6051` 的 Secret 命名和升级兼容策略。

## 补充：批量系统证书替换分发的初步设计

下午继续对 `karmadactl init` 的证书生成和分发路径做了设计层梳理。RANXI2001反馈的关键点是：不要为了改代码而改代码，应该先抽象出证书管理层，再让安装流程消费这一层的结果。

> 分析：如果只在 `deploy.go`、`command.go`、`deployments.go` 和 `statefulset.go` 里到处加 `if secretLayout == split`，短期可以跑通，但后续 Helm、operator、addons 或证书轮转继续接入时会很难维护。更合理的方向是先把“证书身份、证书材料、Secret 分发计划、组件挂载路径”作为独立模型。

### 设计目标

1. 保持默认 `legacy` 行为不变，避免影响现有 `karmadactl init` 用户。
2. 增加可选 `split` 布局，用系统生成的组件级证书替换当前多组件共用证书的方式。
3. 把证书生成和 Secret 分发从 Kubernetes 部署模板里抽出来，形成可测试的证书管理层。
4. 让部署层只消费证书管理层产出的 plan，不直接关心 Secret 名称、data key、证书文件名。
5. 为后续同步 Helm、operator 或证书轮转留下统一抽象。

### 分层方案

| 层级 | 建议位置 | 职责 | 不应该做的事 |
| --- | --- | --- | --- |
| 证书工具层 | `pkg/karmadactl/cmdinit/cert` | 生成 CA、签发证书、写入 PEM 文件 | 不知道 Karmada 组件名、Secret 名称、volume mount |
| 证书管理层 | `pkg/karmadactl/cmdinit/certmanager` 或 `pkg/karmadactl/cmdinit/certstore` | 定义证书身份、layout、Secret plan、组件 kubeconfig plan、mount path plan | 不直接创建 Deployment / StatefulSet |
| Kubernetes 适配层 | `pkg/karmadactl/cmdinit/kubernetes` | 根据 plan 创建 Secret、生成 command、挂载 volume | 不散落证书命名规则 |

### Mermaid 设计图：改造前后对比

改造前，证书生成、Secret 创建、组件挂载路径和 command 参数都散落在 `kubernetes` 包的安装流程中。每新增一种证书布局，都容易变成在多个文件里重复判断 `legacy` / `split`。

```mermaid
flowchart TB
  subgraph Before["改造前：部署流程直接处理证书细节"]
    A["karmadactl init<br/>CommandInitOption"] --> B["genCerts()<br/>固定 certList"]
    B --> C["createCertsSecrets()<br/>直接创建 karmada-cert / etcd-cert / webhook-cert"]
    C --> D["make Deployment / StatefulSet<br/>手写 Secret volume 和 mount path"]
    D --> E["default component command<br/>手写 /etc/karmada/pki/*.crt/key"]
  end

  C -.问题.-> P1["证书身份和组件边界不清"]
  D -.问题.-> P2["Secret 名称、volume 名称、mount path 分散"]
  E -.问题.-> P3["新增 split 布局时需要多处 if 判断"]
```

改造后，`karmadactl init` 先选择 layout，再由证书管理层产出统一的证书身份清单和分发计划。Kubernetes 适配层只消费 plan，不再自己决定证书命名规则。

```mermaid
flowchart TB
  A["karmadactl init<br/>--secret-layout=legacy|split"] --> M["Certificate Manager"]

  subgraph Manager["证书管理层"]
    M --> L["Layout<br/>legacy / split"]
    L --> I["RequiredIdentities()<br/>组件证书身份清单"]
    L --> S["SecretPlans()<br/>Secret 名称、类型、data key"]
    L --> K["KubeconfigPlans()<br/>组件 client cert 分发"]
    L --> C["ComponentPlan()<br/>volume、mount path、command path"]
  end

  I --> G["证书工具层<br/>生成 CA、server cert、client cert、sa key pair"]
  G --> Store["Material Store<br/>Cert / Key / CA / KeyPair"]
  Store --> S
  Store --> K

  subgraph Adapter["Kubernetes 适配层"]
    S --> Secret["CreateOrUpdate Secret"]
    K --> ConfigSecret["Create component kubeconfig Secret"]
    C --> Workload["生成 Deployment / StatefulSet"]
    C --> Command["生成组件 command 参数"]
  end

  Secret --> Runtime["Karmada control plane pods"]
  ConfigSecret --> Runtime
  Workload --> Runtime
  Command --> Runtime
```

这个抽象引入后的核心变化：

| 维度 | 改造前 | 改造后 |
| --- | --- | --- |
| 证书身份 | 主要依赖固定 `certList`，多个组件复用 `karmada` 证书 | layout 明确定义每个组件需要哪些 server / client / special cert |
| Secret 分发 | `createCertsSecrets()` 直接拼 Secret 数据 | `SecretPlans()` 先生成声明式计划，再由 Kubernetes 适配层创建 |
| 挂载路径 | Deployment / StatefulSet 里直接写 mount path | `ComponentPlan()` 统一给出 volume、mount path 和 command path |
| kubeconfig | 多组件共用 admin 风格证书 | split 布局下按组件分发 client cert |
| 扩展 layout | 多文件散落 `if split` | 新增 layout 实现，部署层逻辑保持稳定 |

初步接口草案：

```go
type Manager struct {
    layout Layout
}

type Layout interface {
    Name() string
    RequiredIdentities() []IdentitySpec
    SecretPlans(store Store, input KubeconfigInput) ([]SecretSpec, error)
    ComponentPlan(component ComponentName) ComponentPlan
}

type IdentitySpec struct {
    ID           IdentityID
    CommonName   string
    Organizations []string
    AltNames     certutil.AltNames
    Signer       SignerID
    Kind         IdentityKind
}

type SecretSpec struct {
    Name string
    Type corev1.SecretType
    Data map[string]MaterialRef
}

type ComponentPlan struct {
    Volumes      []corev1.Volume
    VolumeMounts []corev1.VolumeMount
    Paths        map[PathRole]string
}
```

这里 `MaterialRef` 不是直接保存证书字节，而是指向某个证书材料，例如 `APIServerServer.Cert`、`APIServerServer.Key`、`RootCA.Cert`。这样单测可以只验证 plan，不必每次真的签发证书。

### 证书身份模型

split 布局里不应该只是把同一个 `karmada.crt/key` 拆进多个 Secret，而应该按组件生成证书身份。

建议第一版覆盖 `karmadactl init` 当前会部署的核心组件：

| 类型 | 身份 |
| --- | --- |
| CA | `ca`、`front-proxy-ca`、内部 etcd 的 `etcd-ca` |
| server cert | `karmada-apiserver`、`karmada-aggregated-apiserver`、`karmada-webhook`、内部 etcd `etcd-server` |
| component client cert | `karmada-controller-manager-client`、`karmada-scheduler-client`、`karmada-aggregated-apiserver-client`、`karmada-webhook-client`、`kube-controller-manager-client` |
| etcd client cert | `karmada-apiserver-etcd-client`、`karmada-aggregated-apiserver-etcd-client`、`etcd-client` |
| special client cert | `front-proxy-client`、`karmada-scheduler-grpc` |
| key pair | service account `sa.key` / `sa.pub` |

> 注释：`karmadactl init` 还会创建 descheduler、search、metrics-adapter 等 config Secret 名称，但这些组件不一定在 init 阶段部署。第一版可以为它们生成 component client cert 或保留兼容配置，但不能让核心组件继续依赖 admin 证书。

### Secret 分发模型

split 布局应对齐 `artifacts/deploy/*.yaml` 已经使用的路径和 Secret 命名：

| 组件 | Secret | mount path | data key |
| --- | --- | --- | --- |
| karmada-apiserver server | `karmada-apiserver-cert` | `/etc/karmada/pki/server` | `ca.crt`、`tls.crt`、`tls.key` |
| karmada-apiserver etcd client | `karmada-apiserver-etcd-client-cert` | `/etc/karmada/pki/etcd-client` | `ca.crt`、`tls.crt`、`tls.key` |
| karmada-apiserver front proxy client | `karmada-apiserver-front-proxy-client-cert` | `/etc/karmada/pki/front-proxy-client` | `ca.crt`、`tls.crt`、`tls.key` |
| karmada-apiserver service account key pair | `karmada-apiserver-service-account-key-pair` | `/etc/karmada/pki/service-account-key-pair` | `sa.pub`、`sa.key` |
| karmada-aggregated-apiserver server | `karmada-aggregated-apiserver-cert` | `/etc/karmada/pki/server` | `ca.crt`、`tls.crt`、`tls.key` |
| karmada-aggregated-apiserver etcd client | `karmada-aggregated-apiserver-etcd-client-cert` | `/etc/karmada/pki/etcd-client` | `ca.crt`、`tls.crt`、`tls.key` |
| kube-controller-manager CA | `kube-controller-manager-ca-cert` | `/etc/karmada/pki/ca` | `tls.crt`、`tls.key` |
| kube-controller-manager service account key pair | `kube-controller-manager-service-account-key-pair` | `/etc/karmada/pki/service-account-key-pair` | `sa.pub`、`sa.key` |
| karmada-scheduler estimator client | `karmada-scheduler-scheduler-estimator-client-cert` | `/etc/karmada/pki/scheduler-estimator-client` | `ca.crt`、`tls.crt`、`tls.key` |
| webhook serving cert | `karmada-webhook-cert` | `/var/serving-cert` 或 `/etc/karmada/pki/server` | `tls.crt`、`tls.key`，可附带 `ca.crt` |
| internal etcd server | `etcd-cert` | `/etc/karmada/pki/server` | `ca.crt`、`tls.crt`、`tls.key` |
| internal etcd client | `etcd-etcd-client-cert` | `/etc/karmada/pki/etcd-client` | `ca.crt`、`tls.crt`、`tls.key` |

兼容性策略：

- `legacy` 继续创建并挂载现有 `karmada-cert`、`etcd-cert`、`karmada-webhook-cert`，路径不变。
- `split` 下核心组件不再挂载聚合的 `karmada-cert`。
- `split` 下可以保留一个兼容性 `karmada-cert`，供 addons 或旧逻辑读取 CA / 证书，但它不再是核心组件的主依赖。
- external etcd 场景不生成内部 etcd server cert，只读取用户传入的 external etcd CA / client cert / key 并放入对应 etcd client Secret。

### kubeconfig 分发模型

当前 `createCertsSecrets()` 会给多个组件创建同一份 kubeconfig，里面用的是同一个 `karmada` admin 证书。split 方案应该改成按组件分发：

| config Secret | client cert |
| --- | --- |
| `karmada-aggregated-apiserver-config` | `karmada-aggregated-apiserver-client` |
| `karmada-controller-manager-config` | `karmada-controller-manager-client` |
| `karmada-scheduler-config` | `karmada-scheduler-client` |
| `karmada-webhook-config` | `karmada-webhook-client` |
| `kube-controller-manager-config` | `kube-controller-manager-client` |
| `karmada-descheduler-config` | `karmada-descheduler-client` |
| `karmada-search-config` | `karmada-search-client` |
| `karmada-metrics-adapter-config` | `karmada-metrics-adapter-client` |

外部给用户使用的 `karmada-apiserver.config` 仍保持 admin 证书语义，避免影响用户登录 Karmada API Server 的方式。

### 实现步骤草案

1. 新增证书管理层的数据结构和 legacy / split layout plan，不接入部署流程。
2. 给 layout plan 写单测，先验证 Secret 名称、data key、mount path、组件证书身份是否正确。
3. 改 `karmadactl init` 增加 `--secret-layout=legacy|split`，默认 `legacy`。
4. `RunInit` 中先通过 manager 生成证书身份列表，再读取证书材料，最后创建 Secret plan。
5. 部署层逐步改为从 `ComponentPlan` 获取 command path、volume、volumeMount。
6. 最后补命令行 flag 文档和 focused go test。

### 验证计划

| 验证项 | 命令 / 方法 |
| --- | --- |
| 管理层 plan 单测 | `go test ./pkg/karmadactl/cmdinit/... -run Cert` |
| CLI init 相关单测 | `go test ./pkg/karmadactl/cmdinit ./pkg/karmadactl/cmdinit/kubernetes -count=1` |
| command flag 文档 | `hack/verify-command-line-flags.sh` |
| 不破坏 legacy | 对比默认 `CommandInitOption` 生成的 command、volume、Secret key |
| split 布局正确性 | fake client 检查 Secret 名称和 `StringData` key；deployment/statefulset 检查 mount path |

### 仍需确认的问题

1. 证书管理层包名应该叫 `certmanager`、`certstore` 还是留在 `kubernetes` 包内。
2. split 布局第一版是否只覆盖 `karmadactl init` 部署的核心组件，还是同时覆盖 addons。
3. 保留兼容性 `karmada-cert` 时，里面应该放完整 legacy 证书集，还是只放 CA。
4. `#6788` 作者是否还在推进；如果要上游提交，应先避免和已有 PR 重复竞争。
5. `#6051` 的 Helm 命名规范是否要和 `karmadactl init` 的 split layout 使用完全一致的命名表。

## 今日卡点

| 卡点 | 现象 | 处理 |
| --- | --- | --- |
| GitHub CLI 未登录 | `gh search issues` 提示需要 `gh auth login` 或 `GH_TOKEN` | 改用 GitHub REST API 和网页搜索 |
| GitHub API 匿名限流 | 后续 broad search 出现 rate limit exceeded | 已经拿到核心 issue / PR 信息，后续如果继续做需要配置 `GH_TOKEN` |
| “批量证书管理配置工具”不是精确标题 | 搜索不到同名 issue / PR | 通过证书生命周期、self-signed standardization、split secret layout、secret naming convention 串联判断 |

## CI lint 失败复盘

日期：2026-06-30

在 `feature/cert-manager-layout` 分支把证书管理层初版实现推到 fork 后，push CI 已经跑完。结果不是功能测试失败，而是 `CI Workflow / lint` 失败：

| 项目 | 结果 |
| --- | --- |
| commit | `651cbec29 feat: add cert secret layout for init` |
| fork branch | `ranxi2001/karmada:feature/cert-manager-layout` |
| workflow | `CI Workflow` |
| failed job | `lint` |
| failed step | `hack/verify-staticcheck.sh` |
| 通过项 | `compile`、`unit test`、`codegen`、3 个 e2e、CLI / Chart / Operator Kubernetes 矩阵 |
| skipped | `FOSSA`、`image-scanning` |

### 什么是 lint 规范

这里的 lint 不是业务测试，而是项目的静态代码规范检查。Karmada 在 `.golangci.yml` 里配置了 `golangci-lint`，CI 的 `lint` job 会依次跑：

1. `hack/verify-license.sh`
2. `hack/verify-vendor.sh`
3. `hack/verify-staticcheck.sh`
4. `hack/verify-import-aliases.sh`

本次失败发生在第 3 步。`hack/verify-staticcheck.sh` 实际执行 `golangci-lint run`。它会检查代码风格、导出 API 注释、安全误报、现代 Go 写法、未使用参数等问题。即使 `go test` 全部通过，只要这些规范不满足，CI 仍然失败。

### 本次失败原因

本地复现命令：

```bash
PATH="$(go env GOPATH)/bin:$PATH" golangci-lint run ./pkg/karmadactl/cmdinit/...
```

复现结果：31 条问题，全部集中在新增的 `pkg/karmadactl/cmdinit/certmanager` 包。

| 类型 | 数量 | 说明 |
| --- | --- | --- |
| `revive` | 26 | 新增的导出 const / type / function 缺少 Go doc 注释 |
| `gosec` | 4 | `Secret... = "...-cert"` 这类常量被误判为 hardcoded credentials |
| `modernize` | 1 | 测试里手写循环可以改成 `slices.Contains` |
| `unused-parameter` | 1 | `legacyCertificateNames(externalEtcd bool)` 参数未使用 |

根因不是 Karmada 业务逻辑失败，而是提交前只跑了 `go test ./pkg/karmadactl/...` 和 `hack/verify-command-line-flags.sh`，漏跑了 CI lint 对应的 `hack/verify-staticcheck.sh` / `golangci-lint run`。新增一个公开包时，导出符号和常量名会被 lint 严格检查，不能只靠单测判断。

### 以后避免规则

以后只要新增 Go 包、导出类型、导出常量、命令行 flag、证书/Secret 名称或较大抽象层，提交前必须先跑：

```bash
PATH="$(go env GOPATH)/bin:$PATH" golangci-lint run ./pkg/karmadactl/cmdinit/...
go test ./pkg/karmadactl/... -count=1
hack/verify-command-line-flags.sh
```

如果要推到 fork 跑完整 push CI，再跑：

```bash
python3 /home/karmada/.agents/skills/karmada-push-ci-check/scripts/check_push_ci.py \
  --repo ranxi2001/karmada \
  --branch "$(git rev-parse --abbrev-ref HEAD)" \
  --sha "$(git rev-parse HEAD)" \
  --show-jobs failed
```

本次补救计划：

1. 给 `certmanager` 包所有导出符号补 Go doc 注释，或者把没有跨包必要的符号改成未导出。
2. 对 gosec 误判的 Secret 名称常量做合理处理：优先通过更清晰的命名/分组降低误报；必要时对确定安全的常量加局部 `#nosec G101`，但要写明这是 Kubernetes Secret 对象名，不是密钥内容。
3. 删除或真正使用 `legacyCertificateNames` 的 `externalEtcd` 参数。
4. 测试 helper 改用 `slices.Contains`。
5. 复跑 `golangci-lint run ./pkg/karmadactl/cmdinit/...`，通过后再 amend / force-with-lease 推 fork。

## 明日最小行动

1. 把证书管理层设计先整理成更小的代码改动边界，避免直接在部署代码中散落 `split` 判断。
2. 继续确认 `#6788` 的冲突点和设计缺口，但不直接复制它的大 diff。
3. 对照 `artifacts/deploy/*.yaml`、`hack/deploy-karmada.sh` 和 `pkg/karmadactl/cmdinit/`，固化 split Secret / mount path 命名表。
4. 如果 mentor 仍建议先接 `#6051` Helm 部分，则回到 Helm Secret / volume / mount path 差距表。
5. 如果 mentor 要求继续基础学习，则回到 Day 2 计划，深追 `samples/nginx` 传播链路。
