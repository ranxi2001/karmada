# Week 3 简要总结：进入 Karmada 并完成第一项 Upstream 贡献

日期：2026-06-24 至 2026-06-29

证据截止：2026-06-29 23:59 CST

> 说明：Karmada 独立实习记录从 6 月 26 日开始。Week 1、Week 2 的主线仍在 AgentCube，对应总结保留在 AgentCube `intern` 分支，本仓库不重复复制。

## 本周主线

本周从 AgentCube 主线切入 Karmada，先完成一个低风险依赖升级 follow-up，再建立多集群传播链路和证书管理方向的基础认知。目标不是快速扩大改动，而是先跑通一次完整的 issue 分析、fork 验证、upstream PR 和合并流程。

## 主要成果

| 工作项 | 结果 | 状态 |
| --- | --- | --- |
| 安装入口默认版本同步 | 提交并合并 [PR #7666](https://github.com/karmada-io/karmada/pull/7666)，同步 Helm、`karmadactl init`、operator、raw manifest 和部署脚本中的 Kubernetes `v1.36.2` 与 etcd `3.6.8-0` 默认值 | 已完成 |
| Karmada 源码与架构入门 | 梳理 `Resource Template + Policy -> Binding -> Work -> member cluster -> status aggregation` 主链，定位 detector、scheduler、binding、execution 和 status 源码入口 | 已完成第一版 |
| 架构图 | 交付 Karmada 架构的 draw.io、PNG 和 SVG 版本，用于后续源码阅读和组件边界校准 | 已完成 |
| 证书任务筛选 | 确认 #6051 是证书命名规范入口，#6670 是标准化背景，#6788 已有 split-layout 实现，不应重复开发 | 已完成初筛 |
| 证书管理层设计 | 形成证书身份、材料、Secret、kubeconfig 和 mount plan 的本地抽象草案，默认保持 legacy，split layout 仅作为候选模式 | 本地设计 |

## 验证与边界

- #7666 的 command-line flags、相关 Go 测试、operator 测试、Helm lint、shell/YAML 检查和 `git diff --check` 均通过；最终合并 commit 为 `f2b734140b`。
- `kubectl dry-run` 受本机无可用 Kubernetes context 阻塞，chart 依赖下载曾遇到 OCI EOF；两项都按环境限制记录，没有误写成代码验证通过或失败。
- 架构结论来自 README、`samples/nginx` 和当前源码入口。本周尚未运行 `hack/local-up-karmada.sh`，因此没有声称真实多集群传播链路已完成运行时验证。
- 证书管理层仍是本地方案，没有在本周发布功能代码或证书 proposal。

## 下周重点

1. 继续沿 #6051 和维护者方向收敛证书问题，不同时覆盖 Helm、operator 和 CLI。
2. 用真实安装或源码级 preflight 校准当前传播链路理解。
3. 对证书 Secret layout 与 leaf certificate rotation 分开建模，先确认社区需求再写代码。

## 证据索引

- [Day 1：#7598 follow-up 与 PR #7666](day1-karmada-7598-default-version-pr.md)
- [Day 2：Karmada 项目理解和源码地图](day2-karmada-project-understanding.md)
- [Day 3：证书管理任务整理](day3-certificate-management-task-triage.md)
