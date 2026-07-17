# Day 25：Karmada 社区 Issue / PR 扫描

日期：2026-07-17

扫描时间：2026-07-17 09:43（Asia/Shanghai）

## 扫描范围与方法

- 仓库：`karmada-io/karmada`
- 时间窗口：2026-07-16 00:00 至 2026-07-17 09:43（Asia/Shanghai）
- 初筛：窗口内新建或更新的 open issue/PR，以及刚关闭或合并的条目
- 回查：#7697、#7764、#7623、#7662 等已有主线
- 深读方式：先用 `thread_brief.py` 获取 body、assignee、真人/bot review、changed files 和 commits，再用 PR check rollup、review threads 和 exact-head diff 复核关键状态

第一次调用 GitHub Search API 时遗漏 `-X GET`；`gh api -f` 因而切换为 POST 并返回 404。补上显式 GET 后查询正常。本次主扫描仍使用仓库 `issues?state=<state>&since=<time>` 列表接口，因为它可以按精确 UTC 时间覆盖本地时区窗口，再逐项查询 PR/thread。当前 token 缺少 `read:org`，但公开仓库的 repo、issue、pull、review 和 check API 均可读取。

窗口内共看到 17 个 open 条目有更新，另有 6 个 issue/PR 关闭或合并。自动 backport、纯 bot 状态更新和已进入 merge queue 的条目只做归档，不作为介入机会。

> 复盘：初版扫描把“真实可达、CI 绿、无人 review”错误地当成贡献价值，曾把 #7774/#7647 排为 A/B。用户指出这两个场景都依赖特定异常输入，促使本轮补查真实恢复路径并撤回排名。以后必须先过 production relevance gate，再读取完整 diff 或分析 mock tests。
>
> 边界：撤回排名表示我们不再投入分析，不等于建议 maintainer 拒绝其他贡献者的小型正确修复。relevance gate 分配我们的注意力，不是 merge veto。#7774 只有 “operator process crash” 与实际 recovered reconcile panic 不符，构成可选的影响表述修正；#7647 在已有 validation boundary 加一处 parse check，没有具体技术缺陷，因此不应评论“公司没有发生就不要改”。

## 结论先行

