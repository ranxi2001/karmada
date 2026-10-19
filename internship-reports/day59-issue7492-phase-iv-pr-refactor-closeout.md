# Day 59：#7492 Phase IV 三 PR 重构收尾

日期：2026-08-27

状态核对时间：2026-08-27 21:56（Asia/Shanghai）

## 2026-10-19：#7830 当前审查结论

最新状态：按用户要求，已原样采用 RainbowMango 的三处代码 suggestion，再更新测试。本地新版为 `06a3e9578`，race tests 与 lint 均通过，尚未推送；以下保留当日上一轮的审查与发布证据，最新行为以“后续 review”小节为准。

### 先说人话

建议接受 RainbowMango 今天提出的简化意见，并同步处理 PR 描述与提交整理：#7830 只需要判断组件副本是否变化，可以用一个布尔比较函数替代 `ComponentScale` 枚举。扩容、缩容、部分组件增而另一些减，当前调用都会进入同一个重新调度分支；区分方向对这个 PR 的调用者没有额外作用。这是接口复杂度建议，尚未发现由枚举本身导致的行为错误。初次审查只记录建议；随后用户要求实施，具体结果见下文实施状态。

例如已调度结果为 `jobmanager=1, taskmanager=4`，期望改为 `jobmanager=1, taskmanager=6`，应触发重新调度。若期望变为 `jobmanager=2, worker=4`，组件名称集合已经变化，当前 PR 则保留原行为，不能在看到第一个副本差异时提前返回 `true`。

> 注释：这里的“没有触发”只指新增的组件副本比较分支；后续已有的标量副本判断仍照常执行。缺失或无法比较的结果如何恢复，仍未由本 PR 解决。

### 当前代码与讨论证据

