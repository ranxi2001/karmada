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

## Upstream PR #7728 CI 跟进

PR #7728 当前只有一个失败项：

- run：[`28912823833`](https://github.com/karmada-io/karmada/actions/runs/28912823833)
- job：[`CI Workflow / e2e test (v1.35.0)`](https://github.com/karmada-io/karmada/actions/runs/28912823833/job/85774432012)
- head SHA：`0f62fd62b05802961447601da9000403139b600d`

其他同一 PR check 状态：

- `CI Workflow`：`lint`、`codegen`、`compile`、`unit test`、`e2e test (v1.34.0)`、`e2e test (v1.36.1)` 均通过。
- `Chart` / `CLI` / `Operator` 的 Kubernetes `v1.34.0`、`v1.35.0`、`v1.36.1` 矩阵均通过。
- `DCO` 通过。

失败摘要：

- Ginkgo summary：`Ran 169 of 273 Specs in 747.440 seconds`，`165 Passed | 4 Failed | 104 Skipped`，最终 `Interrupted by Other Ginkgo Process`。
- 主要失败：
  - `Karmadactl exec testing / Test exec command`，`test/e2e/suites/base/karmadactl_test.go:561`。
  - `Karmadactl get testing / should return not found error for non-existing namespace`，`test/e2e/suites/base/karmadactl_test.go:977`。
  - `SynchronizedAfterSuite` cleanup，`test/e2e/suites/base/suite_test.go:212`。
  - `CronFederatedHPA` 和 `OverrideRules` 是其他 Ginkgo 进程失败后的 interrupted 项，不是最早根因。

关键现象：

- `karmadactl exec` 在 `02:51:18` 对 `member1` 上的 `pod-pr276` 执行 `echo hello` 超时，stderr 只显示默认容器选择：`Defaulted container "nginx" out of: nginx, busybox`。
- `karmadactl get` 期望拿到 namespace not found，但实际返回 `ServiceUnavailable`：`the server is currently unable to handle the request (get clusters.cluster.karmada.io)`。
- `SynchronizedAfterSuite` 清理 cluster label 时同样因为读取 `clusters.cluster.karmada.io member1` 返回 `503 ServiceUnavailable` 失败。

控制面日志对齐：

- `02:51:14` 起，host `kube-apiserver` 开始出现 etcd `DeadlineExceeded`、`http: Handler timeout` 和 `etcdserver: request timed out`。
- `02:51:15` 起，两个 `karmada-aggregated-apiserver` 副本持续出现访问 `etcd-client.karmada-system.svc.cluster.local:2379` 的 `DeadlineExceeded`。
- `02:51:38` 左右，两个 `karmada-aggregated-apiserver` 副本都停止 serving：
  - `Stopped listening on 10.244.0.7:443`
  - `Stopped listening on 10.244.0.8:443`
- 新的 aggregated apiserver 副本随后恢复：
  - `02:52:21`：`ztlgt` 重新启动并 `Adding GroupVersion cluster.karmada.io v1alpha1`
  - `02:52:24`：`c5pdw` 重新启动并 `Adding GroupVersion cluster.karmada.io v1alpha1`
- `karmada-apiserver` 同一窗口报 `v1alpha1.cluster.karmada.io` APIService 503 / connection refused，解释了 `clusters.cluster.karmada.io` 读请求失败。

伴随发现：

- `karmadactl exec` 超时路径触发 Go race detector 报告，位置在 `test/e2e/framework/karmadactl.go:148`：timeout 分支 kill 进程后立即格式化 `cmd.Stdout` / `cmd.Stderr`，而 `cmd.Wait()` 相关 goroutine 仍可能在写 `bytes.Buffer`。
- 该 race 更像是 timeout 后暴露的 test helper 问题；本 PR 没有改 Go 代码、测试代码或 `karmadactl` 行为，且其他 e2e 矩阵通过，因此不应把它直接归因于 runner label diff。

当前判断：

这次失败更像 CI 资源压力下的 e2e/control-plane flake：etcd 响应超时 -> apiserver handler timeout -> aggregated apiserver 副本重启 -> `cluster.karmada.io` aggregated API 短暂 503 -> `karmadactl get` / cleanup 失败。`ubuntu-24.04` 可能改变 runner 底层资源/内核/容器运行时表现，但当前证据不足以证明 PR 引入确定性兼容性问题。

建议处理：

1. 不改 workflow PR 代码。
2. 优先 rerun failed job；如果没有 upstream rerun 权限，可在用户确认后向 PR 分支推一个 signed-off 空提交重新触发 CI。
3. 如果 rerun 再次集中失败在 `v1.35.0` e2e 且仍是 etcd / aggregated apiserver 503，需要升级为 Ubuntu 24.04 runner 环境差异调查。
4. 不要直接在 PR 下发 upstream 评论或 push 更新，除非用户先确认具体动作和英文文本。

权限确认：

- `gh run rerun 28912823833 --repo karmada-io/karmada --failed` 返回：`run 28912823833 cannot be rerun; its workflow file may be broken`
- `gh run rerun --repo karmada-io/karmada --job 85774432012` 返回：`job 85774432012 cannot be rerun`
- REST API `POST /repos/karmada-io/karmada/actions/jobs/85774432012/rerun` 返回 `403 Must have admin rights to Repository`

结论：当前账号不能直接重跑 upstream failed job。若需要继续验证，只能请维护者 rerun，或由我们向 PR 分支推 signed-off 空提交触发新一轮 PR CI。

## 空提交触发新一轮 CI

用户确认后，已向 PR 分支推送 signed-off 空提交：

- branch：`ranxi2001/karmada:chore/update-github-runner-ubuntu-24`
- commit：`de3b6be675bbf8ad12f91052f7d0fb53c5b592a5`
- commit message：`test: trigger ci`
- diff：空提交，无文件变更

触发结果：

- PR #7728 head 已更新为 `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5`。
- upstream PR CI 已开始，`CI Workflow`、`Chart`、`CLI`、`Operator` 矩阵处于 queued / in_progress。
- fork push CI 也已开始：
  - `CI Workflow` run `28915975049`
  - `Chart` run `28915975027`
  - `CLI` run `28915975040`
  - `Operator` run `28915975026`
  - `FOSSA` run `28915975012`
  - `image-scanning` run `28915975025`，已 skipped

下一步：观察 `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5` 对应的 upstream PR checks，重点看 `CI Workflow / e2e test (v1.35.0)` 是否再次失败。

## PR body 更新草稿

用途：原 PR body 仍写着 fork push CI 的 e2e jobs are still running。原实现提交 `0f62fd62b05802961447601da9000403139b600d` 的 fork push CI 已完成，需要把 validation 段更新为最终状态，并说明最新 `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5` 是空提交，仅用于重触发 PR CI。

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

Fork push CI on `ranxi2001/karmada:chore/update-github-runner-ubuntu-24`, implementation commit `0f62fd62b05802961447601da9000403139b600d`:

- `CI Workflow`: passed, including lint, codegen, compile, unit test, and e2e tests on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `Chart`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `CLI`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `Operator`: passed on Kubernetes v1.34.0, v1.35.0, and v1.36.1
- `FOSSA`: skipped by workflow condition
- `image-scanning`: skipped by workflow condition

The latest PR head `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5` is a signed-off empty commit used only to retrigger pull request CI after an isolated e2e failure; it does not change the diff.

This PR was prepared with AI assistance.

**Does this PR introduce a user-facing change?**:

```release-note
NONE
```
````

更新结果：

- 用户确认后已更新 PR #7728 body。
- `gh pr edit 7728 --repo karmada-io/karmada --body-file internship-reports/pr7728-updated-body.md` 因当前 token 缺少 `read:org` scope，在 GraphQL 查询 PR 元信息时失败。
- 改用 REST API 成功更新：`gh api repos/karmada-io/karmada/pulls/7728 -X PATCH -F body=@internship-reports/pr7728-updated-body.md`。
- 更新后的 PR body 已包含原实现提交 `0f62fd62b05802961447601da9000403139b600d` 的完整 fork push CI 结果，并说明最新 `de3b6be675bbf8ad12f91052f7d0fb53c5b592a5` 是 signed-off empty commit，仅用于重触发 PR CI，不改变 diff。

## 维护者 follow-up：dashboard 仓库

PR #7728 收到维护者 `@RainbowMango` 评论：

- comment：<https://github.com/karmada-io/karmada/pull/7728#issuecomment-4911205082>
- 内容：感谢更新，并指出 `karmada-io/dashborad` repo 里仍有一些 workflow 使用 Ubuntu 22，欢迎继续更新。

核对结果：

- 评论中的 `karmada-io/dashborad` 应为拼写错误；GitHub 上不存在该仓库。
- 实际仓库是 [`karmada-io/dashboard`](https://github.com/karmada-io/dashboard)，默认分支 `main`，描述为 `Web UI for Karmada`。
- 当前没有搜到与 `ubuntu-22.04` / `ubuntu-24.04` 相关的 open PR 或 open issue。
- `ranxi2001/dashboard` fork 当前不存在，若要提交 follow-up PR，需要先 fork dashboard 仓库。

`karmada-io/dashboard` 仍有 18 处 `runs-on: ubuntu-22.04`，分布在 6 个 workflow 文件：

- `.github/workflows/ci.yml`：5 处
- `.github/workflows/codeql-analysis.yml`：1 处
- `.github/workflows/dockerhub-latest-chart.yml`：1 处
- `.github/workflows/dockerhub-released-chart.yml`：1 处
- `.github/workflows/dockerhub-latest-image.yml`：5 处
- `.github/workflows/dockerhub-released-image.yml`：5 处

判断：

- 这不应混入当前 `karmada-io/karmada` PR #7728，因为是另一个仓库。
- 可以做一个独立 dashboard PR，范围同样应保持为机械替换 `ubuntu-22.04` -> `ubuntu-24.04`，并复用 #7728 的 rationale。
- dashboard 的 `.github/workflows/ci.yml` 同样支持 fork push 触发 CI，因此可先 fork `karmada-io/dashboard` 到 `ranxi2001/dashboard`，推送 topic branch，等待 fork push CI 后再开 upstream PR。

可回复维护者的英文草稿：

```md
Thanks for pointing this out. I checked that the remaining `ubuntu-22.04` usages are in `karmada-io/dashboard`; I will handle them in a separate dashboard PR.
```

## Dashboard / Website follow-up branches

按用户要求，dashboard 和 website 分别处理，先 fork 再准备独立 PR：

Fork 状态：

- `ranxi2001/dashboard` 已 fork，parent 是 `karmada-io/dashboard`。
- `ranxi2001/website` 已 fork，parent 是 `karmada-io/website`。

Dashboard branch：

- worktree：`/tmp/karmada-dashboard-ubuntu24`
- upstream base：`karmada-io/dashboard main@ad52076`
- fork branch：`ranxi2001/dashboard:chore/update-github-runner-ubuntu-24`
- commit：`8f6ba046914e3e1bcc3a4d94f33912c10e33c64f`
- title draft：`ci: update GitHub runners to Ubuntu 24.04`
- PR body draft：`internship-reports/pr-dashboard-ubuntu24-body.md`

Dashboard changes：

- 6 files changed, 18 insertions(+), 18 deletions(-)
- `.github/workflows/ci.yml`
- `.github/workflows/codeql-analysis.yml`
- `.github/workflows/dockerhub-latest-chart.yml`
- `.github/workflows/dockerhub-latest-image.yml`
- `.github/workflows/dockerhub-released-chart.yml`
- `.github/workflows/dockerhub-released-image.yml`

Dashboard validation：

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`：无输出。
- `git diff --check upstream/main...HEAD`：无输出。
- Python `yaml.safe_load` 解析所有 workflow：通过。
- fork push CI：`CI Workflow` run `28917428886` passed，包含 `lint`、`unit test`、`build-bin`、`build-frontend`、`e2e-frontend (v1.33.0)`、`e2e-frontend (v1.34.0)`、`e2e-frontend (v1.35.0)`。

Website branch：

- worktree：`/tmp/karmada-website-ubuntu24`
- upstream base：`karmada-io/website main@920919d`
- fork branch：`ranxi2001/website:chore/update-github-runner-ubuntu-24`
- commit：`24e7dd4515225a9462b47e04a7ca79285a586964`
- title draft：`ci: update GitHub runners to Ubuntu 24.04`
- PR body draft：`internship-reports/pr-website-ubuntu24-body.md`

Website changes：

- 2 files changed, 2 insertions(+), 2 deletions(-)
- `.github/workflows/crlf-check.yml`
- `.github/workflows/typos.yml`

Website validation：

- `git grep -n "ubuntu-22.04" HEAD -- .github/workflows || true`：无输出。
- `git diff --check upstream/main...HEAD`：无输出。
- Python `yaml.safe_load` 解析所有 workflow：通过。
- `git grep --cached -I $'\r'`：No CRLF line endings found.
- fork push CI：`Typos Check` run `28917428642` passed。
- `CRLF Check` 只在 `pull_request` 触发，当前无法通过 fork push 预跑；本地等价 CRLF 检查已通过。

下一步：

1. 用户确认后，分别向 `karmada-io/dashboard` 和 `karmada-io/website` 创建 upstream PR。
2. PR 创建后，再按用户确认回复 `@RainbowMango` 评论并附上两个 follow-up PR 链接。
3. 不默认发 upstream comment。

## Dashboard / Website PR 创建结果

用户确认后已创建两个独立 upstream PR：

- Dashboard PR：[`karmada-io/dashboard#643`](https://github.com/karmada-io/dashboard/pull/643)
  - title：`ci: update GitHub runners to Ubuntu 24.04`
  - base：`karmada-io/dashboard:main`
  - head：`ranxi2001/dashboard:chore/update-github-runner-ubuntu-24`
  - head SHA：`8f6ba046914e3e1bcc3a4d94f33912c10e33c64f`
  - DCO：passed
  - upstream PR checks：`CI Workflow` 和 `CodeQL` 已开始运行

- Website PR：[`karmada-io/website#1036`](https://github.com/karmada-io/website/pull/1036)
  - title：`ci: update GitHub runners to Ubuntu 24.04`
  - base：`karmada-io/website:main`
  - head：`ranxi2001/website:chore/update-github-runner-ubuntu-24`
  - head SHA：`24e7dd4515225a9462b47e04a7ca79285a586964`
  - DCO：passed
  - upstream PR checks：`CRLF Check` passed；`Typos Check` 和 Netlify checks 正在运行

同时重新核对主仓库 PR：

- Karmada PR：[`karmada-io/karmada#7728`](https://github.com/karmada-io/karmada/pull/7728)
- 新一轮 PR CI 已全绿：lint、codegen、compile、unit、e2e v1.34/v1.35/v1.36，以及 Chart/CLI/Operator 三套 Kubernetes 矩阵全部 passed，DCO passed。

可回复 `@RainbowMango` 的英文草稿，需用户确认后才能发布：

```md
Thanks for the pointer. I opened the follow-up PRs:

- karmada-io/dashboard#643
- karmada-io/website#1036
```

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
