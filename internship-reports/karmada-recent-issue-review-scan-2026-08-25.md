# Karmada 近期 Issue / PR Review 候选扫描（2026-08-25）

## 先说人话

这轮最值得 review 的不是一个，而是两个已经有实现、但还存在正常生产反例的 PR：

1. [PR #7846](https://github.com/karmada-io/karmada/pull/7846) 修复 Job `FailureTarget` 聚合，但一个 member 已失败、另一个 member 仍在运行时，聚合结果会同时出现 `active > 0` 和 `Failed=True`，Kubernetes API server 仍会拒绝这次状态更新。
2. [PR #7824](https://github.com/karmada-io/karmada/pull/7824) 删除传播到 member 的 `ports[*].nodePort`，却漏掉同样由 API server 分配的 `spec.healthCheckNodePort`；`LoadBalancer + externalTrafficPolicy: Local` 仍可能发生端口冲突。它的新 E2E 只检查端口非零，旧实现也能通过，因此没有证明 bug 被修复。

具体例子：一个 Job 被传播到两个集群，`member-a` 已经失败，`member-b` 还有一个 Pod 在运行。#7846 会把两个状态相加得到 `active: 1`，又因为任一集群失败而写入 `Failed=True`。这在业务上是正常的多集群中间态，但对 Kubernetes Job 来说，“已经终态”与“仍有 active Pod”不能同时成立，所以 control plane 还是写不进去。

结论是：先对 #7846、#7824 做完整代码 review；#7843 适合参与设计讨论；#7819 目前只够做证据边界 review，不适合直接认领修复。本轮没有认领 issue、发布 review 或联系 maintainer。

## 扫描边界

- 时间窗口：2026-08-11 至 2026-08-25。
- 代码基线：`karmada-io/karmada@b6c92395e6e9e0678452f22ce2d7242693fb881c`，已用远端 `refs/heads/master` 复核。
- 该窗口共检查 7 个新建 issue：6 个仍 open，1 个已关闭；最新仍 open 的 issue 创建于 8 月 17 日，8 月 18 日之后没有新建且仍 open 的 issue。
- 判断顺序：生产可达性、用户最终结果、现有 owner/PR、human review 是否已经覆盖、是否存在可由源码或反例验证的新增 review 价值。
- CI 状态只作为旁证。绿色 CI 不等于目标故障已经被反事实测试覆盖，单个红 job 也不自动归因于 PR。

| 优先级 | 对象 | 当前归属 | 结论 | 建议动作 |
| --- | --- | --- | --- | --- |
| P0 | [#7844](https://github.com/karmada-io/karmada/issues/7844) / [#7846](https://github.com/karmada-io/karmada/pull/7846) | PR 作者 `@pujitha24`，assignee/reviewer `@whitewindmills` | Job 聚合修复仍会生成 API server 拒绝的多成员中间态 | Review 当前 PR，不重复实现 |
| P0 | [#7823](https://github.com/karmada-io/karmada/issues/7823) / [#7824](https://github.com/karmada-io/karmada/pull/7824) | issue 已分配 `@ADoggg9`，PR reviewer request `@ikaven1024` | 漏删 `healthCheckNodePort`，E2E 不能区分旧、新实现 | Review 当前 PR，不重复实现 |
| P1-design | [#7843](https://github.com/karmada-io/karmada/issues/7843) | 无 assignee、无 PR | Job failover 的静默 no-op 真实，但 reporter 需要的信号不在 Job 对象内 | 先 review API/可观测性合同，不写通用 native interpreter |
| Watch | [#7819](https://github.com/karmada-io/karmada/issues/7819) | 无正式 assignee；作者表示等方向后愿意实现 | 包内生命周期缺口真实，滚动重启 stale overwrite 尚无生产证据 | 要求真实进程、Lease、PATCH 时间线后再定修复 |
| Light | [#7818](https://github.com/karmada-io/karmada/issues/7818) / [#7820](https://github.com/karmada-io/karmada/pull/7820) | 已有作者 PR | 极端资源数量触发整数溢出，机制真实但生产价值低 | 有余力再做边界 review |

## P0：#7846 Job 终态聚合仍不满足全局校验

### 当前补丁解决了什么

#7844 报告的原始问题是真实生产故障：member Job 已有 `Failed=True`，Karmada 的 `ParsingJobStatus` 却只把 `Failed=True` 写回 control plane。Kubernetes 1.32 起默认启用的 Job 状态校验要求失败终态同时带有 `FailureTarget=True`，所以更新被持续拒绝，TTL 和依赖 control-plane Job 终态的逻辑都不能继续。

#7846 当前 head `eb14ddd2eadc28866ab5d543b36e7d1c19d877bf` 已按 `@whitewindmills` 的 review 修复旧 member 兼容性：只要任一 member Job 失败，就无条件合成 `FailureTarget=True` 和 `Failed=True`。这一方向对单 member 失败路径是正确的，现有 compile、unit、lint、codegen 和 E2E matrix 也都通过。

### Finding 1：多 member 中间态仍会被拒绝

`ParsingJobStatus` 先累加所有 member 的 `Active/Succeeded/Failed`，随后只要 `len(jobFailed) != 0` 就写入终态条件。于是下面这个正常状态可达：

```text
member-a: Failed=True, Active=0
member-b: 仍运行, Active=1
aggregated: Active=1, FailureTarget=True, Failed=True
```

Kubernetes v1.36 的 `validateJobStatus` 在 terminal condition 变化或 `active` 变化时启用 `RejectFinishedJobWithActivePods`，并拒绝 `active>0 is invalid for finished job`。证据是 [validation.go](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/apis/batch/validation/validation.go#L520-L534) 和 [strategy.go](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/registry/batch/job/strategy.go#L398-L410)。

这不是 version-skew 特例，而是一个 federated Job 在不同 member 以不同速度结束时的普通中间态。PR 需要先明确聚合合同：是“任一 member 失败即全局失败”，还是“所有 member 进入终态后才写全局 terminal condition”；无论选哪一种，生成的状态都必须能通过目标 API server 校验。最小回归至少应覆盖 `failed member + active member` 和 `failed member + 尚无 status 的 member`。

### Finding 2：现有 fixture 不能证明状态可被 API server 接受

`aggregatestatus_test.go` 的 mixed complete/failed fixture 给失败聚合结果设置了 `completionTime`，同时只有 `Failed=True` 而没有 `Complete=True`。Kubernetes v1.36 会拒绝“没有 `Complete=True` 却设置 `completionTime`”的状态。当前测试只比较 Go 对象，没有经过 API validation，所以它能通过不代表 control-plane status update 能成功。

这说明测试应该覆盖“生成状态满足 API server 全局不变量”，而不只是条件数组中多了一个字段。PR body 也仍停留在首版 `failureTargetClusters` 方案，并把默认受影响版本笼统写成 `>=1.31`；实际默认受影响从 1.32 开始，1.31 只有显式启用 `JobManagedBy` 才触发。

### Review 决策

- 值得现在 review，且不应按 current head 直接批准。
- 首要 finding 是多 member `Active + Failed` 反例；非法 `completionTime` fixture 和陈旧 PR body 是辅助证据。
- 不重复 `@whitewindmills` 已经提出并由作者修复的“旧 member 没有 `FailureTarget`”问题。
- 不抢实现；先让当前作者明确聚合语义并补能验证 API 接受性的回归。

## P0：#7824 Service 端口冲突只修了一半

### 当前补丁解决了什么

#7823 的正常路径是：Karmada control-plane API server 给 Service 分配 `ports[*].nodePort`，Karmada 再把这个具体值传播给 member；若该端口已在 member 占用，Service apply 失败。#7824 current head `b3e79305979efb63d14b2c556b62d09706d48aa8` 在 native prune 中删除所有 `ports[*].nodePort`，让 member 自行分配。

历史 [PR #1811](https://github.com/karmada-io/karmada/pull/1811) 曾加入“各 member NodePort 相同”的 E2E，但讨论没有把它定义为永久 API 合同。当前 `@chaunceyjiang` 已明确允许移除 equality assertion，同时追问用户如何发现各 member 的实际端口。因此，“成员独立分配”方向得到维护者支持，但可观测性合同仍未闭环。

### Finding 1：遗漏 `spec.healthCheckNodePort`

对 `type: LoadBalancer` 且 `externalTrafficPolicy: Local` 的 Service，Kubernetes 还会单独分配 `spec.healthCheckNodePort`：[NeedsHealthCheck](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/api/service/util.go#L87-L93) 定义触发条件，[Service allocator](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/registry/core/service/storage/alloc.go#L481-L512) 在创建时进入分配路径。如果请求中已有非零值，allocator 会尝试占用这个固定端口；端口已被占用时直接返回错误，见 [allocHealthCheckNodePort](https://github.com/kubernetes/kubernetes/blob/v1.36.1/pkg/registry/core/service/storage/alloc.go#L570-L588)。

#7824 只删除 `ports[*].nodePort`，没有删除 `spec.healthCheckNodePort`，所以 reporter 的 LoadBalancer 场景仍有同类失败路径。Karmada 当前 [retain.go](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/pkg/util/lifted/retain.go#L35-L64) 已明确把 `healthCheckNodePort` 视为“由 API server 分配且不可修改”的 member 字段，并在更新时保留 observed 值。这给出了现有生命周期边界：首次创建前 prune，后续更新 retain member 已分配值。

最小修复范围应同时考虑 `healthCheckNodePort`，并覆盖 `LoadBalancer + externalTrafficPolicy: Local`。这不是为极端配置扩展职责，而是 issue 作者明确使用的 LoadBalancer 正常路径。

### Finding 2：新 E2E 对旧实现也会通过

修改后的 E2E 只断言每个 member 的 `nodePort > 0`。在没有预先制造端口冲突的环境里，旧实现会把 control-plane 分配的同一个非零端口传播到所有 member，也能满足这个断言。

有效反事实测试应先拿到 control plane 分配的端口 `N`，在一个 member 用 blocker Service 占用 `N`，再启动传播，并断言目标 Service 在该 member 创建成功、拿到不同端口且 binding 为 `FullyApplied=True`。`healthCheckNodePort` 应有对应的 LoadBalancer/Local 冲突用例；按当前 head，该用例会失败。

### Review 决策

- 值得现在 review，且不应按 current head 直接批准。
- 首要 finding 是 `healthCheckNodePort` 的同类生产缺口；第二 finding 是 E2E 没有反事实能力。
- 用户显式指定固定 `nodePort` 会被无条件删除，这是行为变化；维护者已接受移除 equality assertion，但仍应在 release note/文档或 follow-up 中明确可发现性，而不是把 control-plane 值误当成 member 实际值。
- v1.35 E2E 红灯位于相邻功能且 v1.34/v1.36 通过，看起来像 flake，但公开证据不足以独立确认根因；本报告不把它归因于补丁，也不宣称已经排除。

## P1-design：#7843 是真实 no-op，但 Job 本身不够做决策

当前 native health interpreter 列表没有 `batch/v1 Job`。缺少 hook 时，status controller 把资源视为 Healthy，而 application failover controller 的 `bindingFilter` 直接返回 false。因此用户给 Job 配置 `failover.application` 时，不会报配置错误，也不会触发 failover：见 [healthy.go](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/pkg/resourceinterpreter/default/native/healthy.go#L31-L45)、[work status controller](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/pkg/controllers/status/work_status_controller.go#L393-L410) 和 [application failover filter](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/pkg/controllers/applicationfailover/rb_application_failover_controller.go#L228-L242)。

但 reporter 想区分“Pending，因为 autoscaler 正在扩容”和“永久 Unschedulable”。两者在 Pod 上都可能只有 `PodScheduled=False/Unschedulable`；可靠信号来自 Karpenter `NodeClaim`、GKE autoscaler annotation/event 等外部、非可移植状态，而 Lua/native Job interpreter 只收到 Job 对象。

因此这项值得做设计 review，不值得直接实现一个声称通用的 Job interpreter。应拆成两个问题：

1. 当 `failover.application` 没有可用 `InterpretHealth` hook 时，如何让用户看到配置不会生效，而不是静默 no-op。
2. 是否需要允许 interpreter 访问关联 Pod/外部 autoscaler 状态；若需要，权限、缓存一致性、provider 差异和超时合同是什么。

在第二项没有共识前，ResourceInterpreterWebhook 是现有可行边界。

## Watch：#7819 证明包内缺口，未证明滚动重启覆盖

#7819 的 fake-client 测试能证明：`Scheduler.Run` 关闭 queue 后不 join 已开始的 worker，调度和 PATCH 路径又使用 `context.TODO()`，所以 `Run` 返回后包内 goroutine 仍可能继续写。这一局部生命周期缺口真实存在。

但默认二进制启用 leader election。SIGTERM 取消 context 后，client-go 随后调用 `OnStoppedLeading`，Karmada 执行 `klog.Fatalf` 并退出进程；同时 `ReleaseOnCancel` 没有开启，新 scheduler 要等 Lease 过期才能接管。源码见 [scheduler Run](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/pkg/scheduler/scheduler.go#L311-L381) 和 [leader-election callback](https://github.com/karmada-io/karmada/blob/b6c92395e6e9e0678452f22ce2d7242693fb881c/cmd/scheduler/app/scheduler.go#L224-L235)。

所以 issue 的测试省略了真实进程退出和 Lease 交接，尚不能证明“旧 scheduler 在新 leader 之后提交 stale PATCH”。下一步证据应来自两个真实 scheduler 进程、真实 Lease 和可记录/延迟 PATCH 的 API server 或代理，明确旧进程退出、Lease acquisition、两次 PATCH 的 server commit/resourceVersion 顺序。在此之前，只能把潜在 PR 描述为 context/lifecycle cleanup，不能宣称修复了生产 stale overwrite。

## 低价值或已占用项

- [#7818](https://github.com/karmada-io/karmada/issues/7818) / [#7820](https://github.com/karmada-io/karmada/pull/7820)：`replicas * resource` 的 `int64` 溢出机制真实，但 issue 使用 `3 x 4Ei` 的极端资源量，且 `Quantity.Value/MilliValue` 本身还有更广的溢出边界。适合轻量 correctness review，不应挤占前两个生产路径。
- [#7826](https://github.com/karmada-io/karmada/issues/7826)：已分配给 `@ranxi2001`，并有现有 PR #7827，是自己的进行中任务，不作为新的 review 候选。
- [#7831](https://github.com/karmada-io/karmada/issues/7831)：backport 任务已关闭，不再投入。

## 下一步

1. 先对 #7846 current head 做完整 review，主 finding 只聚焦 `failed member + active member` 产生非法终态；同时指出 fixture 未经过 API validation。
2. 再 review #7824，聚焦 `healthCheckNodePort` 和无法区分旧/新实现的 E2E；不要重复讨论已经被 maintainer 接受的 equality assertion 移除。
3. #7843 只准备设计问题清单；#7819 等生产级交接时间线，不认领实现。
4. 任何 upstream review/comment 的 exact English text 都在用户确认目标和文本后另行准备与发布。
