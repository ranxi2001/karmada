# 实习生术语扫盲

日期：2026-06-26

这份文件用于沉淀 Karmada 实习过程中反复遇到的工程术语。目标不是写百科，而是让以后读 PR、issue、设计文档和源码时，能快速知道一个词在系统里承担什么角色。

> 使用方式：先按等级读。L0 / L1 是读懂 Karmada 文档的最低前置；L2 / L3 是理解调度、传播、控制器和多集群状态的核心；L4 用于做测试设计、社区 review 和生产化分析。
>
> 更新规则：如果一个术语在日报、PR review、设计文档里反复出现，或者不解释就会影响判断，应补到这里。解释要优先回答“它是什么、为什么在 Karmada 里重要、容易误解什么”，不要只翻译英文。

## L0：先能读懂项目文档

| 术语 | 简明解释 | 在 Karmada 里的意义 |
| --- | --- | --- |
| Kubernetes / K8s | 容器编排系统 | Karmada 复用 Kubernetes API 体系，把单集群资源扩展到多集群管理 |
| multi-cluster | 多个 Kubernetes 集群协同工作 | Karmada 的核心场景是跨云、跨地域、边缘和混合云集群统一编排 |
| control plane | 控制面 | Karmada API Server、Controller Manager、Scheduler 等组成 Karmada 控制面 |
| host cluster | 承载 Karmada 控制面的 Kubernetes 集群 | Quick Start 脚本会创建 host cluster 来运行 Karmada 组件 |
| member cluster | 被 Karmada 管理的业务集群 | 工作负载最终被分发到 member clusters |
| kubeconfig | kubectl 访问集群的配置文件 | Karmada 本地环境会产生 control plane、host、member clusters 等多个 context |
| kubectl | Kubernetes 命令行工具 | 可直接访问 Karmada API Server，因为 Karmada 暴露 Kubernetes-native API |
| karmadactl | Karmada CLI | 用于初始化、加入集群、解释资源等 Karmada 专用操作 |
| Helm chart | Kubernetes 应用打包模板 | `charts/` 下保存 Karmada 和 operator 的安装模板 |

## L1：Kubernetes API 与控制器基础

| 术语 | 简明解释 | 在 Karmada 里的意义 |
| --- | --- | --- |
| API Server | Kubernetes API 入口 | Karmada API Server 存储和暴露 Karmada 资源对象 |
| etcd | Kubernetes API Server 背后的持久存储 | 保存 Karmada control plane 对象 |
| CRD | CustomResourceDefinition，自定义资源定义 | Karmada 的 Cluster、PropagationPolicy、ResourceBinding、Work 等都通过 API 类型扩展表达 |
| CR | 某个 CRD 的具体对象 | 一个 PropagationPolicy 或 Work 对象就是一个 CR |
| controller | 持续观察对象并让实际状态接近期望状态的控制器 | Karmada controller-manager 中的 policy、binding、execution、status controller 都按这个模式工作 |
| reconcile | controller 的核心循环 | 对象变化后控制器重新计算并修正资源状态 |
| informer | Kubernetes 客户端缓存和事件机制 | 控制器依赖 informer 监听对象变化，避免直接高频打 API Server |
| lister | 从 informer cache 查询对象的接口 | 控制器常用 lister 获取当前缓存状态 |
| workqueue | controller 的任务队列 | 对象事件通常先进入队列，再由 worker 调用 reconcile |
| ownerReference | Kubernetes 对象归属关系 | 用于资源清理和对象关系追踪 |
| status | 资源的观测状态 | Karmada 需要汇总 member cluster 结果并更新到 control plane 视图 |

> 注释：CRD 是声明式资源，不是同步函数调用。创建 PropagationPolicy 只是写入期望状态，真正分发到 member clusters 要等待多个 controller reconcile。

## L2：Karmada 核心资源

| 术语 | 简明解释 | 在 Karmada 里的意义 |
| --- | --- | --- |
| Resource Template | 原生 Kubernetes 资源模板 | 用户仍然提交 Deployment、Service 等熟悉资源，Karmada 再决定传播位置 |
| PropagationPolicy | 命名空间级传播策略 | 描述哪些资源要传播到哪些集群，以及调度约束 |
| ClusterPropagationPolicy | 集群级传播策略 | 作用范围比 PropagationPolicy 更大，适合 cluster-scoped resources 或全局策略 |
| OverridePolicy | 命名空间级差异化覆盖策略 | 针对不同集群改 image、replicas、StorageClass 等字段 |
| ClusterOverridePolicy | 集群级覆盖策略 | 全局范围的 override 规则 |
| ResourceBinding | 单个资源模板的调度绑定结果 | 连接 resource template、policy 和目标集群分配结果 |
| ClusterResourceBinding | 集群级资源的绑定结果 | 类似 ResourceBinding，但用于 cluster-scoped resource |
| Work | 发往某个 member cluster 的实际工作载体 | execution controller 根据 Work 在 member cluster 创建或更新真实资源 |
| Cluster | Karmada 管理的成员集群对象 | 描述 member cluster 的 API endpoint、状态、资源和调度属性 |
| ResourceInterpreter | 资源解释器 | 帮助 Karmada 理解自定义资源的副本数、依赖、状态和健康语义 |
| ResourceDetector | 资源探测器 | 监听资源模板与传播策略，匹配成功后创建待调度的 ResourceBinding 或 ClusterResourceBinding；旧概览中相近职责可能称为 Policy Controller |
| Binding Controller | 绑定控制器 | 读取已调度 Binding，应用 Override，并为每个目标集群生成 Work |
| Execution Controller | 执行控制器 | 读取 Work，把其中 manifests 创建、更新或删除到成员集群；它不负责生成 Work |

