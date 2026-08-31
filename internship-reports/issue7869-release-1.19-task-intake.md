# Issue #7869：release-1.19 本周可认领任务尽调

状态核对时间：2026-08-31 20:14（Asia/Shanghai）

## 先说人话

认领 comment 已发布：本轮认领 `Stop maintaining version 1.16 and maintain version 1.19` 与 `Update Kubernetes compatibility` 两个 checkbox。这两项应沿用上一轮 [#7591](https://github.com/karmada-io/karmada/pull/7591) 的边界，合成一个四文件 PR，而不是拆成两个互相产生短暂不一致的 PR。

发布评论只记录我们的认领意向，不等于 maintainer 已分配或接受任务。`release-1.19` branch 尚未创建；三个定时 CI / Dependabot 配置若提前合入，会引用不存在的 branch，因此当前等待 issue author 回应或更新 owner map，并等待 branch 创建。

## 当前状态

- #7869：Open，无 assignee，只有 `kind/feature`；body 已增加其他子任务 owner，但尚未把这两项标给 `@ranxi2001`。
- `upstream/master`：`6d7b233a54d59c8473803901768153f6e4353d02`。
- `release-1.19` branch、`v1.19.0` tag 和 final GitHub Release：均不存在。
- Release notes：[PR #7870](https://github.com/karmada-io/karmada/pull/7870) 已由 `@RainbowMango` 提交；CI 全绿但尚未合并，不能重复认领。
- 已标 owner：正式 release、patch Helm CI 与 website release branch 为 `@RainbowMango`；website Reference、release docs 与 prune v1.13 为 `@zhzhuang-zju`。
- 未标 owner 且无冲突 PR：主仓库 maintenance、Kubernetes compatibility、website upgrading docs。v1.19.0 Helm index 是自动生成任务，不是人工改文件的候选。

## 当前认领：主仓库 maintenance 与 compatibility

| 文件 | 改动 |
| --- | --- |
| `.github/workflows/ci-schedule-compatibility.yaml` | 维护版本轮换为 `master, release-1.19, release-1.18, release-1.17` |
| `.github/dependabot.yml` | 三个 Docker `target-branch` 轮换为 `release-1.19`、`release-1.18`、`release-1.17` |
| `.github/workflows/ci-image-scanning-on-schedule.yml` | matrix 轮换为 `release-1.19, release-1.18, release-1.17` |
| `README.md` | 删除 Karmada v1.16，增加 v1.19，并按实际 branch 依赖核对 compatibility 行 |

README 表格不能机械压成整表只有 10 个 Kubernetes 版本；v1.17/v1.18 仍覆盖 Kubernetes 1.26，不能提前删除仍有使用者的列。v1.19 的勾选范围必须在 branch cut 后按实际依赖确认，不能预填猜测。

## 暂不认领：website upgrading docs

`Add upgrading v1.18 to v1.19 docs` 仍未标 owner，但本轮不同时占第三个任务。原 upgrading-docs comment 草稿保留为 superseded 记录，不得发布。

## 不认领的任务

- `prepare release notes`：已有 #7870。
- 正式 release、patch release、website release branch：需要 release owner 权限，#7869 已指定 `@RainbowMango`。
- Helm index：由 release workflow 自动生成或由 `@RainbowMango` 手动触发，不手改 `charts/index.yaml`。
- website Reference / release docs / prune：已经标给 `@zhzhuang-zju`，不再认领。

## 认领发布证据

- Published comment：[issuecomment-5478158840](https://github.com/karmada-io/karmada/issues/7869#issuecomment-5478158840)
- Author / time：`@ranxi2001`，`2026-08-31T12:12:55Z`
- Local exact draft：[issue7869-maintenance-task-claim-draft.md](issue7869-maintenance-task-claim-draft.md)
- Local / remote body SHA-256：`eb677800da62d594640dc857d4267c6fc19f73d6171e3be574043ee891b8bb37`
- Byte verification：remote decoded body 与 local draft 的 `cmp` exit `0`
- Issue invariant：title 仍为 `[Umbrella] Publish release-1.19`；body SHA-256 在发布前后均为 `5c5042955bea65c1c0e0685ecb4d7c3fb75849f77eac8390745fa02948310449`

[upgrading-docs draft](issue7869-upgrading-docs-claim-draft.md) 已显式标为 superseded，不得发布。本轮没有修改 issue body、title、labels、assignee 或 checkbox。

## 下一步

1. 等待 issue author / release owner 回应或在 body 中标注 owner；不把自己的 comment 当作 maintainer acceptance。
2. 等待 `release-1.19` branch 创建；触发后再次检查 #7869、open PR 和 compatibility baseline。
3. 确认无冲突后，从最新 `upstream/master` 创建独立 topic worktree，完成四文件原子更新。
