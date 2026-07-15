# Rendering And Tooling

Use the official `@mermaid-js/mermaid-cli` (`mmdc`) for reproducible local PNG, SVG, or PDF generation.

## Preferred Setup

Install a project-local or global CLI:

```bash
npm install --save-dev @mermaid-js/mermaid-cli@11.16.0
# or
npm install -g @mermaid-js/mermaid-cli@11.16.0
```

Then render through the bundled wrapper:

```bash
python3 <this-skill-dir>/scripts/render_mermaid.py diagram.mmd -o diagram.png
```

The wrapper searches `PATH` and `./node_modules/.bin/mmdc`. It defaults to a white background, the CLI's default theme, 2000px page width, and scale 1. Templates may still select Mermaid's `base` theme in their source frontmatter for custom theme variables.

## Explicit Npx Fallback

When `mmdc` is unavailable but `npx` is installed, announce the network/package download and run:

```bash
python3 <this-skill-dir>/scripts/render_mermaid.py \
  diagram.mmd -o diagram.png --backend npx
```

The wrapper pins `@mermaid-js/mermaid-cli@11.16.0`. Do not silently use npx because it changes the local package cache and requires network access.

The wrapper reuses `PUPPETEER_EXECUTABLE_PATH`, a Chrome/Chromium executable on `PATH`, or a Playwright Chromium cache when one is available. For the explicit npx backend, this avoids downloading a second browser. Otherwise Puppeteer follows its normal browser-install behavior.

## Root And CI

The wrapper automatically supplies a temporary Puppeteer configuration with `--no-sandbox` and `--disable-setuid-sandbox` when running as root. An explicit config can be supplied with `--puppeteer-config`.

Official container fallback:

```bash
docker run --rm -u "$(id -u):$(id -g)" \
  -v "$PWD:/data" \
  ghcr.io/mermaid-js/mermaid-cli/mermaid-cli \
  -i diagram.mmd -o diagram.png -b white
```

## Other Formats

The output extension selects the format:

```bash
python3 <this-skill-dir>/scripts/render_mermaid.py diagram.mmd -o diagram.svg
python3 <this-skill-dir>/scripts/render_mermaid.py diagram.mmd -o diagram.pdf
```

PNG is the default report/chat preview. SVG is useful for GitHub and print scaling, but verify its background in the target viewer.

## Remote Rendering

Do not upload source, topology, service names, or internal flows to a public rendering service without explicit user approval. For public open-source diagrams, a remote renderer may be used only as a declared fallback; record the service and keep the `.mmd` source canonical.

## Troubleshooting

- `mmdc not found`: install the official CLI or use the explicit npx/container path.
- Chrome refuses to run as root: use the wrapper or pass a Puppeteer config with `--no-sandbox`.
- Blank image: verify the first Mermaid keyword (`flowchart`, `sequenceDiagram`, or `stateDiagram-v2`) and render again.
- Parse failure around `end`: quote or bracket labels containing the reserved word `end`.
- Tiny text: reduce participants/nodes before increasing scale. Split the diagram when the canvas is the real problem.
- Dark or transparent PNG: keep `--background white`; avoid relying only on an SVG viewer's background behavior.
- Layout differs after a CLI upgrade: record the CLI version and visually review regenerated assets before committing them.
