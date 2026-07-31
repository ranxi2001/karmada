# Week 4 简要总结：从证书布局提案转向可验证的轮换路径

日期：2026-06-30 至 2026-07-05

证据截止：2026-07-05 23:59 CST

## 本周主线

本周最大的调整是放下范围过大的 split Secret 实现，转向维护者明确提出的 `karmadactl init` leaf certificate rotation。工作从 issue 方向校准、源码边界设计、最小实现，一直推进到真实证书过期和人工恢复实验。

## 主要成果

| 工作项 | 结果 | 状态 |
| --- | --- | --- |
| 证书布局提案 | 发布 [Issue #7690](https://github.com/karmada-io/karmada/issues/7690)，说明 plan-based split certificate Secret layout，并保留待 maintainer 决策的问题 | 等待方向 |
| 方向纠偏 | 确认 #7690 prototype 范围过大且未完全对齐官方证书框架，暂缓 split-layout PR，转向 [Issue #7693](https://github.com/karmada-io/karmada/issues/7693) 的 leaf rotation | 已完成 |
| 证书轮换实现 | 创建 [PR #7697](https://github.com/karmada-io/karmada/pull/7697)，增加 `karmadactl init --cert-mode=rotate`，复用已有 CA、续签 init-managed leaves，并 update-only 更新既有 Secrets | 进行中 |
| 真实运行验证 | 在三节点 host kind 集群中让 10 分钟 leaf certificates 真实过期，执行 rotate 到 8760h，并通过组件 restart 恢复控制面、两个 Push member 和 APIService | 已完成一次闭环 |
| #7643 真实性验证 | 函数级和默认 Flink interpreter 路径均保持 `100m`，JM+TM 汇总为 `200m`，没有支持 functional bug 结论 | 不开重复 PR |

## 验证与边界

- #7697 的 targeted Go tests、flag/import verifier、staticcheck/lint 和 `git diff --check` 通过；fork push CI 为 16 success、2 skipped、0 failed。
- 实验确认 rotate 会更新 Secret 中的 leaf certificates，但运行中组件不会自动热加载，因此恢复步骤仍需要有序 restart。
- CA、`caBundle`、自动 restart、Helm/operator parity、website runbook 和 external-etcd credential rotation 均不在第一版范围。
- 旧 split-layout prototype 通过 fork CI，只能证明代码可运行，不能证明命名、RBAC 和升级合同已获社区接受。
- #7643 只保留验证证据和评论草稿，本周没有向上游发布未经确认的 functional bug 结论。

## 社区记录

- 本周创建 1 个 Karmada issue：#7690。
- 本周创建 1 个 Karmada PR：#7697；周末仍开放，尚未合并。
- 经确认在 #7697 发布 scope/data-flow 和 runtime validation 两条说明；本地会议 one-pager 没有作为独立 upstream artifact 发布。

## 下周重点

1. 跟进 #7697 CI 和 review，继续核对 CA key 来源、external etcd、原安装参数/SAN 与 restart UX。
2. 将 website 手册、CA migration、Helm/operator parity 拆为后续工作，不扩大当前 PR。
3. 对每个安全声明增加真实证书或 no-mutation regression，避免只靠 mock happy path。

## 证据索引

- [Day 4：#7690 gap 与 #7693 方向纠偏](day4-certificate-layout-issue-follow-up.md)
- [Day 5：#7643 Flink memory 验证](day5-issue-7643-flink-memory-verification.md)
- [Day 6：证书轮换设计与实现](day6-certificate-rotation-design-implementation.md)
- [Day 7：证书轮换社区会议提案](day7-certificate-rotation-community-proposal.md)
- [Day 8：#7697 scope、运行态实验与拆分](day8-after-pr7697-follow-up-pr-split.md)
