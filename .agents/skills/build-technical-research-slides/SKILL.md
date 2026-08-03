---
name: build-technical-research-slides
description: Create, revise, and validate evidence-backed technical research HTML slide decks for live presentations, especially Chinese Kubernetes or Karmada architecture, scheduler/controller flows, issue and PR research, implementation comparisons, and engineering roadmaps. Use when turning a long report into speaker-led slides, replacing a table-heavy deck, applying the Swiss Modern Style A direction, improving terminology and cross-slide continuity, or checking a fixed 1920x1080 browser presentation before delivery.
---

# Build Technical Research Slides

Turn a detailed technical report into a presentation that can be understood while someone is speaking. Preserve evidence and uncertainty, but move dense proof out of the audience's first reading path.

## Companion Skills

- Use the available `frontend-slides` skill for the fixed-stage runtime, navigation, editing, and browser delivery contract.
- Use `explain-technical-content` for Chinese wording, concrete examples, source identifiers, and claim-strength boundaries.
- Keep the research report as the evidence source. Treat the HTML as the presentation layer, not as a replacement for the report.

## Workflow

### 1. Freeze The Evidence

1. Read the report, linked source notes, and current presentation before editing.
2. Reduce the assignment to three to five questions the audience must be able to answer.
3. Classify consequential statements as source-proven fact, engineering inference, recommendation, or open boundary.
4. Protect exact component names, API fields, modes, commands, issue and PR numbers, plugin names, version numbers, and error strings.
5. Do not convert an internal product assumption, an open proposal, or a review suggestion into established behavior.

For Karmada scheduler research, explicitly identify who observes, who decides, who writes, and what event starts the next component.

### 2. Build A Continuous Story

Use this order unless the material requires another sequence:

`结论 -> 具体例子 -> 运行过程 -> 技术证据 -> 未决边界 -> 建议路线`

- Give each slide one question and one answer.
- Add a short footer bridge: `本页回答` on the left and `下一页` on the right.
- Make the next slide resolve the question raised by the previous footer.
- Prefer 12-18 readable slides for a 15-minute internal presentation over fewer overloaded slides.
- Keep the cover about the literal research subject and the questions being answered. Do not create a marketing landing page.

For speaker-led decks, replace tables with the visual form that matches the relationship:

- history or scope change: timeline;
- component ownership: actor lanes;
- controller or scheduler behavior: numbered flow;
- two mechanisms: parallel tracks;
- prerequisites: gates plus stop conditions;
- limitations: horizontal risk bands;
- abstraction comparison: split layers;
- plugin inventory: typography wall;
- safety chain: pipeline;
- implementation proposal: staged roadmap.

Split a crowded page instead of shrinking technical text. Do not use a table merely because the source report has one.

### 3. Introduce Terms Before Reusing Them

- Introduce recurring Chinese domain nouns with an English reference on the first key slide: `副本（replica）`, `工作负载（workload）`.
- Expand unfamiliar abbreviations on first use and state their plain Chinese purpose: `GVK（Group / Version / Kind，资源类型标识）`.
- Name a component by role and exact identifier when the audience may not know it: `调度器（karmada-scheduler）`.
- After the first clear introduction, use the shorter Chinese term unless the English term improves a comparison or spoken reference.
- Never invent a Chinese translation for an exact source identifier.
- Scan the final visible text for unexplained abbreviations, isolated English nouns, and labels whose actor is unclear.

### 4. Apply Style A Deliberately

Use Swiss Modern / Style A for a speaker-led technical route presentation:

