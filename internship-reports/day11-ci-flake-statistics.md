# Day 11：Karmada CI Flake 专项统计

- 报告日期：`2026-07-09`
- 统计窗口：`2026-06-26 00:00 UTC` 至 `2026-07-09`
- 最新状态快照：`2026-07-10 17:08 CST`

> 本报告把“当前该关注什么”放在前面。历史统计口径、PR 文案、详细样本和数据采集过程统一放在附录。

## 一页结论

1. **当前第一优先级是 PR #7732。** #7719 已从 flake 证据推进到修复 PR；代码复查没有发现 correctness finding，核心 lint、unit、e2e v1.34-v1.36 均通过。当前等待 Chart/Operator workflow rerun 收尾和 human `lgtm`/approval。
2. **本窗口确认了 3 类高置信 flake。** 分别是 FlinkDeployment cleanup/APIEnablements 竞态、Remedy status cleanup 超时、aggregated API/etcd 短暂失稳。
3. **失败数量不能直接当成 flake 数量。** 598 条 upstream run 中有 32 条 failed run，但其中还包含真实代码问题、lint、release、chart template 和 image scan；只有 4 个 upstream 样本达到本报告的高置信标准。
4. **下一项最值得补证据的是 schedule workflow。** 已有 37 行 schedule/compatibility e2e 或 setup 非成功 job，但缺少 Ginkgo failure summary，尚不能按 spec 或根因归类。
5. **Remedy 暂不急着发新 issue。** 当前只有一次与历史 #5323 高度一致的新复现；再出现一次时，再准备 reopen 或新 issue 的证据包。

