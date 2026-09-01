# Issue #7869：release-1.19 本周可认领任务尽调

状态核对时间：2026-09-01 09:50（Asia/Shanghai）

## 先说人话

认领已经完成：#7869 的 issue body 已把 `Stop maintaining version 1.16 and maintain version 1.19` 标给 `@ranxi2001`，此前的认领 comment 也同时声明处理 `Update Kubernetes compatibility`。这两项应沿用上一轮 [#7591](https://github.com/karmada-io/karmada/pull/7591) 的边界，合成一个四文件 PR，而不是拆成两个互相产生短暂不一致的 PR。

现在已经可以开工。`release-1.19` branch、正式 `v1.19.0` tag 和 GitHub Release 均已建立，并指向 `6d7b233a54d59c8473803901768153f6e4353d02`；当前 `upstream/master@4a6efcd1b` 还只比 release branch 多 release notes 与 Helm index。用户最初提到的 RC 可以作为历史预发布证据，但本次实现与测试应以正式 release branch/tag 为准。

## 当前状态

- #7869：Open，issue-level assignee 为空，但 body 已把 maintenance 子任务标给 `@ranxi2001`；compatibility 在认领 comment 中与它绑定为同一 PR。
- `upstream/master`：`4a6efcd1b4e4a2d3fd244016d66adc2235f2c1e1`。
- `release-1.19` branch / `v1.19.0` tag：均为 `6d7b233a54d59c8473803901768153f6e4353d02`；branch 已 protected，正式 Release 发布于 `2026-08-31T12:50:17Z`。
- Release notes：[PR #7870](https://github.com/karmada-io/karmada/pull/7870) 已合并；自动 Helm index [PR #7871](https://github.com/karmada-io/karmada/pull/7871) 也已合并。
- 已标 owner：正式 release、patch Helm CI 与 website release branch 为 `@RainbowMango`；website Reference、release docs 与 prune v1.13 为 `@zhzhuang-zju`。
- 当前认领状态：maintenance 已在 body 标给 `@ranxi2001`；compatibility 未单独标 owner，但已在同一认领 comment 中绑定，且没有冲突 PR。website upgrading docs 仍未标 owner；v1.19.0 Helm index 已由自动化完成。

## 当前认领：主仓库 maintenance 与 compatibility

| 文件 | 改动 |
| --- | --- |
| `.github/workflows/ci-schedule-compatibility.yaml` | 维护版本轮换为 `master, release-1.19, release-1.18, release-1.17` |
| `.github/dependabot.yml` | 三个 Docker `target-branch` 轮换为 `release-1.19`、`release-1.18`、`release-1.17` |
| `.github/workflows/ci-image-scanning-on-schedule.yml` | matrix 轮换为 `release-1.19, release-1.18, release-1.17` |
| `README.md` | 删除 Karmada v1.16，增加 v1.19，并按实际 branch 依赖核对 compatibility 行 |

README 表格不能机械压成整表只有 10 个 Kubernetes 版本；v1.17/v1.18 仍覆盖 Kubernetes 1.26，不能提前删除仍有使用者的列。v1.19 的勾选范围必须在 branch cut 后按实际依赖确认，不能预填猜测。

## 实现设计

### 文件范围

| 文件 | Change type | 为什么修改 | 风险 | 验证 |
| --- | --- | --- | --- | --- |
| `.github/dependabot.yml` | maintenance set rotation | Docker target branches 从 `1.18/1.17/1.16` 轮换为 `1.19/1.18/1.17` | 错写不存在 branch，或误动 master/github-actions 配置 | YAML parse、精确 target 集合、remote branch existence |
| `.github/workflows/ci-image-scanning-on-schedule.yml` | matrix rotation | 定时扫描维护中的三个 release branches | 漏扫新版本或继续扫描 EOL v1.16 | YAML / workflow parse、精确 matrix 断言 |
| `.github/workflows/ci-schedule-compatibility.yaml` | matrix rotation | compatibility workflow 改测 `master + 1.19/1.18/1.17` | 误改 Kubernetes 版本窗口或 matrix 次序 | YAML / workflow parse、精确 matrix 断言 |
| `README.md` | compatibility record | 删除 v1.16，增加 v1.19；删除无人使用的 Kubernetes 1.25 列 | 列错位、错误扩大兼容范围、误删仍被使用的 1.26 | table 结构断言、逐格 diff review、证据边界复核 |

### 明确不改

| 文件 / 区域 | 原因 |
| --- | --- |
| `.github/workflows/ci.yml`、`ci-schedule.yml`、installation workflows | Kubernetes version window 已由 #7665 更新；本任务只轮换 Karmada maintenance branches |
| `charts/index.yaml` 与 release workflows | v1.19.0 Helm index 已由 #7871 自动生成，不属于手工维护范围 |
| `docs/CHANGELOG/**` | release notes 已由 #7870 合并 |
| website repo | upgrading/reference/release docs 是 #7869 中的独立任务 |
| API、Go production code、generated files | 本任务只维护 CI 配置和 README，不改变运行时行为 |
| 新增长期测试文件 | 一次性固定集合轮换不值得扩大成新测试框架；用结构化本地断言验证即可 |

### README compatibility 结论

`Karmada v1.19` 应勾选 Kubernetes `1.36..1.27` 共 10 个版本，并在 `1.26` 留空。依据是：

1. `release-1.19@6d7b233a54` 的 Kubernetes modules 统一为 `v0.36.4`；
2. 当前 compatibility workflow 的十版本窗口精确为 `v1.27.3..v1.36.1`；
3. #7591 采用“新 release 行复用当时 HEAD 窗口”的已接受模式；
4. #7665 的 maintainer 解释确认“每个 Karmada 行覆盖 10 个 Kubernetes 版本”，不是整张表只能有 10 列；
5. 删除 v1.16 后，Kubernetes 1.25 不再被任何保留行使用，应删除；1.26 仍被 v1.17/v1.18 使用，必须保留。

证据限制：当前 workflow 尚未把 `release-1.19` 加入 matrix，因此没有 `6d7b233a54` exact-branch 的十组合全绿结果。最近一次 pre-release master run 中，1.27、1.28、1.29、1.31..1.36 成功，1.30 在所有 release branches 同轮失败；本报告不把它写成 v1.19 exact SHA 全绿。README 行表示当前维护规则确定的预期兼容窗口，完整 runtime 结果由更新后的 scheduled workflow 后续持续验证。

### 验证计划

1. `git diff --check upstream/master...HEAD`，并确认 diff 精确为上述四文件。
2. 用 `Python 3 + PyYAML` 解析三个 YAML；不以正则替代结构化解析。
3. 结构化断言三个集合：Dependabot 为 implicit master + `1.19/1.18/1.17`；compatibility 为 `master + 1.19/1.18/1.17`；image scanning 为 `1.19/1.18/1.17`。
4. 用 `git ls-remote --exit-code upstream` 验证 `release-1.19/1.18/1.17` 均存在。
5. 检查 README table 每行列数一致，并断言 v1.17/v1.18/v1.19/HEAD 的勾选窗口。
6. 可用时对两个 workflow 运行 `actionlint`；仓库未内置该工具，若安装失败只记录环境缺口，不用完整 `make verify` 代替。

不运行 `make test`、`make all`、完整 `make verify`、40 组合 compatibility E2E 或 33 组合 image scan。这些昂贵命令不能在本地证明固定集合替换正确，而且 `make verify` 没有覆盖这四个文件的 YAML / Markdown 语义。

## 本地候选结果

```text
worktree: /tmp/karmada-release-1.19-maintenance
branch:   chore/maintain-release-1.19
base:     upstream/master@4a6efcd1b4e4a2d3fd244016d66adc2235f2c1e1
commit:   3c3f74c5df16aba3dcccc3ca5d5c0101a351a291
subject:  chore: update maintained release versions
```

提交包含 `Signed-off-by: ranxi2001 <ranxi2001@users.noreply.github.com>`，最终 diff 精确为 4 files、`+11/-11`。重新 fetch `upstream/master` 后基线未漂移，且没有同范围 open PR。

### 最终验证

| 检查 | 结果 | 能证明什么 |
| --- | --- | --- |
| `git diff --check upstream/master...HEAD` | pass | 最终 committed diff 无 whitespace error |
| PyYAML `6.0.1` parse | 3 files pass | Dependabot 与两个 workflow 仍是合法 YAML |
| structured matrix assertions | pass | 三个 Karmada maintenance sets 与十个 Kubernetes versions 精确匹配设计 |
| README table assertions | pass | 所有行列数一致；v1.17/v1.18 与 v1.19/HEAD 各自保留正确十版本窗口 |
| `git ls-remote --exit-code upstream` | `release-1.19/1.18/1.17` pass | 所有新增/保留 target refs 存在 |
| `actionlint v1.7.12` | 2 workflows pass | GitHub Actions schema / expression / workflow syntax 可接受 |
| retired-entry negative check | pass | 四文件中不再包含 `release-1.16`、`Karmada v1.16` 或 `Kubernetes 1.25` |
| fresh-context diff review | no findings | 四文件 scope、matrix rotation 与 README alignment 无额外问题 |

没有运行 live scheduled compatibility 或 image-scanning matrix；因此不能声称 v1.19 exact branch 的 40 组合 compatibility 或 33 组合 image scan 已通过。

### PR 文案草稿

- Title：[issue7869-pr-title.txt](issue7869-pr-title.txt)；SHA-256 `44a0ae88110aa3168e2651a01a85a4d79532af2ede3ad0fb4426b7bc9a85457f`
- Body：[issue7869-pr-body-draft.md](issue7869-pr-body-draft.md)；92 visible words / 13 nonblank lines；SHA-256 `094150375532f364e6b78cbfde7b0c1f075c0222ce07bbc937935114aa2e5981`

文案以 [#7242](https://github.com/karmada-io/karmada/pull/7242) 为主要风格先例：lowercase title、单一 `/kind documentation`、一句话 what/why、`Part of #7869` 和 `NONE` release note；只额外加入真实 validation boundary 与 AI assistance disclosure。

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
- 后续 owner 更新：issue author 于 `2026-09-01T01:16:47Z` 修改 body，把 maintenance 子任务标给 `@ranxi2001`；这不是我们发布 comment 时对 issue body 的修改。

[upgrading-docs draft](issue7869-upgrading-docs-claim-draft.md) 已显式标为 superseded，不得发布。本轮没有修改 issue body、title、labels、assignee 或 checkbox。

## 下一步

1. 用户核对 local commit、diff、测试与 PR 文案。
2. 获得 exact push / PR approval 后才把 `chore/maintain-release-1.19` 推到 origin 并创建 upstream PR。
3. PR 创建后以 official PR CI 为动态验证面，不把 fork push CI 当作发布证据。
