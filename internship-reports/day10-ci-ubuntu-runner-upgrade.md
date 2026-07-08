# Day 10：GitHub Actions Ubuntu runner 升级调研与候选 PR

日期：2026-07-08

## 目标

用户发现 Karmada `.github/workflows/ci.yml` 仍使用 `ubuntu-22.04`，希望参考上一次 runner 升级 PR，判断是否可以升级。

本次目标：

- 查当前 `upstream/master` workflow runner 版本。
- 查上次 Karmada runner 升级 PR 的范围、原因和 review 结论。
- 对照 GitHub 官方 runner-images 公告判断 `ubuntu-22.04` 是否需要迁移。
- 准备一个最小、可 review 的候选分支，并用 fork push CI 验证。

## 当前状态

- upstream base：`upstream/master@d01d3a8fd`
- 候选 worktree：`/tmp/karmada-ci-ubuntu24`
- 候选分支：`chore/update-github-runner-ubuntu-24`
- 候选提交：`0f62fd62b05802961447601da9000403139b600d`
- fork 分支：`ranxi2001/karmada:chore/update-github-runner-ubuntu-24`
- fork push CI：已触发，等待主要矩阵完成
- upstream PR：[karmada-io/karmada#7728](https://github.com/karmada-io/karmada/pull/7728)

## 当前 workflow runner 分布

`upstream/master` 下 `.github/workflows` 共有 30 处 `runs-on: ubuntu-22.04`，没有 `ubuntu-24.04` 或 `ubuntu-latest`。

涉及文件：

- `.github/workflows/ci.yml`
- `.github/workflows/ci-schedule.yml`
- `.github/workflows/ci-schedule-compatibility.yaml`
- `.github/workflows/ci-performance-compare.yaml`
- `.github/workflows/installation-chart.yaml`
- `.github/workflows/installation-cli.yaml`
- `.github/workflows/installation-operator.yaml`
- `.github/workflows/release.yml`
- 镜像/Chart/FOSSA/image-scanning/update-helm-index 相关 workflow

> 分析：如果只改用户贴出的 `ci.yml`，会留下其他 workflow 继续使用即将弃用的 runner。上一次 Karmada PR 也不是只改主 CI，而是批量更新所有当时固定旧 Ubuntu 的 workflow。

## 上次相关 PR

相关链接：

- Karmada PR：[#3699 upgrade CI ubuntu image](https://github.com/karmada-io/karmada/pull/3699)
- 修复 issue：[#3667 Flaking test: setup e2e test environment](https://github.com/karmada-io/karmada/issues/3667)
- 触发讨论的 PR：[#3614](https://github.com/karmada-io/karmada/pull/3614)

PR #3699 信息：

- 作者：`@chaosi-zju`，Karmada member
- 类型：`/kind flake`
- 变更：13 个 workflow 文件，19 处 `ubuntu-20.04` -> `ubuntu-22.04`
- 原因：CI 大面积失败，核心是 CI runner 镜像中预装 kind 版本与 `ubuntu-20.04` 的组合触发 kind cluster 创建失败。
- review：`@RainbowMango` `/lgtm /approve`，评论 `It works.`
- 后续：维护者要求 cherry-pick 到 `release-1.6`、`release-1.5`、`release-1.4`。

关键维护者脉络：

1. #3614 CI 出现 kind cluster 创建超时，`@RainbowMango` 提到问题应由 #3667 修复。
2. `@RainbowMango` 建议尝试 `ubuntu-22.04`，因为当时主 CI 使用 `ubuntu-20.04`。
3. #3699 将多个 workflow 统一升级到 `ubuntu-22.04`。
4. 维护者接受该解法，并要求同步到 release branches。

> 注释：#3699 的核心不是“跟新版本”，而是 runner 镜像和 kind 环境导致 e2e 无法稳定创建集群。现在的升级理由不同：`ubuntu-22.04` 官方已进入明确弃用时间线。

## 官方 runner-images 证据

GitHub Actions runner-images 官方 README 当前列出：

- `ubuntu-24.04` 是 GA image，YAML label 支持 `ubuntu-latest` 或 `ubuntu-24.04`。
- `ubuntu-22.04` 仍可用，但处于旧 GA image。
- `ubuntu-26.04` 仍是 preview，不适合 Karmada 主 CI 直接切换。

官方公告 [actions/runner-images#14254](https://github.com/actions/runner-images/issues/14254)：

- `ubuntu-22.04` / `ubuntu-22.04-arm` 将从 2026-09-17 开始 deprecation。
- 2027-04-17 完全 unsupported。
- 官方 mitigation 建议更新到 `ubuntu-24.04`、`ubuntu-26.04` 或 `ubuntu-latest`。

> 分析：Karmada 更适合固定 `ubuntu-24.04`，而不是 `ubuntu-latest`。现有 workflow 一直固定具体版本，能避免 `ubuntu-latest` 迁移期带来的非预期 runner 变化。

## Ubuntu 24.04 支持期限

Canonical 官方 release cycle 页面显示 Ubuntu 24.04 LTS：

- Standard security maintenance：到 2029 年 5 月。
- Ubuntu Pro / Expanded Security Maintenance：到 2034 年 5 月。
- Legacy add-on：到 2039 年 5 月。

> 分析：这说明 `ubuntu-24.04` 作为基础 OS 自身仍处于较长 LTS 支持窗口。但 GitHub Actions hosted runner 的可用期限不完全等同于 Canonical OS 支持期限；GitHub runner-images 的策略是最多支持同一 OS 的 2 个 GA images，并在新 GA image 发布后对最老 image 启动弃用流程。因此 upstream PR 中更稳妥的表述是“migrate away from the announced `ubuntu-22.04` runner deprecation to the current GA `ubuntu-24.04` runner”，不要承诺 GitHub 会一直提供 `ubuntu-24.04` 到 2029 年。

## 候选改动

候选分支只做机械替换：

```text
ubuntu-22.04 -> ubuntu-24.04
```

变更范围：

```text
18 files changed, 30 insertions(+), 30 deletions(-)
```

本地验证：

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`：无输出。
- `git diff --check upstream/master...HEAD`：无输出。
- Python `yaml.safe_load` 解析 `.github/workflows/*.yml` 和 `.github/workflows/*.yaml`：通过。
- `actionlint`：本地未安装，未运行。

fork push CI：

- commit：`0f62fd62b05802961447601da9000403139b600d`
- `Chart`：passed
- `CLI`：passed
- `Operator`：passed
- `CI Workflow`：`lint`、`codegen`、`compile`、`unit test` 已 passed；主 e2e 预计耗时较长，仍在运行中，暂不等待
- `FOSSA`：skipped
- `image-scanning`：skipped

## PR 草稿方向

标题：

```text
ci: update GitHub runners to Ubuntu 24.04
```

正文要点：

- `/kind cleanup`
- GitHub runner-images 已宣布 `ubuntu-22.04` 将于 2026-09-17 开始 deprecation，并在 2027-04-17 unsupported。
- Karmada 当前 `.github/workflows` 仍有 30 处固定 `ubuntu-22.04`。
- 本 PR 将所有 GitHub workflow runner 统一更新到固定的 `ubuntu-24.04`，延续项目现有固定 runner label 的方式，避免 `ubuntu-latest` 自动迁移风险。
- 参考历史 PR #3699：Karmada 上一次 runner image 升级也是跨 workflow 统一更新。

测试段落应在 fork CI 完成后补充最终结果。

## Upstream PR 草稿

> 状态：已按以下标题和正文创建 upstream PR [#7728](https://github.com/karmada-io/karmada/pull/7728)。PR 创建后 DCO 已通过，upstream CI 正在运行。

Title:

```text
ci: update GitHub runners to Ubuntu 24.04
```

Body:

````md
**What type of PR is this?**

/kind cleanup

**What this PR does / why we need it**:

This PR updates GitHub-hosted Ubuntu runners from `ubuntu-22.04` to `ubuntu-24.04` across the workflow files under `.github/workflows`.

GitHub Actions runner-images has announced that `ubuntu-22.04` will begin deprecation on September 17, 2026 and become fully unsupported on April 17, 2027:

https://github.com/actions/runner-images/issues/14254

`ubuntu-24.04` is the current GA Ubuntu runner image, while `ubuntu-26.04` is still in preview. This keeps Karmada on a fixed Ubuntu runner label instead of switching to `ubuntu-latest`, so workflow environments remain explicit and predictable.

This follows the same repository-wide runner image update pattern as #3699.

**Which issue(s) this PR fixes**:

None

**Special notes for your reviewer**:

Changed files:

- Updated all `runs-on: ubuntu-22.04` labels under `.github/workflows` to `runs-on: ubuntu-24.04`.
- No workflow logic, job matrix, action version, script, or test command was changed.

Validation:

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`
- `git diff --check upstream/master...HEAD`
- Parsed all `.github/workflows/*.yml` and `.github/workflows/*.yaml` with Python `yaml.safe_load`

Fork push CI on `ranxi2001/karmada:chore/update-github-runner-ubuntu-24`, commit `0f62fd62b05802961447601da9000403139b600d`:

- `Chart`: passed
- `CLI`: passed
- `Operator`: passed
- `CI Workflow`: lint, codegen, compile, and unit test passed; e2e jobs are still running
- `FOSSA`: skipped by workflow condition
- `image-scanning`: skipped by workflow condition

This PR was prepared with AI assistance.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
````

## 下一步

1. 继续观察 upstream PR #7728 CI，不需要再轮询 fork CI。
2. 如果 upstream CI 失败，先判断是 `ubuntu-24.04` 环境差异、Karmada 代码问题、fork 环境差异还是 e2e flake。
3. 如果 reviewer 要求补充依据，可引用 #3699 和 runner-images #14254。
4. 不在当前 `intern` 分支混入 upstream workflow 改动；代码分支保持在 `/tmp/karmada-ci-ubuntu24`。
