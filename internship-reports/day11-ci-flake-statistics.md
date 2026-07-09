# Day 11：Karmada CI Flake 专项统计

日期：2026-07-09

## 目标与结论

mentor 要求统计 Karmada CI flake 情况。本报告不把所有失败都算成 flake，而是优先找“有证据说明失败不是业务代码引入”的高置信样本，并整理成后续能推进 issue / PR 的台账。

当前结论：

- 统计窗口内 upstream Actions 共覆盖 598 条 run，其中 32 条失败；失败主要集中在 e2e / setup / Kubernetes test。
- 已确认或高置信 flake 有 3 类、4 个 upstream 样本；另有 1 个个人 fork CI 补充样本。
- 这 3 类都有 issue 或 PR 链路：#7719、#5323、#6841 / #7388、#7697、#7728。
- 当前最适合直接推进的是 #7719：有独立 issue、本地 diagnostic、候选修复和 fork CI 证据。

> 分析：这里的“失败率”不是“flake 率”。失败可能来自真实代码问题、release publish、lint、chart template、CI 环境或 e2e 时序问题。只有满足明确证据的失败，才进入“高置信 flake”。

## 简化口径

| 项目 | 本报告口径 |
| --- | --- |
| 统计仓库 | [`karmada-io/karmada`](https://github.com/karmada-io/karmada) |
| 时间窗口 | `2026-06-26 00:00 UTC` 到 `2026-07-09` |
| 数据来源 | GitHub Actions run / job metadata，必要时补 job log 和 artifact |
| 覆盖数量 | 598 条 upstream Actions run |
| 高置信 flake | 同一变更 rerun 或空提交 trigger 后转绿；或失败与 PR diff 无关，并落在已知 e2e 异步等待 / control-plane transient 边界 |
| 暂不计入 flake | lint、release publish、chart template、image scan，或缺少日志只能看到 job 失败的样本 |

个人 fork push CI 不计入 upstream 598 条 run 的总量统计；只在能补强同类现象时作为“补充样本”记录。

## 关键数字

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| Upstream Actions runs | 598 | 本窗口实际覆盖数量 |
| Failed runs | 32 | run 级失败，不等于 flake |
| 非成功 job rows | 72 | 从失败 run 展开后的 job 行数 |
| e2e / setup / Kubernetes test job rows | 56 | 本次分析重点 |
| 高置信 flake 类型 | 3 | FlinkDeployment、Remedy、control-plane transient |
| 高置信 upstream 样本 | 4 | 都有 issue / PR 链路 |
| fork CI 补充样本 | 1 | `test/flinkdeployment-crd-cleanup` v1.34 control-plane transient |
| rerun / trigger 后直接转绿样本 | 5 | 2 个 upstream 原生 rerun，2 个空提交 trigger，1 个 fork job rerun |

失败集中度：

- 按 workflow 看，失败最多的是 `CI Workflow`，共 16 条 failed run。
- 按 job 类型看，e2e / setup / Kubernetes test 有 56 行非成功 job，是主要噪声来源。
- schedule 相关失败有 37 行 e2e / setup / Kubernetes test job，说明只看 PR CI 不足以判断 master 稳定性。

## Rerun / Trigger 证据

这部分只回答一个问题：是否存在“没有业务代码修复，重跑或空提交后直接转绿”的证据。

| 类型 | 数量 | 样本 | 结论 |
| --- | ---: | --- | --- |
| GitHub 原生 rerun 后转绿 | 2 | [`28212061472`](https://github.com/karmada-io/karmada/actions/runs/28212061472)、[`28256528352`](https://github.com/karmada-io/karmada/actions/runs/28256528352) | 可作为 e2e / Kubernetes test transient 证据 |
| 空提交 trigger 后转绿 | 2 | [`#7697`](https://github.com/karmada-io/karmada/pull/7697) 的 [`93eaf7e`](https://github.com/ranxi2001/karmada/commit/93eaf7e57515c959fe30fa2aba387ce10029046d)、[`#7728`](https://github.com/karmada-io/karmada/pull/7728) 的 [`de3b6be`](https://github.com/ranxi2001/karmada/commit/de3b6be675bbf8ad12f91052f7d0fb53c5b592a5) | 两个空提交均为 `files=0/additions=0/deletions=0`，后续 CI 全绿 |
| fork job rerun 后转绿 | 1 | `test/flinkdeployment-crd-cleanup` 的 [`run 29006012630`](https://github.com/ranxi2001/karmada/actions/runs/29006012630) attempt 2 | 不计入 upstream 598 条 run 总数，但证明该 fork validation failure 是 transient |
| 原生 rerun 但不算 flake | 8 | workflow approval、release 失败、cancelled 等 | 不用于证明 e2e flake |

> 分析：原生 rerun 和空提交 trigger 的意义不同，但都能证明“这次失败不一定需要代码修复”。#7697 和 #7728 的空提交尤其有价值，因为 commit API 确认没有文件变更。

## 已确认或高置信 Flake

### 1. FlinkDeployment / estimator ResourceBinding 等待超时

相关 issue：

- [`#7719 FlinkDeployment e2e cleanup can leave stale APIEnablements`](https://github.com/karmada-io/karmada/issues/7719)，open，`kind/flake`

证据：

| 时间 | Run / Job | 关联 PR | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-01 | [`run 28499042349 / job 84472927003`](https://github.com/karmada-io/karmada/actions/runs/28499042349/job/84472927003) | [`#7697`](https://github.com/karmada-io/karmada/pull/7697) | `[EstimatorAssumption] ResourceQuota plugin assumption testing` 等待 `FlinkDeployment` 对应 `ResourceBinding` 超时 |
| 2026-07-09 | [`run 28998390044 / job 86054168911`](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911) | [`#7728`](https://github.com/karmada-io/karmada/pull/7728) merge 后 master push | `[EstimatorAssumption] NodeResource plugin assumption testing` 等待多个 `flinkdeployment-*-flinkdeployment` 的 `ResourceBinding` 出现超时 |

日志特征：

- `resourcebindings.work.karmada.io "...-flinkdeployment" not found`
- `Timed out after 420.000s` 或 `420.001s`
- 失败点落在 `test/e2e/framework/resourcebinding.go:47`

当前判断：

- 高置信 e2e timing flake。
- #7697 同一提交 rerun 后全绿，说明不是证书轮换代码路径导致。
- #7719 已经记录更完整的原因：FlinkDeployment CRD cleanup 只等 CRD object，未同步等待 `Cluster.Status.APIEnablements` 收敛，可能让下一轮 estimator test 看到过期 API 状态。
- 当前修复分支为 `test/flinkdeployment-crd-cleanup`，commit `1240559dd34cc0eedd0ec6cffe97b5c0076660dc`；本地 `git diff --check` 和 focused `go test` 已通过。第一次 fork CI 只在 v1.34 命中另一类 control-plane transient flake，rerun 后通过，最终 fork push CI 全绿。

### 2. Remedy 删除后 `TrafficControl` 未从 Cluster status 收敛

相关 issue：

- [`#5323 [flaky test] remedy testing test with nil decision matches remedy ...`](https://github.com/karmada-io/karmada/issues/5323)，closed，`kind/flake`

证据：

| 时间 | Run / Job | 关联 PR | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-09 | [`run 28998390044 / job 86054168903`](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168903) | [`#7728`](https://github.com/karmada-io/karmada/pull/7728) merge 后 master push | `remedy testing test with nil decision matches remedy / Create an immediately type remedy, then remove it` 超时 |

日志特征：

- `Cluster(member1) remedyActions: map[TrafficControl:{}]` 重复出现
- `Timed out after 420.000s`
- 失败点落在 `test/e2e/framework/cluster.go:318`

当前判断：

- 高置信 e2e flake，且和历史 issue #5323 标题完全匹配。
- #5323 关闭时认为“maybe has been fixed”，但 2026-07-09 master push CI 中同名用例重新出现。
- 建议先继续收集第二次复现。如果再次出现，可新开 issue 或在 #5323 下补充复现链接，请 maintainer 决定 reopen 还是新建 tracking issue。

### 3. Aggregated API / control plane 短暂不可用导致多用例连锁失败

相关 issue：

- 可先挂到 [`#6841 Flaky E2E tests – tracking intermittent failures`](https://github.com/karmada-io/karmada/issues/6841)
- 与 [`#7388 e2e: Multiple tests failing exclusively on Kubernetes v1.35.0`](https://github.com/karmada-io/karmada/issues/7388) 有部分现象相似，但本次不是只在 v1.35 长期复现，暂不直接归并。

证据：

| 时间 | Run / Job | 关联 PR | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-08 | [`run 28912823833 / job 85774432012`](https://github.com/karmada-io/karmada/actions/runs/28912823833/job/85774432012) | [`#7728`](https://github.com/karmada-io/karmada/pull/7728) PR CI | `karmadactl get` 读 `clusters.cluster.karmada.io` 返回 `503 ServiceUnavailable`，`karmadactl exec` 超时，`SynchronizedAfterSuite` 也失败 |

补充样本：

| 时间 | Run / Job | 关联分支 | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-09 | [`run 29006012630 / job 86080188511`](https://github.com/ranxi2001/karmada/actions/runs/29006012630/job/86080188511) | fork validation branch `ranxi2001:test/flinkdeployment-crd-cleanup` for [`#7719`](https://github.com/karmada-io/karmada/issues/7719) | `e2e test (v1.34.0)` 中最早硬失败为 `ClusterPropagationPolicy suspend` 更新时报 `etcdserver: request timed out`；随后 Karmada/member API 大量 `connection refused`，FlinkDeployment cleanup 在控制面失稳后超时 |

> 注释：这个样本来自个人 fork push CI，不计入上面 `karmada-io/karmada` 598 条 run 的总量统计；但它复现了同类控制面 transient failure，可作为 PR 前验证阶段的 flake 证据保留。

日志特征：

- `Error from server (ServiceUnavailable): the server is currently unable to handle the request (get clusters.cluster.karmada.io)`
- `timed out waiting for command ... karmadactl ... exec ... echo hello`
- `Summarizing 5 Failures`
- `etcdserver: request timed out`
- `dial tcp ...: connect: connection refused`
- `leader election lost`

补充证据：

- Day 10 artifact 分析里看到同一时间段 etcd `DeadlineExceeded`、aggregated apiserver 停止 serving 后重启恢复。
- #7728 只改 workflow runner label；同一 PR 后续 rerun 全绿。
- `test/flinkdeployment-crd-cleanup` 第一次 fork CI attempt 中 lint、codegen、compile、unit、e2e v1.35、e2e v1.36 均通过；只有 e2e v1.34 失败。artifact 显示 `09:26:12-09:26:19` 多个控制面容器退出，`karmada-controller-manager` 记录 `leader election lost`，之后才出现 FlinkDeployment cleanup timeout。失败 job `86080188511` rerun 后，attempt 2 的 job `86098566248` 已通过，整个 fork push CI 最终 success。

当前判断：

- 高置信 CI 资源或 control-plane transient flake，不是 Ubuntu 24.04 runner 升级的确定性失败。
- 若后续再次出现，应该单独统计 “aggregated apiserver / etcd transient 503” 类别，不能只归到某个 e2e 用例名。
- fork validation branch 上的样本不应直接修改 Day 11 的 upstream 失败率数字，但可以作为“PR 前 CI 也会命中同类控制面失稳”的补充证据。

## 疑似 Flake / 待补日志

### 1. setup e2e / setup operator e2e test environment

相关历史：

- [`#3667 Flaking test: setup e2e test environment`](https://github.com/karmada-io/karmada/issues/3667)
- [`#3682 fix: repair flaking test job of setup e2e test environment`](https://github.com/karmada-io/karmada/pull/3682)
- [`#3699 upgrade CI ubuntu image`](https://github.com/karmada-io/karmada/pull/3699)

本轮样本：

| 时间 | Workflow / Job | Run / Job | 关联 PR / 分支 | 当前证据 |
| --- | --- | --- | --- | --- |
| 2026-07-06 | CI Workflow / `e2e test (v1.34.0)` | [`run 28818641938 / job 85466088131`](https://github.com/karmada-io/karmada/actions/runs/28818641938/job/85466088131) | [`#7721`](https://github.com/karmada-io/karmada/pull/7721) | `setup e2e test environment` step 失败，日志需补 artifact |
| 2026-07-07 | Operator / `Test on Kubernetes (v1.35.0)` | [`run 28863480122 / job 85607622872`](https://github.com/karmada-io/karmada/actions/runs/28863480122/job/85607622872) | [`#7721`](https://github.com/karmada-io/karmada/pull/7721) | `setup operator e2e test environment` step 失败，日志需补 artifact |
| 2026-07-06 | Operator / `Test on Kubernetes (v1.34.0)` | [`run 28761483062 / job 85277656027`](https://github.com/karmada-io/karmada/actions/runs/28761483062/job/85277656027) | master push after [`#7716`](https://github.com/karmada-io/karmada/pull/7716) | setup step 失败，日志需补 artifact |
| 2026-06-28 | CLI / `Test on Kubernetes (v1.36.1)` | [`run 28322104916 / job 83905699582`](https://github.com/karmada-io/karmada/actions/runs/28322104916/job/83905699582) | [`#7678`](https://github.com/karmada-io/karmada/pull/7678) | `setup init e2e test environment` step 失败，日志需补 artifact |

当前判断：

- 这类失败很可能属于环境准备 flake，但本轮通过 `gh` 取到的日志不足，不能直接写确定原因。
- 下一步要从 Actions UI 下载 artifacts 或重新拉日志，重点看 kind cluster create、image pull、disk pressure、Docker build、kube-apiserver readiness。

### 2. Schedule workflow 大量 e2e matrix 失败

本轮 schedule 失败集中在：

- `CI Schedule Workflow`：4 个 run，17 个 e2e job 失败，覆盖 v1.27.3、v1.28.0、v1.29.0、v1.30.0、v1.31.0。
- `APIServer compatibility`：4 个 run，20 个 e2e job 失败，覆盖 `master`、`release-1.16`、`release-1.17`、`release-1.18` 与多个 Kubernetes version 组合。

代表性 run：

| Workflow | Run | 失败 job 概况 | 关联 issue |
| --- | --- | --- | --- |
| CI Schedule Workflow | [`28297782357`](https://github.com/karmada-io/karmada/actions/runs/28297782357) | v1.27.3 / v1.28.0 / v1.29.0 / v1.30.0 / v1.31.0 e2e failed | [`#6841`](https://github.com/karmada-io/karmada/issues/6841) |
| CI Schedule Workflow | [`28750372834`](https://github.com/karmada-io/karmada/actions/runs/28750372834) | v1.27.3 / v1.28.0 / v1.29.0 / v1.30.0 e2e failed | [`#6841`](https://github.com/karmada-io/karmada/issues/6841) |
| APIServer compatibility | [`28300711541`](https://github.com/karmada-io/karmada/actions/runs/28300711541) | v1.27.3 master、v1.30.0 master / release branches failed | [`#6841`](https://github.com/karmada-io/karmada/issues/6841) |
| APIServer compatibility | [`28753707990`](https://github.com/karmada-io/karmada/actions/runs/28753707990) | v1.28.0 / v1.30.0 / v1.32.0 compatibility matrix failed | [`#6841`](https://github.com/karmada-io/karmada/issues/6841) |

当前判断：

- schedule 失败数量多，是 mentor 值得关注的 CI 稳定性信号。
- 但缺少 Ginkgo failure summary，不能把这些失败直接归到具体 spec 或具体 PR。
- #6841 是当前最合适的 umbrella；#7388 只适合作为 “v1.35-only compatibility regression” 的历史对照，不应强行套到所有 schedule 失败。

## 暂不归为 Flake 的失败

| 类型 | 样本 | 判断 |
| --- | --- | --- |
| lint | [`run 28706816762 / job 85133752460`](https://github.com/karmada-io/karmada/actions/runs/28706816762/job/85133752460)、[`run 28410342955 / job 84181794733`](https://github.com/karmada-io/karmada/actions/runs/28410342955/job/84181794733) | 更可能是代码静态检查或格式问题，不按 flake 统计 |
| Chart template | [`run 28369536076 / job 84043597099`](https://github.com/karmada-io/karmada/actions/runs/28369536076/job/84043597099) | `Run chart-testing (template)` 失败，需看 PR diff，不直接归 e2e flake |
| Release publish / upload | `v1.19.0-alpha.1` release 相关 runs `28418213942`、`28418213914`、`28418214110` | release 资产构建、上传、发布链路问题，不是 e2e flake |
| Image scanning | [`run 28307314200 / job 83865734420`](https://github.com/karmada-io/karmada/actions/runs/28307314200/job/83865734420) | Dockerfile build / image scan 路径，暂不纳入 e2e flake |

## 相关 PR / Issue 台账

| 编号 | 类型 | 状态 | 关系 |
| --- | --- | --- | --- |
| [`#6841`](https://github.com/karmada-io/karmada/issues/6841) | issue | open, `kind/flake` | umbrella：间歇性 e2e failures 追踪；schedule 失败和 aggregated API 503 可先归到这里 |
| [`#7388`](https://github.com/karmada-io/karmada/issues/7388) | issue | open, `kind/flake` | v1.35.0 专项环境 / 兼容性失败历史；本轮 #7728 PR CI v1.35 transient failure 可作为相似现象参考 |
| [`#7719`](https://github.com/karmada-io/karmada/issues/7719) | issue | open, `kind/flake` | FlinkDeployment cleanup / stale APIEnablements；本轮最高价值、最可推进的 flake 修复方向 |
| [`#7691`](https://github.com/karmada-io/karmada/issues/7691) | issue | open, `kind/flake` | ClusterResourceBinding cleanup 前缺少 propagation synchronization；同类异步等待问题 |
| [`#7692`](https://github.com/karmada-io/karmada/pull/7692) | PR | open, `kind/flake`, `kind/failing-test` | 修复 #7691，增加 cleanup 前 member cluster `ClusterRole` present 等待；可作为 #7719 修复模式参考 |
| [`#5323`](https://github.com/karmada-io/karmada/issues/5323) | issue | closed, `kind/flake` | Remedy 同名用例历史 flake；2026-07-09 master push CI 疑似复现 |
| [`#3667`](https://github.com/karmada-io/karmada/issues/3667) | issue | closed, `kind/flake` | setup e2e test environment 历史 flake |
| [`#3682`](https://github.com/karmada-io/karmada/pull/3682) | PR | merged, `kind/flake` | 历史 setup e2e repair |
| [`#3699`](https://github.com/karmada-io/karmada/pull/3699) | PR | merged, `kind/flake` | 历史 Ubuntu runner 升级，用于解决当时 kind / e2e CI flake |
| [`#5263`](https://github.com/karmada-io/karmada/pull/5263) | PR | merged, `kind/flake` | e2e 失败后打印 binding 和相关对象，说明社区已经在补 flake 可观测性 |
| [`#4427`](https://github.com/karmada-io/karmada/pull/4427) | PR | merged, `kind/flake` | 单个 k8s version e2e 失败时避免整个 CI fast fail，方便收集更多 matrix 信号 |
| [`#7697`](https://github.com/karmada-io/karmada/pull/7697) | PR | open | 证书轮换 PR；曾命中 FlinkDeployment flake，后来同 commit rerun 通过，是 #7719 的重要证据 |
| [`#7728`](https://github.com/karmada-io/karmada/pull/7728) | PR | merged | Ubuntu 24.04 runner 升级；PR CI rerun 全绿，merge 后 master push 命中 Remedy + Flink 两个 e2e flake |

## 当前结论

1. 近期失败的主要体感来自 e2e，而不是 lint / unit / compile。
2. 能确认到具体原因的高价值 flake 有三类：FlinkDeployment estimator 等待超时、Remedy status cleanup 超时、aggregated API / etcd transient 503。
3. 原生 rerun 后直接转绿的 upstream 样本有 2 条，空提交 trigger CI 后直接转绿的高置信样本有 2 个：#7697 和 #7728；另有 1 个 fork validation job rerun 后转绿的补充样本。
4. #7719 是最适合马上推进的修复项：已有 issue、日志证据、本地 diagnostic、候选修复和最终全绿的 fork push CI；第一次 fork CI 的 v1.34 control-plane transient failure 已单独归类。
5. Remedy 复现与历史 #5323 高度一致，但目前只有 1 次新样本，建议继续观察或补第二次样本再发 upstream。
6. schedule workflow 失败数量大，但根因证据不足；下一轮专项应优先下载 artifacts，把 schedule 的 37 个失败 job 归并到具体 Ginkgo spec 或 setup 阶段。

## 下一步

- 准备开 #7719 的独立 upstream PR，避免继续只停留在统计。
- 对 `run 28998390044 / job 86054168903` 的 Remedy 失败保留链接；如果一周内再次出现，准备英文 issue/comment，引用 #5323。
- 补 schedule workflow artifacts：优先最近两次 `CI Schedule Workflow` 和 `APIServer compatibility`，按 spec 名称聚类。
- 若 mentor 需要每周统计，沉淀脚本到 `.agents/skills/karmada-pr-management/` 或单独 `ci-flake-triage` skill，自动输出 run/job/spec/issue 映射。
- 不在 upstream issue 里一次性贴太多未经确认的推测；发评论前先把英文文本给用户确认。

## 附录：数据获取方式

正文只保留结论和关键数字；这里记录复查入口。

中间文件：

- `/tmp/karmada-actions-all-1000-20260626-20260709.json`
- `/tmp/karmada-actions-failures-20260626-20260709.json`
- `/tmp/karmada-failed-jobs-clean-20260626-20260709.tsv`
- `/tmp/karmada-flake-keylines-20260626-20260709.txt`

核心命令：

```bash
gh run list --repo karmada-io/karmada \
  --created '>=2026-06-26' \
  --limit 1000 \
  --json databaseId,name,displayTitle,event,headBranch,headSha,status,conclusion,createdAt,updatedAt,url

gh run list --repo karmada-io/karmada \
  --created '>=2026-06-26' \
  --status failure \
  --limit 200 \
  --json databaseId,name,displayTitle,event,headBranch,headSha,status,conclusion,createdAt,updatedAt,url

gh run view <run-id> --repo karmada-io/karmada --json jobs
gh run view <run-id> --repo karmada-io/karmada --job <job-id> --log
```

限制：

- 部分较早的 job 日志通过 `gh run view --job --log` 返回空内容，只能基于 workflow / job / step metadata 归类。
- schedule workflow 的失败不绑定具体 PR diff，只能作为 master 分支持续稳定性的信号。
- release、publish、lint、chart template 失败保留在总失败统计里，但不直接计入 e2e flake。
