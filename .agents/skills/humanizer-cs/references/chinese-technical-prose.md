# Chinese technical prose

Use this reference for Chinese research notes, experiment reports, incident summaries, status tables, and other explanatory technical prose. Apply it after technical truth and project terminology are frozen.

## Prefer established terms

- Use the established term when the field or project already has one. Do not replace it with a new phrase merely for variety or vividness.
- Name the mechanism or measurement directly: `截断`, `checkpoint`, `长度启发式基线`, `置信区间与基线重叠`.
- Keep one concept, one term across headings, tables, and prose.

Examples:

```text
超长度 -> 截断
Ray 的端口会跟自己撞 -> 发生 Ray 端口冲突
存档 -> checkpoint
```

Expand the actor or mechanism only when the source or supplied context establishes it. A vivid but vague phrase does not authorize a more specific causal claim.

## Make referents explicit

Remove metaphors and personification when readers must infer the technical referent. Replace the image with the component, operation, metric, or relation it stands for.

```text
已经吃掉一半空间 -> 已覆盖一半区间
挑出来的题目看上去健康得多 -> 选中问题的截断比例更低
一旦超就制造出参差 -> 截断发生时会增大奖励方差
24 步训练只挪动 0.05 -> 24 步训练后正确率变化为 0.05
```

Do not apply this as a blind ban on all figurative language. Preserve a project-defined term or a familiar explanation when its referent is unambiguous and changing it would reduce precision. In formal technical artifacts, prefer the direct form whenever both carry the same meaning.

## Use neutral labels

Use neutral noun phrases for headings, table headers, categories, and state labels:

- `问题`, `现象`, `影响`, `结果`;
- `确认程度`, `实验设置`, `重采样后的重合率`, `取值数量`;
- `已完成`, `已确认`, `未达到基线`, `结论待定`, `进行中`.

Keep the label vocabulary consistent across one artifact. Do not begin with neutral states and later rotate to conversational labels such as `做通了`, `需要修`, or `没有买到想要的`.

Neutral labels are a default, not permission to overwrite repository-required headings, severity labels, or a user's established glossary.

## State the measured relation

Avoid rhetorical contrasts such as `是 X，不是 Y` when the evidence can be stated directly. Name the observation, comparison boundary, and measured relation.

```text
梯度对齐：是噪声，不是信号
-> 梯度对齐：三项检查结果均在噪声范围内

稳定是靠粗糙换来的
-> 取值数量少的指标重合率高

越稳定的指标越挑不出东西，越挑得出东西的指标越不稳定
-> 重合率与取值数量呈反向关系
```

Keep a contrast when it carries normative scope, corrects a specific ambiguity, or is the shortest precise form. The target is unsupported rhetoric, not the words `是` and `不是` themselves.

## Do not complete a pattern by invention

- A row or bullet may report only what happened. Do not force every item to contain a number, cause, conclusion, lesson, or recommendation.
- Preserve quantitative detail that exists, but never invent a number to make rows look parallel.
- When the cause is unknown, write `原因未查明`. Do not append a plausible mechanism.
- If a relationship has not been tested, state that boundary directly: `该现象与截断的关系尚未验证`.
- Keep later confirmed explanations if the source establishes them; do not let an earlier uncertainty label erase newer evidence.

## Replace conversational judgment with technical content

In formal technical prose, replace colloquial evaluation with the measurement or boundary it summarizes:

```text
赢得很干脆 -> 差值为 0.030
测得更准 / 测得更糙 -> 估计精度更高 / 更低
基本上等于抓阄 -> 接近随机选取
白跑 / 白占 -> 无效运行 / 空占
有事后找补的嫌疑 -> 该切分方式在观察结果之后确定
```

Delete transition commentary that adds no technical relation, then start with the next decision-relevant section.

Do not erase every informal word mechanically. A short maintainer reply may follow the project's conversational register. Rewrite when the phrase hides a referent, measurement, evidence level, or state.

## Table pass

For each table:

1. Replace expressive headers with neutral categories.
2. Keep one grammatical role per column: problem, observation, impact, result, or state.
3. Preserve exact values, units, and technical terms.
4. Let short rows stay short when their content is complete.
5. Mark unknown causes explicitly instead of balancing the row with speculation.
6. Check state-label consistency across the surrounding document.
