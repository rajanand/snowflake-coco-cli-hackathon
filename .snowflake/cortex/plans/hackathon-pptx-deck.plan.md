---
name: "hackathon-pptx-deck"
created: "2026-09-27T18:07:38.859Z"
status: pending
---

## Goal

Produce `docs/hackathon-deck.pptx` — a complete, judge-ready presentation for the Snowflake CoCo CLI Hackathon submission ("Supply Chain Ontology & Governed Conversational Analytics"), built with **python-pptx**, using the visual design system studied from the slides.com reference deck (kicker labels, bold big headlines, alternating black/cream backgrounds, single blue accent progress bar, footer breadcrumb + page counter), with every fact sourced from files already in this repo.

## Design system

- **Colors:** background alternates pure black (`#0A0A0A`) ↔ off-white cream (`#F5F5F0`); text is white-on-black / near-black-on-cream; **one accent color**, blue (`#2D5BFF`), used only for the bottom progress bar, badge pills, and select highlight numbers.
- **Type:** bold sans (Arial/Arial Black — safest cross-platform fallback since we can't embed custom fonts reliably in a portable .pptx). Small tracked ALL-CAPS "kicker" label above every headline. Large bold headline (40–54pt). Body copy 14–16pt.
- **Footer convention on every slide:** bottom-left breadcrumb ("SUPPLY CHAIN ONTOLOGY"), bottom-right "N / 17" counter, thin blue bar along the very bottom edge sized to `page/total`.
- **Slide-type layouts to implement as functions:** title/cover; 2×2 stat-grid; 4/5-col card-grid; numbered list (ring-diagram style, simplified to numbered circles + text rows since no image assets); list+badge rows; scale/big-number comparison; split-panel closer.

## Slide-by-slide outline (17 slides, content sourced from repo files noted)

1. **Cover** (black) — Kicker "SNOWFLAKE COCO CLI HACKATHON 2026 — GCC EDITION". Title "Supply Chain Ontology & Governed Conversational Analytics". Subtitle: one governed semantic layer that gets Planning, Procurement, and Logistics to the same number. Footer tag: "100% synthetic data · built end-to-end with CoCo". *(Source: README.md title/intro)*

2. **The problem** (cream, 2×2 stat grid) — Kicker "THE PROBLEM". Headline "One question, five answers." Intro line from the challenge brief. Stats: **5** source systems / **4** divergent OTD answers / **0** shared definition / **1** governed truth. *(Source: README.md "problem, in one table")*

3. **Our approach** (black, architecture flow) — Kicker "OUR APPROACH". Headline "Ontology → Semantic View → Governed Answer." Horizontal 6-stage flow drawn with shapes: Source systems → Bronze → Silver (entity resolution) → Gold (dimensional model) → Semantic View → Agents/App. *(Source: README.md Architecture section, docs/architecture-and-er-diagram.html)*

4. **Genuine fragmentation, by design** (cream, 4-col card grid) — Kicker "PHASE 0 — SOURCE SYSTEMS". Cards: ERP (ship-confirm, excludes cancelled/backorder, 89.4%), TMS (2-day carrier buffer, 91.3%), Supplier Portal (drops in-transit, 78.6%), IoT Sensor (70% coverage, biased). *(Source: sql/00\_source\_schemas/README.md, README.md table)*

5. **Entity resolution** (black, key-facts list + big callout) — Kicker "PHASE 2 — SILVER". Headline "One shipment, four systems, one identity." Facts: 800/800 orders matched (100%), supplier identity cross-system match 800/800 (100%), IoT tracking match 560/800 (70.0%). Big callout: **100%** entity resolution. *(Source: sql/02\_silver/README.md)*

6. **The ontology** (cream, stat-grid + simplified entity chain) — Kicker "PHASE 3–4 — GOLD + SEMANTIC VIEW". Headline "9 entities, 10 relationships, 5 governed metrics." Entity chain row: Supplier → Part → Plant → Shipment → Order → Customer (mirrors the challenge brief's own example). Stat grid: 9 tables / 10 relationships / 5 metrics / 5 dimensions. *(Source: sql/04\_semantic\_view/README.md "Structural validation", docs/architecture-and-er-diagram.html ER section)*

7. **Canonical metrics & governance decisions** (black, list+badge rows) — Kicker "GOVERNANCE". Headline "Business meaning, not column names." 5 rows: On-Time Delivery / Customer Fill Rate / Supplier Fill Rate / Days of Inventory / Landed Cost per Unit — each with its formula, governance-decision one-liner, and validated value (64.875%, 90.8%, 86.294%, 48.60 days, $251.68). *(Source: sql/04\_semantic\_view/README.md metric table)*

8. **Legacy vs. governed** (cream, scale/big-number comparison) — Kicker "THE PROOF". Headline "Stricter, not just different." Big-number row: ERP 89.4 / TMS 91.3 / Portal 78.6 / **Governed 64.875**. Secondary rows for Fill Rate, DOI, Landed Cost divergence. Callout: governed OTD is lower than every legacy answer — closes loopholes, doesn't split the difference. *(Source: sql/10\_workspace\_artifact/README.md, sql/00\_source\_schemas/README.md)*

9. **Governed conversational analytics** (black, numbered list) — Kicker "PHASE 5 — MULTI-AGENT ROUTER". Headline "One router, four specialist agents." Numbered rows: 1 CortexAnalystClient (semantic view Q\&A), 2 SimulationAgent (what-if), 3 EvidenceTraceAgent (root cause), 4 DocumentQAAgent (contracts) — behind a 5-intent classifier. *(Source: agents/agent\_router.py class structure)*

10. **Guardrails that make it trustworthy** (cream, card grid) — Kicker "GOVERNANCE JUDGING CRITERION". Headline "Fails safely, never fabricates." Cards: constrained SQL for high-stakes intents / semantic-vocabulary lock (synonyms+comments) / PreQueryValidator (length, forbidden terms) / confidence threshold 0.6 fallback / PostQueryEnricher evidence grounding / try/except fallback everywhere. *(Source: docs/hackathon-review-human.md §8)*

11. **Cross-persona proof** (black, Q\&A/quiz-style grid) — Kicker "CHALLENGE REQUIREMENT". Headline "Same question, different words, same number." Planning / Procurement / Logistics ask OTD differently → all resolve to 64.875% + same base\_table/measure\_name. Honest caveat line: golden-test suite 2/5 passing, disclosed REST auth gap (not a metric-logic problem). *(Source: docs/hackathon-review-human.md §2.4, tests/test\_golden\_questions.py docstring)*

12. **The Governed Answer Engine app** (cream, placeholder mockup box) — Kicker "PHASE 7 — STREAMLIT IN SNOWFLAKE, CONTAINER RUNTIME". Headline "Ungoverned vs. Governed, live." Labeled dashed-border placeholder box: "\[Insert screenshot: Ungoverned/Governed toggle + sidebar trace log]" plus caption bullets (persona chips per metric, 4-step trace: Understand→Scope→SQL→Answer). *(Source: app/streamlit\_app.py, memory governed-answer-engine-app)*

13. **Document intelligence** (black, small feature slide) — Kicker "UNSTRUCTURED DATA". Headline "Contracts become queryable evidence." Pipeline: PDF → AI\_PARSE\_DOCUMENT → Cortex Search → DocumentQAAgent. Validated example: "Does SUP-0002's contract have a late-delivery penalty?" → 2%/day capped at 15%, cosine similarity 0.60. *(Source: sql/04\_semantic\_view/README.md "Document intelligence")*

14. **Platform rigor** (cream, 3-col card grid) — Kicker "GOVERNANCE & TRUST". Headline "Least privilege, real external data, real cost discipline." Cards: RBAC negative test (CREATE TABLE denied under read-only role) / Marketplace weather enrichment (Pelmorex Frostbyte, honest null-result disclosure) / Workspace artifact (legacy queries published, not just a .sql file). *(Source: sql/07\_rbac/README.md, sql/08\_marketplace\_enrichment/README.md, sql/10\_workspace\_artifact/README.md)*

15. **CoCo across the full lifecycle** (black, checklist table) — Kicker "HOW THIS WAS BUILT". Headline "CoCo end-to-end: plan → build → run → validate." Planning (8 dated plan files, 2026-09-12 → 2026-09-23) / Development (SQL+Python across 5 phases, 29 commits) / Execution (28 Dynamic Tables, ops pause/resume scripts, real 30-day cost: 8.79 credits) / Testing (golden-question suite, disclosed 2/5, honest not hidden). *(Source: .snowflake/cortex/plans + .cortex/plans file list, git log, docs/token-and-cost-tracking.md)*

16. **Ingenuity + honest roadmap** (cream, done-vs-deferred 2-col) — Kicker "ROADMAP". Headline "Built, and what's honestly still ahead." Done: custom tools/function calling, multi-agent orchestration, layered guardrails, RBAC split, Marketplace + Workspace artifacts. Deferred by explicit decision (not oversight): skills packaging, MCP connectors, Tasks/automation + alerting — with the stated reason (no External Access Integration on this trial account). *(Source: docs/pending-gaps.md, docs/hackathon-review-human.md §5–6)*

17. **Close** (black, split-panel) — Kicker "JUDGING FOCUS". Headline "Real-world relevance. Technical execution. Solution completeness." Three columns mapping each judging dimension to its strongest piece of evidence (genuine multi-system fragmentation / full medallion+agent+app stack / ontology-to-app completeness with disclosed gaps). Closing line/CTA: "Ask it three ways. Get one answer."

## Build approach

- New file: `docs/build_hackathon_deck.py` — a single script using `python-pptx` (`pip install python-pptx` first if not present; confirmed not currently installed).
- 16:9 slide size (13.333 × 7.5 in). Helper functions for the design tokens and each slide-type layout, then one function per slide (17 total) calling those helpers with the content above.
- No external image assets — all visuals (stat grids, card grids, numbered lists, flow diagrams, the placeholder box) are drawn with native pptx shapes/textboxes/lines so the deck is fully self-contained and portable.
- Output: `docs/hackathon-deck.pptx`.

## Verification

- Re-open the generated file with `python-pptx` to confirm 17 slides parse without error, and report final slide count + file size to the user.
- Spot-check 2–3 rendered slides by taking a look at generated XML/shape count sanity (no crash), since we can't visually render pptx directly in this tool — call out to the user that they should do a final visual pass in PowerPoint before submission.
