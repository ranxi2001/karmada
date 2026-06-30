# Day 4: #7690 发布后的 branch / proposal gap 分析

日期：2026-06-30

## 今日目标

Day 3 已经把证书 layout 方向整理成 upstream issue，并发布为 [karmada-io/karmada#7690](https://github.com/karmada-io/karmada/issues/7690)。今天先不急着开 PR，而是确认当前 prototype branch `feature/cert-manager-layout` 和 #7690 提案之间还有哪些 gap，避免把“长期方案图”和“第一版可合并代码”混在一起。

## 当前社区状态

- Issue: [#7690 Proposal: plan-based split certificate Secret layout for karmadactl init](https://github.com/karmada-io/karmada/issues/7690)
- Label: `kind/feature`
- 状态：open
- Assignee / milestone：暂无
- 评论：已通过 `/kind feature` 添加 label，暂无 maintainer 设计反馈。
- 相关背景：
  - [#6051](https://github.com/karmada-io/karmada/issues/6051)：配置和证书 Secret/path naming convention umbrella。
  - [#6670](https://github.com/karmada-io/karmada/issues/6670)：标准化 self-signed certificates 的 proposal。
  - [#6788](https://github.com/karmada-io/karmada/pull/6788)：已有 open split secret layout PR，当前 proposal 需要尊重已有工作，不能装作没有相关实现。

## Prototype branch 状态

- 本地目录：`/home/karmada-cert-bulk`
- Branch: `feature/cert-manager-layout`
- Commit: `eb02bde96cbd88697bb808e2cb56137070d18a4c`
- Commit message: `feat: add cert secret layout for init`
- DCO: 已带 `Signed-off-by`
- Diff 规模：14 files changed, 1551 insertions(+), 326 deletions(-)
- Fork push CI：已通过。18 个 check runs 中 16 success、2 skipped、0 failed。
- 本地验证：

```bash
PATH="$(go env GOPATH)/bin:$PATH" golangci-lint run ./pkg/karmadactl/cmdinit/...
PATH="$(go env GOPATH)/bin:$PATH" hack/verify-staticcheck.sh
hack/verify-import-aliases.sh
go test ./pkg/karmadactl/... -count=1
hack/verify-command-line-flags.sh
git diff --check
```

## 已经对齐 #7690 的部分

| #7690 提案点 | branch 覆盖情况 | 证据 |
| --- | --- | --- |
| `karmadactl init --secret-layout=legacy\|split` | 已实现，默认 `legacy` | `pkg/karmadactl/cmdinit/cmdinit.go` 新增 flag；`docs/command-line-flags/karmadactl_init.md` 已生成更新。 |
| config file 支持 layout | 已实现 | `pkg/karmadactl/cmdinit/config/types.go` 新增 `spec.secretLayout`，测试覆盖 config parse。 |
| plan-based certificate layout abstraction | 已实现核心抽象 | 新增 `pkg/karmadactl/cmdinit/certmanager/types.go`，`Plan` 包含 identities、Secrets、kubeconfigs、component volumes/mounts/paths。 |
| legacy layout 保持默认兼容 | 已实现 | `legacyPlan()` 保留当前 aggregated `karmada-cert` / `etcd-cert` / `karmada-webhook-cert` 行为。 |
| split layout 分发 component-scoped Secrets | 已实现 prototype | `splitSecrets()` 拆出 apiserver、aggregated-apiserver、kube-controller-manager、scheduler/descheduler estimator、webhook、internal etcd 等 Secret。 |
| workload commands / volumes / mounts 消费 declarative plan | 已实现 | `pkg/karmadactl/cmdinit/kubernetes/cert_plan.go` 将 plan 翻译成 `corev1.Volume` / `VolumeMount`；`command.go` 从 plan paths 取证书路径。 |
| kubeconfig 使用 component client cert | 已实现 | `splitKubeconfigs()` 根据组件选择 client identity，`createCertsSecrets()` 按 plan 生成 kubeconfig Secret。 |
| external etcd 使用用户提供材料 | 已实现 prototype | `splitPlan(externalEtcd=true)` 不生成 internal etcd server Secret，apiserver/aggregated-apiserver etcd client Secret 复用 `EtcdClient`。 |
| split 下保留 legacy-compatible `karmada-cert` | 已实现 | `legacyCompatibleKarmadaCert()` 保留兼容 Secret，并对 external etcd 的部分 material 标记 optional。 |

结论：branch 覆盖的是 #7690 中“第一版 `karmadactl init` layout-plan subset”，不是图片里的完整长期证书管理系统。

## 主要 gap

### 1. Issue 还在问方向，branch 已经做了设计选择

#7690 的最后 5 个问题还是待 maintainer 确认的问题：

1. `karmadactl init` 是否接受 plan-based certificate layout boundary。
2. 第一版是否只做 `karmadactl init`，还是需要同时设计 Helm/operator。
3. split mode 是否应该临时保留 legacy-compatible `karmada-cert`。
4. component client cert 的 group/privilege 是否应该在本 PR 收窄。
5. 现有 #6788 是继续、替换，还是先在 #6670 讨论。

但是 prototype branch 已经默认选择：

- 只做 `karmadactl init`。
- 保留 legacy-compatible `karmada-cert`。
- 不做 RBAC/client privilege 收窄。
- 不引入 cert-manager/CRD/controller。
- 用新的 `certmanager.Plan` 抽象替代在部署代码里散落 `legacy/split` 判断。

这不是代码错误，但意味着在 maintainer 回复前不要直接开 upstream PR；否则 PR 看起来像已经绕过设计讨论。

### 2. 图片里的长期方案没有实现，这是 intentional gap

#7690 的两张图展示了更大的长期方向，包括：

- certificate policy / plan / inventory CRDs；
- certificate management controllers；
- cert-manager / CA integration；
- 多集群 Secret 分发；
- rotation / hot reload；
- observability / alerting。

当前 branch 没有实现这些内容。这个 gap 是刻意保留的，因为 #7690 的 `Non-goals` 已经写清楚第一版不做 CRD、controller、cert-manager integration、rotation/hot reload、Helm/operator。后续如果 reviewer 误解图片范围，需要回复说明：图片只用于解释长期方向和前后对比，第一版 PR 只取 `karmadactl init` 的 layout-plan 子集。

### 3. PR diff 可能偏大，需要考虑拆小

当前 diff 是 14 个文件、约 +1551/-326。它同时包含：

- 新抽象层；
- 新 flag 和 config 字段；
- 新证书 identity / Secret layout；
- Deployment / StatefulSet / command path 接入；
- Secret/kubeconfig 生成逻辑改造；
- tests 和 command-line flag docs。

如果直接开 PR，reviewer 需要一次性审抽象设计、证书命名、部署模板、external etcd、兼容策略和测试。更稳妥的拆法：

1. PR 1：引入 plan abstraction，保持 legacy 行为等价，证明 abstraction boundary 不改变用户行为。
2. PR 2：新增 `--secret-layout=split` 和 split Secret/kubeconfig 分发。
3. PR 3（可选）：根据 maintainer 反馈处理 RBAC/client identity 收窄、Helm/operator 对齐或 #6788 迁移。

如果 maintainer 明确希望一个 PR 解决，也可以保留当前 branch，但 PR body 需要非常清晰地列出 scope 和 review checklist。

### 4. 命名规范还未被社区确认

branch 已经选择了一批 Secret 名称、volume 名称、mount path 和 data key，例如：

- `karmada-apiserver-cert`
- `karmada-apiserver-etcd-client-cert`
- `karmada-apiserver-front-proxy-client-cert`
- `karmada-apiserver-service-account-key-pair`
- `karmada-aggregated-apiserver-cert`
- `karmada-aggregated-apiserver-etcd-client-cert`
- `kube-controller-manager-ca-cert`
- `kube-controller-manager-service-account-key-pair`
- `karmada-scheduler-scheduler-estimator-client-cert`
- `karmada-descheduler-scheduler-estimator-client-cert`
- `etcd-etcd-client-cert`

这些命名是基于 #6051 和现有 manifests 的理解，但还不是 maintainer 明确确认的共识。尤其要注意：

- `karmada-scheduler-scheduler-estimator-client-cert` 读起来重复，但语义是 “scheduler 组件使用的 scheduler-estimator client cert”。
- `kube-controller-manager-ca-cert` 实际包含 CA cert/key，用于 cluster signing，是否应该叫 `ca-cert` 还是 `cluster-signing-cert` 需要确认。
- `etcd-etcd-client-cert` 语义是 internal etcd 组件使用的 etcd client cert，但名称可能显得重复。

发布 PR 前应把命名表单独列出来，让 reviewer 可以逐项确认，而不是隐藏在代码 diff 里。

### 5. 安全身份粒度和权限还没有真正收窄

branch 生成了 component client cert，但不少 client cert 仍然使用 `system:masters` group。这和“更细粒度、更安全”的长期目标之间有差距。

这不是当前 PR 必须立即解决的问题，因为 #7690 已经把 “Should component client certificate groups/privileges be narrowed in the layout PR, or left for a follow-up?” 列为 open question。当前建议：

- 第一版只解决 Secret/layout/path/kubeconfig 分发；
- RBAC/client privilege 收窄单独做 follow-up；
- PR body 中主动说明 “client identity privilege tightening is intentionally deferred unless maintainers request it in this PR”。

### 6. 真实部署验证还不足

当前已有 unit test、lint、staticcheck、command flag verify 和 fork push CI。但 fork CI 主要说明代码能编译、基础测试能跑，不等于 split layout 的真实安装链路已经验证。

PR 前最好补一次 smoke test：

```bash
karmadactl init --secret-layout=split ...
kubectl -n karmada-system get secret
kubectl -n karmada-system get deploy,statefulset,pod
kubectl -n karmada-system describe pod <karmada-apiserver-pod>
```

重点检查：

- expected split Secrets 是否创建；
- apiserver / aggregated-apiserver / scheduler / webhook / etcd volume mounts 是否存在；
- command args 中证书路径是否指向 split mount path；
- pods 是否 Ready；
- external etcd 场景是否仍使用用户提供的 CA/client cert；
- legacy layout 默认路径是否没有回归。

## 当前判断

branch 和 #7690 的关系可以这样描述：

> `feature/cert-manager-layout` is a concrete prototype for the first `karmadactl init` subset proposed in #7690. It does not implement the broader certificate-management system shown in the diagrams, and it intentionally defers cert-manager integration, CRDs/controllers, rotation, Helm/operator alignment, and RBAC privilege tightening.

换成中文就是：

> 当前 branch 基本能作为 #7690 第一版 PR 的原型，但不能说它已经完成整个证书管理层长期方案。它更像是先把 `karmadactl init` 中证书生成、Secret 分发、kubeconfig 生成和 workload 消费之间的边界抽象出来。

## 下一步最小行动

1. 先等 #7690 maintainer 回复，不急着开 PR。
2. 如果 maintainer 认可方向，优先把当前 branch 收敛成小 PR，最好先做 plan abstraction + legacy no-op，降低 review 压力。
3. 在 PR body 中主动说明 intentional gaps：不做 CRD/controller/cert-manager、rotation、Helm/operator、RBAC 收窄。
4. 补一个 split layout smoke test 记录，证明 `karmadactl init --secret-layout=split` 真能跑通。
5. 准备命名表让 reviewer 确认 Secret name、volume name、mount path、data key，而不是只让 reviewer 从代码里猜。
