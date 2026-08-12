# Developer communication anti-patterns

AI-writing signals are editing clues, not proof of authorship. Fix trust and reviewability before style.

| Priority | Pattern | Why it fails | Correction |
| --- | --- | --- | --- |
| P0 | Fabricated verification | Reviewers rely on tests and CI claims | Name only commands and results supported by evidence |
| P0 | Confidence inflation | A hypothesis becomes a false root cause | Restore `may`, `appears`, tested boundary, or an explicit question |
| P0 | Severity drift | Suggestions become blockers or defects become nits | Preserve the author's technical intent and repository labels |
| P0 | Policy laundering | AI-prohibited text is reframed as editing or translation | Stop without producing paste-ready text |
| P0 | Terminology drift | Synonym variation changes APIs or normative meaning | Reuse the exact project term |
| P0 | Acceptance drift | Submitted, open, or waiting-review work is described as merged, accepted, or completed | Separate reporter-owned completion from external decisions |
| P1 | Vague finding | "This may cause issues" gives no reachable impact | Name trigger, path, consequence, and evidence |
| P1 | Diff narration | A PR lists files instead of behavior | Describe old and new contract; let the diff show files |
| P1 | Local report paste | A PR body or comment repeats full investigation notes | Use locators, validation, risks, and the reviewer entry point |
| P1 | Template overfill | Empty sections and repeated summaries hide the decision | Keep required fields; remove sections that add no decision value when allowed |
| P1 | Prior-art flattening | Related issues or PRs are called duplicate or unrelated without evidence | Name same symptom, same root cause, partial overlap, fixed, or superseded |
| P1 | Flake shortcut | A green rerun is treated as root cause or merge proof | State nondeterminism and ask for logs, operation, pattern, or counterfactual |
| P1 | Status fog | "Many things progressed" hides object, evidence, owner, or blocker | Use result/state plus project, locator, value/risk, and next owner |
| P1 | Reviewer coercion | "Clearly", "obviously", or broad appeals replace reasoning | State the evidence and why the change is required |
| P1 | Actor hiding | Passive voice obscures who writes, retries, deletes, or owns state | Name the component when ownership matters |
| P1 | Unbounded claim | "Fixes performance" omits workload and method | Include measurement boundary or narrow the claim |
| P2 | Chatbot preamble | "Great question" and "You're absolutely right" delay the answer | Start with the answer or finding |
| P2 | Deference theater | Repeated thanks and apologies reduce signal | Use one natural acknowledgment only when socially useful |
| P1 | Canned acknowledgment plus report dump | A fixed "Thanks for pointing this out" opening followed by a long recap sounds generated and hides the reply | Use one short, context-specific acknowledgment or none, then answer the thread |
| P1 | Question-list ending | Several unrelated requests leave the other person unsure what to answer first | Ask only for the fact or decision that changes the next step; link the rest |
| P1 | Repeated meta-validation disclaimer | Repeated "I checked the relevant paths" or broad "this does not establish ... end to end" scaffolding narrates the process instead of the result | Keep one concrete tested boundary when it matters, then omit redundant process narration |
| P2 | Promotional adjectives | "Robust", "seamless", and "comprehensive" replace behavior | Name the guarantee, failure mode, or measured result |
| P2 | Mechanical structure | Every point has a bold label and three subpoints | Use the artifact's natural shape; keep lists only for list-shaped content |
| P2 | Generic conclusion | "This improves quality and maintainability" adds no evidence | End on validation, residual risk, decision, or next action |
| P2 | Offer to continue | "Let me know if you want more" leaks assistant framing | Remove it |

## False-positive guards

Do not rewrite solely because the text contains:

- passive voice where the actor is unknown, irrelevant, or intentionally de-emphasized;
- repeated technical terms that preserve one concept and one name;
- precise formal vocabulary used by the project or standard;
- bullets, tables, headings, or templates that improve scanning;
- hedging that accurately represents incomplete evidence;
- short review comments whose context is visible in the referenced line;
- status bullets that use exact locators and terse state words;
- mixed Chinese and English required by source identifiers and community terminology;
- courtesy consistent with the contributor's own voice.

Do not add random variation, typos, slang, personal anecdotes, or emotional reactions. Those simulate a person without improving trust.
