# Day 8: PR #7697 后续说明图和 follow-up PR 拆分回复

日期：2026-07-01

## 目标

PR [#7697](https://github.com/karmada-io/karmada/pull/7697) 已经进入 review 阶段。为了让 reviewer 更快理解这次变更，需要准备一条英文 PR comment，配合数据流变化图说明：

- 这个 PR 解决什么问题。
- `karmadactl init --cert-mode=rotate` 和原 install flow 的关系。
- 哪些证书会被轮换，哪些不会。
- 这个 PR 的 scope / non-goals。
- #7697 之后应该如何拆 follow-up PR，而不是继续把所有证书管理能力塞进同一个 PR。

这篇 Day 8 只准备草稿，不直接发布 upstream comment。发布前需要用户确认完整英文文本。

## 图片资产

当前准备了两张图：

1. 英文主图：`Karmada Certificate Rotation - Data Flow Change.png`
2. 中文/中英混合辅助图：`karmada证书pr7697变动.png`

建议 PR comment 使用英文主图：

![Karmada Certificate Rotation - Data Flow Change](Karmada%20Certificate%20Rotation%20-%20Data%20Flow%20Change.png)

上传到 fork `intern` 分支后，可在 GitHub comment 中使用这个 raw URL：

```text
https://raw.githubusercontent.com/ranxi2001/karmada/intern/internship-reports/Karmada%20Certificate%20Rotation%20-%20Data%20Flow%20Change.png
```

> 注释：图中底部 Change Summary 的 metadata 表达应按当前实现理解为 Secret update 时保留 existing metadata。当前 PR 不引入证书 rotation controller，也不新增自动 watcher / audit / monitoring 机制。

## 给自己看的中文理解

这条评论不是重新解释整个 PR，而是帮 reviewer 快速建立 mental model。

#7697 的核心变化可以概括为：

```text
原来：
karmadactl init 主要是安装路径，生成 CA + leaf certificates，然后创建 Secrets 和工作负载。

现在：
karmadactl init 增加 rotate mode。
rotate mode 不走安装资源创建，只读取现有 CA material，重新签发组件 leaf certificates，更新 init-managed certificate Secrets 和 kubeconfig Secrets，然后提示用户手动重启相关组件。
```

最重要的边界：

- CA/root CA 不轮换。
- caBundle 不更新。
- WebhookConfiguration / APIService / CRD conversion caBundle 不更新。
- Helm/operator 不处理。
- 不自动 rollout restart。
- 不引入 cert-manager。
- 不把 Secret layout redesign 混进来。

为什么要这么拆：

```text
leaf certificate renewal 是证书续期问题；
CA rotation 是 trust-root migration 问题。
```

如果把 CA rotation、caBundle、Helm/operator、自动重启、监控审计全放进 #7697，会让第一版 PR 失焦，也更难 review。#7697 应该先提供一个可工作的、低风险的 init-managed leaf certificate rotation path。

## Suggested PR Comment Draft

> 发布前需要用户确认。不要直接发 upstream PR comment。

```md
I prepared a data-flow diagram to make the scope of this PR easier to review:

![Karmada Certificate Rotation - Data Flow Change](https://raw.githubusercontent.com/ranxi2001/karmada/intern/internship-reports/Karmada%20Certificate%20Rotation%20-%20Data%20Flow%20Change.png)

This PR adds a new certificate rotation path to `karmadactl init` through `--cert-mode=rotate`.

High-level behavior:

- The existing install/generate flow remains the default behavior.
- The new rotate flow reuses existing CA material from current init-managed Secrets.
- It renews component identity certificates, also known as leaf certificates.
- It updates init-managed certificate Secrets and kubeconfig Secrets.
- It preserves existing Secret metadata during updates.
- It prints restart guidance; components are not restarted automatically.

Intentional non-goals in this PR:

- No root CA / Front-Proxy CA / Etcd CA rotation.
- No caBundle updates in kubeconfigs, WebhookConfiguration, APIService, or CRD conversion configs.
- No workload recreation.
- No automatic rollout restart.
- No Helm or Karmada Operator flow changes.
- No cert-manager integration.
- No new certificate watcher/controller, audit log, or monitoring metric.

The main reason for this scope is to keep the first version focused on leaf certificate renewal. CA rotation is a trust-root migration problem and should be handled separately, because it would require updating all trust consumers consistently.

Suggested follow-up split after this PR:

1. Documentation PR: add a user-facing certificate rotation guide, including the required command, original install flags, backup recommendation, and manual restart steps. This can align with `karmada-io/website#1014`.
2. Restart UX follow-up: discuss whether Karmada should add an optional restart helper later. The current PR only prints restart guidance.
3. CA rotation design: if the community wants root CA rotation, handle it as a separate design/PR for trust-root migration, including caBundle and kubeconfig updates.
4. Helm/operator parity: if maintainers want rotation support outside `karmadactl init`, split Helm and operator support into separate PRs.
5. Observability follow-up: if needed, discuss audit logs or metrics separately from the core rotation flow.

For review, I think the most important parts are:

- Whether `--cert-mode=rotate` is an acceptable UX.
- Whether reading existing CA material from init-managed Secrets is acceptable for this first version.
- Whether the update-only Secret behavior is safe enough.
- Whether the current non-goals are aligned with maintainers' expectations.
```

## 后续 PR 拆分计划

| 顺序 | PR / 任务 | 范围 | 不包含 |
| --- | --- | --- | --- |
| 1 | #7697 当前 PR | `karmadactl init --cert-mode=rotate`，复用现有 CA，轮换 leaf certs，更新 init-managed Secrets | CA rotation、caBundle、Helm/operator、自动重启 |
| 2 | docs / website PR | 用户手册：备份、命令、参数、restart steps、风险说明 | 新代码 |
| 3 | restart UX follow-up | 可选讨论是否加自动 restart helper 或更明确 restart command 输出 | 默认自动重启 |
| 4 | CA rotation proposal | 单独设计 trust-root migration：CA 替换、caBundle、kubeconfig、组件重启顺序 | 不混入 leaf renewal PR |
| 5 | Helm/operator parity | 分别评估 Helm chart 和 Karmada Operator 是否需要类似 rotate 支持 | 不复用 `karmadactl init` PR 强行覆盖 |
| 6 | observability | 如果维护者需要，单独讨论 audit / metrics / event | 不阻塞第一版 rotate |

## 发布前检查

- [ ] 图片已经推到 `origin/intern`，raw URL 可访问。
- [ ] PR #7697 最新 CI 状态已确认。
- [ ] 英文 comment 已由用户确认。
- [ ] upstream comment 只发一次，避免刷屏。
- [ ] 如果 comment 中提到 follow-up PR，不承诺具体实现时间，只表达建议拆分方向。

## Mentor 追问后的本地多集群运行态观测

### 背景

mentor 提醒：之前新增的短有效期证书测试更偏向代码路径 / e2e 风格验证，只能说明 `karmadactl init` 可以生成短期证书并触发轮换逻辑，不能直接证明真实运行中的多集群控制面在证书过期后可以通过本 PR 恢复。

因此补做一次本地多集群观测实验，目标是验证完整运行态链路：

```text
短期证书安装 Karmada
  -> 等待证书真实过期
  -> 观察 Karmada API 和控制面组件异常
  -> 执行 --cert-mode=rotate 更新 Secret 中的 leaf certificates
  -> 手动重启相关组件加载新证书
  -> 观察 Karmada API、控制面组件和 member cluster 状态恢复
```

这次实验要注意表述边界：#7697 不是自动过期检测、自动轮换、自动重启方案。它验证的是用户发现证书过期或即将过期后，可以人工执行 rotate，然后人工重启组件使控制面恢复。

### 实验环境

| 项目 | 内容 |
| --- | --- |
| PR branch | `feature/cert-mode-rotate` |
| 本地 commit | `152ab4542` |
| 控制面安装方式 | 本地 PR 分支编译出的 `/root/go/bin/karmadactl` |
| 组件镜像 | `docker.io/karmada/*:v1.18.0` |
| kind 集群 | `cert-rotate-host`、`cert-rotate-member1`、`cert-rotate-member2`、`cert-rotate-member3` |
| 实际 join 的 member | `cert-rotate-member1`、`cert-rotate-member2`，Push mode |
| 初始证书有效期 | `--cert-validity-period=10m` |
| 轮换后证书有效期 | `--cert-validity-period=8760h` |
| etcd 存储 | `--etcd-storage-mode=hostPath` |
| 本地证据目录 | `/tmp/karmada-cert-rotate-observe/logs/` |

为什么改用 `hostPath` etcd：

之前用默认 `emptyDir` 做过一次验证，组件重启时 etcd 数据会随 pod 删除丢失，导致恢复结果被测试环境污染。为了验证“证书轮换后控制面恢复”，etcd 数据必须跨 pod 重启保留，所以这次改为 hostPath。

为什么使用 pod delete 而不是 `rollout restart`：

本地 kind 是单节点环境，Karmada init 创建的部分组件带有 pod anti-affinity。直接 `rollout restart` 会让新旧 pod 同时存在，新 pod 可能因为调度约束 Pending。为了观察证书加载效果，这次直接删除旧 pod，让 Deployment / StatefulSet 重新拉起组件。

### 关键命令

初始安装使用 10 分钟短证书：

```bash
/root/go/bin/karmadactl --kubeconfig="$MAIN_KUBECONFIG" --namespace=karmada-system init \
  --karmada-data "$DATA" \
  --karmada-pki "$PKI" \
  --crds "$WORKDIR/crds.tar.gz" \
  --cert-validity-period=10m \
  --port 32443 \
  --etcd-data /var/lib/karmada-etcd-cert-rotate \
  --etcd-storage-mode=hostPath \
  --etcd-replicas=1 \
  --karmada-scheduler-image docker.io/karmada/karmada-scheduler:v1.18.0 \
  --karmada-controller-manager-image docker.io/karmada/karmada-controller-manager:v1.18.0 \
  --karmada-webhook-image docker.io/karmada/karmada-webhook:v1.18.0 \
  --karmada-aggregated-apiserver-image docker.io/karmada/karmada-aggregated-apiserver:v1.18.0 \
  --wait-component-ready-timeout=300 \
  --v=4
```

证书过期后执行 rotate：

```bash
/root/go/bin/karmadactl --kubeconfig="$MAIN_KUBECONFIG" --namespace=karmada-system init \
  --cert-mode=rotate \
  --cert-validity-period=8760h \
  --port 32443 \
  --etcd-storage-mode=hostPath \
  --etcd-replicas=1 \
  --v=4
```

手动重启相关组件加载新证书：

```bash
for selector in \
  app=etcd \
  app=karmada-apiserver \
  app=karmada-aggregated-apiserver \
  app=kube-controller-manager \
  app=karmada-controller-manager \
  app=karmada-scheduler \
  app=karmada-webhook; do
  kubectl --kubeconfig="$MAIN_KUBECONFIG" --context="$HOST_CLUSTER_NAME" \
    -n karmada-system delete pod -l "$selector" \
    --ignore-not-found --wait=true --timeout=120s
done
```

### 观测结果

#### 1. 过期前基线

证据文件：

```text
/tmp/karmada-cert-rotate-observe/logs/baseline-before-expiry.log
```

过期前 Karmada 控制面组件全部 Running：

```text
etcd-0                                      1/1 Running
karmada-apiserver                          1/1 Running
karmada-aggregated-apiserver               1/1 Running
kube-controller-manager                    1/1 Running
karmada-controller-manager                 1/1 Running
karmada-scheduler                          1/1 Running
karmada-webhook                            1/1 Running
```

初始 leaf certificates 的过期时间：

```text
karmada.crt       notAfter=Jul  1 09:03:26 2026 GMT
apiserver.crt     notAfter=Jul  1 09:03:26 2026 GMT
etcd-client.crt   notAfter=Jul  1 09:03:26 2026 GMT
```

注意：baseline 抓取时 `cert-rotate-member2` 刚 join，状态还短暂显示为 `Unknown`。这不是最终恢复结论，后续恢复验证里两个 member 都是 `Ready=True`。如果后续整理成可复用脚本，应该在进入过期等待前先 wait 两个 member cluster 都 Ready。

#### 2. 证书真实过期后的故障现象

证据文件：

```text
/tmp/karmada-cert-rotate-observe/logs/after-expiry-observation.log
```

旧 `karmada-apiserver.config` 访问 Karmada API 失败：

```text
Unable to connect to the server: tls: failed to verify certificate:
x509: certificate has expired or is not yet valid:
current time 2026-07-01T17:03:56+08:00 is after 2026-07-01T09:03:26Z
old_kubeconfig_get_clusters_rc=1
```

控制面组件出现运行态异常：

```text
karmada-controller-manager   0/1 Error
kube-controller-manager      0/1 Error
karmada-scheduler            1/1 Running, but leader election failed repeatedly
```

`karmada-controller-manager` 日志中可见访问 Karmada apiserver 证书过期：

```text
Failed to get API Group-Resources
tls: failed to verify certificate:
x509: certificate has expired or is not yet valid
```

`karmada-scheduler` 日志中可见 leader election 失败：

```text
Error retrieving lease lock
Get "https://karmada-apiserver.karmada-system.svc.cluster.local:5443/...":
tls: failed to verify certificate:
x509: certificate has expired or is not yet valid
```

这说明短证书过期不是只影响本地命令行访问，真实控制面组件也会因为无法信任 / 访问 apiserver 而异常。

#### 3. 执行 rotate 后 Secret 中证书被更新

证据文件：

```text
/tmp/karmada-cert-rotate-observe/logs/karmadactl-rotate-after-expiry.log
/tmp/karmada-cert-rotate-observe/logs/after-rotate-secret-dates.log
```

rotate 命令成功更新 Secret，并打印需要重启组件的提示：

```text
Certificate Secrets in namespace "karmada-system" have been updated.
Restart Karmada control plane components to load the rotated certificates.
```

leaf certificates 被更新到 2027 年：

```text
karmada-cert/karmada.crt       notAfter=Jul  1 09:03:57 2027 GMT
karmada-cert/apiserver.crt     notAfter=Jul  1 09:03:57 2027 GMT
karmada-cert/etcd-client.crt   notAfter=Jul  1 09:03:57 2027 GMT
etcd-cert/etcd-server.crt      notAfter=Jul  1 09:03:57 2027 GMT
```

CA 证书保持不变，符合 #7697 的设计边界：

```text
karmada-cert/ca.crt      notAfter=Jun 28 08:53:26 2036 GMT
etcd-cert/etcd-ca.crt    notAfter=Jun 28 08:53:28 2036 GMT
```

这里的结论是：#7697 轮换的是组件身份 leaf certificates，不轮换 CA/root CA。

#### 4. 手动重启组件后恢复

证据文件：

```text
/tmp/karmada-cert-rotate-observe/logs/pods-recovery-poll-3.log
/tmp/karmada-cert-rotate-observe/logs/recovery-verification.log
```

手动删除旧 pod 后，组件重新加载 Secret 中的新证书，最终全部恢复 Running：

```text
etcd-0                                      1/1 Running
karmada-apiserver                          1/1 Running
karmada-aggregated-apiserver               1/1 Running
kube-controller-manager                    1/1 Running
karmada-controller-manager                 1/1 Running
karmada-scheduler                          1/1 Running
karmada-webhook                            1/1 Running
```

从更新后的 Secret 中导出 kubeconfig，并替换为 host 可访问的 apiserver 地址后，可以再次访问 Karmada API：

```text
NAME                  VERSION   MODE   READY   AGE
cert-rotate-member1   v1.36.1   Push   True    8m28s
cert-rotate-member2   v1.36.1   Push   True    8m23s
```

补充验证 Karmada APIService：

```bash
kubectl --kubeconfig=/tmp/karmada-cert-rotate-observe/data/karmada/rotated-karmada.config \
  get apiservice v1alpha1.cluster.karmada.io \
  -o jsonpath='{.status.conditions[?(@.type=="Available")].status}{"\n"}'
```

结果：

```text
True
```

### 脚本问题和修正

本次脚本最后一条 APIService 检查写错了：

```text
kubectl --kubeconfig="$MAIN_KUBECONFIG" --context="$HOST_CLUSTER_NAME" get apiservice v1alpha1.cluster.karmada.io
```

它去 host Kubernetes API 查 Karmada APIService，因此返回：

```text
Error from server (NotFound): apiservices.apiregistration.k8s.io "v1alpha1.cluster.karmada.io" not found
```

这个错误是脚本检查对象错了，不是轮换恢复失败。正确检查应该使用轮换后的 Karmada kubeconfig：

```text
/tmp/karmada-cert-rotate-observe/data/karmada/rotated-karmada.config
```

手动补查结果为 `True`。

### 实验结论

这次观测可以作为 PR #7697 的运行态证据：

- 短有效期 leaf certificates 真实过期后，Karmada API 访问失败。
- 控制面组件会出现实际异常，不只是测试对象中的证书过期。
- 执行 `karmadactl init --cert-mode=rotate` 可以更新 init-managed Secrets 中的 leaf certificates。
- CA 证书保持不变，符合“不轮换 CA/root CA”的 scope。
- 手动重启相关组件后，控制面组件恢复 Running。
- 使用轮换后的 kubeconfig 可以重新访问 Karmada API。
- 两个 Push mode member cluster 最终均为 `Ready=True`。

需要谨慎对外表述：

```text
#7697 verifies a manual recovery path:
rotate init-managed leaf certificates, then manually restart related components.

It does not implement automatic expiry detection, automatic certificate rotation,
automatic component restart, CA rotation, or caBundle migration.
```

### 后续可改进的验证脚本

如果要把这次观测整理成更可复用的本地验证脚本，建议：

- 在 baseline 阶段 wait 两个 member cluster 都 `Ready=True` 后再进入过期等待。
- 最后的 APIService 检查使用 rotated Karmada kubeconfig，而不是 host kubeconfig。
- 把 `kind` 路径、`karmadactl` 路径、组件镜像版本抽成变量。
- 明确输出四段证据：before expiry、after expiry、after rotate、after restart recovery。
- 继续保留 `hostPath` etcd，避免重启 etcd 时丢数据。
