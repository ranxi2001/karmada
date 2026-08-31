# Issue #7869：release-1.19 本周可认领任务尽调

状态核对时间：2026-08-31 17:58（Asia/Shanghai）

## 先说人话

可以认领，但不应 `/assign` 整个 umbrella issue。最合适的范围是把“停止维护 v1.16、开始维护 v1.19”和“更新 Kubernetes compatibility”合成一个四文件 PR：它不需要发布权限，与上一轮 [#7591](https://github.com/karmada-io/karmada/pull/7591) 的边界完全相同，也没有发现正在进行的重复 PR。

当前不能直接合入这项改动，因为 `release-1.19` branch 尚未创建；三个定时 CI / Dependabot 配置若提前引用不存在的 branch，会形成无效目标。正确顺序是先在 [#7869](https://github.com/karmada-io/karmada/issues/7869) 留言认领，等待 release owner 确认或 branch 创建，再从最新 `upstream/master` 实现。

## 当前状态

- #7869：Open，无 assignee、无评论，只有 `kind/feature`，所有 checkbox 未勾选；尚无 `help wanted`。
- `upstream/master`：`6d7b233a54d59c8473803901768153f6e4353d02`。
- `release-1.19` branch、`v1.19.0` tag 和 final GitHub Release：均不存在。
- Release notes：[PR #7870](https://github.com/karmada-io/karmada/pull/7870) 已由 `@RainbowMango` 提交，不能重复认领。
- 精确搜索未发现标题包含 `maintain version 1.19` 的 open PR。

## 建议认领的最小范围

| 文件 | 改动 |
| --- | --- |
| `.github/workflows/ci-schedule-compatibility.yaml` | 维护版本轮换为 `master, release-1.19, release-1.18, release-1.17` |
| `.github/dependabot.yml` | 三个 Docker `target-branch` 轮换为 `release-1.19`、`release-1.18`、`release-1.17` |
| `.github/workflows/ci-image-scanning-on-schedule.yml` | matrix 轮换为 `release-1.19, release-1.18, release-1.17` |
| `README.md` | 删除 Karmada v1.16，增加 v1.19，按实际 branch 依赖核对 compatibility 行 |

README 表格不能机械压成整表只有 10 个 Kubernetes 版本。v1.17/v1.18 仍覆盖 Kubernetes 1.26，因此只应删除已经没有维护版本使用的 Kubernetes 1.25 列；v1.19 的勾选范围必须在 branch cut 后按实际依赖确认，不能预填猜测。

## 不认领的任务

- `prepare release notes`：已有 #7870。
- 正式 release、patch release、website release branch：需要 release owner 权限，#7869 已指定 `@RainbowMango`。
- Helm index：由 release workflow 自动生成或由 `@RainbowMango` 手动触发，不手改 `charts/index.yaml`。
- website Reference / release docs / prune：是另一组大规模生成任务，需单一 owner 和明确的冻结基线。

备选任务是 website 的 `Add upgrading v1.18 to v1.19 docs`，对应上一轮 [website #1017](https://github.com/karmada-io/website/pull/1017)，范围为英文、中文和 `sidebars.js` 三个文件。它可以在 final branch 创建前准备，但需要以最终 v1.19.0 release notes 核对升级事项。

## 认领草稿

精确 comment 保存在 [issue7869-maintenance-task-claim-draft.md](issue7869-maintenance-task-claim-draft.md)。发布目标是 `karmada-io/karmada#7869` 的一条新 comment；不会修改 issue body、title、labels、assignee 或 checkbox。

## 下一步

1. 用户确认 exact target/text/hash 后发布认领 comment，并核对 comment URL 与远端正文。
2. 等待 issue author / release owner 回应；在没有确认时不建立重复 PR。
3. 获得确认且 `release-1.19` branch 可用后，从最新 `upstream/master` 创建独立 topic worktree。
