# Issue #7869：release-1.19 本周可认领任务尽调

状态核对时间：2026-08-31 19:49（Asia/Shanghai）

## 先说人话

可以继续认领，但不应 `/assign` 整个 umbrella issue。#7869 更新 owner map 后，本周首选是 website 的 `Add upgrading v1.18 to v1.19 docs`：当前没有 owner 或冲突 PR，个人 website fork 已存在，且最小范围只有英文、中文和 `sidebars.js` 三个文件。

主仓库的“停止维护 v1.16、开始维护 v1.19”与 Kubernetes compatibility 也仍未标 owner，但 `release-1.19` branch 尚未创建；三个定时 CI / Dependabot 配置若提前合入，会引用不存在的 branch。因此它保留为 branch cut 后的备选，不和 upgrading docs 同时占位。

## 当前状态

- #7869：Open，无 assignee、无评论，只有 `kind/feature`；checkbox 尚未勾选，但 body 已增加各子任务 owner。
- `upstream/master`：`6d7b233a54d59c8473803901768153f6e4353d02`。
- `release-1.19` branch、`v1.19.0` tag 和 final GitHub Release：均不存在。
- Release notes：[PR #7870](https://github.com/karmada-io/karmada/pull/7870) 已由 `@RainbowMango` 提交；CI 全绿但尚未合并，不能重复认领。
- 已标 owner：正式 release、patch Helm CI 与 website release branch 为 `@RainbowMango`；website Reference、release docs 与 prune v1.13 为 `@zhzhuang-zju`。
- 未标 owner 且无冲突 PR：主仓库 maintenance、Kubernetes compatibility、website upgrading docs。v1.19.0 Helm index 是自动生成任务，不是人工改文件的候选。
- [`ranxi2001/website`](https://github.com/ranxi2001/website) 已是 upstream website fork；fork `main` 落后 upstream，应直接从最新 upstream `main` 建 topic branch。

## 首选：website upgrading docs

| 文件 | 改动 |
| --- | --- |
| `docs/administrator/upgrading/v1.18-v1.19.md` | 英文升级事项 |
| `i18n/zh/docusaurus-plugin-content-docs/current/administrator/upgrading/v1.18-v1.19.md` | 与英文语义一致的中文升级事项 |
| `sidebars.js` | 将新升级文档加入导航 |

上一轮 [website #1017](https://github.com/karmada-io/website/pull/1017) 是同型先例。可以先依据 `CHANGELOG-1.19.md` 和 #7870 起草，但 #7870 尚未合并，当前内容只能作为候选发布说明；开 PR 前必须复核最终 API removal、deprecation、Kubernetes dependencies 和 upgrade constraints，并运行 website build / preview。

## 备选：主仓库 maintenance 与 compatibility

该任务对应上一轮 [#7591](https://github.com/karmada-io/karmada/pull/7591)，仍应保持一个四文件 PR：

- `.github/workflows/ci-schedule-compatibility.yaml`
- `.github/dependabot.yml`
- `.github/workflows/ci-image-scanning-on-schedule.yml`
- `README.md`

它需要先等 `release-1.19` branch 创建，并确认 README 中 v1.19 的 Kubernetes compatibility 行。README 表格不能机械压成整表只有 10 个 Kubernetes 版本；v1.17/v1.18 仍覆盖 Kubernetes 1.26，不能提前删除仍有使用者的列。

## 不认领的任务

- `prepare release notes`：已有 #7870。
- 正式 release、patch release、website release branch：需要 release owner 权限，#7869 已指定 `@RainbowMango`。
- Helm index：由 release workflow 自动生成或由 `@RainbowMango` 手动触发，不手改 `charts/index.yaml`。
- website Reference / release docs / prune：已经标给 `@zhzhuang-zju`，不再认领。

## 认领草稿

当前精确 comment 保存在 [issue7869-upgrading-docs-claim-draft.md](issue7869-upgrading-docs-claim-draft.md)。原 [maintenance draft](issue7869-maintenance-task-claim-draft.md) 已显式标为 superseded，不得发布。发布目标是 `karmada-io/karmada#7869` 的一条新 comment；不会修改 issue body、title、labels、assignee 或 checkbox。

## 下一步

1. 用户确认 exact target/text/hash 后发布认领 comment，并核对 comment URL 与远端正文。
2. 等待 issue author / release owner 回应；在没有确认时不建立重复 PR。
3. 获得确认后，从 website upstream `main` 创建独立 topic branch；先起草三文件，再在 #7870 稳定后复核并运行 website validation。
