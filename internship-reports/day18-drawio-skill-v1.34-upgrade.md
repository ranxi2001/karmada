# Day 18：drawio-skill v1.34.0 升级与版本同步缺陷

## 目标与结论

本轮将仓库内 `.agents/skills/drawio-skill/` 从 `v1.14.0` 升级到官方最新稳定版 [`v1.34.0`](https://github.com/Agents365-ai/drawio-skill/releases/tag/v1.34.0)，固定 release commit 为 `f8f4e89dcf19d92582701f18024282adc729a77c`。升级完成并通过本地回归；没有复制或启用上游 GitHub Actions。

审计同时发现一个真实的上游分发缺陷：`SKILL.md` 顶层版本已经是 `1.34.0`，但 JSON metadata 仍是 `1.19.0`，而同步到 `Agents365-ai/365-skills` 的 workflow 正好读取旧字段。结果是 [`v1.34.0` 同步 run](https://github.com/Agents365-ai/drawio-skill/actions/runs/29328512589) 成功，但目标 marketplace 仍登记 `1.19.0`。

已在独立临时 worktree 准备修复 commit `9b7105f`，推送到 [`ranxi2001/drawio-skill:fix/skill-version-sync`](https://github.com/ranxi2001/drawio-skill/tree/fix/skill-version-sync)，并按确认文案创建 upstream [PR #94](https://github.com/Agents365-ai/drawio-skill/pull/94)。

## 本地升级范围

官方 tag 中 `skills/drawio-skill/` 有 60 个运行时文件。本仓库最终保留 62 个文件：60 个官方运行时文件，加本地 Codex UI metadata `agents/openai.yaml` 和上游 MIT `LICENSE`。

相对 `v1.34.0` 官方运行时，只有四个预期适配文件不同：

- `SKILL.md`：Codex frontmatter 只保留 `name` 和 `description`；不把 OpenClaw/Hermes metadata 当成 Codex 配置。
- `references/pr-bot.md`：明确本仓库没有安装上游 composite Action 或示例 workflow。
- `references/toolbox.md`：把 PR diagram bot 标为可选的上游 CI 集成，不暗示 runtime 升级会修改 Karmada CI。
- `references/xml-authoring.md`：只移除官方文件末尾会触发 `git diff --check` 的空白行。

MIT 许可正文随 vendored 代码保存；当前 Windows 机器的 per-user draw.io 路径继续由根 `AGENTS.md` 覆盖，不写进通用上游 skill。

## 新能力摘要

从 `v1.14.0` 到 `v1.34.0`，主要增加了：

- Terraform、Kubernetes、Docker Compose、live state、OpenAPI、SQL ERD 和 CI pipeline importers。
- C4、sequence、SysML、BPMN、network、swimlane 和 Tube-Map authoring。
- `.drawio` 到 Mermaid、PowerPoint、interactive HTML、animated SVG 和 Markdown 的反向输出。
- diagram diff、git history timelapse、heatmap、relabel、restyle、raster-to-drawio、build-up animation、executive compression、click-through runbook 和 PR diff report。
- 新增 dark、colorblind-safe presets，并扩展 structural validator、Graphviz layout 和 XML authoring guidance。

## 供应链与执行边界

- 来源只使用官方仓库 `Agents365-ai/drawio-skill` 的稳定 release tag，不跟随 release 之后的未发布 `main`。
- `v1.34.0` tag 指向 merge commit `f8f4e89d`；升级时上游在本轮内从 `v1.33.0` 发布到 `v1.34.0`，因此重新刷新 release 后才完成最终同步。
- Python 脚本主要读写用户指定的本地文件。需要外部进程的能力会显式调用 `drawio`、Graphviz `dot`/`tred` 或 `git`。
- `aiicons.py --embed` 会按用户选择访问图标 CDN；普通 shape search、XML generation 和 validation 不需要网络。
- live infrastructure recipes 只解析用户主动提供的 `terraform`、`docker` 或 `kubectl` JSON 输出，不自行登录云账号。
- 上游 PR bot 的 composite Action 会安装工具并发布 GitHub comment，但该 Action 不在本地 runtime vendor 中，本次没有复制或启用它。
- 可选依赖包括 PyYAML、python-pptx 和 Pillow；缺少时只影响对应 importer/export/GIF 功能。

## 验证结果

```text
quick_validate.py .agents/skills/drawio-skill
Skill is valid!

python3 -m compileall -q .agents/skills/drawio-skill/scripts
PASS

python3 -W error::ResourceWarning -m unittest discover -s tests -v
Ran 128 tests
OK (skipped=7)
```

7 个 skip 都与当前 Linux 环境缺少 draw.io CLI、Graphviz `dot`、python-pptx 有关。当前环境也缺少 Pillow，因此没有跑真实 GIF export。PyYAML 可用。

仓库内三个历史 `.drawio` 都用新版 validator 执行 `--strict`：

```text
day15-issue-7621-current-proposed-flow.drawio: 0 error(s), 0 warning(s)
day15-pr7662-karmada-component-position.drawio: 0 error(s), 0 warning(s)
day2-karmada-architecture.drawio: 0 error(s), 0 warning(s)
```

新增 `tubemap.py` 使用官方 demo JSON 生成 11 stations / 4 lines 的可编辑 XML，随后严格校验为 `0 error(s), 0 warning(s)`。`explain.py`、`drawio2mermaid.py` 和 `runbook.py` 也对现有 Day 15 图完成 smoke test。

测试套件仍会打印若干未关闭文件的 `ResourceWarning`，即使命令使用 `-W error::ResourceWarning` 也不会令 unittest 失败，因为这些警告发生在对象析构阶段。这是后续可单独提交的 test hygiene 候选，不与本次版本同步修复混在一起。

## 上游缺陷证据

当前 [`v1.34.0` SKILL.md](https://github.com/Agents365-ai/drawio-skill/blob/v1.34.0/skills/drawio-skill/SKILL.md) 同时声明：

```text
version: 1.34.0
metadata: {...,"version":"1.19.0"}
```

`.github/workflows/sync-365-skills.yml` 解析的是 `metadata.version`，然后用它更新 `Agents365-ai/365-skills/.claude-plugin/marketplace.json`。实际观察：

- source skill 内容和 top-level version 已同步到 `v1.34.0`。
- [`Sync to 365-skills` run 29328512589](https://github.com/Agents365-ai/drawio-skill/actions/runs/29328512589) 为 success。
- `Agents365-ai/365-skills` 的 `drawio` marketplace version 仍是 `1.19.0`。

因此这是 CODE + OBS 证据支持的分发版本缺陷，不只是显示文本不一致。

## 已准备的修复

临时 worktree：`/tmp/drawio-skill-version-fix`

本地 commit：`9b7105f fix: keep distribution version metadata in sync`

四个文件：

- `skills/drawio-skill/SKILL.md`：metadata version 对齐 `1.34.0`。
- `.github/workflows/sync-365-skills.yml`：以顶层 `version` 为 canonical source；解析失败或 marketplace entry 不存在时让 job 失败。
- `tests/test_skill_metadata.py`：断言 top-level version 与 metadata version 一致。
- `.github/workflows/tests.yml`：`SKILL.md` 和 sync workflow 变化时也运行测试。

修复分支验证：129 tests passed，7 skipped；两个 workflow YAML 解析成功；用当前 marketplace JSON 模拟时恰好替换一个 `drawio` entry 为 `1.34.0`；`git diff --check` 通过。

## 已发布的 upstream PR 文案

目标：`Agents365-ai/drawio-skill:main`

Title:

```text
fix: keep distribution version metadata in sync
```

Body:

```markdown
## Problem

`skills/drawio-skill/SKILL.md` declares `version: 1.34.0`, but `metadata.version` is still `1.19.0`. The `sync-365-skills` workflow reads the stale metadata field, so successful sync runs copy current skill files while leaving the `365-skills` marketplace entry at `1.19.0`.

This is observable after the v1.34.0 sync: the workflow completed successfully, the target skill contains v1.34.0 content, and the marketplace still reports v1.19.0.

## Changes

- Align `metadata.version` with v1.34.0.
- Use the top-level `version` as the canonical value in the sync workflow.
- Fail the sync when the version or marketplace entry cannot be resolved.
- Add a regression test for version consistency and run tests when the skill metadata or sync workflow changes.

## Testing

- `python3 -W error::ResourceWarning -m unittest discover -s tests -v` (129 tests passed, 7 skipped because optional local tools are unavailable)
- Parsed both modified workflow files as YAML.
- Simulated the marketplace replacement against the current `365-skills` JSON; exactly one `drawio` entry changed to `1.34.0`.

## AI assistance

I used Codex to inspect the release and sync history, prepare the patch, and run the validation above. I reviewed the final diff and test results.
```

## 发布边界

PR #94 已回读为 open、非 draft、base `main@f8f4e89`、head `ranxi2001:fix/skill-version-sync@9b7105f`，4 个文件 `+43/-7`，`mergeable_state=clean`。远端正文与确认稿一致，唯一 check `unittest` 已 success；尚未修改 `Agents365-ai/365-skills`，需要等待 maintainer review/merge 和 merge 后 sync run。
