# Week 5 简要总结：稳定 CI 环境并建立 Flake 证据链

日期：2026-07-06 至 2026-07-10

证据截止：2026-07-10 23:59 CST

## 本周主线

本周一条线继续维护 #7697，另一条线把一次 runner 更新和几次 E2E 红灯拆成可验证的 CI 环境治理与 flake 调查。重点从“重跑后绿了”转向区分代码错误、控制面瞬时失稳、异步状态窗口和真正可修复的同步缺口。

## 主要成果

| 工作项 | 结果 | 状态 |
| --- | --- | --- |
| Ubuntu runner 固定 | Karmada [#7728](https://github.com/karmada-io/karmada/pull/7728) 将 18 个 workflow、30 处 runner 更新到 Ubuntu 24.04；Dashboard #643 与 Website #1036 同步完成 | 3 个 PR 已合并 |
| #7697 CI 维护 | 通过 signed-off 空提交重触发后，lint、codegen、compile、unit、三版本 E2E 及 Chart/CLI/Operator matrix 全绿 | 等待 review |
| Flink cleanup flake | 从 #7697 的偶发红灯拆出 [Issue #7719](https://github.com/karmada-io/karmada/issues/7719) 和 [PR #7732](https://github.com/karmada-io/karmada/pull/7732)，补齐 member CRD 与 `Cluster.Status.APIEnablements` cleanup barrier | 周内提交，等待 review |
| CI flake 台账 | 扫描 598 个 upstream runs，识别 32 个 failed runs 和 72 条非成功 job；严格门槛下只确认 4 个高置信样本、3 类 flake | 已建立第一版 |
| 其他 PR 深读 | 深读 #7692 的传播 cleanup barrier 和 draft #7663 的 bearer-token hot reload，并运行 #7663 focused tests | 只读 review |

## 验证与边界

- #7728 完成 workflow YAML 解析、旧 runner label 清零、`git diff --check` 和 fork CI；首轮 v1.35 红灯追到 etcd/API 503，重跑完整矩阵通过，没有为无关 flake 修改 workflow diff。
- #7732 第一版等待点在三版本 E2E 中稳定失败，说明同步条件选错；修正为等待真实 consumer 所需的 CRD cleanup 和 APIEnablements 后，fork/upstream CI 全绿。
- #7663 的 token-refresh focused tests 本地通过，但该 PR 仍由原作者和 reviewer 推进，本周没有重复认领或评论。
- 37 条 schedule/compatibility 非成功记录仍缺 first-hard-failure 分类；Remedy 只有新样本，尚不足以在本周提出产品修复。
- #7732 当时达到源码贯通的 E3，但没有确定性重放 420 秒链路的完整系统 E4，不能从一次绿色重跑外推 flake 已完全消失。

> 后续闭环：#7732 于 2026-07-13 合并为 `d0714678fe18`，#7719 随之关闭；这项 merge 计入 Week 6，不回算 Week 5 活动指标。

## 社区记录

- 周内合并本人 PR：Karmada #7728、Dashboard #643、Website #1036，共 3 个。
- 周内创建 flake issue/PR：#7719、#7732。
- 社区扫描接受“近期小 issue 多数已有认领或 PR”的结果，没有为了数量重复抢任务。

## 下周重点

1. 继续按 first hard failure、producer、consumer、queue/retry 和 recovery event 补齐 flake RCA。
2. 跟进 #7732 maintainer review，并将同步条件与实际断言保持一致。
3. 继续维护 #7697，但不把 runner 或测试环境红灯自动归因到证书代码。

## 证据索引

- [Day 9：社区扫描、#7697 CI 与 Flink cleanup 原型](day9-community-issue-pr-ci-watch.md)
- [Day 10：Ubuntu runner 升级与 #7728](day10-ci-ubuntu-runner-upgrade.md)
- [Day 11：Karmada CI Flake 专项统计](day11-ci-flake-statistics.md)
