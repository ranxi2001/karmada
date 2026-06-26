# Day 1：Karmada #7598 依赖升级 follow-up 和 upstream PR

日期：2026-06-26

## 今日目标

围绕 Karmada umbrella issue [#7598](https://github.com/karmada-io/karmada/issues/7598) 做一次低风险 upstream 贡献练习：分析 Kubernetes v1.36 依赖升级后还有哪些安装入口默认版本没有同步，并完成 PR 准备、fork 验证和 upstream PR 提交。

## 阅读和分析

- 阅读 issue #7598，确认它是 `Bump Kubernetes dependency from v1.35 to v1.36` 的 umbrella issue。
- 对照已经合并的相关 PR，确认 Go、Kubernetes 依赖、kind、CI matrix、README 等主体升级已经完成。
- 参考历史 PR [#7229](https://github.com/karmada-io/karmada/pull/7229)，确认这类 follow-up 通常会同时更新 Helm chart、`karmadactl init`、`karmada-operator` 等安装工具里的默认 Kubernetes / etcd 版本。
- 最后补充检查发现 `artifacts/deploy/karmada-etcd.yaml` 和 `hack/deploy-karmada.sh` 也属于安装入口，需要一起同步。

## 代码改动

正式 PR：[#7666](https://github.com/karmada-io/karmada/pull/7666)

分支：`test/update-default-control-plane-images`

本次同步的默认版本：

- `kube-apiserver`: `v1.35.2` -> `v1.36.2`
- `kube-controller-manager`: `v1.35.2` -> `v1.36.2`
- `etcd`: `3.6.6-0` -> `3.6.8-0`
- `hack/deploy-karmada.sh` 原默认 `KARMADA_APISERVER_VERSION` 是 `v1.35.0`，同步改为 `v1.36.2`

涉及文件：

- `charts/karmada/values.yaml`
- `pkg/karmadactl/cmdinit/cmdinit.go`
- `pkg/karmadactl/cmdinit/kubernetes/deploy.go`
- `docs/command-line-flags/karmadactl_init.md`
- `operator/pkg/constants/constants.go`
- `operator/config/samples/karmada.yaml`
- `operator/config/samples/karmada-sample.yaml`
- `artifacts/deploy/karmada-etcd.yaml`
- `hack/deploy-karmada.sh`

## 验证记录

已通过：

- `hack/verify-command-line-flags.sh`
- `go test ./pkg/karmadactl/cmdinit ./pkg/karmadactl/cmdinit/kubernetes -count=1`
- `go test ./operator/...`
- `helm dependency build charts/karmada && helm lint charts/karmada`
- `bash -n hack/deploy-karmada.sh`
- `ruby -e 'require "yaml"; YAML.load_stream(File.read("artifacts/deploy/karmada-etcd.yaml")); puts "deploy yaml ok"'`
- `git diff --check upstream/master...HEAD`

有环境限制但已定位：

- `kubectl apply --dry-run=client --validate=false -f artifacts/deploy/karmada-etcd.yaml` 在本机失败，因为当前没有可用 Kubernetes API context，`kubectl` 仍尝试访问 `localhost:8080` 做 discovery。这个失败不代表 YAML 格式问题。
- `make package-chart VERSION=test-default-images` 早先因 Docker Hub / OCI 拉取 `bitnamicharts/common` 出现 EOF，后续改用 `helm dependency build charts/karmada && helm lint charts/karmada` 验证通过。
- `go test ./pkg/karmadactl/cmdinit/...` 早先只有 `pkg/karmadactl/cmdinit/utils` 的 `TestInternetIP` 受本地外网/IP 查询影响失败；本次相关包定向测试通过。

## PR 流程记录

- 创建 fork 验证 PR：<https://github.com/ranxi2001/karmada/pull/1>
- 一开始误把改动拆成 `karmadactl init` 和 `karmada-operator` 两个 fork PR，后来对照 #7229 发现三个安装入口一起提更符合维护者习惯，于是关闭拆分 PR，reopen 合并版 PR。
- 创建 upstream PR：<https://github.com/karmada-io/karmada/pull/7666>
- 最后补充 `artifacts/deploy/karmada-etcd.yaml` 和 `hack/deploy-karmada.sh` 后 amend 到同一个 commit，并 force-with-lease 更新 PR。

## 学到的点

- Karmada 里默认镜像版本分散在多个安装入口：Helm chart、CLI、operator、raw manifests 和部署脚本都可能需要同步。
- 做依赖升级 follow-up 时，不能只搜索一个路径；应该以“用户从哪些入口安装控制面”为线索做覆盖检查。
- fork CI 可能和 upstream CI 不完全一样。例如 fork 没有 tag 时，`git describe --tags` 会影响 operator e2e 中 Karmada 组件版本解析。
- PR 标题和正文最好贴近历史 PR 风格。#7229 的标题和 release-note 格式可作为同类 follow-up 的模板。

## 下一步

- 等待 upstream PR #7666 的 GitHub Actions 结果。
- 如果 CI 失败，先区分代码问题、环境抖动、fork/upstream 环境差异，再决定是否修改。
- 继续 Day 1 原计划的 Quick Start 预检或把它顺延到 Day 2，补本地 kind/Docker/kubeconfig 状态记录。
