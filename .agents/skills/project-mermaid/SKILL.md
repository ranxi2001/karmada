---
name: project-mermaid
description: Create and maintain project-local Mermaid diagrams as canonical .mmd sources with rendered PNG or SVG outputs. Use for data-flow diagrams, request/response and controller sequence diagrams, event flows, retry or lifecycle timelines, current/proposed process comparisons, and requests mentioning Mermaid, .mmd, data flow, sequence diagrams, or diagram PNGs. Prefer this text-first skill for flows that belong in version control; route rich system architecture, topology, vendor icons, swimlanes, and precise custom geometry to drawio-skill.
---

# Project Mermaid

Create source-grounded technical diagrams with one canonical `.mmd` file and a directly viewable PNG by default. Keep the diagram easy to review in git and easy to regenerate.

## Routing

| Main question | Use |
| --- | --- |
| How does data, an event, or control move through a process? | `project-mermaid` data flow |
| What calls happen, in what order, including retries or failures? | `project-mermaid` sequence |
| How does a lifecycle move between a small number of states? | `project-mermaid` flowchart/state diagram |
| How can a GitHub review comment explain branching, ordering, or competing causes without a long paragraph? | compact inline Mermaid review diagram |
| Where do many components live across layers, clusters, networks, or trust zones? | `drawio-skill` architecture |
| Does the diagram need vendor icons, exact waypoints, swimlanes, or a presentation-specific canvas? | `drawio-skill` |

If the user explicitly requires `.mmd`, keep Mermaid as the canonical source. Do not create a parallel `.drawio` unless requested.

## Workflow

1. Inspect the relevant source, configuration, logs, or proposal. List the proven actors, state stores, messages, and boundaries before drawing.
2. State the one question the diagram answers. Split diagrams that mix data flow, full architecture, and detailed chronology.
3. Choose the diagram type:
   - Read [references/data-flow.md](references/data-flow.md) for a data or event flow.
   - Read [references/sequence.md](references/sequence.md) for ordered interactions, retries, concurrency, or failure recovery.
4. Start from the matching template in `assets/`, then replace every example actor and label with project evidence. Do not leave template-only nodes in the result.
5. Save the canonical source as `<name>.mmd`. Honor project-specific language and filename rules.
6. Render a white-background PNG with:

```bash
python3 <this-skill-dir>/scripts/render_mermaid.py \
  <name>.mmd -o <name>.png
```

The script uses an installed official `mmdc` by default. If it is unavailable and `npx` is available, announce that the official package will be downloaded, then use `--backend npx`. Read [references/rendering.md](references/rendering.md) for installation, root/CI handling, SVG, and troubleshooting.

7. Inspect the PNG with image vision. Check reading order, clipped text, tiny labels, excessive canvas, ambiguous arrows, and whether the image still communicates at chat/README width.
8. Make targeted `.mmd` edits and re-render. Do not patch the PNG.
9. Deliver the `.mmd` and PNG together. State the renderer/backend and any unverified or inferred relationship.

## Inline Review Comment Mode

[GitHub renders Mermaid](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) in pull requests, Issues, and Discussions. Use a compact fenced `mermaid` block when a reviewer would otherwise need to mentally simulate one of these shapes from prose:

- three or more actors, state layers, or dependent steps;
- an ordered event, retry, cleanup, or recovery sequence;
- one observed signal with two or more possible causes;
- current behavior versus the requested behavior.

This mode is a deliberate exception to the project-artifact workflow: for a one-off upstream comment, the exact fenced block stored in the local approved draft is canonical, and a separate `.mmd`/PNG is not required. Create project-local source and a rendered image when the diagram belongs in a report, issue, proposal, or reusable evidence record.

Keep inline review diagrams to one question and usually 4-10 nodes. Use `flowchart` for branching causes or current/proposed logic, `sequenceDiagram` for ordered actors and retries, and `stateDiagram-v2` for lifecycle transitions. Put one plain-language conclusion before the diagram and one specific requested action after it.

Do not use a diagram for a single local condition that is clearer in one or two sentences. Do not paste a large architecture view into a line comment. A diagram supplements rather than replaces evidence: label inferred edges, cite source/log support in nearby prose, and preserve a text summary because not every rendered chart is equally accessible.

Validate the exact Mermaid source before posting. Prefer the bundled renderer when practical; if local rendering is unavailable, keep syntax conservative and disclose that only GitHub rendering remains unverified.

## Quality Gates

- Use one stable reading direction. Prefer `LR` for data movement and `TB` for staged decisions or comparisons.
- Keep ordinary diagrams near 5-18 meaningful nodes. Split a larger graph unless one overview is the explicit goal.
- Label nodes with responsibilities or state, and edges with the data, event, command, or response being transferred.
- Use subgraphs only for real ownership, lifecycle, trust, or execution boundaries.
- Use solid arrows for direct/synchronous flow and dashed or open arrows for async, feedback, or inferred paths; include a legend when the distinction is not obvious.
- In flowcharts, use role-based colors with sufficient contrast. For current-versus-proposed diagrams, keep unchanged/current nodes neutral and give changed or new nodes restrained accent colors; reserve red for material risk. Pair color with explicit labels, borders, or line styles so color is not the only carrier of meaning. In sequence diagrams, rely first on participant labels, arrow semantics, and control blocks; do not force unsupported participant-specific styling. Avoid decorative gradients.
- Put unresolved or inferred paths in a distinct class and label them explicitly. Do not draw a hypothesis as an established edge.
- When a diagram synthesizes meeting, log, experiment, or research evidence, state what the source supports, what it does not establish, and any provenance limitation. Visual clarity must not turn an inference into an approved fact.
- Keep labels compact. Use `<br/>` for intentional label breaks; do not hard-wrap prose in the `.mmd` source.
- Default PNG background to white so the image remains readable in light and dark Markdown viewers.
- Treat a successful render as syntax validation, not semantic validation. Recheck the diagram against project evidence.

## Source Ownership

The `.mmd` is canonical and the PNG/SVG is generated. Never edit generated images as source. If another editable format coexists, record which source generated each image and do not call independently authored files synchronized without a mechanical check.