- author at `1920x1080` and scale the stage uniformly without mobile reflow;
- use paper `#f7f7f3`, ink `#111111`, red `#e63b2e`, orange `#d96724`, blue `#2563a6`, and green `#27845b`;
- do not use yellow accents on the white or paper background;
- use Archivo for display text, Noto Sans SC for Chinese body text, and IBM Plex Mono for identifiers;
- expose a quiet 12-column construction grid and use square, hairline geometry;
- avoid gradients, shadows, decorative cards, nested cards, and table-heavy composition;
- use circles only when the shape carries meaning, such as a gate or replica token;
- reserve large display type for the cover and primary slide conclusion;
- keep red for conclusions or state-changing risk, blue for scheduler or placement, and green for allowed, safe, or replacement paths;
- use orange sparingly for validation or transition when a five-step flow needs a distinct intermediate stage; do not let orange become the page background or dominant palette.

Keep controls out of the authored content. On 16:9 landscape viewports, place them vertically in the right gutter; on portrait viewports, place them in the letterbox below the stage.

### 5. Preserve The Runtime Contract

- Deliver one self-contained HTML file with inline CSS and JavaScript.
- Include the complete fixed-stage viewport base from `frontend-slides`.
- Switch slides with `visibility`, `opacity`, and `pointer-events`; do not use `display` for active slide state.
- Support arrow keys, Page Up/Down, Space, Home/End, hash navigation, wheel throttling, touch swipe, fullscreen, and reduced motion.
- Keep inline text editing available through the top-left hot zone or `E`; make `Ctrl+S` download the edited HTML.
- Print one `1920x1080` slide per page and reveal all staged animations for print.
- Keep navigation chrome outside slide content and hide it in print.

### 6. Validate In A Real Browser

Reuse an installed compatible Playwright and Chromium build before downloading another browser.

Run all of these checks after any content or layout change:

1. Render every slide at `1280x720`; capture individual screenshots and a contact sheet.
2. Confirm exactly one active slide, the expected page counter, and zero browser console or page errors.
3. For every active slide, reject elements outside the slide bounds, clipped children, or a slide `scrollWidth` or `scrollHeight` larger than `1920x1080`.
4. Check `1920x1080` fills the viewport and has zero document overflow.
5. Check `390x844` preserves the complete 16:9 stage, has zero document overflow, and leaves controls outside the stage.
6. Test `End`, `ArrowLeft`, hash navigation, fullscreen state handling, and print output page count.
7. Visually inspect the cover and the densest actor, comparison, plugin, safety, and roadmap slides. DOM measurements do not detect every visual collision.
8. Run static searches for forbidden tables, gradients, yellow theme tokens, stale filenames, and missing protected identifiers.

Do not call the deck complete while any clipped text, incoherent overlap, stale link, blank slide, or unexplained abbreviation remains.

### 7. Replace Versions Cleanly

- Create a separate file for a new visual direction and preserve the current deck until the user explicitly chooses a replacement.
- When the user asks to delete the old version, remove it and update every report intro, README index, TODO entry, `PROGRESS.md` link, and raw image or HTML URL that referenced it.
- Search the entire allowed record tree for the deleted filename and require zero remaining references.
- Record only the selected current deck in the active snapshot; remove superseded duplicate entries from rolling progress.
- Remember that a committed deletion remains recoverable from Git history.

## Karmada Record-Branch Handoff

- Keep the presentation, report links, and reusable skill under the `intern` branch allowlist.
- Keep `PROGRESS.md` within its line and byte budgets.
- Inspect the final diff, run `git diff --check`, commit the finished record, and push `origin/intern` without a separate reminder.
- Do not push an upstream topic branch or publish a PR, issue, review, comment, or maintainer mention without explicit confirmation.

## Completion Checklist

- The first three slides establish the subject, actors, and historical scope.
- A concrete numbered example appears before the abstract mechanism.
- Every component has a clear observation, decision, or write responsibility.
- Recurring terms and abbreviations are explained before reuse.
- Recommendations remain distinct from community consensus and product facts.
- The selected deck has no table-driven pages, yellow-on-white accents, clipped content, or stale links.
- Desktop, phone, navigation, console, overflow, screenshot, and print checks pass.
- Indexes, progress state, commit, and `origin/intern` match the delivered file.
