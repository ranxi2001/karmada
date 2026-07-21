---
name: explain-technical-content
description: Explain complex engineering analysis in plain language without losing source evidence. Use when a user says they cannot understand an explanation, asks for a simpler or more conversational explanation, or when writing Chinese internship reports, daily reports, mentor summaries, API/design reviews, scheduler/controller flows, distributed-system concepts, CI RCA, or other technical notes that would otherwise require the reader to decode jargon and private chat context.
---

# Explain Technical Content

Make the reader understand the decision before asking them to parse implementation details. Preserve exact identifiers, evidence, uncertainty, and risk boundaries; simplify the route to the conclusion, not the conclusion itself.

## Workflow

1. Identify the reader and the decision.
   - State what the reader needs to understand or decide after reading.
   - Assume basic Kubernetes knowledge only for Karmada internship reports unless the surrounding document proves more context.
   - Do not require private chat history or another report to decode the explanation.

2. Lead with the outcome in ordinary language.
   - Use a section such as `## 先说人话` near the beginning of a Chinese report.
   - State what changed, why it matters, and whether action is possible now.
   - Distinguish `已确定`, `建议方向`, `仍待确认`, and `移出当前范围`.

3. Give one concrete example before the abstraction.
   - Use realistic names, numbers, or event order.
   - For scheduling, show an actual placement such as `member1: 6 assigned / 4 available`.
   - For state or cache behavior, use an analogy only when it maps exactly to the mechanism, then name the real field. For example, call `schedulerObservingAffinityName` the scheduler's previous affinity-group "bookmark" before explaining the field.

4. Explain the actors and flow.
   - Name each component by role first, then identifier: `调度器（karmada-scheduler）`.
   - Use 3-7 short steps or a compact table for the main path.
   - Explain who reads, who decides, who writes, and what state survives to the next step.
   - Use a diagram only when it is easier to scan than the same relationship in prose.

5. Add technical evidence as a second layer.
   - Keep code identifiers, API fields, commands, exact errors, and upstream quotations in their original language.
   - Cite the source or observation that supports each consequential claim.
   - Separate source-proven facts from engineering inference and open questions.
   - Preserve the source's claim strength. Do not turn a suggestion into consensus, an open question into a requirement, or a possible risk into an observed failure merely to make the explanation decisive.
   - Do not hide compatibility, data-loss, concurrency, or lifecycle risk to make the explanation feel simpler.

6. End with the practical boundary.
   - State what can be done now, what must wait, and the evidence that will unblock it.
   - Explain when a problem was removed from scope rather than solved.
   - When the contract is undecided, state the choices and the decision needed instead of silently selecting one behavior.
   - Avoid ending with a list of symbols; translate them into the decision they affect.

7. Run the standalone comprehension check.
   - Hide the detailed evidence section and verify that the opening lets the reader answer:
     - What changed?
     - Give one concrete example.
     - Why does it matter?
     - What is still unknown?
     - What should happen next?
   - Rewrite the opening if any answer depends on unexplained jargon.

## Chinese Report Contract

- Write the majority of local internship-report prose and headings in Chinese.
- Keep English only where it carries exact technical meaning: code, API names, commands, errors, upstream titles, links, and short original quotations.
- Put `## 先说人话` or `## 通俗解释` within the first substantial section for API design, controller/scheduler flow, RCA, concurrency, lifecycle, or multi-component reviews.
- Introduce a technical term as `中文作用（exactIdentifier）` on first use when the Chinese reader may not know it.
- Prefer short paragraphs and concrete examples over dense English matrices. Keep a matrix when comparison is the point, but explain its conclusion before the table.
- Do not translate identifiers into invented Chinese names that make source lookup difficult.

## Default Report Shape

Use this order when the existing report does not require another structure:

```markdown
# Day N：中文标题

## 先说人话

一句话结论、一个具体例子、当前能否行动。

## 背景与目标

## 实际运行过程

## 技术证据

## 已确定与仍待确认

## 下一步
```

Do not force every section into a short report. Preserve the ordering principle: understanding first, evidence second.
