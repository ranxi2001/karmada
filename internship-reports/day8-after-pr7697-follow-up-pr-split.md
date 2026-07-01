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
