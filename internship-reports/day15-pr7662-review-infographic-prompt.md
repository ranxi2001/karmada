请生成一张 16:9、1672x941 的中文技术信息图，主题是：

「为什么 Karmada PR #7662 还不能直接进入实现」

用途：帮助刚接触 Kubernetes controller 的 junior 工程师理解一次成熟开源项目的 proposal review。画面必须专业、克制、清晰，像 CNCF/Kubernetes 架构评审材料，而不是营销海报。

视觉要求：
- 白色或极浅灰背景，使用蓝、绿色、黄色、红色作为语义色；不要深色底，不要紫色渐变，不要米黄色主题。
- 采用从左到右的三栏布局，栏之间用细箭头或分隔线连接；所有重要信息在一屏内完整可读。
- 中文必须大而清楚，文字少而准确；不要生成英文乱码、伪代码长段落、装饰性小字、品牌 Logo 或人物。
- 用简洁的 Kubernetes 资源方框、集群圆柱/节点、Controller 齿轮和箭头表达关系；图标只辅助理解。
- 红色叉表示“已有代码路径可反证”，绿色对勾表示“仅在明确前提下成立”，黄色警告表示“设计合同缺失”。

顶部：
- 主标题：「为什么 #7662 还不能直接进入实现」
- 副标题：「Safe Rescheduling Proposal：三个必须先闭合的安全合同」

第一栏，标题：「1  PreserveReady 不是通用策略」
用紧凑矩阵展示：
- Duplicated：10 / 10 / 10，红色叉
- Static 1:1:8：1 / 1 / 8，红色叉
- Aggregated / Dynamic：仅 Steady 且 ready 集群仍 eligible，绿色对勾，并标注「有条件成立」
- Fresh 或 ready 集群被过滤，红色叉
栏底结论：「必须声明支持的调度模式，并 fail closed」

第二栏，标题：「2  两个控制器同时写 Binding」
上半部分画理想时序，绿色细箭头：
「保留 Source」→「打开 Target」→「等待 stableWindow」→「缩容 Source」
下半部分画真实冲突，红色箭头：
「SafeMigration 修改 Binding.spec.clusters」→「触发 Scheduler 重算」→「dynamicScaleDown」→「Source 可能提前缩容」
旁边放黄色说明：
「GracefulEvictionTasks 能暂留整个 Source Work，但没有 unit identity / stableWindow」
栏底结论：「先定义单一状态源和唯一写入者」

第三栏，标题：「3  删除不等于取消」
上半部分画危险路径，红色箭头：
「Running WR」→「用户直接 delete」→「无 finalizer」→「WR 消失」
在末端保留一个孤立的 Binding 方框，并标注：「副作用仍在」
下半部分画正确的删除合同，绿色箭头：
「finalizer」→「deletionTimestamp 锁定取消」→「恢复安全状态」→「移除 finalizer」
栏底结论：「长事务必须定义 direct deletion」

底部做一条醒目的深灰结论带，文字必须完整准确：
「先明确单一状态源、支持的调度模式和删除合同，再进入实现。」

整体层级：标题最大，三栏标题次之，流程标签和数字清晰可读，结论最醒目。不要添加本提示词之外的新技术结论。