> 分析：Karmada 的关键链路可以先粗略理解为：用户提交资源模板和 policy，ResourceDetector 生成待调度 binding，karmada-scheduler 写入放置结果，Binding Controller 生成 Work，Execution Controller 再下发到 member cluster。

## L3：调度、传播与状态

| 术语 | 简明解释 | 在 Karmada 里的意义 |
| --- | --- | --- |
| placement | 资源应该放到哪些集群 | PropagationPolicy 的核心决策内容 |
| cluster affinity | 集群亲和性 | 按 region、provider、label、字段等选择目标集群 |
| spread constraint | 分散约束 | 控制副本或资源跨 region/zone/cluster 分布 |
| replica scheduling | 副本调度 | 决定 Deployment 等多副本 workload 在不同集群的副本数 |
| karmada-scheduler | 多集群调度器 | 把资源放到合适的成员集群，并可分配跨集群副本；决策层级是资源到集群 |
| member kube-scheduler | 成员集群的 Kubernetes 调度器 | 把待调度 Pod 绑定到该成员集群的 Node；决策层级是 Pod 到 Node |
| scheduler estimator | 调度估算器 | 帮助 scheduler 估算 member cluster 是否能承载资源 |
| failover | 故障转移 | member cluster 异常时迁移或重建工作负载 |
| graceful eviction | 优雅驱逐 | 在迁移或重平衡时尽量降低业务中断 |
| work propagation | 工作负载传播 | 把 control plane 中的期望资源下发到 member clusters |
| status aggregation | 状态聚合 | 从多个 member clusters 汇总资源状态并呈现给用户 |
| Multi-Cluster Service | 多集群服务发现能力 | Karmada 支持跨集群服务发现和相关 MCS API |

## L4：测试、贡献与生产化

| 术语 | 简明解释 | 在 Karmada 里的意义 |
| --- | --- | --- |
| e2e test | 端到端测试 | 验证真实或近真实 Karmada 部署、资源传播、调度和清理 |
| flaking test | 偶发失败测试 | 多集群、异步 controller、网络和时间等待都容易导致 flake |
| conformance | 一致性测试 | 验证行为是否符合 Kubernetes 或 Karmada 预期契约 |
| compatibility | 兼容性 | Karmada 需要兼容多个 Kubernetes 版本 |
| `make verify` | 仓库验证入口 | PR 前必须重点关注的本地检查之一 |
| `make test` | 仓库测试入口 | PR 前必须重点关注的测试之一 |
| OWNERS | 代码评审责任配置 | 找 review owner、理解模块归属时需要查看 |
| DCO / signoff | 开源提交签署规则 | 若项目要求，commit 需要 `Signed-off-by` |
| cleanup | 清理 | e2e 或本地部署后要确认 cluster、context、Work、member resources 没有残留 |
| 组件身份证书 / leaf certificate | 组件用于证明自己 TLS server/client 身份的证书，由 CA 签发，有具体 CN/O/SAN 和过期时间 | #7693 第一版证书轮换目标是重新签发这些组件身份证书，例如 apiserver server cert、client kubeconfig cert、front-proxy-client cert、etcd server/client cert |
| CA / root certificate | 签发并背书其他证书的根或中间证书，是信任链基石 | 第一版证书轮换不轮转 CA/root certificates；改变 CA 会影响 kubeconfig、WebhookConfiguration、APIService、CRD conversion caBundle 和组件间 TLS 信任链，属于单独的信任根迁移问题 |

## 常见对照关系

| 容易混淆的词 | 区别 |
| --- | --- |
| host cluster vs member cluster | host cluster 运行 Karmada 控制面；member cluster 运行最终业务资源 |
| Karmada API Server vs member cluster API Server | 前者存储 Karmada control plane 对象；后者是真实业务集群 API |
| PropagationPolicy vs ResourceBinding | policy 是用户期望；binding 是针对单个资源计算后的绑定结果 |
| ResourceBinding vs Work | binding 表示调度结果；Work 是下发到某个 member cluster 的资源载体 |
| OverridePolicy vs PropagationPolicy | propagation 决定放到哪里；override 决定在某个集群里怎么改 |
| controller vs scheduler | controller 负责状态推进和对象创建；scheduler 负责放置和副本分配决策 |
| karmada-scheduler vs member kube-scheduler | 前者决定资源去哪些集群、各集群多少副本；后者决定一个 Pod 去该集群中的哪个 Node |
| ResourceDetector vs Binding Controller vs Execution Controller | ResourceDetector 做资源与策略匹配并建 Binding；Binding Controller 把调度结果变成 Work；Execution Controller 把 Work 应用到成员集群 |
| status aggregation vs propagation | propagation 是把期望下发出去；status aggregation 是把实际状态收回来 |
| 组件身份证书 vs CA/root 证书 | 组件身份证书是被轮转的对象；CA/root 证书是签发者和信任根，第一版不轮转、不更新 caBundle |

## 后续追加优先级

1. 影响读懂 Karmada README、docs、samples 的词。
2. 影响源码阅读和 controller/scheduler 流程判断的词。
3. 影响 issue/PR review、测试设计和社区讨论的词。
4. 只出现一次、短期不会复用的词可以先不加。
