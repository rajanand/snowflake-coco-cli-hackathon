# Prompt: Replicate the "Hackathon End-to-End Report" Design System

Use this prompt (verbatim or lightly adapted) with an AI coding assistant to generate a new
standalone HTML report that reuses the exact same design system, diagram style, and table
styling as `docs/hackathon-end-to-end-report.html`. This file documents the **prompt**, not
the report content.

---

## Prompt to paste

```
I have a sample.html file in the docs folder (docs/sample.html). I want to use the same
design system to create a report documenting [DESCRIBE YOUR PROJECT / WHAT TO DOCUMENT].

Requirements:

1. USAGE & SCOPE
   - This will be used as a local HTML file only (not published through any report-sharing
     sandbox). Confirm this with me if it changes any constraints.
   - Write a full end-to-end narrative, not a short executive summary: problem →
     architecture → data model → core components → apps/consumers → governance/testing →
     cost/status → setup → appendix (adapt sections to my actual project).

2. DESIGN SYSTEM — copy from docs/sample.html exactly
   - Reuse the same CSS custom properties for light/dark theming via
     `prefers-color-scheme`: --bg, --surface, --ink, --muted, --line, --accent,
     --accent-soft, --ok/--ok-soft, --warn/--warn-soft, --bad/--bad-soft, --code-bg.
   - Reuse the same font stack: --f-display (IBM Plex Sans Condensed), --f-body
     (IBM Plex Sans), --f-mono (IBM Plex Mono).
   - Reuse the same layout shell: `.wrap` grid with a sticky `nav.rail` on the side,
     `.answers`/`.answer` card grid for section content, `.pill` badges
     (`.ok`/`.warn`/`.bad`/`.info`), `.callout` boxes, `.step` cards, `.check` checklist
     styling.
   - Do not introduce a different font, color palette, or layout grid — match
     sample.html's CSS 1:1, only adding new component classes if a genuinely new UI
     pattern is needed (e.g. diagrams).

3. TABLES
   - Every `<table>` must use `border-collapse: collapse` and get a vertical dotted
     column divider between every column (not before the first column), using the
     theme-aware line color, e.g.:
     `th:not(:first-child), td:not(:first-child) { border-left: 1px dotted var(--line); }`
   - Keep the existing bottom-border row divider and header styling from sample.html.

4. DIAGRAMS — no mermaid.js, hand-crafted inline SVG only
   - Do not use mermaid.js or any other auto-layout diagram library. Auto-layout produces
     mismatched fonts and arrows that cross unpredictably.
   - Build each diagram (architecture flow, ER diagram, pipeline, etc.) as a hand-coded
     inline `<svg viewBox="...">` with manually computed coordinates for every box and
     connector, so the layout is fully deterministic.
   - Style diagram boxes/text/links with CSS classes that reference the same root-level
     CSS variables used elsewhere on the page (e.g. `fill: var(--bg)`,
     `stroke: var(--accent)`, text using var(--ink)/var(--muted)), so diagrams
     automatically match the page's light/dark theme and typography — never hardcode
     hex colors or a different font inside the SVG.
   - Use SVG `<marker>` elements for arrowheads (`orient="auto-start-reverse"`) and
     orthogonal elbow-routed paths (`M...L...L...L...`) rather than straight diagonal
     lines, staggering bend heights to minimize line overlap.
   - Hard rule: no two connectors may share the same start point or the same end point.
     Every arrow must have its own distinct, separate entry and exit port on each box/
     entity — compute evenly spaced ports along each node's edge so it's always visually
     unambiguous which line goes where. Mark each port with a small dot
     (`<circle class="...-dot">`) where more than one line could plausibly be confused.
   - If a diagram box would get overcrowded with a long list (e.g. "all N table names"),
     don't cram the list into the box — show a short summary/count in the diagram and put
     the full itemized list in its own dedicated section elsewhere in the document, with
     a cross-reference pointer from the diagram.

5. CONTENT SOURCING
   - Every factual claim, number, table name, or metric in the report must be traceable to
     an actual file in this repository (source code, SQL, README, docs). Read the
     relevant source files before writing each section rather than inferring content.
   - Call out nuances found in source files even if not previously documented elsewhere
     (e.g. a table that looks like all others but is actually static, not incremental).

6. VERIFICATION
   - After each structural change (new section, diagram rewrite, CSS rule), open the file
     in a browser, check the console for errors, and take a screenshot of the affected
     area to confirm it renders as intended before moving on.

Ask me only the clarifying questions you need (e.g. local-file vs. sandboxed usage, full
narrative vs. executive summary) before you start, then build the report end to end.
```

---

## Notes for reuse

- Replace the bracketed `[DESCRIBE YOUR PROJECT / WHAT TO DOCUMENT]` line with the specific
  system/project you want documented.
- If the target report will be published through a Snowflake report-sharing sandbox instead
  of used as a local file, say so explicitly — that reintroduces the stricter sandbox rules
  (no CDN resources, `/libs/`-only vendored assets, meta provenance tags), which this prompt
  intentionally relaxes for the local-file case.
- Point the assistant at your own `sample.html`-equivalent design reference file; the prompt
  assumes one already exists in `docs/`.
