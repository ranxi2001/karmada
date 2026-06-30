# Day 6: 证书轮换方案设计与实现准备

日期：2026-06-30

## 今日目标

Day 4 已经确认之前把主线放在 `secret-layout` / split Secret prototype 上有偏差。维护者在 [karmada-io/karmada#7693](https://github.com/karmada-io/karmada/issues/7693) 给出的新方向更具体：先为安装工具增加证书轮换能力，第一步聚焦 `karmadactl init`。

今天的目标是把这个方向整理成可实现的方案：

1. 对齐 website 侧的证书轮换文档任务 [karmada-io/website#1014](https://github.com/karmada-io/website/issues/1014)。
2. 梳理历史问题和已有尝试，避免重复走大而散的方案。
3. 写清楚 `karmadactl init --cert-mode=rotate` 的实现边界、代码切入点、风险和测试计划。

## 社区背景

### website#1014：证书轮换指南的文档任务

- Issue: [karmada-io/website#1014 Publish Certificate Rotation Guide](https://github.com/karmada-io/website/issues/1014)
- 状态：open
- Label: `kind/feature`
- Assignee：暂无
- 任务清单：
  - Manual Karmada certificate rotation guide
  - Automated Karmada certificate rotation guide (cert-manager integration)
  - Karmada built-in certificate rotation support (agent certificate auto-rotation) 已由 [website#1016](https://github.com/karmada-io/website/pull/1016) 完成

这个 issue 说明证书轮换不是单纯代码功能，还需要文档配套。当前已合并的是 agent built-in certificate rotation 文档；控制面证书的手动轮换和自动轮换仍然缺入口。

### karmada#4787：生产环境真实痛点

- Issue: [karmada-io/karmada#4787 How to rotate karmada certificate if it is expired](https://github.com/karmada-io/karmada/issues/4787)
- 状态：open
- Label: `kind/question`
- Milestone: `v1.19`

这个 issue 里用户遇到的问题很直接：很多安装方式下证书默认 365 天过期，过期后 apiserver、controller-manager、kube-controller-manager 等组件进入 CrashLoop。评论里也有用户明确希望有类似 `kubeadm certs renew all` 的一键续期工具。

这说明 #7693 的价值不是“锦上添花”，而是解决生产环境中证书过期后难恢复、手工步骤容易出错的问题。

### karmada#5037：cert-manager 大 PR 的经验

- PR: [karmada-io/karmada#5037 Support automatic cert rotation & fix a few bugs](https://github.com/karmada-io/karmada/pull/5037)
- 状态：open，但长期未推进，mergeable state 为 dirty
- Scope：Helm chart、cert-manager/trust-manager、ServiceMonitor、HPA、audit policy、bugfix 等混在一个 XXL PR 中
- 维护者明确反馈：希望拆成更小的 PR

这个 PR 对当前任务的启发是：

- 自动轮换和 cert-manager integration 是合理方向，但不适合作为 #7693 第一版。
- 第一版必须小，最好只解决 `karmadactl init` 的一个明确能力。
- 不要把 HPA、ServiceMonitor、Helm chart 大改、Secret layout、cert-manager integration 混进同一个 PR。

### website#1016：agent 证书轮换文档已合并

- PR: [karmada-io/website#1016 publish karmada cert rollout guide](https://github.com/karmada-io/website/pull/1016)
- 状态：closed / merged
- 重点讨论：`karmada-agent` 当前不支持证书热加载，需要重启后读取新证书；旧证书过期时可能由组件自动重启触发加载

这个结论对控制面证书轮换也适用：第一版不做 hot reload。Secret 更新后，用户仍需要重启相关组件，让 Pod 重新挂载 Secret 并加载新证书。

## 当前问题定义

现在要解决的问题可以用一句话描述：

> 对于通过 `karmadactl init` 安装的 Karmada 控制面，提供一个可重复执行的证书轮换模式，复用原安装参数重新生成证书材料并替换相关 Secrets，避免用户手工识别证书、Secret、mount path 和 kubeconfig 的对应关系。

不是当前第一版目标的内容：

- 不做 `--secret-layout=split`。
- 不做 Helm chart 证书结构改造。
- 不做 operator 证书轮换。
- 不做 cert-manager / trust-manager integration。
- 不做 CRD/controller 形式的证书管理系统。
- 不做组件热加载。
- 不自动 rollout restart，除非维护者明确要求。

## 用户视角流程

预期使用方式：

```bash
karmadactl init --cert-mode=rotate \
  --namespace karmada-system \
  --cert-validity-period 8760h \
  --cert-external-ip <same-as-original-install> \
  --cert-external-dns <same-as-original-install> \
  <other flags consistent with the original installation>
```

工具做的事情：

1. 读取和普通 `init` 相同的 flags / config。
2. 根据这些参数重新生成 Karmada 组件身份证书，也就是 server/client 等 leaf certificates。
3. 更新 `karmada-config-*`、`karmada-cert`、`etcd-cert`、`karmada-webhook-cert` 等相关 Secrets。
4. 输出需要重启的组件提示。

用户仍需要做的事情：

1. 确认 rotate 命令使用的证书参数和原安装一致。
2. 在 Secret 更新后重启相关 Karmada 组件。
3. 确认使用的是原有 CA 签发新的组件身份证书。CA/root certificate 是底层信任链基石，第一版不轮转、不更新。

## 当前代码链路

`karmadactl init` 的入口在 `pkg/karmadactl/cmdinit/cmdinit.go`：

```text
NewCmdInit()
  -> Validate()
  -> Complete()
  -> RunInit()
```

证书相关实现主要在 `pkg/karmadactl/cmdinit/kubernetes/deploy.go`：

```text
RunInit(parentCommand)
  -> genCerts()
  -> load cert/key files into CertAndKeyFileData
  -> prepareCRD()
  -> createKarmadaConfig()
  -> CreateOrUpdateNamespace()
  -> createCertsSecrets()
  -> initKarmadaAPIServer()
  -> karmada.InitKarmadaResources()
  -> initKarmadaComponent()
```

与 rotate mode 最相关的是：

| 函数 | 当前作用 | rotate mode 是否复用 |
| --- | --- | --- |
| `Validate()` | 解析 config file、校验参数 | 需要复用，但可能要按 mode 调整校验 |
| `Complete()` | 初始化 kube client、检查 NodePort、处理 node selector、获取 apiserver IP、初始化 command args、清理/创建 data path | 不能原样复用，需要小心拆分 |
| `genCerts()` | 根据参数生成 CA、leaf cert、etcd cert、front-proxy cert | 不能在 rotate mode 原样复用，需要避免生成新 root CA，只复用既有 CA 签发组件身份证书 |
| `readExternalEtcdCert()` | external etcd 场景读取用户提供的 etcd cert/key | 需要复用 |
| `createCertsSecrets()` | 创建/更新 kubeconfig Secrets、`etcd-cert`、`karmada-cert`、`karmada-webhook-cert` | 需要复用 |
| `initKarmadaAPIServer()` | 创建 etcd/apiserver/aggregated-apiserver workload | rotate mode 不执行 |
| `karmada.InitKarmadaResources()` | 创建/patch CRD、webhook、APIService、bootstrap RBAC 等 | rotate mode 不复用；因为 CA 不变，不需要更新 caBundle/APIService/Webhook/CRD conversion 信任配置 |
| `initKarmadaComponent()` | 创建 controller-manager、scheduler、webhook 等 workload | rotate mode 不执行 |

## 关键设计点

### 1. `Complete()` 不能直接复用

这是实现时最容易踩的坑。现在 `Complete()` 是安装流程的 complete，不是通用 complete：

- `isNodePortExist()` 对正常安装有意义，但 rotate 时 apiserver NodePort 已经存在，不能因此失败。
- hostPath etcd 场景会尝试给 Node 加 label；rotate 时不应该修改 Node。
- `getKarmadaAPIServerIP()` 依赖安装时逻辑，但 rotate 只需要构造证书 SAN。
- `initializeDirectory(i.KarmadaDataPath)` 会清理并重建 data path，rotate 时如果用户已有本地配置，不能无脑清空。

因此建议拆成两个阶段：

```text
completeCommon()
  -> rest config
  -> kube client
  -> parse config / basic defaults

completeInstall()
  -> nodePort conflict check
  -> node selector mutation/check
  -> install command args
  -> initialize data path for install

completeRotate()
  -> ensure target namespace exists
  -> prepare temporary output directory for regenerated cert material
  -> compute cert SAN inputs without mutating cluster install resources
```

如果不想第一版拆太大，也至少要在 `Complete()` 里根据 cert mode 跳过 install-only 逻辑。

### 2. 证书材料准备应独立抽取

当前 `RunInit()` 中证书准备逻辑和后续安装逻辑混在一起。建议抽成：

```text
prepareCertMaterial()
  -> genCerts()
  -> i.CertAndKeyFileData = map[string][]byte{}
  -> for each certList item:
       if external etcd cert, read from user provided path
       else read generated .crt/.key from KarmadaPkiPath
```

然后普通安装和 rotate 共享这个函数。

### 3. Secret 更新也应独立抽取

当前 `createCertsSecrets()` 已经使用 `util.CreateOrUpdateSecret()`，语义上接近 rotate 的需求。建议保留它作为核心同步函数，但命名上可以考虑：

```text
syncCertSecrets()
  -> create/update component kubeconfig Secrets
  -> create/update etcd cert Secret
  -> create/update karmada cert Secret
  -> create/update webhook cert Secret
```

如果为了减少 diff，第一版可以继续使用 `createCertsSecrets()` 名称，但 PR 描述里要说明 rotate mode 复用它更新 Secret。

### 4. 只轮转组件身份证书，不轮转 CA

当前 `cert.GenCerts()` 的行为是：

- 如果用户传 `--ca-cert-file` 和 `--ca-key-file`，使用该 CA 签发新的 Karmada leaf cert。
- 如果用户不传 CA 文件，会生成新的 `karmada` root CA。
- `front-proxy-ca` 和 internal `etcd-ca` 每次都会重新生成。
- leaf cert 的有效期由 `--cert-validity-period` 控制。

这里已经明确第一版策略：

> 轮转的是组件身份证书，也就是组件用于 TLS server/client 身份验证的 leaf certificates。CA/root certificates 是底层信任链基石，数量少、影响面大，不在这个功能里轮转。

原因是 CA 一旦变化，所有信任这个 CA 的 kubeconfig、WebhookConfiguration、APIService、CRD conversion caBundle、组件间 TLS 信任链都可能需要同步更新。对用户来说，这不是普通证书续期，而是信任根迁移，兼容风险明显更高。

因此 rotate mode 必须复用既有 CA 签发新的组件身份证书，不能偷偷生成新的 root CA。

明确后的场景表：

| 场景 | 含义 | rotate mode 影响 |
| --- | --- | --- |
| 复用旧 CA 续签组件身份证书 | 新 server/client cert 仍由旧 CA 签发 | 第一版目标路径，只更新相关 Secrets 并提示用户重启组件 |
| 生成新 Karmada root CA | 信任根变化 | 第一版不支持，避免破坏现有信任链 |
| 生成新 front-proxy CA | front-proxy 信任根变化 | 第一版不支持，应复用既有 front-proxy CA 签发新的 front-proxy-client cert |
| 生成新 internal etcd CA | etcd mutual TLS 信任根变化 | 第一版不支持，应复用既有 etcd CA 签发新的 etcd server/client cert |
| external etcd | 外部 etcd CA/client cert 由用户提供 | 工具不轮转 external etcd CA；如用户提供新的 external etcd client cert/key，只作为输入材料同步进 Secret |

这会直接影响实现：

1. 不能在 rotate mode 里直接调用当前 `cert.GenCerts()`，因为它在未传 CA 文件时会生成新的 `karmada` root CA，并且总是重新生成 `front-proxy-ca` 和 internal `etcd-ca`。
2. rotate mode 需要有“读取既有 CA 材料”的能力，来源可以是用户显式传入的 CA 文件，也可以是从现有 Secret 中读取 CA cert/key。
3. 轮转函数应只重新签发组件身份证书：apiserver server cert、admin/client cert、front-proxy-client cert、etcd server/client cert、webhook serving cert/kubeconfig client cert 等。
4. 如果找不到签发所需的既有 CA private key，应该直接报错，而不是自动生成新 CA。

换句话说，`--cert-mode=rotate` 的语义更接近 “renew component identity certificates”，不是 “rotate trust roots”。

### 5. caBundle 不属于第一版更新范围

`karmada.InitKarmadaResources()` 在安装时会使用 CA 更新：

- CRD conversion webhook patches 中的 `caBundle`
- `MutatingWebhookConfiguration`
- `ValidatingWebhookConfiguration`
- aggregated APIService 的 `CABundle`

现在策略明确为“不轮转 CA”，所以 rotate mode 不应该更新这些 caBundle。这样可以避免把证书身份证明续期扩展成信任根迁移。

如果未来社区需要 root CA migration，应作为单独设计处理，至少需要：

- 信任 bundle 双写或过渡期机制；
- WebhookConfiguration / APIService / CRD conversion caBundle 同步；
- kubeconfig client CA bundle 更新；
- 组件重启顺序和回滚策略；
- external etcd / internal etcd 不同信任链的迁移边界。

这些都不是 #7693 第一版目标。

## 建议实现方案

### API / option 设计

新增 mode 常量：

```go
const (
    CertModeInstall = "install"
    CertModeRotate  = "rotate"
)
```

`CommandInitOption` 增加字段：

```go
CertMode string
```

`karmadactl init` 增加 flag：

```bash
--cert-mode string
```

默认值建议是 `install`，这样比空字符串更容易校验和写文档。

如果支持 config file，则 `KarmadaInitSpec` 增加：

```yaml
spec:
  certMode: rotate
```

不过 config file 字段是否第一版加入，需要看社区是否希望 CLI flag 和 config file 能力一致。Karmada 当前 `init` 已支持 `--config`，如果只加 flag 不加 config 字段，会留下一个小的不一致。

### 执行流程

建议目标流程：

```mermaid
flowchart TD
    A[karmadactl init] --> B[parse flags/config]
    B --> C{cert-mode}

    C -->|install| D[complete install options]
    D --> E[prepare cert material]
    E --> F[prepare CRDs and kubeconfig]
    F --> G[create/update namespace and cert Secrets]
    G --> H[create/update workloads and Karmada resources]

    C -->|rotate| I[complete rotate options]
    I --> J[load existing CA material]
    J --> K[renew component identity certs]
    K --> L[update cert-related Secrets]
    L --> M[print restart guidance]
```

### 代码拆分建议

第一步做纯重构，保证普通安装行为不变：

```text
RunInit()
  -> prepareCertMaterial()
  -> runInstall()
```

第二步加 rotate：

```text
RunInit()
  -> switch CertMode
       install: runInstall()
       rotate: runRotate()

runInstall()
  -> prepareCertMaterial()
  -> prepareCRD()
  -> createKarmadaConfig()
  -> CreateOrUpdateNamespace()
  -> createCertsSecrets()
  -> initKarmadaAPIServer()
  -> InitKarmadaResources()
  -> initKarmadaComponent()

runRotate()
  -> loadExistingCAMaterial()
  -> renewComponentIdentityCerts()
  -> ensure namespace exists
  -> createCertsSecrets()
  -> print restart guidance
```

如果维护者不希望拆 `RunInit()` 太多，可以先把证书逻辑抽出来，保留安装主流程的顺序。

## 测试计划

### 单元测试

1. mode validation：
   - 默认 `install` 通过。
   - `rotate` 通过。
   - 未知 mode 报错。

2. config parsing：
   - 如果加 `spec.certMode`，测试 YAML config 能解析到 `CommandInitOption.CertMode`。

3. cert material preparation：
   - internal etcd 场景能读取既有 `karmada` CA、`front-proxy-ca`、`etcd-ca`，并重新签发组件身份证书。
   - rotate mode 找不到既有 CA private key 时必须报错，不能自动生成新 CA。
   - external etcd 场景读取用户提供的 external etcd client cert/key，不生成 external etcd CA。

4. rotate secret sync：
   - fake client 中预置 namespace 和旧 Secrets。
   - 执行 rotate path 后，相关 Secrets 被更新。
   - component kubeconfig Secrets 仍包含新的 cert data。

5. rotate 不创建 workload：
   - fake client action list 中不应出现 Deployment、StatefulSet、Service、CRD 创建。
   - 这条测试很重要，能防止 rotate mode accidentally reinstall。

6. CA bundle 行为：
   - rotate mode 不更新 WebhookConfiguration / APIService / CRD conversion caBundle。
   - 测试可以通过 fake client action list 确认没有相关 update/patch 行为。
   - 如果输入会导致生成新 CA，应直接报错或拒绝，而不是进入 caBundle 更新路径。

### 本地验证命令

开发分支上至少跑：

```bash
go test ./pkg/karmadactl/cmdinit/... -count=1
hack/verify-command-line-flags.sh
git diff --check
```

如果新增导出类型或包级常量，再跑：

```bash
PATH="$(go env GOPATH)/bin:$PATH" golangci-lint run ./pkg/karmadactl/cmdinit/...
hack/verify-staticcheck.sh
hack/verify-import-aliases.sh
```

### 手工 smoke test

真实部署验证需要单独安排，至少覆盖：

```bash
karmadactl init ...
kubectl -n karmada-system get secret karmada-cert etcd-cert karmada-webhook-cert
karmadactl init --cert-mode=rotate <same cert flags>
kubectl -n karmada-system get secret karmada-cert -o yaml
kubectl -n karmada-system rollout restart deploy/karmada-apiserver
kubectl -n karmada-system rollout restart deploy/karmada-aggregated-apiserver
kubectl -n karmada-system rollout restart deploy/karmada-controller-manager
kubectl -n karmada-system rollout restart deploy/karmada-kube-controller-manager
kubectl -n karmada-system rollout restart deploy/karmada-scheduler
kubectl -n karmada-system rollout restart deploy/karmada-webhook
kubectl -n karmada-system get pod
```

如果使用 internal etcd，rotate mode 应复用既有 etcd CA 重新签发 etcd server/client cert。Secret 更新后仍要评估 etcd StatefulSet 和 apiserver 的重启顺序，因为 etcd server/client leaf cert 同时更新会影响 apiserver 连接 etcd。

## PR 切分建议

建议不要直接把所有内容做成一个大 PR。比较稳的拆法：

1. PR 1：引入 `CertMode`、抽取证书材料准备函数，默认安装行为不变。
2. PR 2：实现 `--cert-mode=rotate`，只更新相关 Secrets，补 fake client 测试和 flag 文档。
3. PR 3：website 文档，补 manual control-plane certificate rotation guide，关联 website#1014。

如果社区希望一个 PR 完成 #7693，也可以合并 PR 1/2，但不建议把 cert-manager 自动轮换、Helm chart 和 split Secret layout 混进去。

## 当前需要确认的问题

提交代码前最好在 issue 或 PR body 中明确这些问题：

1. `--cert-mode` 默认值是否用 `install`，还是保持空值代表普通安装。
2. rotate mode 从哪里读取既有 CA private key：要求用户传 `--ca-cert-file` / `--ca-key-file`，还是优先从现有 Secret 中读取。
3. rotate mode 是否应该要求 namespace 和现有 cert Secrets 已存在，避免用户传错 namespace 时创建无用 Secret。
4. 是否更新本地 kubeconfig 文件，还是只更新集群内 kubeconfig Secrets。
5. 是否自动输出 restart 命令；是否自动执行 rollout restart。
6. external etcd 场景是否只复用用户提供的 external cert，不做任何生成。

## 当前结论

证书方向现在应聚焦 #7693：

> 第一版不是重做 Secret layout，也不是 cert-manager 自动轮换，而是把 `karmadactl init` 已有的证书生成和 Secret 写入能力抽出来，提供一个 `--cert-mode=rotate` 路径，让用户能可靠地替换 `karmadactl init` 管理的证书 Secrets。

更准确地说，第一版轮转的是组件身份证书，不轮转 CA/root certificates。CA 是底层信任链基石，变化会带来不兼容风险，不应混入这个功能。

这条路径和 website#1014 也能对齐：代码侧先提供可执行工具，后续文档侧补 manual certificate rotation guide，把“命令如何跑、哪些参数必须和原安装一致、哪些组件要重启、为什么 CA 不轮转”写清楚。

## 下一步最小行动

1. 从最新 `upstream/master` 新建干净 topic branch。
2. 先做源码级最小重构：抽出证书材料准备边界，保持 `RunInit()` 默认行为不变。
3. 增加 `CertMode` 和 validation，不急着改 Secret layout。
4. 实现 rotate path：读取既有 CA，重新签发组件身份证书，更新 Secrets。
5. 用 fake client 测试证明 rotate 只更新 Secrets、不创建 workloads、不更新 caBundle。
