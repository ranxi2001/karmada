# Comment communication

Use this reference for `review-comment`, `review-reply`, and `discussion` artifacts. A comment is an increment to a visible thread, not a compressed investigation report.

## Decide whether to reply

Before drafting, name the one thing the message adds:

- a new observation or test result;
- a decision or disagreement;
- a question that changes the next step; or
- a concrete action or request.

If it adds none of these, do not produce a redundant technical comment. A short coordination reply that closes a request or records ownership (`Thanks, got it.`, `Understood, I'll update the test.`) is still valid; keep it short and do not repeat the settled technical conclusion. Otherwise keep the evidence in the local report or wait for a new question.

## Choose the thread shape

- **Direct reply:** one brief acknowledgment may come first, then the answer.
- **New discussion:** start with the behavior, conclusion, or decision needed.
- **Inline review:** rely on the diff location; one or two focused sentences are often enough.
- **Follow-up:** mention only what changed since the previous message.

For a direct reply, use this as an optional order, not a checklist:

```text
acknowledgment -> answer or judgment -> one reason or evidence -> one question or action
```

Skip any slot that does not help the reader act. Prefer one unresolved question; keep more only when the questions are tightly coupled and jointly determine the next step. Move unrelated questions, chronology, raw logs, and broad investigation notes to a linked report.

## Sound like a developer

Use the object and action as the subject: `Scaling X does not trigger Y` is clearer than `I checked the relevant paths and found...`. Separate levels of certainty:

- fact: `The scheduler skips this path when ...`;
- judgment: `I don't think this is sufficient because ...`;
- hypothesis: `It looks like ...` or `I guess ...`;
- bounded result: `I failed to reproduce this in the current test run.` Use this only when that test run actually happened.

Keep paragraphs short and let each sentence do one job. Use a natural acknowledgment only when responding to someone else's contribution, and keep it to one sentence (`Good point.`, `Thanks for sharing this.`). Do not add a named greeting, stacked praise, or an apology before every answer. Do not imitate a particular maintainer's wording, spelling, or mannerisms.

When disagreeing or asking for clarification, say exactly what is unclear and why it matters, then ask one answerable question. When proposing options, use bullets only when there are genuinely multiple choices.

For a design discussion, keep the same compression: concrete scenario or example -> current gap -> suggested scope or API -> one decision request. It can be longer when the example or contract needs code, but do not turn it into a chronology of the investigation.

## Final check

Read the comment without the local chat history. It should make clear what changed in the discussion, why that matters, and what the other person should do next. If it still reads like a report or a status update, cut the history and keep the decision-relevant sentence.

These rules were calibrated against de-identified patterns from public issue and review threads across several mature open-source projects. They describe a communication shape, not a named contributor's voice.