| 优先级 | 条目 | 当前判断 | 建议动作 |
| --- | --- | --- | --- |
| Skip | [PR #7774](https://github.com/karmada-io/karmada/pull/7774) operator nil panic 修复 | 真实可达但低价值：刻意非法 label 触发；controller-runtime 已 recover 并进入相同 rate-limited retry，补丁只把 panic 变成 error，资源仍 stuck | 不再深挖 mock tests 或扩展防御分支；根本的 CRD input boundary 仍未解决 |
| Lightweight / Skip | [PR #7647](https://github.com/karmada-io/karmada/pull/7647) `--etcd-pvc-size` 非法值 panic | 真实但很窄：只有 PVC 模式显式输入非法 quantity 才触发，属于 CLI UX hardening | 不作为战略 review；不要继续发散零值/负值等更多边角防御 |
| No new target | 本轮新增/更新条目 | 没有“正常生产路径、影响实际结果、无人认领”的干净新机会 | 接受没有候选，不为了社区活跃度强行分析边角 PR |
| Follow-up | [PR #7764](https://github.com/karmada-io/karmada/pull/7764) E2E RCA skill | 新 head 只落实了不 hard-wrap；artifact compatibility scope、fast-wait diagnosis 和 single-hit retry inference 仍未改变 | 如要继续回复，先用具体反例与 inline Mermaid 重写，并让用户确认 exact target/text |
| Wait | [PR #7697](https://github.com/karmada-io/karmada/pull/7697) 证书轮换 | head 与代码未变，17 checks success，只有 Tide pending；仍无真人 review | 保持 `WAITING_HUMAN_REVIEW`，不扩 scope；reviewer ping 需另行确认 exact text |
| Wait | [PR #7771](https://github.com/karmada-io/karmada/pull/7771) schedulingGates | 已有 assignee/实现 PR，但 codegen failure，生成 CRD/deepcopy 与 patcher tests 尚缺 | 等作者更新，不重复实现，也不重复 bot 已指出的问题 |
| Avoid duplicate | [Issue #7767](https://github.com/karmada-io/karmada/issues/7767) staged propagation | 已被 @karthik120710 `/assign`，且属于大 API/状态机设计，无 maintainer direction | 不抢实现；若后续有 proposal PR，可从已有 #7662 迁移状态经验做 design review |

## 初筛误判为机会的边角 PR

### PR #7774：operator deployment 创建失败后的 nil panic

- 作者：@pujitha24，首次向 Karmada 提 PR
- PR 认领 @：无
- head：`f416214b58`
- surface：8 files，`+193/-5`
- checks：17 success，只有 Tide pending
- 真人 review：无；现有 review 均来自 Gemini/Copilot

该 PR 对应 [Issue #7731](https://github.com/karmada-io/karmada/issues/7731)。Issue 作者确实用非法 label 做了真实 operator 实验：Karmada CRD 接受 `extraVolumes[].ephemeral.volumeClaimTemplate.metadata.labels`，hosting cluster API 拒绝生成的 Deployment，随后错误路径解引用 nil deployment。这证明 production reachability，测试里的 fake reactor 也模拟了真实 API `Invalid` 返回，不是任意 mock。

但它没有通过 contribution value gate：

1. 触发输入是刻意违反 Kubernetes label 规则的配置，不是普通安装路径；
2. 实际日志明确显示 `panic ... [recovered]`，controller-runtime 默认 recover 后把它作为普通 error，并与补丁后的返回 error 一样进入 rate-limited retry；operator 进程没有 crash；
3. 补丁只用静态 component name 避免 nil dereference，不会让非法 Deployment 创建成功，Karmada resource 仍不能完成 reconcile；
4. 根本的 CRD validation/input contract 被明确留作 follow-up，当前四组 fake-client tests 主要证明错误表现从 panic stack 变成普通 error。

因此这是可接受的小型诊断质量修复，但不值得我们继续审查五个重复 error paths、扩展更多 mock cases，或建议再加一层 defensive logic。PR body 的 “operator crash” 也比证据更强，准确说法是 reconcile panic 被框架恢复。

### PR #7647：非法 PVC size 的小型 CLI 修复

- 作者：@Anand-240，首次贡献
- PR 认领 @：无
- head：`62c16da05a`
- surface：2 files，`+34/-2`
- checks：17 success，只有 Tide pending
- 真人 review：maintainer 只要求 squash；作者已完成，尚无 code-level human review

这条路径同样真实：`--etcd-pvc-size` 直接进入 `resource.MustParse`，输入 `abc` 会让 CLI 进程输出 panic stack。补丁在 PVC 模式的已有 validation 中调用 `resource.ParseQuantity`，把它变成普通参数错误。

但触发必须由用户显式提供非法 quantity，影响只是一条失败命令的错误体验；没有安全、数据损坏、长期不可用或普通工作流证据。它属于小而合理的 UX hardening，不值得继续发散“零值、负值、更多 quantity 边界”并堆积验证层，也不应占用我们的主要 review 时间。

### PR #7770：先核对“已处理”回复与 head 是否一致

[PR #7770](https://github.com/karmada-io/karmada/pull/7770) 修改 5 files、`+118/-1`，修复 host kubeconfig `proxy-url` 解析导致的 apiserver 安装失败；17 checks success，尚无真人 review。作者对 16 个 review thread 都回复了 “addressed”，但 PR 当前仍只有一个 head commit `1b09785e10`。除非先有证据表明 host kubeconfig proxy 是普通安装路径并造成实际失败，否则也不因“无人 review”继续深挖；thread/code 对齐只在该项通过 relevance gate 后检查。

## 已认领或已有活跃 reviewer 的条目

### Issue #7768 / PR #7771：operator schedulingGates

- Issue [#7768](https://github.com/karmada-io/karmada/issues/7768) 已由 @karthik120710 `/assign`；PR #7771 是对应实现。
- PR 修改 9 files、`+43/-10`，但 `codegen` failure。
- Bot 已指出 operator CRD YAML、generated deepcopy 与 patcher unit tests 缺失，另有 Kubernetes feature version 表述需要校准。
- 当前没有真人 review，也没有作者新 push。最合理动作是等待作者先闭合 generated artifacts 和 CI，而不是重复 bot 评论或另开实现。

### Issue #7767：Sequential Staged Propagation

该 issue 提议在 `PropagationPolicy` 加 `rolloutStrategy`，包含顺序、health gate、timeout、Pause/RollbackAll/Continue 等状态机语义。@karthik120710 已 `/assign`，目前无 maintainer 技术意见，也没有 linked PR。

它与 #7662 的 SafeMigration 在“跨 reconcile 持久状态、健康判定、失败/取消、多个 desired-state writer”方面高度相关，但 API surface 很大。当前只适合观察未来 proposal，不适合作为快速实现项。

### 其他活跃 PR

- [#7616](https://github.com/karmada-io/karmada/pull/7616)：6 个 Prometheus metrics，@jabellard 已认领并要求从真实 metrics endpoint 验证指标确实发出；等待作者补证据。
- [#7663](https://github.com/karmada-io/karmada/pull/7663)：push-mode bearer token rotation，仍是 draft，@jabellard 已做多轮 review，作者持续响应；不插入重复 review。
- [#7633](https://github.com/karmada-io/karmada/pull/7633)：metricsadapter deterministic sort，仅 1 file、`+4/-1`，但 @zhzhuang-zju 已认领并要求解释功能价值、请 metrics expert review；没有确定功能影响，不作为候选。

## 已有主线状态

### PR #7764：新 head 的实际变化

当前 head 是 `7570842fb5`，parent 仍是 `2f47894fa6`。与上次已复核的 `1972f0b4e` 比较只改 `.claude/skills/e2e-root-cause-analysis/SKILL.md`，`+24/-71`；逐块 diff 显示变化是合并 prose/list item 内的物理换行，没有修改 RCA wording 或命令。

因此：

- 已修：错误的 `member1/member2` artifact layout；systematic hard-wrap。
- 未修：compatibility E2E 的双版本 artifact 名称仍不匹配固定下载名。
- 未修：fast wait 仍被写成 `usually means stale state`，没有 lifecycle correlation gate。
- 未修：single log hit 仍直接推出 `did not retry`，没有 queue/control-flow evidence gate。
- 未修：component glob 仍不是递归搜索。

Review thread 状态也不能替代代码状态：artifact thread 仍 open/current；fast-wait thread resolved/outdated 但原 wording 未变；retry thread open/outdated且 wording 未变；hard-wrap thread open/outdated，但该建议已被代码落实。当前 17 checks success，只有 Tide pending。

### PR #7697、#7623、#7662

- #7697：head `3d1bc25b09`，10 files、`+1696/-22`、1 commit；17 checks success，Tide pending，无新 human review。
- #7623：head 仍为 `793f47dbfe`，作者没有回复 7 月 15 日的 cache-commit review，也没有新 push。
- #7662：head 仍为 `586f6fc350`，作者没有回复 7 月 14 日的 target-first review，也没有吸收 6 月 30 日会议反馈。

这三条都不需要重复催促或追加未经审批的评论。

## 已闭环动态

- [Issue #7612](https://github.com/karmada-io/karmada/issues/7612) 已由 [PR #7613](https://github.com/karmada-io/karmada/pull/7613) 修复并关闭/合并。
- 自动 backport [#7772](https://github.com/karmada-io/karmada/pull/7772)（release-1.18）和 [#7773](https://github.com/karmada-io/karmada/pull/7773)（release-1.17）已合并；[#7775](https://github.com/karmada-io/karmada/pull/7775)（release-1.16）已 `lgtm/approved`，不需要介入。
- [#7704](https://github.com/karmada-io/karmada/pull/7704) 已合并；scope 过大的 [#7703](https://github.com/karmada-io/karmada/pull/7703) 已关闭。

## 建议下一步

1. 本轮结论改为“没有值得新介入的 issue/PR”，不再 review #7774/#7647，也不从它们的 mocks 扩展更多防御性场景。
2. 继续把主要精力放在 #7697 的合并维护和 #7662 的生产级调度/迁移状态设计；它们影响正常用户路径和长期架构边界。
3. #7764 如需继续，只回复最有价值的 inference gap，并使用已有 Mermaid 降低理解成本；发布前给用户确认 exact thread 和 English text。
4. 后续社区扫描先用 compact metadata 判断 trigger normality、最终结果、恢复行为、频率和 fix leverage；未通过 relevance gate 时停止，不读取 full JSON/diff 或运行 mock tests。

## #7774 影响表述评论（已发布）

评论发布在 PR conversation，因为需要修正的是 PR body 的影响表述，不是某一行实现。#7647 没有具体 correctness/complexity finding，不准备评论。

- 评论链接：https://github.com/karmada-io/karmada/pull/7774#issuecomment-4998449728
- 发布身份：`ranxi2001`
- 发布时间：2026-07-17 10:39:15 CST

```text
The reproduction in #7731 shows that controller-runtime recovered the panic and returned it as a reconcile error; the operator process did not crash. Before and after this patch, the request is rate-limited and the invalid Deployment still cannot be created. Could the PR description narrow the impact to avoiding a recovered reconcile panic and preserving the original API error? The broader input-validation issue remains unchanged.
```

本轮只发布了上述 #7774 conversation comment；未 `/assign`、未 request reviewer，也未修改其他 upstream PR/issue 状态。
