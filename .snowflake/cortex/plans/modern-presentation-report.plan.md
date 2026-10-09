## Plan: Modern presentation redesign of the hackathon report

### Goal
Produce a **new file**, `docs/hackathon-presentation.html`, containing the same end-to-end
narrative as `docs/hackathon-end-to-end-report.html`, but with a **completely different
visual design** — a clean, light, minimal, modern scrolling landing page suitable for
presenting live to the team. The original engineering-report file is left untouched.

### Why a new file
The user wants to "take the same report and apply a totally different design" — this is a
new presentation artifact, not an edit to the existing report. Keeping both files lets the
team use the detailed engineering report for reference and the new file for the live
walkthrough/demo.

### Confirmed direction (from user's answers)
- **Format:** Scrolling landing page (not slides, not a dashboard).
- **Aesthetic:** Clean light, minimal corporate — white/light surfaces, generous
  whitespace, restrained single accent color, Apple/Linear-style minimalism.
- **Depth:** Full content, redesigned — all 14 sections carried over, just re-skinned,
  not trimmed.

### New design system (distinct from sample.html)
- New CSS variable names/values so it reads as a genuinely different system (not just a
  palette swap of the old one): e.g. `--surface: #fff`, `--surface-alt: #f7f8fa`,
  `--text: #14181f`, `--text-soft: #5b6472`, `--accent: #2563eb` (or similar restrained
  blue), `--border: #e7e9ee`, success/warn/danger soft tints for pills/callouts.
- Typography: a cleaner modern sans pairing (e.g. a condensed display face for big
  headlines + a standard sans for body) — bundled as a self-contained font stack
  (system-ui / Segoe UI / Helvetica fallback chain) to avoid any CDN dependency, keeping
  the file fully local/offline-safe like the current report.
- Layout shell: hero section at top (big headline + sub-pitch + 3 KPI tiles), slim sticky
  top nav bar (not a left rail) with a scroll-progress bar, then full-width alternating
  background bands per section (white / very light gray) instead of a card grid inside a
  sidebar layout — this is the main structural change that makes it "look totally
  different" while presenting the same content.
- Tables: keep the vertical dotted (or thin solid, re-themed) column dividers concept but
  restyle borders/weights to match the new lighter aesthetic.
- Diagrams: reuse the existing hand-crafted SVG markup and coordinates (already verified
  to have distinct start/end ports and no mermaid dependency) from the current report,
  but repoint their CSS `var(--...)` references to the new design tokens so they visually
  match the new palette instead of redrawing geometry from scratch.

### Section-by-section mapping (content source → new design)
All content is carried over 1:1 from `docs/hackathon-end-to-end-report.html` (which itself
was sourced from README.md, SQL files, and docs/*.md) — no new facts are introduced, only
new presentation:

1. Hero (new) — headline + pitch + 3 KPI tiles (reuses Summary's top metrics)
2. Summary → KPI/stat band
3. The problem, in one table → problem table + governed-truth callout card
4. Architecture (as built) → re-skinned SVG flow diagram
5. Gold layer tables → re-skinned tables
6. Ontology & ER model → re-skinned SVG ER diagram + field tables
7. Semantic view & canonical metrics → cards/table
8. Multi-agent router & guardrails → cards/table
9. Deployed apps → cards
10. RBAC & governance → table
11. Marketplace enrichment & Workspace artifact → cards
12. Testing → table/checklist
13. Token & cost tracking → table
14. Current status & deferred work → status pills/checklist
15. Setup & demo → numbered steps
16. Appendix: repository structure → collapsible/code block

### Verification
After building the file: open in browser, confirm no console errors, and screenshot the
hero, one diagram section, and one table section to confirm the new look renders
correctly in light mode.
