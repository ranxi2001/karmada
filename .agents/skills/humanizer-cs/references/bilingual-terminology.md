# Bilingual terminology

Translate for technical equivalence before fluency. The target project's glossary and existing usage outrank this generic guidance.

## Decide what not to translate

Keep these unchanged unless the project has an established localized form:

- code identifiers, API kinds, field names, package names, commands, flags, labels, paths, environment variables, and error strings;
- product and project names, GitHub usernames, issue references, commit SHAs, versions, units, and protocol keywords;
- canonical terms whose English form is how developers search source and documentation.

Use project capitalization exactly. `Deployment`, `Secret`, `Pod`, and a lowercase common noun are not interchangeable merely because the surrounding sentence is Chinese.

## Keep one concept, one term

- Reuse the same translation for the same concept. Do not rotate synonyms for style.
- On first use, add the English term or expansion only when it helps readers map the text to source, API, or standards.
- Keep abbreviations after defining them once: `Pod 干扰预算（Pod Disruption Budget，PDB）`.
- If no stable Chinese term exists, keep the English term and explain it briefly instead of inventing a translation.
- Maintain a small glossary while editing a long issue or PR. Check every occurrence before returning.

## Preserve modality and evidence

Do not flatten distinct meanings:

| English | Chinese guidance |
| --- | --- |
| MUST / required | 必须 / 必需；retain normative force |
| SHOULD / recommended | 应 / 建议；do not promote to 必须 |
| MAY / optional | 可以 / 可选；distinguish permission from possibility |
| may fail | 可能失败；this is uncertainty, not permission |
| blocking | 阻塞；do not soften to 建议 |
| non-blocking / nit | 非阻塞 / 细节建议；do not turn into a requirement |
| reproduced | 已复现；include the verified boundary |
| observed | 已观察到；do not translate as 已确认根因 |
| mitigates | 缓解；do not translate as 修复 or 消除 |

Preserve negative scope: `does not validate`, `not reproduced`, and `not covered` must remain negative after translation.

## Chinese developer voice

- Prefer direct subjects and verbs. State the component, behavior, and result.
- Use `你` rather than `您` when direct address is necessary, but usually address the code or behavior instead.
- Remove translated chatbot politeness such as `非常感谢你的宝贵建议`, `希望这些信息对你有所帮助`, and `如果你愿意我可以继续`.
- Do not add `请` to every instruction. Keep it when the sentence is genuinely a request to another contributor.
- Keep established English engineering words when translation would reduce searchability or precision. Do not mix languages merely to sound technical.
- Use a space between Chinese text and adjacent English words, numbers, or inline code unless project style says otherwise.
- Keep Chinese punctuation in prose and ASCII punctuation inside code, commands, URLs, and Markdown syntax.

## Translation pass

1. Extract protected literals and the working glossary.
2. Translate claims sentence by sentence without changing evidence level.
3. Restore protected literals exactly.
4. Compare normative keywords, negatives, quantities, units, and causal language with the source.
5. Read the result as a developer in the target community; remove translationese without replacing precise terms.
