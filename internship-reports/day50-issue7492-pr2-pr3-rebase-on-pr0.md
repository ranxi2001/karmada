# Day 50：#7492 PR2/PR3 基于 PR0 的 ancestry 重排

- 日期：2026-08-16
- PR0：[#7837](https://github.com/karmada-io/karmada/pull/7837)，head `76589a9d514543edc8c8ca47174cff360d3b832e`
- PR1：[#7830](https://github.com/karmada-io/karmada/pull/7830)，head `6ff28fe4a1d42b8a7980e60e0276306731c15656`
- PR2：[#7833](https://github.com/karmada-io/karmada/pull/7833)，旧 head `1d2ee95c4f701cc618d3c5a730ffe560298b4b8f`
- PR3：[#7835](https://github.com/karmada-io/karmada/pull/7835)，旧 head `b1c41a584ce043746b293271abd85ccf1341014b`
- 本轮状态：本地重排与验证已完成；远端分支和 PR 正文尚未更新，等待 exact-action/text 确认

## 先说人话

PR1 已经采用“PR0 current head + 自身 residual”的方式重建，并在 `6ff28fe4a` 上通过全部 16 个
GitHub Actions checks 与 DCO。PR2/PR3 也按同一规则处理：不再把旧 PR1 `c0b68f728` 或另一个后续 PR 带进自己的历史，
各自只保留一个功能 commit，直接接到 PR0 `76589a9d5`。

例如，PR3 当前在 GitHub 的 `master` comparison 中同时出现旧 PR1、PR2 和自己，共 65 个文件；它真正的
planner residual 只有 4 个文件。重排后，reviewer 仍可用 `76589a9d5...<new-pr3>` 只看这 4 个文件，
而 PR 的完整 `master` comparison 只包含 PR0 API 和 PR3 planner，不再夹带 PR1/PR2。

当前与目标历史：

```text
当前：1d954fcf8 -> c0b68f728 -> 1d2ee95c4 -> b1c41a584
                         PR1(old)      PR2(old)      PR3(old)

目标：a957f64d5 -> 76589a9d5 (PR0)
                          |-> 6ff28fe4a (PR1)
                          |-> 98535c541 (PR2)
                          `-> 782232b7d (PR3)
```

这里的 PR2/PR3 指现有开放 PR #7833/#7835，不在 ancestry 变更中顺带采用维护者 Draft 的另一套功能编号。
现有 #7833 同时包含 scheduler producer、`ReviseComponents`、Work delivery 和 Flink customization，确实比
Draft PR2 更宽；重新拆成 Draft PR2/PR3/PR4 会改变功能边界、PR 文本和验证面，必须作为单独设计处理。

## 设计边界

| PR | 旧 residual | 目标 parent | 允许变化 | 预期验证 |
| --- | --- | --- | --- | --- |
| #7833 | `c0b68f728..1d2ee95c4`，40 文件 `+1445/-45` | `76589a9d5` | 只处理 3 个共享生成文件的组合冲突；手写行为不变 | non-generated patch 等价、codegen/Swagger、focused race、base E2E compile、`make verify` |
| #7835 | `1d2ee95c4..b1c41a584`，4 文件 `+448/-6` | `76589a9d5` | 无文件交集，patch-id 应完全相同 | `range-diff =`、focused race、`make verify` |

源码交集已经通过 read-only merge simulation 证明：

- PR2 residual 与 PR0 只在 `api/openapi-spec/swagger.json`、
  `pkg/generated/applyconfigurations/internal/internal.go`、
  `pkg/generated/openapi/zz_generated.openapi.go` 相交；它们都由生成器重新合成。
- PR3 residual 与 PR0、PR2 residual 均无文件交集，只使用 PR0 已提供的
  `TargetCluster.Components` / `TargetComponent`，不调用 PR2 新符号。

## 明确不改

- 不修改 PR0 `76589a9d5`、PR1 `6ff28fe4a` 或 PR4 prototype `f54f228d7`。
- 不把 PR1 validation/compatibility 9 文件带入 PR2 或 PR3。
- 不把 #7833 的 40 文件在本轮重新拆成维护者 Draft PR2/PR3/PR4。
- 不把 #7835 接在新 PR2 后；其 4 文件 residual 可独立建立在 PR0 上。
- 不修改生产行为、测试断言、commit message、author 或 DCO trailer；生成文件只接受仓库脚本输出。
- 本地验证完成前不 force-push，不修改 PR title/body，不发布评论。

## 实现结果

| PR | 新 head 与 parent | residual 等价性 | 完整 `master` diff |
| --- | --- | --- | --- |
| #7833 | `98535c541`，parent 精确为 `76589a9d5` | `range-diff` 为 `=`；patch-id 仍为 `ba61f0270c1f33851cad169a31fdf4b33cde4e06`；40 文件 `+1445/-45` | 49 文件 `+1764/-50` |
| #7835 | `782232b7d`，parent 精确为 `76589a9d5` | `range-diff` 为 `=`；patch-id 仍为 `e2132d5cfa480aca264b3bf2ac0c12fa7ad8f0b6`；4 文件 `+448/-6` | 17 文件 `+767/-11` |

两个新 commit 都保持原 author、commit message 与匹配的 `Signed-off-by` trailer。PR2 的 3 个共享生成文件由
Git 自动合并且结果通过仓库生成物校验；PR3 无冲突。两个 source worktree 均保持 clean。

## 验证证据

| PR | 命令 | 结果与边界 |
| --- | --- | --- |
| #7833 | `go test -race -count=1 ./pkg/scheduler/core ./pkg/detector ./pkg/controllers/binding ./pkg/resourceinterpreter/... ./pkg/util/interpreter ./pkg/karmadactl/interpret ./pkg/webhook/configuration` | 通过，覆盖 scheduler producer、detector、Work delivery 与各 interpreter/configuration 路径 |
| #7833 | `go test -count=1 ./test/e2e/suites/base -run '^$'` | 通过，仅证明 base E2E package 可编译，不是 live E2E |
| #7833 | `GOMODCACHE=/home/ranxi/go/pkg/mod make verify` | 通过，codegen、Swagger、gofmt、vendor、license 等均无漂移 |
| #7835 | `go test -race -count=1 ./pkg/scheduler/core ./pkg/util` | 通过，覆盖 planner 与 component comparison |
| #7835 | `GOMODCACHE=/home/ranxi/go/pkg/mod make verify` | 通过 |
| 两者 | `git diff --check a957f64d5..<new-head>` | 通过 |

PR1 #7830 current head `6ff28fe4a` 的 16 个 GitHub Actions checks 与 DCO 也已全部成功；Tide 仍只是等待
`lgtm/approved`，不属于 CI 失败。

## 待确认的远端动作

- 对 `feature/multi-component-result-producer` 使用旧 head `1d2ee95c4` 作为 lease，更新到 `98535c541`。
- 对 `feature/multi-component-scale-planning` 使用旧 head `b1c41a584` 作为 lease，更新到 `782232b7d`。
- #7833/#7835 标题和 Draft 状态保持不变；正文只修正依赖 SHA 和本轮真实验证边界。完整草稿见
  [#7833 body](day50-pr7833-body.md) 与 [#7835 body](day50-pr7835-body.md)。
- 不发布评论；推送新 SHA 后由 upstream PR CI 重新验证。

## 当前未决边界

这次只解决 reviewer comparison 被旧 stack 污染的问题，不证明 #7833 的功能切分已经符合维护者 Draft。
#7833/#7835 当前都是 Draft 且没有 human review；重排后应先让 CI 验证新 SHA，再单独决定是否按 Draft
把 interpreter/Flink 从 #7833 拆出。不能把一次干净 rebase 写成 maintainer 已接受现有 PR2/PR3 边界。