| 关注项 | 当前判断 | 下一动作 |
| --- | --- | --- |
| [`#7732`](https://github.com/karmada-io/karmada/pull/7732) | 修复方向成立，代码复查无 finding；等待 CI rerun 和 human review | 观察 pending checks、`lgtm`、approval，不因无关 CI interruption 改代码 |
| Remedy / [`#5323`](https://github.com/karmada-io/karmada/issues/5323) | 历史 flake 疑似复现一次 | 保留 job 链接；第二次复现后再发社区更新 |
| Schedule / compatibility | 数量多但根因未知 | 下载最近 artifacts，按 Ginkgo spec、setup 阶段和控制面故障聚类 |
| Aggregated API / etcd transient | 高置信环境或控制面瞬时失稳 | 挂到 [`#6841`](https://github.com/karmada-io/karmada/issues/6841) 台账，不修改无关业务代码 |

## 最新关注

### #7719 修复 PR #7732

状态快照：

| 项目 | 状态 |
| --- | --- |
| PR | [`karmada-io/karmada#7732`](https://github.com/karmada-io/karmada/pull/7732)，open，非 draft |
| Head | `1240559dd34cc0eedd0ec6cffe97b5c0076660dc` |
| Merge state | GitHub 显示 mergeable；Tide 仍缺 `approved` / `lgtm` |
| Human review | 暂无 human review；现有 review 来自 bot 和作者回复 |
| 核心 CI | DCO、lint、codegen、compile、unit、e2e v1.34/v1.35/v1.36 已通过 |
| 安装 workflows | 先前取消的 Chart v1.34、Operator v1.35 已触发 workflow rerun；`17:08 CST` 快照下各有一个 job pending |

当前判断：

- 不需要再修改 helper 来回应 Gemini 的 nil pointer 评论；该评论已通过 Gomega 控制流测试证明不成立。
- pending checks 是对先前 cancelled workflows 的重新执行，当前没有指向 `test/e2e/` diff 的失败证据。
- 最小行动是等待 rerun 结束和 human review。只有出现新的、与 diff 相关的失败时才重新进入代码分析。

### Remedy 再次出现

- 样本：[`run 28998390044 / job 86054168903`](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168903)。
- 失败点：删除 Remedy 后，`Cluster.Status.RemedyActions` 中的 `TrafficControl` 长时间不消失。
- 历史关联：closed issue [`#5323`](https://github.com/karmada-io/karmada/issues/5323) 的标题与 spec 路径高度一致。
- 当前动作：继续观察。再次出现时记录 head SHA、Kubernetes 版本、first error 和 rerun 结果，再决定 reopen 还是新建 issue。

### Schedule 与 compatibility 失败

- 统计窗口内有 37 行 schedule/compatibility e2e 或 setup 非成功 job。
- 当前数据只能说明“稳定性信号明显”，不能说明 37 行都是 flake，也不能归因到同一个根因。
- 下一步优先下载最近两次 `CI Schedule Workflow` 和 `APIServer compatibility` artifacts，提取 Ginkgo failure summary、first hard failure 和 control-plane logs。

### 持续更新触发条件

只在以下事件发生时更新报告正文：

- #7732 checks、review、labels 或 state 发生变化。
- Remedy spec 再次复现。
- schedule/compatibility artifacts 已能归到具体 spec 或 setup 根因。
- 新一周统计窗口完成，关键数字发生变化。

普通 queued/running 波动、无日志的单个 cancelled job、与 diff 无关的 bot 评论不单独扩写正文。

## 已确认或高置信 Flake

### 1. FlinkDeployment / estimator ResourceBinding 等待超时

| 时间 | Run / Job | 关联 PR | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-01 | [`run 28499042349 / job 84472927003`](https://github.com/karmada-io/karmada/actions/runs/28499042349/job/84472927003) | [`#7697`](https://github.com/karmada-io/karmada/pull/7697) | ResourceQuota assumption 用例等待 FlinkDeployment `ResourceBinding` 超时 |
| 2026-07-09 | [`run 28998390044 / job 86054168911`](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168911) | [`#7728`](https://github.com/karmada-io/karmada/pull/7728) merge 后 master push | NodeResource assumption 用例反复找不到多个 FlinkDeployment `ResourceBinding` |

关键证据：

- scheduler 曾报告 `member1` missing `flink.apache.org/v1beta1/FlinkDeployment` API。
- 本地 diagnostic 证明旧 cleanup 在 control plane CRD 消失后即可返回，此时 member CRD 和 `Cluster.Status.APIEnablements` 仍可能保留数秒。
- #7697 没有修改 estimator/Flink 路径，同一代码通过空提交重触发后全绿。
- #7728 只改 runner label，PR CI 全绿，合并后的独立 master push 再次命中同类 Flink timeout。

结论：高置信 e2e timing flake。跟踪 issue 为 [`#7719`](https://github.com/karmada-io/karmada/issues/7719)，修复 PR 为 [`#7732`](https://github.com/karmada-io/karmada/pull/7732)。

### 2. Remedy status cleanup 超时

| 时间 | Run / Job | 失败表现 |
| --- | --- | --- |
| 2026-07-09 | [`run 28998390044 / job 86054168903`](https://github.com/karmada-io/karmada/actions/runs/28998390044/job/86054168903) | `remedy testing ... Create an immediately type remedy, then remove it` 等待 `TrafficControl` 从 cluster status 消失超时 |

日志特征：

- `Cluster(member1) remedyActions: map[TrafficControl:{}]` 重复出现。
- `Timed out after 420.000s`。
- 失败点为 `test/e2e/framework/cluster.go:318`。

结论：与历史 [`#5323`](https://github.com/karmada-io/karmada/issues/5323) 高度一致，但本窗口只有一次新样本，先观察第二次复现。

### 3. Aggregated API / control plane transient

| 时间 | Run / Job | 关联变更 | 失败表现 |
| --- | --- | --- | --- |
| 2026-07-08 | [`run 28912823833 / job 85774432012`](https://github.com/karmada-io/karmada/actions/runs/28912823833/job/85774432012) | #7728 PR CI | `clusters.cluster.karmada.io` 返回 503，`karmadactl exec` 超时，AfterSuite 连锁失败 |
| 2026-07-09 | [`fork run 29006012630 / job 86080188511`](https://github.com/ranxi2001/karmada/actions/runs/29006012630/job/86080188511) | #7732 fork validation | `etcdserver: request timed out` 后出现 API connection refused、leader election lost 和 cleanup 连锁超时 |

关键证据：

- 最早硬失败来自 etcd/control-plane，而不是后续报错的业务 spec。
- 同一 run 中出现 aggregated apiserver 停止 serving、多控制面容器退出和 API connection refused。
- #7728 rerun 后通过；#7732 fork v1.34 failed job 在 attempt 2 通过。

结论：高置信 CI 资源或 control-plane transient flake。fork 样本不计入 upstream 598 条 run 的统计总数，只用于补强分类证据。

## 持续关注台账

| 编号 | 状态 | 本报告中的作用 | 下一检查点 |
| --- | --- | --- | --- |
| [`#7732`](https://github.com/karmada-io/karmada/pull/7732) | open, `kind/flake` | 当前首要修复 PR | checks 完成、human `lgtm`/approval、merge state |
| [`#7719`](https://github.com/karmada-io/karmada/issues/7719) | open, `kind/flake` | Flink cleanup/APIEnablements 根因与证据入口 | 随 #7732 合并状态更新 |
| [`#5323`](https://github.com/karmada-io/karmada/issues/5323) | closed | Remedy 同名历史 flake | 第二次新复现后决定 reopen/new issue |
| [`#6841`](https://github.com/karmada-io/karmada/issues/6841) | open, `kind/flake` | e2e 间歇失败 umbrella | schedule/control-plane 新样本归档 |
| [`#7388`](https://github.com/karmada-io/karmada/issues/7388) | open, `kind/flake` | v1.35 环境/兼容性历史参照 | 仅在失败持续集中于 v1.35 时关联 |
| [`#7692`](https://github.com/karmada-io/karmada/pull/7692) | open | 同类异步同步屏障参考 | 不与 #7732 重复实现 |
| [`#7697`](https://github.com/karmada-io/karmada/pull/7697) | open | 第一次 Flink failure 和空提交转绿证据 | 不把 flake 修复混入证书 PR |
| [`#7728`](https://github.com/karmada-io/karmada/pull/7728) | merged | runner 更新与第二次 Flink/Remedy 样本 | 只作为历史证据，不归因给 runner label |

## 附录 A：统计口径与关键数字

### 统计口径

| 项目 | 口径 |
| --- | --- |
| 仓库 | [`karmada-io/karmada`](https://github.com/karmada-io/karmada) |
| 时间窗口 | `2026-06-26 00:00 UTC` 至 `2026-07-09` |
| 数据源 | GitHub Actions run/job metadata，必要时补 job log 和 artifact |
| 高置信 flake | rerun/空提交后转绿；或 failure 与 diff 无关并落在已验证的异步等待、control-plane transient 边界 |
| 不直接计入 | lint、release、chart template、image scan，或只有失败状态而没有日志的样本 |

> “Failed run 比例”不是“flake 率”。本报告只把证据足够的样本列为高置信 flake。

### 关键数字

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| Upstream Actions runs | 598 | 统计窗口覆盖总量 |
| Failed runs | 32 | run 级失败，不等于 flake |
| 非成功 job rows | 72 | 从失败 run 展开后的 job 行数 |
| e2e/setup/Kubernetes test rows | 56 | 主要分析对象 |
| Schedule/compatibility rows | 37 | 数量高，但根因尚未归类 |
| 高置信 flake 类型 | 3 | FlinkDeployment、Remedy、control-plane transient |
| 高置信 upstream 样本 | 4 | 都能关联 issue/PR 和具体日志 |
| Fork CI 补充样本 | 1 | 不计入 upstream 总数 |
| Rerun/trigger 后转绿样本 | 5 | 2 个 upstream rerun、2 个空提交、1 个 fork rerun |

失败集中度：`CI Workflow` 有 16 条 failed run；e2e/setup/Kubernetes test 共 56 行非成功 job，是本窗口的主要噪声来源。

## 附录 B：Rerun / Trigger 证据

| 类型 | 数量 | 样本 | 用法 |
| --- | ---: | --- | --- |
| GitHub 原生 rerun 后转绿 | 2 | [`28212061472`](https://github.com/karmada-io/karmada/actions/runs/28212061472)、[`28256528352`](https://github.com/karmada-io/karmada/actions/runs/28256528352) | 证明 e2e/Kubernetes test 可能 transient |
| 空提交 trigger 后转绿 | 2 | #7697 的 [`93eaf7e`](https://github.com/ranxi2001/karmada/commit/93eaf7e57515c959fe30fa2aba387ce10029046d)、#7728 的 [`de3b6be`](https://github.com/ranxi2001/karmada/commit/de3b6be675bbf8ad12f91052f7d0fb53c5b592a5) | 两个 commit 均为 `files=0/additions=0/deletions=0` |
| Fork job rerun 后转绿 | 1 | [`run 29006012630`](https://github.com/ranxi2001/karmada/actions/runs/29006012630) attempt 2 | 只作 control-plane transient 补充样本 |
| Rerun 但不算 flake | 8 | workflow approval、release failure、cancelled 等 | 不用于证明业务 e2e flake |

## 附录 C：PR #7732 文案与技术复查

### PR 文案摘要

- Title：`test(e2e): wait for FlinkDeployment CRD cleanup`
- Kind：`/kind flake`
- Issue：`Fixes #7719`
- 用户影响：`NONE`
- 核心说明：旧 cleanup 只等待 control plane CRD 消失；PR 补齐 member CRD 和 `Cluster.Status.APIEnablements` 收敛等待。
- 非目标：不修改 scheduler、estimator、resource interpreter、CRD propagation controller 或生产行为。
- AI disclosure：用于日志分析、diff 对比和 PR 文案整理，最终代码由提交者审阅验证。

GitHub 上的 [PR #7732 正文](https://github.com/karmada-io/karmada/pull/7732) 是最终文案来源，本报告不再维护第二份完整 body。

### 文件范围

| 文件 | 作用 |
| --- | --- |
| `test/e2e/framework/customresourcedefine.go` | 新增等待 CRD 从 member cluster `APIEnablements` 消失的 helper |
| `test/e2e/suites/base/estimator_test.go` | 覆盖 ResourceQuota 与 NodeResource 两个 cleanup |
| `test/e2e/suites/base/federatedresourcequota_test.go` | 补齐 multi-components cleanup |
| `test/e2e/suites/base/schedule_multi_template_test.go` | 补齐 ScheduleMultiTemplate cleanup |

### 同步屏障

```text
control plane CRD disappeared
  -> member cluster CRD disappeared
  -> Cluster.Status.APIEnablements no longer reports FlinkDeployment as APIEnabled
  -> next test performs a fresh propagation/readiness wait
```

### 代码复查结论

- 4 个 FlinkDeployment CRD 创建路径均已覆盖。
- Ginkgo `DeferCleanup` LIFO 顺序正确：先清 workload/policy，再删 ClusterPropagationPolicy，最后删除源 CRD并等待 member 状态。
- helper 接受 `APIUnknown` 是合理的：member CRD 已直接确认为 NotFound，下一轮 setup 仍必须等到 `APIEnabled`。
- Gemini 的 nil pointer finding 不成立：注入的 `gomega.Gomega` 断言失败会中止当前 poll 并让 `Eventually` 重试。
- 没有发现需要修改的 correctness finding。

### 验证

- `git diff --check upstream/master...upstream/pr-7732`：通过。
- `go test ./test/e2e/framework ./test/e2e/suites/base -run '^$' -count=0`：通过。
- Topic worktree 干净，commit 包含 `Signed-off-by`，base 是 PR head 的祖先。
- Fork push CI 的 CI Workflow、Chart、CLI、Operator 最终通过。
- Upstream 核心 lint、codegen、compile、unit、e2e v1.34-v1.35-v1.36 通过。

剩余风险：原竞态依赖多个异步控制器和 discovery/status 时序，没有稳定触发原 timeout 的自动化回归测试；本地 diagnostic 已直接证明旧 cleanup 会提前返回。

## 附录 D：待补日志样本

### Setup failures

| 时间 | Workflow / Job | Run / Job | 当前证据 |
| --- | --- | --- | --- |
| 2026-07-06 | CI / e2e v1.34 | [`28818641938 / 85466088131`](https://github.com/karmada-io/karmada/actions/runs/28818641938/job/85466088131) | setup e2e step 失败，需补 artifact |
| 2026-07-07 | Operator / v1.35 | [`28863480122 / 85607622872`](https://github.com/karmada-io/karmada/actions/runs/28863480122/job/85607622872) | setup operator step 失败，需补 artifact |
| 2026-07-06 | Operator / v1.34 | [`28761483062 / 85277656027`](https://github.com/karmada-io/karmada/actions/runs/28761483062/job/85277656027) | master push setup failure，需补 artifact |
| 2026-06-28 | CLI / v1.36 | [`28322104916 / 83905699582`](https://github.com/karmada-io/karmada/actions/runs/28322104916/job/83905699582) | setup init e2e failure，需补 artifact |

相关历史：[`#3667`](https://github.com/karmada-io/karmada/issues/3667)、[`#3682`](https://github.com/karmada-io/karmada/pull/3682)、[`#3699`](https://github.com/karmada-io/karmada/pull/3699)。当前证据不足，不能直接写成确定 flake。

### Schedule/compatibility 代表样本

| Workflow | Run | 失败概况 |
| --- | --- | --- |
| CI Schedule Workflow | [`28297782357`](https://github.com/karmada-io/karmada/actions/runs/28297782357) | v1.27-v1.31 多个 e2e failed |
| CI Schedule Workflow | [`28750372834`](https://github.com/karmada-io/karmada/actions/runs/28750372834) | v1.27-v1.30 多个 e2e failed |
| APIServer compatibility | [`28300711541`](https://github.com/karmada-io/karmada/actions/runs/28300711541) | master/release branches 多组合失败 |
| APIServer compatibility | [`28753707990`](https://github.com/karmada-io/karmada/actions/runs/28753707990) | v1.28/v1.30/v1.32 compatibility failures |

分类时必须先找 first hard failure，不能把 AfterSuite、cleanup 或 API connection refused 的后续错误当成根因。

## 附录 E：暂不归为 Flake

| 类型 | 样本 | 原因 |
| --- | --- | --- |
| lint | runs `28706816762`、`28410342955` | 更可能是代码静态检查或格式问题 |
| Chart template | run `28369536076` | 需结合 PR diff，不能仅凭 job failure 判 flake |
| Release publish/upload | `v1.19.0-alpha.1` 相关 runs | 属发布资产链路，不是 e2e |
| Image scanning | run `28307314200` | 属镜像构建/扫描路径 |

## 附录 F：数据获取流程

### 中间文件

- `/tmp/karmada-actions-all-1000-20260626-20260709.json`
- `/tmp/karmada-actions-failures-20260626-20260709.json`
- `/tmp/karmada-failed-jobs-clean-20260626-20260709.tsv`
- `/tmp/karmada-flake-keylines-20260626-20260709.txt`

### 核心命令

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

PR #7732 的持续状态检查：

```bash
gh pr checks 7732 --repo karmada-io/karmada
gh api repos/karmada-io/karmada/pulls/7732/reviews --paginate
gh api repos/karmada-io/karmada/pulls/7732/comments --paginate
```

### 限制

- 部分较早 job 的日志通过 `gh run view --job --log` 返回空内容，只能先基于 workflow/job/step metadata 归类。
- Schedule workflow 不绑定具体 PR diff，只能作为 master 分支持续稳定性的信号。
- Fork CI 不进入 upstream 598 条 run 总量，只能作为补充证据。
- Release、publish、lint、chart template 和 image scanning failure 保留在失败统计里，但不直接进入高置信 flake。
