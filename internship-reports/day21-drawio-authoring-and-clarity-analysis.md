# Day 21 - Day 15 绘图方式与清晰度分析

日期：2026-07-15

## 今日目标

复盘 Day 15 的两张 #7621 / #7662 架构图是如何在当时的 Linux 环境中产生的，区分以下三个问题：

1. 报告中看到的 PNG/SVG 是由什么源文件渲染的？
2. `.drawio` 和 `.mmd` 当时如何维护，是否真正同步？
3. 即使维护方式不理想，为什么最终图片仍然清晰、有效？

## 结论

用户认为 Day 15 的图清晰，这个判断成立。视觉检查和结构校验都支持这一点。

需要修正的是 provenance，而不是视觉质量：Day 15 报告中的两张 PNG/SVG 是 Mermaid fallback 的渲染结果，不是 Ubuntu 上由 draw.io CLI 导出的图片；`.drawio` 是同一轮分析中并行编写的可编辑版本。两套源共享核心叙事，但并非自动转换，也不是严格一一对应。

> 分析：图是否清晰，和源文件是否易维护，是两个独立维度。Day 15 在“成图表达”上成功，在“双源同步”上留下维护风险。不能因为后者存在，就反向否定前者。

## 分析对象

### 当前路径与提案路径

![#7621 current and proposed architecture](day15-issue-7621-current-proposed-flow.png)

- [PNG](day15-issue-7621-current-proposed-flow.png)
- [SVG](day15-issue-7621-current-proposed-flow.svg)
- [Mermaid presentation source](day15-issue-7621-current-proposed-flow.mmd)
- [Editable draw.io parallel source](day15-issue-7621-current-proposed-flow.drawio)

### PR #7662 在 Karmada 中的组件定位

![PR #7662 component position in Karmada](day15-pr7662-karmada-component-position.png)

- [PNG](day15-pr7662-karmada-component-position.png)
- [SVG](day15-pr7662-karmada-component-position.svg)
- [Mermaid presentation source](day15-pr7662-karmada-component-position.mmd)
- [Editable draw.io parallel source](day15-pr7662-karmada-component-position.drawio)

这些是 Day 15 原有资产，本报告只复用和分析，没有创建新的 Day 21 图片。

## Provenance 证据

| 证据 | 结果 | 说明 |
| --- | --- | --- |
| Day 15 失败与绕过记录 | 当时 Linux 环境没有 draw.io / Graphviz CLI | 保留 `.drawio` 与 `.mmd`，使用 Mermaid remote renderer 生成 PNG/SVG |
| 两个 SVG 的 metadata | 都包含 `aria-roledescription="flowchart-v2"` 和 `mermaid` 标记 | 证明报告中的 SVG 来自 Mermaid renderer |
| PNG 内容与 `.mmd` 标签、分组和布局 | 一致 | PNG 的 presentation source 是 `.mmd` |
| 第一个文件对的创建 commit | `0ee1d9657`，2026-07-13 | `.drawio`、`.mmd`、PNG、SVG 同一 commit 加入 |
| 第二个文件对的创建 commit | `6084841ad`，2026-07-14 | `.drawio`、`.mmd`、PNG、SVG 同一 commit 加入 |
| `drawio2mermaid.py` 引入 commit | `940492efb`，2026-07-14 | 两张图创建时还没有该转换工具，因此不是脚本生成的双源 |

Day 2 的 draw.io 原生 PNG/SVG 则来自 Windows 用户级安装：

```text
C:\Users\ranxi\AppData\Local\Programs\draw.io\draw.io.exe
```

因此不能把 Day 2 的原生导出过程推广成 Day 15 的 Ubuntu 过程。

## 当时的实际工作流

Day 15 使用的是 narrative-first 的人工双写方式：

1. 从 #7621、#7662 proposal 和源码分析中提取共同语义模型：组件、阶段、状态写入者、控制流和未解决风险。
2. 先确定每张图只回答一个问题：
   - 图一回答“当前路径和 proposal 执行路径有什么差别”。
   - 图二回答“#7662 位于 Karmada 哪一层，不替代哪些现有组件”。
3. 人工写 `.mmd`，依靠 Mermaid 自动布局得到适合报告阅读的 PNG/SVG。
4. 人工写 `.drawio` XML，保存可编辑形状、坐标、颜色、容器和连接线。
5. 使用 `validate.py --strict` 检查 `.drawio` 的 XML、parent、edge、重叠和交叉问题。
6. 视觉检查 Mermaid PNG，把过长节点文案拆行，并把风险从主执行流中移到独立区域。

这不是下面两种自动工作流：

```text
.mmd -> draw.io CLI >= 30 -> .drawio
.drawio -> drawio2mermaid.py -> .mmd
```

当时两个方向都没有执行。

## 为什么第一张图清晰

第一张图把一个复杂 proposal 拆成三个视觉区域：

- 顶部灰色虚线区域是 decision plane，明确标记“#7621 需要，但 #7662 不负责”。
- 左侧蓝色区域是当前 master 路径，保持单一的自上而下主链。
- 中间绿色区域是 proposal 执行层，用 strategy diamond 分出 Full、PreserveReady 和 SafeMigration。
- 右侧红色区域集中列出尚未解决的 safety contract，没有让风险节点打断正常执行流。

它清晰的具体原因：

1. **先划 scope，再画流程。** 读者第一眼先知道哪些内容属于当前 proposal，哪些不属于。
2. **Current / Proposed 形成稳定比较。** 蓝色和绿色不是装饰，而是两套行为的固定语义。
3. **主路径保持垂直。** 当前链和 SafeMigration 链都能从上往下连续阅读。
4. **分支点只有一个。** `Strategy executor` 使用 diamond，避免每个 executor 都和 lifecycle controller 直接形成杂乱连线。
5. **风险独立成列。** 红色节点通过虚线连接到相关阶段，既保留上下文，又不抢占主路径。
6. **节点写行为，不只写组件名。** 例如 `remove orphan Works then ensure target Works`、`only after target is stable`，读图本身就能理解行为差异。
7. **留白充足。** 复杂图有足够的 routing corridor，没有出现节点堆叠或大面积交叉。

视觉上的主要限制是画布较宽，缩略图中文字会变小；它更适合在报告中点击原图阅读，而不是放在窄栏中一次看完。

## 为什么第二张图清晰

第二张图不是把所有 controller 放在一个平面，而是建立四个编号区域：

1. Decision & Intent
2. Proposed Rebalancing Orchestration
3. Existing Karmada Control Plane
4. Member Clusters & Async Feedback

它清晰的关键点：

1. **组件定位先于实现细节。** 读者能先判断 #7662 是 orchestration layer，而不是 scheduler replacement。
2. **共享状态位于视觉中心。** `ResourceBinding / ClusterResourceBinding` 使用黄色，承担 scheduler、WR executor、Binding Controller 和反馈路径的交汇点。
3. **现有与新增职责分色。** 蓝色是现有 Karmada，绿色是 proposal，黄色是共享 API state，灰色是 out of scope，红色是 unresolved contract。
4. **反馈闭环完整。** 图不只画 intent -> execution，也画 member status -> Binding aggregatedStatus -> WR controller。
5. **关键结论直接写在图上。** 右侧 component-position note 明确说明 #7662 不替代 Scheduler、Binding Controller、Work 或 execution path。
6. **风险连接到真实冲突点。** unresolved writer contract 同时关联 WR executor、scheduler 和 Binding，而不是成为没有上下文的警告框。

这张图的代价是跨区域连线更长，完整尺寸为 `3043 x 2206`；在原图中层次清楚，但在聊天缩略图中需要放大。这个取舍对架构定位图是合理的。

## 结构化检查

对两个 `.drawio` 执行当前 v1.34.0 validator：

```text
python3 .agents/skills/drawio-skill/scripts/validate.py \
  internship-reports/day15-issue-7621-current-proposed-flow.drawio \
  --strict --score

0 error(s), 0 warning(s)
score: 0 (0 through-vertex, 0 crossings, 0 overlaps)
```

```text
python3 .agents/skills/drawio-skill/scripts/validate.py \
  internship-reports/day15-pr7662-karmada-component-position.drawio \
  --strict --score

0 error(s), 0 warning(s)
score: 0 (0 through-vertex, 0 crossings, 0 overlaps)
```

`explain.py` 提取结果：

| 图 | Components | Relations |
| --- | ---: | ---: |
| Current vs proposed | 23 | 23 |
| Component position | 25 | 23 |

> 注释：validator 的 `score: 0` 只说明 XML 几何中没有检测到穿过节点、交叉和重叠，不等于自动证明图的叙事清晰。视觉质量仍需要检查阅读顺序、scope、颜色语义和文字密度。

## 双源漂移

`.mmd` 和 `.drawio` 保留了相同的核心结论，但已有可观察差异：

| 概念 | Mermaid presentation | draw.io parallel source |
| --- | --- | --- |
| Decision plane | 独立 `DNOTE` 节点 | 使用 container title 表达 |
| GracefulEviction relationship | 独立红色 `REL` 节点 | `SafeMigration -> GracefulEvictionTask` 边标签 |
| Binding controller | `remove orphan Works then ensure target Works` | `remove orphan Works first` |
| 第二张图标题 | `Where PR #7662 Fits in Karmada` | `PR #7662: Proposed Rebalancing in the Karmada Control Loop` |

这些变化大多是 presentation compression，没有破坏主要观点；但它们证明两份源不能称为 synchronized 或 mechanically equivalent。

## 后续建议

Day 15 的视觉语言值得保留，不应为了追求机械单源而牺牲清晰度。更稳妥的规则是：

1. **明确 canonical source 和 renderer。** 每张 PNG/SVG 都要能回答“由哪个文件、哪个工具生成”。
2. **优先保证一个问题对应一张图。** 不把 current/proposed comparison 和 full component topology 强塞进同一画布。
3. **需要精细样式时以 `.drawio` 为 canonical。** 使用 native CLI 导出 PNG/SVG；Mermaid 只作为自动生成的结构 fallback。
4. **普通流程图且 draw.io CLI >= 30 时以 `.mmd` 为 canonical。** 通过 CLI 转成 native `.drawio`，避免再手写第二份结构。
5. **确实需要两种独立布局时，称为 curated parallel views。** 两份都可以人工优化，但需要用组件/关系/invariant checklist 做语义审校，不能声称自动同步。
6. **清晰度验收必须包含原图和缩略图。** 原图检查结构和文本，缩略图检查区域划分和主阅读顺序。

对于现有 Day 15 资产，建议保留当前 PNG/SVG，不重新生成。它们已经清楚完成报告任务。后续若内容变化，应先决定是继续维护 Mermaid presentation，还是转为 draw.io canonical native export，而不是无约束地同时修改两份源。

## Ubuntu 路径

当时的 Ubuntu fallback：

```text
analysis -> hand-authored .mmd -> Mermaid remote renderer -> PNG/SVG
        \-> hand-authored .drawio -> validate.py --strict
```

安装官方 draw.io `.deb` 后，推荐的 native headless 路径是：

```bash
export HOME=${HOME:-/tmp}

xvfb-run -a --server-args="-screen 0 1280x1024x24" \
  drawio -x -f png --width 2000 \
  -o diagram.png diagram.drawio \
  --disable-gpu --no-sandbox
```

预览不使用 `-e`。最终可编辑 PNG 再使用 `-e -s 2`，随后运行 `repair_png.py`。当前 Ubuntu 24.04 环境有 `xvfb-run`，但没有 `drawio`，因此尚不能在本机执行 native export。

## 最终判断

Day 15 的图不是“因为用了 draw.io 才清晰”，也不是“虽然双源漂移所以不可靠”。更准确的结论是：

- 清晰来自先收敛叙事问题、再做区域分层、颜色语义、主路径和风险隔离。
- Mermaid renderer 帮助完成自动布局，但没有替代架构判断。
- `.drawio` 提供可编辑的平行版本，但当时没有自动同步能力。
- 后续应保留 Day 15 的视觉设计原则，同时把 source provenance 和 canonical ownership 写清楚。

## Follow-up：project-mermaid Skill

根据本次分析新增通用 `.agents/skills/project-mermaid/`，将工具边界固定为：

- `project-mermaid`：以 `.mmd` 为 canonical source，默认交付白底 PNG，主要用于数据流、事件流、生命周期和时序图。
- `drawio-skill`：以 `.drawio` 为 canonical source，主要用于跨层架构、拓扑、vendor icons、swimlane 和精细自定义布局。

新 skill 提供 data-flow / sequence 模板、各自的 authoring reference，以及调用官方 `@mermaid-js/mermaid-cli` 的 `render_mermaid.py`。默认只使用已安装的 `mmdc`；`--backend npx` 会固定下载经过验证的 CLI 版本，必须显式选择，不会静默上传图内容到 public renderer。

本机验证使用固定版本 `@mermaid-js/mermaid-cli@11.16.0`。wrapper 能自动复用 `PUPPETEER_EXECUTABLE_PATH`、PATH 中的 Chrome/Chromium，或 Playwright Chromium cache；本次因此绕过了 Puppeteer 重复下载 Chromium 的失败。验证结果包括：

- data-flow 和 sequence 模板都成功生成白底 PNG，并通过视觉检查；data-flow 同时成功导出 SVG。
- 已安装 `mmdc` 的 auto backend 和显式 npx backend 都成功。
- 非法 `.mmd` 返回 parse failure，且 wrapper 不保留不可用 PNG。
- 两个 fresh-context forward tests 分别从给定事实生成 1656x255 data-flow PNG 和 958x903 sequence PNG，均无裁切且没有把未给出的关系画成既定事实。

前向测试还补出了两个细节：数据流图只关心数据移动时，可用 `store -> consumer` 表示加载的数据；如果必须区分 read request 和 returned value，应改用 sequence diagram。Sequence diagram 主要依靠 participant label、箭头语义、failure cross 和 control block，不强求 flowchart 的 role-based participant colors。