审查对象为 [#7830](https://github.com/karmada-io/karmada/pull/7830)，head `3529779731010c16be738017b047ba490293a592`，base `61af4b2bb186f5b2bf929348d57a1f0bec0988cb`；3 files，`+362/-8`。已读取 PR body、全部 conversation comments、line comments、reviews、当前 diff 与 RB/CRB 调用路径。

- [mszacillo 的分类建议](https://github.com/karmada-io/karmada/pull/7830#discussion_r3891434535)希望用分类函数简化调用，并为 #7835 复用；后续又建议去掉 admission 已保证的 desired-name 校验与多余 map helper。作者已完成这些修改；[2026-09-01 的评论](https://github.com/karmada-io/karmada/pull/7830#issuecomment-5495468406)给出 `/lgtm`。
- [RainbowMango 2026-10-19 的意见](https://github.com/karmada-io/karmada/pull/7830#discussion_r4311034303)认为当前 PR 只需 yes/no，枚举过重。两条建议的关注点分别是后续复用与当前需求，可以通过当前 PR 保持布尔接口、方向分析由估算阶段负责来处理。
- [当前 `IsBindingReplicasChanged` 与分类函数](https://github.com/karmada-io/karmada/blob/3529779731010c16be738017b047ba490293a592/pkg/util/binding.go#L54)把 `Up/Down/Mixed` 全部映射为 `true`，`None/Unknown` 均继续旧路径；全仓检索没有发现当前 #7830 内其他 production classifier caller。
- RainbowMango 同日的 review 总结还明确要求处理剩余评论、按内容更新 PR 描述、整理 commits。API 确认当前共 5 commits：`78dfc7a`、`ae34007`、`e3e9d4e`、`0673179`、`3529779`；其中比较函数与分类函数的迭代可整理为一个最终聚焦提交。当前 body 已匹配 trigger-only 职责，但修改接口后仍需检查描述、验证命令与结果是否一致。
- [RB 调用](https://github.com/karmada-io/karmada/blob/3529779731010c16be738017b047ba490293a592/pkg/scheduler/scheduler.go#L428)与 [CRB 调用](https://github.com/karmada-io/karmada/blob/3529779731010c16be738017b047ba490293a592/pkg/scheduler/scheduler.go#L504)仅使用 bool 决定是否调度，并记录 `ScaleSchedule`；两者不消费方向。
- #7835 当前 head `e19a318ebb664e02abbbf1f5c4f1d19b43c83835` 的 `pkg/scheduler/core/estimation.go` 仍有自己的 `componentReplicaScaleDirection`，并未调用 #7830 新增的 `ClassifyComponentScale`。#7841 当前 head `9a048730721a558c9e70c490a2890abf4491603f` 仍使用旧版 `ComponentReplicasEqual`，因此后续 stack 更新需要检查接口衔接，不能假定远端三个 PR 已同步。
- 当前 PR body 已关联 [#7895](https://github.com/karmada-io/karmada/issues/7895)，其三个任务仍是触发重新调度、增量估算/缩容跳过估算、失败时阻止下发。该 issue 有另一位贡献者的认领请求，不能据此推断已获得分配或实现已经被替代。

### 建议修改边界与验证

建议删除 `ComponentScale` 及其常量，将分类函数改为只返回 bool 的副本变化比较。比较仍按名称进行，保留 desired 名称由 admission 保证非空且唯一的前提；长度不同、scheduled 缺失或名称不匹配时不触发新增分支。可以在遍历时累积 `changed`，但必须完成名称匹配检查后才返回它。不要简化成“任何不相等都触发”，那会把目前排除的组件集合变化带入重新调度。

现有 helper 测试应改为布尔断言，保留扩容、缩容、混合变化、仅重排、缺失/不可比较结果的语义。修改后最小验证是 helper 与 `TestIsBindingReplicasChanged`，再验证 `TestDoScheduleBinding` / `TestDoScheduleClusterBinding`；保持 Placement annotation 与 Placement 相同，确保用例真正走到副本变化分支。

初次审查没有修改 executable code，也没有重新运行 Go tests。GitHub exact-head check-runs 已核对：`3529779` 的 17 项检查全部成功，包含 unit、lint、codegen、compile 与 E2E；Tide pending 的原因是缺少 `approved` 标签。这只证明当前 head 的现有 CI 结果，不证明尚未实现的布尔版本通过测试，也不代表完整 #7835/#7841 功能已验收。

### 2026-10-19 实施设计（源码修改前）

用户已要求开始实施。源码范围为 `pkg/util/binding.go`（删除枚举并替换比较函数）、`pkg/util/binding_test.go`（布尔断言与不可比较边界）、`pkg/scheduler/scheduler_test.go`（保留既有 RB/CRB 入口测试）。不修改 scheduler 路由、估算器、Binding controller、API、generated files 或 #7835/#7841 分支。

比较函数拟命名 `IsComponentReplicasChanged`，返回单一 bool；desired 由 admission 保证有效。先检查非空/等长，再构造 scheduled name-to-replicas map；遍历 desired 时若名称不存在即返回 false，副本不同时只累积 changed，全部名称匹配后返回 changed。新增边界用例覆盖“先发现副本变化，后发现名称缺失”，防止错误的提前成功返回。

在 latest upstream/master 的独立 worktree 重建当前 PR 的三文件 diff，并整理为一个 signed-off commit；如 base 有相关变更，先核对重叠再继续。验证先跑 helper 与 IsBindingReplicasChanged、RB/CRB 调度入口的 race tests，再跑受影响包和 changed-path lint；不启动 live E2E 或全仓测试。待验证通过后更新本地 PR body 草稿，展示 exact diff/text 后再发布。

### 2026-10-19 实施与发布结果

新版已在 `/home/ranxi/projects/karmada-pr7830-bool` 的 `review/pr7830-bool` 分支准备，基于最新 `upstream/master@b14c23c6d`。原 5 commits 整理为一个 signed-off commit `8806479cd39473a0d09bb3a117278ef61b0302b8`，相对 master 为 3 files `+339/-8`；工作区干净，祖先关系与 diff whitespace 检查通过。latest master 相对原 base 前进 70 commits，但三个目标文件没有重叠变化。

`ComponentScale` 与 `ClassifyComponentScale` 已移除，替换为单一 bool 函数 `IsComponentReplicasChanged`；保持 admission 前提、按名称比较和不可比较时返回 false 的行为。新增测试覆盖先遇到副本差异、随后出现名称不匹配的情况。RB/CRB 调度入口测试保持原样。相对旧 PR head 的三个目标文件，源码为 `+11/-40`、util tests 为 `+21/-15`，scheduler tests 不变。

验证命令及结果：

- `GOTOOLCHAIN=go1.26.9 GOMAXPROCS=4 go test -race -count=1 -p=4 ./pkg/util ./pkg/scheduler`：通过；util `13.103s`、scheduler `1.663s`，覆盖两个包全部 tests。
- `GOTOOLCHAIN=go1.26.9 GOMAXPROCS=4 golangci-lint run --concurrency=4 ./pkg/util ./pkg/scheduler`：通过，`0 issues`。
- 未运行完整 `make test`、全仓 `make verify` 或 live E2E。没有 API/generated files 变化。

本机默认 Go 为 1.27.0，latest master 已要求 1.26.9，故通过 `GOTOOLCHAIN=go1.26.9` 下载并使用版本匹配的工具链；没有修改 topic branch 的 `go.mod` 或 `.go-version`。本地检查已完成；正文可见 171 words / 15 nonblank lines，回复 17 words / 1 line，无长文例外。test log 为 `/tmp/pr7830-bool-tests.log`，lint log 为 `/tmp/pr7830-bool-lint.log`。本地 `git diff 8806479cd^ 8806479cd` 可复查完整提交。

发布目标：现有 `karmada-io/karmada#7830`，head branch `ranxi2001/karmada:feature/multi-component-scale-rescheduling`，title 保持 `feat: trigger rescheduling on component replica changes`；正文以 [current body 草稿](day58-pr7830-current-body.md) 为准，仍保留官方模板与 AI assistance disclosure。发布应使用旧 head `3529779731010c16be738017b047ba490293a592` 的 exact force-with-lease；不改动旧本地 feature worktree，不更新 #7835/#7841，不自行 resolve threads 或请求 reviewer。

用户确认后，已在 RainbowMango 的枚举意见下发布以下 [17-word 回复](https://github.com/karmada-io/karmada/pull/7830#discussion_r4311221327)，`in_reply_to_id=4311034303`；回读正文与获准文本一致：

> Replaced the enum with a boolean comparison, updated the description, and squashed the changes into one commit.

发布核验：exact force-with-lease `3529779731010c16be738017b047ba490293a592` 成功，origin branch 与 GitHub PR head 均已更新为 `8806479cd39473a0d09bb3a117278ef61b0302b8`。PR base 为 `b14c23c6dfa652d0b1b8d4a0dce28043b33e0c0c`，公开 diff 为 1 commit、3 files `+339/-8`，mergeable=true；title 未变。远端 body 与获准本地文件逐字节一致，SHA-256 为 `8875b1315a4e71dc595fa4a4124400e9ab7f967c0a4841c383233f5f4d3ad578`。

`gh pr edit --body-file` 首次失败，错误为 `GraphQL: Projects (classic) is being deprecated ... (repository.pullRequest.projectCards)`。这是 gh 获取旧 Projects 字段时的 API 兼容问题；使用 REST `PATCH /repos/karmada-io/karmada/pulls/7830`，从正文文件构造 JSON input 后更新成功。没有重复发布回复，也没有 resolve review thread 或新增 reviewer mention。

current-head official CI 已启动：首次回读为 DCO success、lint/codegen 与多版本 jobs in_progress，Tide pending。其余 job 尚未完成；不沿用旧 head 的 green checks，不检查 fork push workflows。

### 2026-10-19 后续 review：先采用建议，再更新测试

RainbowMango 在 [review](https://github.com/karmada-io/karmada/pull/7830#pullrequestreview-5568228463) 提供三处完整 suggestion，并要求更新单测。用户随后明确要求先接受代码建议、再写测试。此轮以这三处 suggestion 为实现基准：修改注释、调用 `isComponentReplicasChanged(bindingSpec.Components, bindingSpec.Clusters)`、原样采用私有 helper。

新的触发语义覆盖所有 target clusters：任一有组件结果的集群出现副本或组件集合变化就触发；没有组件结果的集群跳过，继续 legacy replica checks。此 maintainer 指导替代上轮单目标、同名集合限定，不继续保留旧的 incomparable-return-false 测试预期。`pkg/scheduler/core/common.go:AssignReplicas` 在 multi-template applicable 时为每个目标写入 `buildTargetComponents(spec.Components)`；空结果的旧数据与单组件路径仍可出现，所以 skip 与 legacy fallback 都需要测试。

源码只修改 `pkg/util/binding.go`；随后调整 `pkg/util/binding_test.go`，保留原 scheduler 入口测试。单测覆盖多目标第二目标变化、组件增删/改名、重排相等、空结果跳过后继续后续集群、全部空结果及单组件 legacy replica checks。验证使用 util/scheduler 两包全部 race tests 与 changed-package lint；不改 estimator、controller 或下游 PR。PR body 同步去掉 snapshot、single-target 与忽略组件集合变化的旧描述。发布仍需确认本轮 exact diff/text。

实施结果：三处 suggestion 文本均从 GitHub API 读取并与最终 `pkg/util/binding.go` 精确匹配，没有额外改动 helper。之后重写 helper 测试为 `Test_isComponentReplicasChanged`，包含 14 个用例；调用层另新增 4 个用例，覆盖多个 target、移除至单组件、Duplicated/Divided legacy checks。原“名称/数量变化不触发”用例已改为触发；删除依赖旧 incomparable 语义的 malformed-result 用例，没有新增防御分支。scheduler 入口 tests 未改动。

新验证（Go 1.26.9）：`go test -race -count=1 -p=4 ./pkg/util ./pkg/scheduler` 全部通过，util `13.062s`、scheduler `1.683s`；`golangci-lint run --concurrency=4 ./pkg/util ./pkg/scheduler` 通过，`0 issues`。日志为 `/tmp/pr7830-maintainer-tests.log` 与 `/tmp/pr7830-maintainer-lint.log`。没有运行 live E2E 或全仓 verify。

本地提交已 amend 为单个 signed-off `06a3e9578bc833dfce616dee49e8b60d65b5203d`，base 仍为 `b14c23c6d`；相对 master 3 files `+403/-9`，本轮相对已发布 `8806479cd` 只改 util 的源码与 tests，`+146/-83`。工作区干净，diff check 通过。尚未推送，本轮代码修改授权不代替新的上游 exact diff/text 发布确认。

[新版 body 草稿](day58-pr7830-current-body.md) 已去掉 snapshot、single-target 与忽略组件集合变化的描述，并更新 release note。后续发布目标仍为现有 #7830；可用旧 head `8806479cd39473a0d09bb3a117278ef61b0302b8` 的 exact lease 更新；不自动 resolve threads 或更新下游 PR。待发布回复草稿：

> Applied the suggested changes and updated the unit tests.

合并门槛核对：用户看到的 `Merging is blocked — 1 review requesting changes by reviewers with write access` 对应 RainbowMango 的 [CHANGES_REQUESTED review](https://github.com/karmada-io/karmada/pull/7830#pullrequestreview-5568228463)，review commit 为远端 `8806479cd`。API 当前 `mergeable=true`、`mergeable_state=blocked`；本地修订 `06a3e9578` 仍未推送。按 [GitHub required reviews 说明](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)，这种规则下需原 reviewer 后续提交 approving review；发布修订与解除审查阻塞是两件事，不能把本地修改或 resolve thread 写成 approval。

### 本地记录与下一步

本地原 feature worktree 停留在 `cf59527e2`，与远端分支存在分歧；当前证据直接读取 exact-SHA Git 对象，未切换或重置旧 worktree。若继续实现，应从审查 head 建独立 worktree，并先确认当前 base 差异与依赖接口。

环境中 `/home/humanizer-cs/skills/humanizer-cs/SKILL.md` 不存在，改用已安装的 `/home/ranxi/.codex/skills/humanizer-cs/SKILL.md` 及其必读 references；更新检查使用 `python3`（`python` 不存在），版本为 `0.5.3`，无可用更新。

上一轮 `8806479cd` 已发布；本轮 follow-up `06a3e9578` 的代码与测试已完成，本地等待发布确认。以下保留 2026-08-27 历史交付证据，其旧 head、CI 和“尚无 review”表述不代表今天状态。

## 先说人话

#7492 的三个 PR 已经按“触发、计算、失败保护”重新发布，旧的 `ReviseComponents` / component delivery 大包没有保留。当前工作已从“继续改设计”转为“等待 official CI 和 human review”。

还不能把任务写成完全结束：#7841 旧 head `c8146e039` 的 official lint 发现 `calAvailableReplicas` cyclomatic complexity 为 17，超过阈值 15。修复已经以 signed-off follow-up `2b567c5a5` 发布；本地 core lint、完整 race tests 和 E2E compile 均通过，current-head official `lint` 与 `codegen` 也已通过，其余 jobs 仍在运行。

具体例子仍是：accepted `JM=1, TM=4`，source 改为 `JM=1, TM=6`。#7830 只触发 scheduler，#7835 只计算 `TM=+2`，#7841 只在 scheduler 接受后更新 Work；无法容纳时 accepted snapshot 与旧 Work 都保持 `TM=4`。

## 最终 PR 职责

| PR | Public head | 唯一职责 | Residual diff | Public stacked diff |
| --- | --- | --- | --- | --- |
| [#7830](https://github.com/karmada-io/karmada/pull/7830) | `e3e9d4e9f` | component replicas changed → trigger rescheduling | 3 files，`+277/-8` | 同 residual |
| [#7835](https://github.com/karmada-io/karmada/pull/7835) | `e19a318eb` | positive delta / scale-down skip calculation | 2 files，`+403/-6` | 5 files，`+680/-14` |
| [#7841](https://github.com/karmada-io/karmada/pull/7841) | `2b567c5a5` | failure-safe accepted-result commit 与 Work guard | 14 files，`+816/-33` | 18 files，`+1496/-47` |

三个 remote head、title、changed-file surface 和 body bytes/SHA-256 已逐项验证。PR 仍为 Open / blocked on CI and review，没有 external human review，也没有 `/lgtm` 或 `/approve`。

## 分 PR 答辩口径

### #7830：触发重新调度

#7830 的核心目的是让 multi-template workload 在 component replicas 改变时重新进入现有 scheduler，因为这类 workload 的 scalar `spec.replicas` 为 0，旧的副本变化判断无法感知 `TM=4 -> 6`。它不新增 CRD 或 interpreter 接口，而是复用 #7837 定义、#7833 持久化的数据边界：desired `ResourceBindingSpec.Components` 与 accepted `ResourceBindingSpec.Clusters[0].Components`；实现上扩展现有 `IsBindingReplicasChanged`，并提供按 component name 比较的 `ComponentReplicasEqual`，只有 feature gate 开启、accepted snapshot 可比较且副本确实不同时才沿既有 `ScaleSchedule` 路径触发重调度，equal、普通单模板和不可比较状态保持旧行为。这个 PR 到“要不要重新调度”为止，不计算 delta，也不碰 Work。

### #7835：计算重新调度所需容量

#7835 的核心目的是在 component scale 已经被判定后给出不会 double count 的容量计算，而不是决定何时调度或如何提交结果。它没有增加对外 API，只在 scheduler core 内提供 `calculateMultiTemplateAvailableSetsForScale(ctx, multiTemplateEstimationContext)`：以 desired `spec.Components`、accepted `spec.Clusters[0].Components` 和唯一 accepted target 为输入，按 name 判断方向；纯扩容构造 positive delta 后通过现有 `ReplicaEstimator.MaxAvailableComponentSets` 估算，纯缩容直接返回 `minimumAvailableComponentSets` 这一内部容量证据并跳过 estimator，mixed、equal、snapshot 缺失/不完整以及 new candidate 都显式报错，绝不 fallback 到 full desired estimation。该 PR 有意不接 production caller，因为单独激活后，旧 scheduler 会在 `FitError` 时清空 accepted result；#7841 必须把 planner activation 与 failure retention 一起接入，最终完整 component assignment 仍由既有 scheduler result 流程生成。

### #7841：失败时保留已接受状态

#7841 的核心目的是把“新配置是否被 scheduler 接受”变成 Work 更新的门槛：成功时提交新 accepted snapshot 并允许最新 source 下发，失败时保留旧 snapshot 和旧 Work。接口设计只增加内部调度选项 `ScheduleAlgorithmOption.IsMultiComponentScale`，用它固定当前 accepted target、调用 #7835 planner，并让任何 component-scale error 在现有 `Spec.Clusters` result patch 前返回；交付侧在 source fetch 与既有 `ensureWork` 之间调用 `shouldWaitForComponentScheduleResult`，通过现有只读接口 `ResourceInterpreter.GetComponents` 提取 source replicas，再用 #7830 的 `ComponentReplicasEqual` 对照 accepted `TargetCluster.Components`，相等才继续更新 Work，不相等或不可比较就等待。source 本身已经包含新 replicas，所以这里不需要 `ReviseComponents`、workload rewrite 或新的 interpreter API。

## 实际代码数据流

```text
source workload replicas change
        ↓
detector updates Binding.Spec.Components
        ↓
#7830: IsBindingReplicasChanged
        ↓ component ScaleSchedule
#7841 routing calls #7835 planner on accepted target
        ↓
#7835: positive delta / scale-down skip / unsupported fail closed
        ↓
success                       failure
  ↓                              ↓
patch complete accepted result   return before Spec.Clusters patch
  ↓                              ↓
source replicas == accepted      source replicas != accepted
  ↓                              ↓
ensureWork updates Work          binding controller keeps old Work
```

> 注释：#7835 保持 calculation-only，没有 production caller。production activation 必须与 #7841 的 failure result retention 同时出现，否则 intermediate PR 遇到 `FitError` 会清空 accepted result。#7841 只调用 #7835，不复制 delta 算法。

## #7830 收尾

Production 只修改 `pkg/util/binding.go`：

- `IsBindingReplicasChanged` 使用 desired `spec.components` 与 accepted `clusters[0].components`；
- `ComponentReplicasEqual` 返回 `equal/comparable`，供 #7841 Work guard 复用；
- scale-up / scale-down changed，equal/reordered no-change，missing/incomparable 保持旧 trigger 行为。

测试前置条件也已纠正：component cases 设置与当前 Placement 相等的 `PolicyPlacementAnnotation`，verbose 日志证明实际命中 replica-change branch，而不是更早的 `placementChanged` branch。

## #7835 收尾

Residual 只包含：

```text
pkg/scheduler/core/estimation.go
pkg/scheduler/core/estimation_test.go
```

- scale-up 按 name 计算 positive delta；
- scale-down 返回内部 one-component-set capacity evidence，不调用 estimator；
- mixed、equal、missing/partial/incomparable snapshot 与 new candidate 全部 error；
- 不再对新 candidate fallback full desired estimation；
- requirements provenance 没有存入 `TargetCluster.Components`，因此 replicas 与 requirements 同时变化仍是未覆盖边界，本轮没有增加 hash/API。

## #7841 收尾

Scheduler owner：

- component scale pin 当前 accepted target；
- ordered `ClusterAffinities` 只按当前 observed path 调一次，不进入 fallback migration loop；
- mixed/unknown/estimator failure capacity 为 0，不回退 scalar `spec.Replicas`；
- success 继续使用现有 result patch；任何 component-scale error 在 main-resource patch 前返回。

Binding controller owner：

- source fetch 后调用现有 `GetComponents`；
- 使用 #7830 comparator 与 accepted snapshot 比较；
- mismatch / incomparable 在 `ensureWork` 前返回；
- equal replicas 的 image/label/annotation/requirements-only update 保持旧 propagation 行为；
- feature off、single-template、custom scheduler 和 missing snapshot 保持旧行为。

因此不需要 `ReviseComponents`：success 时 source 已包含新 replicas；failure 时旧 Work 不被覆盖。

## 本地验证

```text
go test -race -count=1 ./pkg/util ./pkg/scheduler
go test -race -count=1 ./pkg/scheduler/core
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
golangci-lint run ./pkg/scheduler/core/... ./test/e2e/suites/base/...
git diff --check
```

以上 unit/race、E2E package compile 和本地 lint 已通过。没有运行 live multi-cluster E2E；新增 Flink workflow 只完成 compile/lint，不能写成 live quota/no-fit 已验证。

## Official CI 快照

| PR | Checks | Failure | Human review |
| --- | --- | --- | --- |
| #7830 | 14 success / 3 jobs running + Tide pending / 18 total | 0 | 无 external human review |
| #7835 | 14 success / 3 jobs running + Tide pending / 18 total | 0 | 无 external human review |
| #7841 | 3 success / 10 jobs running + Tide pending / 14 total | 0 | 无 external human review |

动态 CI 状态以 GitHub 为准。本报告只记录核对时快照，不把 pending、DCO 或 Tide 当作设计认可。

## #7841 lint failure 与本地修复

Official job：[lint / 98535147326](https://github.com/karmada-io/karmada/actions/runs/33077412359/job/98535147326)

GitHub annotation：

```text
pkg/scheduler/core/util.go:57
cyclomatic complexity 17 of func `calAvailableReplicas` is high (> 15) (gocyclo)
```

漏检原因：发布前只对 `test/e2e/suites/base/...` 跑了 changed-path lint，没有覆盖同时修改的 `pkg/scheduler/core/...`。Follow-up `2b567c5a5` 把 component-scale pre-estimator resolution 提取到 `resolveComponentScaleWithoutEstimator`，并用 `targetClustersWithReplicas` 统一构造 capacity result；行为不变。

Follow-up 验证：

```text
golangci-lint run ./pkg/scheduler/core/...
golangci-lint run ./pkg/scheduler/core/... ./test/e2e/suites/base/...
go test -race -count=1 ./pkg/scheduler/core ./pkg/scheduler ./pkg/controllers/binding
go test -count=1 ./test/e2e/suites/base -run '^$'
```

全部通过。用户确认后已按旧 head `c8146e039` 执行精确 `--force-with-lease`；origin branch 与 GitHub PR head 均为 `2b567c5a553b6c34b49e0a7d5b0a6d1630b3a7cf`。Title 未变，remote body 与获准草稿逐字节一致，SHA-256 仍为 `71b09b39992fdfb446689aaccea96116cd15ad86e18a39e56b3ba591da5797ac`。Current-head official [lint job 98540268305](https://github.com/karmada-io/karmada/actions/runs/33078785199/job/98540268305) 已在 5m46s 后通过，旧 head 的唯一红灯已经消除。

## 反面案例与方法沉淀

- [Day 49](day49-7830-review.md) 保留“从现有代码反推需求、扩成 API/interpreter/delivery”的反面案例；不再修改。
- [Day 58](day58-issue7492-pr-responsibility-refactor.md) 保存完整拆分、架构冲突、range/residual diff 和 upstream update packet。
- Day 59 记录最终交付状态、分 PR 答辩口径、CI gap 和下一 owner，不重复 Day 58 的完整实现过程。

可复用规则：

1. 先把 Issue requirement 映射到 owner，再看现有代码是否应保留。
2. stacked PR 必须同时报告 GitHub full diff 与当前 PR residual diff。
3. 测试 case 名称不能证明调用链；必须控制更早 predicate 并断言下游 mode/result。
4. changed-path lint 必须覆盖每个修改过的 production package，不只覆盖新增 E2E 文件。
5. remote update 必须分别验证 branch head、PR head、title、file surface 和 body bytes。

## 未决边界

- #7830、#7835 的 live E2E jobs 与 #7841 新一轮 official jobs 尚未完成；
- 三个 PR 尚无 external human review；
- live Flink quota/no-fit、ordered-affinity 和 CRB 行为尚未本地 E2E 验证；
- requirements provenance、legacy missing snapshot、failover/recovery 明确移出当前 Phase IV。

## 下一步

1. 只监控 official PR CI；exact-head failure 出现后按 diff 相关性分类。
2. 等待 maintainer review，不为 pending 状态重复 push、retest 或恢复旧大包范围。
